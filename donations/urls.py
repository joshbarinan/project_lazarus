from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    
    # PayMongo endpoints
    path('create-paymongo-payment/', views.create_paymongo_payment, name='create_paymongo'),
    path('report-qr-payment/', views.report_qr_payment, name='report_qr'),
    
    # PayPal endpoints
    path('create-paypal-order/', views.create_paypal_order, name='create_paypal'),
    path('paypal-success/', views.paypal_success, name='paypal_success'),
    path('paypal-webhook/', views.paypal_webhook, name='paypal_webhook'),
    
    # Shared endpoints
    path('success/', views.payment_success, name='success'),
    path('webhook/', views.payment_webhook, name='webhook'),
]