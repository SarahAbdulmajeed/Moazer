from django.contrib import admin
from .models import Plan, Wallet, UsageLog, SubscriptionPurchase

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "attempts", "price_sar")
    search_fields = ("name",)

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "total_attempts")
    search_fields = ("user__username",)

@admin.register(UsageLog)
class UsageLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "product_code", "amount", "created_at")
    search_fields = ("user__username", "product_code")

@admin.register(SubscriptionPurchase)
class SubscriptionPurchaseAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "plan", "invoice_id", "status", "granted", "amount_sar", "created_at")
    search_fields = ("invoice_id", "user__username")
    list_filter = ("status", "granted")