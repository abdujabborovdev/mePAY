# Django + Click to'lov

## Ishga tushirish

    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env            # qiymatlarni to'ldiring
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py runserver

- Kirish: `/accounts/login/`
- Balansni to'ldirish: `/topup/`
- Admin: `/admin/` (Wallet va Order jadvallari)
- Click webhook: `/click/webhook/`

## Click kabinetida (mc.click.uz -> СЕРВИСЫ -> ✏️)

Prepare URL va Complete URL ga bir xil manzil:

    https://SIZNING-SAYTINGIZ.uz/click/webhook/

Sayt HTTPS bo'lishi va internetdan ochiq turishi kerak.
`.env` dagi CLICK_SERVICE_ID / CLICK_MERCHANT_ID / CLICK_SECRET_KEY shu servisniki bo'lsin.

## "Sign check failed" (-1) chiqsa

Hamma so'rovlar `click_webhook.log` fayliga yoziladi. Imzo mos kelmasa, logda
Click yuborgan imzo va biz hisoblagan imzo ko'rinadi.

Click qo'llab-quvvatlashi yuborgan so'rovni tekshirish:

    python manage.py check_sign click_trans_id=3916408728 service_id=111209 merchant_trans_id=2 merchant_prepare_id=2 amount=1000 action=1 sign_time="2026-10-01 18:40:40" sign_string=470850eeea25b96a3dc6de4ef7710545

U "✅ MOS" yoki qaysi keng uchraydigan xato bo'lganini ko'rsatadi.

## Balansni ishlatish

    request.user.wallet.balance

Saytingizda allaqachon balans maydoni bo'lsa, `payments/views.py` dagi
"balansga qo'shish" qismini shunga moslang.
