from django.db import models


class Donation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('paymongo', 'PayMongo'),
        ('paypal', 'PayPal'),
        ('qrph', 'QRPH'),
        ('other', 'Other'),
    ]

    donor_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    proposed_name = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default='paymongo')
    payment_intent_id = models.CharField(max_length=255, blank=True)
    paypal_order_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_first_donation = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.donor_name or 'Anonymous'} – {self.amount} {self.payment_method}"
