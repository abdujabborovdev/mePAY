import hashlib

from django.conf import settings
from django.core.management.base import BaseCommand


def md5(*parts):
    return hashlib.md5("".join(str(p) for p in parts).encode()).hexdigest()


class Command(BaseCommand):
    help = (
        "Click yuborgan so'rovning imzosini tekshiradi.\n"
        "Misol:\n"
        "python manage.py check_sign click_trans_id=123 service_id=111 merchant_trans_id=2 "
        "merchant_prepare_id=2 amount=1000 action=1 sign_time='2026-10-01 18:40:40' sign_string=abc..."
    )

    def add_arguments(self, parser):
        parser.add_argument("pairs", nargs="+", help="kalit=qiymat juftliklari")

    def handle(self, *args, **opts):
        p = {}
        for item in opts["pairs"]:
            k, _, v = item.partition("=")
            p[k] = v

        secret = settings.CLICK_SECRET_KEY.strip()
        cid, sid = p["click_trans_id"], p["service_id"]
        mtid, amount = p["merchant_trans_id"], p["amount"]
        action, st = p["action"], p["sign_time"]
        pid = p.get("merchant_prepare_id", "")
        given = p["sign_string"]

        variants = {"TO'G'RI formula": (
            md5(cid, sid, secret, mtid, amount, action, st)
            if action == "0"
            else md5(cid, sid, secret, mtid, pid, amount, action, st)
        )}
        if action == "1":
            variants["prepare_id tushib qolgan (keng uchraydigan xato)"] = md5(cid, sid, secret, mtid, amount, action, st)
        try:
            as_float = str(float(amount))
            variants[f"amount float bo'lib ketgan ({as_float})"] = md5(
                cid, sid, secret, mtid, *( [pid] if action == "1" else [] ), as_float, action, st
            )
        except ValueError:
            pass

        self.stdout.write(f"Click yuborgan imzo : {given}")
        self.stdout.write(f"Kalit uzunligi      : {len(secret)} belgi")
        for name, value in variants.items():
            mark = "✅ MOS" if value == given else "❌"
            self.stdout.write(f"{mark}  {name}: {value}")
