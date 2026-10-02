import hashlib
import hmac
import logging
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Order, Wallet

log = logging.getLogger("click")

MIN_AMOUNT = 1_000
MAX_AMOUNT = 10_000_000

# Click xato kodlari
OK = 0
SIGN_FAILED = -1
INVALID_AMOUNT = -2
ACTION_NOT_FOUND = -3
ALREADY_PAID = -4
ORDER_NOT_FOUND = -5
TRANSACTION_NOT_FOUND = -6
REQUEST_ERROR = -8
CANCELLED = -9


# ------------------------------------------------------------------
# Yordamchi funksiyalar
# ------------------------------------------------------------------
def _md5(*parts) -> str:
    return hashlib.md5("".join(str(p) for p in parts).encode()).hexdigest()


def _num(value):
    return int(value) if str(value).isdigit() else value


def _reply(code, note, click_trans_id="", merchant_trans_id="", **extra):
    return JsonResponse(
        {
            "click_trans_id": _num(click_trans_id),
            "merchant_trans_id": merchant_trans_id,
            "error": code,
            "error_note": note,
            **extra,
        }
    )


def _amount_ok(raw, order) -> bool:
    try:
        return Decimal(raw) == Decimal(order.amount)
    except InvalidOperation:
        return False


def build_pay_url(order: Order) -> str:
    params = {
        "service_id": settings.CLICK_SERVICE_ID,
        "merchant_id": settings.CLICK_MERCHANT_ID,
        "amount": order.amount,
        "transaction_param": order.id,  # webhookda merchant_trans_id bo'lib qaytadi
        "return_url": settings.SITE_URL.rstrip("/") + "/topup/",
    }
    return "https://my.click.uz/services/pay?" + urlencode(params)


# ------------------------------------------------------------------
# Balansni to'ldirish sahifasi
# ------------------------------------------------------------------
@login_required
def topup(request):
    error = None

    if request.method == "POST":
        raw = request.POST.get("amount", "").replace(" ", "")
        amount = int(raw) if raw.isdigit() else 0

        if not (MIN_AMOUNT <= amount <= MAX_AMOUNT):
            error = f"Summa {MIN_AMOUNT:,} dan {MAX_AMOUNT:,} so'mgacha bo'lishi kerak.".replace(",", " ")
        else:
            order = Order.objects.create(user=request.user, amount=amount)
            return redirect(build_pay_url(order))

    wallet = Wallet.objects.filter(user=request.user).first()
    orders = Order.objects.filter(user=request.user).order_by("-id")[:10]
    return render(
        request,
        "payments/topup.html",
        {"balance": wallet.balance if wallet else 0, "orders": orders, "error": error},
    )


# ------------------------------------------------------------------
# Click webhook (Prepare va Complete bitta URL'da)
# ------------------------------------------------------------------
@csrf_exempt
@require_POST
def click_webhook(request):
    p = request.POST

    try:
        click_trans_id = p["click_trans_id"]
        service_id = p["service_id"]
        merchant_trans_id = p["merchant_trans_id"]
        amount = p["amount"]
        action = p["action"]
        sign_time = p["sign_time"]
        sign_string = p["sign_string"]
        error = int(p.get("error", 0))
    except (KeyError, ValueError):
        return _reply(REQUEST_ERROR, "Error in request from click")

    prepare_id = p.get("merchant_prepare_id", "")
    secret = settings.CLICK_SECRET_KEY.strip()
    ids = (click_trans_id, merchant_trans_id)
    log.info("Click so'rovi: %s", dict(p))

    if str(service_id) != str(settings.CLICK_SERVICE_ID):
        return _reply(REQUEST_ERROR, "Unknown service", *ids)

    # --- imzoni tekshirish ---
    if action == "0":
        expected = _md5(click_trans_id, service_id, secret, merchant_trans_id, amount, action, sign_time)
    elif action == "1":
        expected = _md5(click_trans_id, service_id, secret, merchant_trans_id, prepare_id, amount, action, sign_time)
    else:
        return _reply(ACTION_NOT_FOUND, "Action not found", *ids)

    if not hmac.compare_digest(expected, sign_string):
        log.warning(
            "IMZO MOS KELMADI | action=%s | Click yuborgan=%s | biz hisoblagan=%s | "
            "service_id=%s (sozlamada: %s) | kalit uzunligi=%s",
            action, sign_string, expected, service_id, settings.CLICK_SERVICE_ID, len(secret),
        )
        return _reply(SIGN_FAILED, "SIGN CHECK FAILED!", *ids)

    try:
        order_id = int(merchant_trans_id)
    except ValueError:
        return _reply(ORDER_NOT_FOUND, "Order not found", *ids)

    with transaction.atomic():
        order = Order.objects.select_for_update().filter(pk=order_id).first()

        # ================= PREPARE (action = 0) =================
        if action == "0":
            if order is None:
                return _reply(ORDER_NOT_FOUND, "Order not found", *ids)
            if not _amount_ok(amount, order):
                return _reply(INVALID_AMOUNT, "Incorrect parameter amount", *ids)
            if order.status == Order.Status.PAID:
                return _reply(ALREADY_PAID, "Already paid", *ids)
            if order.status == Order.Status.CANCELLED:
                return _reply(CANCELLED, "Transaction cancelled", *ids)

            order.status = Order.Status.PREPARED
            order.click_trans_id = str(click_trans_id)
            order.click_paydoc_id = p.get("click_paydoc_id", "")
            order.save(update_fields=["status", "click_trans_id", "click_paydoc_id"])
            return _reply(OK, "Success", *ids, merchant_prepare_id=order.id)

        # ================= COMPLETE (action = 1) =================
        if (
            order is None
            or prepare_id != str(order.id)
            or order.click_trans_id != str(click_trans_id)
        ):
            return _reply(TRANSACTION_NOT_FOUND, "Transaction does not exist", *ids)
        if not _amount_ok(amount, order):
            return _reply(INVALID_AMOUNT, "Incorrect parameter amount", *ids)
        if order.status == Order.Status.PAID:
            return _reply(ALREADY_PAID, "Already paid", *ids)
        if order.status == Order.Status.CANCELLED:
            return _reply(CANCELLED, "Transaction cancelled", *ids)

        if error < 0:  # Click to'lovni bekor qildi
            order.status = Order.Status.CANCELLED
            order.save(update_fields=["status"])
            return _reply(CANCELLED, "Transaction cancelled", *ids)

        # --- balansga qo'shish ---
        wallet, _ = Wallet.objects.select_for_update().get_or_create(user_id=order.user_id)
        wallet.balance += order.amount
        wallet.save(update_fields=["balance"])

        order.status = Order.Status.PAID
        order.paid_at = timezone.now()
        order.save(update_fields=["status", "paid_at"])

        return _reply(OK, "Success", *ids, merchant_confirm_id=order.id)
