from django.conf import settings
from django.db import models


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet"
    )
    balance = models.BigIntegerField(default=0)

    def __str__(self):
        return f"{self.user} — {self.balance} so'm"


class Order(models.Model):

    class Status(models.TextChoices):
        NEW = "new", "Yangi"
        PREPARED = "prepared", "Tekshirildi"
        PAID = "paid", "To'langan"
        CANCELLED = "cancelled", "Bekor qilingan"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders"
    )
    amount = models.PositiveBigIntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW, db_index=True
    )
    click_trans_id = models.CharField(max_length=64, blank=True, default="")
    click_paydoc_id = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Order #{self.pk} — {self.amount} so'm — {self.status}"
