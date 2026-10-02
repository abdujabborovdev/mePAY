from django.contrib import admin

from .models import Order, Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance")
    search_fields = ("user__username",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "status", "click_trans_id", "created_at", "paid_at")
    list_filter = ("status",)
    search_fields = ("user__username", "click_trans_id")
