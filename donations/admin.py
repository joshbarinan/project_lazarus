from django.contrib import admin
from .models import Donation


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('donor_name', 'email', 'amount', 'payment_method', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'is_first_donation')
    search_fields = ('donor_name', 'email', 'payment_intent_id', 'paypal_order_id')
