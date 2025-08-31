from django.contrib import admin
from .models import Plan, Wallet, UsageLog
admin.site.register(Plan)
admin.site.register(Wallet)
admin.site.register(UsageLog)