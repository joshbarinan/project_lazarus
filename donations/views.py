import json
import base64
import requests
import logging
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.db import models

from .models import Donation

# Set up logging
logger = logging.getLogger(__name__)

def index(request):
    try:
        total_donations = Donation.objects.filter(status='paid').aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        donation_count = Donation.objects.filter(status='paid').count()
        first_donor = Donation.objects.filter(is_first_donation=True, status='paid').first()
        
        milestones = [
            {'amount': 5000, 'title': '💀 The Domain Awakens', 'desc': 'Mysterious domain name acquired (₱5,000)', 'unlocked': total_donations >= 5000},
            {'amount': 20000, 'title': '🔮 Azure Portal Opens', 'desc': 'Migration to Azure cloud begins (₱20,000)', 'unlocked': total_donations >= 20000},
            {'amount': 50000, 'title': '🤖 AI Entity Summoned', 'desc': 'Dark AI integrated into the system (₱50,000)', 'unlocked': total_donations >= 50000},
            {'amount': 100000, 'title': '🌐 The Gateway Opens', 'desc': 'Full public launch with all features (₱100,000)', 'unlocked': total_donations >= 100000},
        ]
        
        upcoming = [
            '⚡ Quantum database encryption',
            '🎮 Play-to-earn mini-games',
            '🕯️ Anonymous chat with the developer',
            '🔮 AI-powered fortune telling',
            '💀 Leaderboard of the chosen ones',
        ]
        
        if total_donations < 5000:
            mystery_level = 'FROZEN'
            mystery_desc = 'The project slumbers in the void... waiting for a spark'
        elif total_donations < 20000:
            mystery_level = 'AWAKENING'
            mystery_desc = 'Whispers of code echo through the darkness'
        elif total_donations < 50000:
            mystery_level = 'EVOLVING'
            mystery_desc = 'The entity begins to take form'
        elif total_donations < 100000:
            mystery_level = 'ASCENDING'
            mystery_desc = 'Reality bends around the growing power'
        else:
            mystery_level = 'TRANSCENDED'
            mystery_desc = 'The project has achieved godhood'
        
        context = {
            'paymongo_public_key': settings.PAYMONGO_PUBLIC_KEY,
            'paypal_client_id': settings.PAYPAL_CLIENT_ID,
            'total_donations': float(total_donations),
            'donation_count': donation_count,
            'first_donor': first_donor,
            'milestones': milestones,
            'upcoming': upcoming,
            'mystery_level': mystery_level,
            'mystery_desc': mystery_desc,
        }
        return render(request, 'donations/index.html', context)
    except Exception as e:
        logger.error(f"Error in index view: {e}")
        context = {
            'paymongo_public_key': settings.PAYMONGO_PUBLIC_KEY,
            'paypal_client_id': settings.PAYPAL_CLIENT_ID,
            'total_donations': 0,
            'donation_count': 0,
            'first_donor': None,
            'milestones': [],
            'upcoming': [],
            'mystery_level': 'ERROR',
            'mystery_desc': 'The entity is confused... try again',
        }
        return render(request, 'donations/index.html', context)

# ============ PAYMONGO FUNCTIONS ============
@csrf_exempt
def create_paymongo_payment(request):
    if request.method == 'POST':
        try:
            # Log the raw request for debugging
            logger.info(f"PayMongo request body: {request.body}")
            
            data = json.loads(request.body)
            amount = int(float(data.get('amount', 100)) * 100)  # Convert to centavos
            proposed_name = data.get('proposed_name', '')
            
            request.session['proposed_name'] = proposed_name
            request.session['donation_amount'] = amount / 100
            request.session['payment_method'] = 'paymongo'
            
            auth = base64.b64encode(f"{settings.PAYMONGO_SECRET_KEY}:".encode()).decode()
            
            payload = {
                "data": {
                    "attributes": {
                        "amount": amount,
                        "payment_method_allowed": ["card", "gcash", "grab_pay"],
                        "payment_method_options": {
                            "card": {
                                "request_three_d_secure": "automatic"
                            }
                        },
                        "description": f"Project Lazarus - {proposed_name or 'Anonymous'}",
                        "currency": "PHP",
                        "capture_type": "automatic",
                        "statement_descriptor": "LAZARUS DEV",
                        "metadata": {
                            "proposed_name": proposed_name
                        }
                    }
                }
            }
            
            response = requests.post(
                'https://api.paymongo.com/v1/payment_intents',
                json=payload,
                headers={
                    'Authorization': f'Basic {auth}',
                    'Content-Type': 'application/json'
                },
                timeout=30
            )
            
            logger.info(f"PayMongo response status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                result = response.json()
                return JsonResponse({
                    'payment_intent_id': result['data']['id'],
                    'client_key': result['data']['attributes']['client_key']
                })
            else:
                logger.error(f"PayMongo error response: {response.text}")
                return JsonResponse({'error': 'Payment service error'}, status=400)
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in PayMongo: {e}")
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(f"Error in create_paymongo_payment: {e}")
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

# ============ PAYPAL FUNCTIONS ============
def get_paypal_access_token():
    """Get PayPal access token"""
    try:
        auth = base64.b64encode(f"{settings.PAYPAL_CLIENT_ID}:{settings.PAYPAL_CLIENT_SECRET}".encode()).decode()
        
        url = f"{settings.PAYPAL_API_BASE}/v1/oauth2/token"
        
        response = requests.post(
            url,
            data={'grant_type': 'client_credentials'},
            headers={
                'Authorization': f'Basic {auth}',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            timeout=30
        )
        
        logger.info(f"PayPal token response status: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()['access_token']
        else:
            logger.error(f"PayPal token error: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error getting PayPal token: {e}")
        return None

@csrf_exempt
def create_paypal_order(request):
    """Create PayPal order"""
    if request.method == 'POST':
        try:
            # Log the raw request
            logger.info(f"PayPal request body: {request.body}")
            
            # Parse JSON data
            data = json.loads(request.body)
            amount = float(data.get('amount', 100))
            proposed_name = data.get('proposed_name', '')
            
            logger.info(f"Creating PayPal order for amount: {amount}, name: {proposed_name}")
            
            # Store in session
            request.session['proposed_name'] = proposed_name
            request.session['donation_amount'] = amount
            request.session['payment_method'] = 'paypal'
            
            # Get PayPal access token
            access_token = get_paypal_access_token()
            if not access_token:
                logger.error("Failed to get PayPal access token")
                return JsonResponse({'error': 'Could not authenticate with PayPal'}, status=400)
            
            url = f"{settings.PAYPAL_API_BASE}/v2/checkout/orders"
            
            payload = {
                "intent": "CAPTURE",
                "purchase_units": [{
                    "amount": {
                        "currency_code": "PHP",
                        "value": f"{amount:.2f}"
                    },
                    "description": f"Project Lazarus Donation - {proposed_name or 'Anonymous'}",
                    "custom_id": proposed_name or "anonymous"
                }],
                "application_context": {
                    "brand_name": "Project Lazarus",
                    "landing_page": "BILLING",
                    "user_action": "PAY_NOW",
                    "return_url": f"{request.build_absolute_uri('/paypal-success/')}",
                    "cancel_url": f"{request.build_absolute_uri('/')}"
                }
            }
            
            logger.info(f"PayPal payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                url,
                json=payload,
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                timeout=30
            )
            
            logger.info(f"PayPal order response status: {response.status_code}")
            logger.info(f"PayPal order response: {response.text}")
            
            if response.status_code == 201:
                result = response.json()
                
                # Create pending donation record
                donation = Donation.objects.create(
                    donor_name='Pending PayPal',
                    email='pending@paypal.com',
                    amount=amount,
                    payment_method='paypal',
                    payment_intent_id=result['id'],
                    proposed_name=proposed_name,
                    status='pending',
                    paypal_order_id=result['id']
                )
                
                logger.info(f"Created donation record with ID: {donation.id}")
                
                # Find approval URL
                approval_url = None
                for link in result['links']:
                    if link['rel'] == 'approve':
                        approval_url = link['href']
                        break
                
                if approval_url:
                    return JsonResponse({'approval_url': approval_url})
                else:
                    logger.error("No approval URL found in PayPal response")
                    return JsonResponse({'error': 'No approval URL found'}, status=400)
            else:
                logger.error(f"PayPal API error: {response.text}")
                return JsonResponse({'error': f'PayPal API error: {response.status_code}'}, status=400)
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in PayPal: {e}")
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(f"Error in create_paypal_order: {e}")
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@csrf_exempt
def paypal_success(request):
    """Handle PayPal success callback"""
    order_id = request.GET.get('token')
    payer_id = request.GET.get('PayerID')
    
    logger.info(f"PayPal success callback - Order ID: {order_id}, Payer ID: {payer_id}")
    
    if not order_id:
        logger.error("No order_id in PayPal success callback")
        return redirect('/')
    
    try:
        # Get access token
        access_token = get_paypal_access_token()
        if not access_token:
            logger.error("Failed to get access token in success callback")
            return redirect('/')
        
        # Capture the PayPal order
        url = f"{settings.PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture"
        
        response = requests.post(
            url,
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            timeout=30
        )
        
        logger.info(f"PayPal capture response status: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            
            if result['status'] == 'COMPLETED':
                # Update donation record
                donation = Donation.objects.filter(paypal_order_id=order_id).first()
                
                if donation:
                    # Check if this is the first donation
                    is_first = Donation.objects.filter(status='paid').count() == 0
                    
                    donation.status = 'paid'
                    donation.donor_name = 'PayPal Donor'
                    donation.email = 'paypal@donor.com'
                    donation.is_first_donation = is_first
                    donation.save()
                    
                    total = Donation.objects.filter(status='paid').aggregate(
                        total=models.Sum('amount')
                    )['total'] or 0
                    
                    logger.info(f"Payment completed for donation {donation.id}")
                    
                    return render(request, 'donations/success.html', {
                        'donation': donation,
                        'total_raised': float(total),
                        'is_first_donor': is_first,
                        'payment_method': 'PayPal'
                    })
                else:
                    logger.error(f"No donation found for order_id: {order_id}")
        
        return redirect('/')
        
    except Exception as e:
        logger.error(f"Error in paypal_success: {e}")
        return redirect('/')

@csrf_exempt
def paypal_webhook(request):
    """Handle PayPal webhook events"""
    return JsonResponse({'status': 'ok'})

# ============ SHARED FUNCTIONS ============
@require_http_methods(['GET'])
def payment_success(request):
    payment_intent_id = request.GET.get('payment_intent_id')
    
    if not payment_intent_id:
        return redirect('/')
    
    try:
        auth = base64.b64encode(f"{settings.PAYMONGO_SECRET_KEY}:".encode()).decode()
        
        response = requests.get(
            f'https://api.paymongo.com/v1/payment_intents/{payment_intent_id}',
            headers={'Authorization': f'Basic {auth}'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            status = result['data']['attributes']['status']
            amount = result['data']['attributes']['amount'] / 100
            
            if status == 'succeeded':
                is_first = Donation.objects.filter(status='paid').count() == 0
                proposed_name = request.session.get('proposed_name', '')
                
                donation = Donation.objects.create(
                    donor_name='Anonymous Donor',
                    email='anonymous@donor.com',
                    amount=amount,
                    payment_method='paymongo',
                    payment_intent_id=payment_intent_id,
                    is_first_donation=is_first,
                    proposed_name=proposed_name,
                    status='paid'
                )
                
                total = Donation.objects.filter(status='paid').aggregate(
                    total=models.Sum('amount')
                )['total'] or 0
                
                request.session.flush()
                
                return render(request, 'donations/success.html', {
                    'donation': donation,
                    'total_raised': float(total),
                    'is_first_donor': is_first,
                    'payment_method': 'PayMongo'
                })
        
        return redirect('/')
        
    except Exception as e:
        logger.error(f"Error in payment_success: {e}")
        return redirect('/')

@csrf_exempt
def payment_webhook(request):
    """Handle webhook events from both PayMongo and PayPal"""
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def report_qr_payment(request):
    """Handle manual QRPh payment reports"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Create pending donation for manual verification
            donation = Donation.objects.create(
                donor_name='Manual QR Payment',
                email='manual@qrph.com',
                amount=data.get('amount', 0),
                payment_method='qrph',
                payment_intent_id=data.get('reference_code', ''),
                proposed_name=data.get('proposed_name', ''),
                status='pending'
            )
            
            return JsonResponse({'success': True, 'donation_id': donation.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)