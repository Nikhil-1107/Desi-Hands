"""
Checkout views for DesiHands — Address → Payment → Confirmation flow.
"""

import json
import uuid

import razorpay
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt

from .models import Cart, Order, OrderItem, Product
from .views import get_logged_in_registration, registration_login_required


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_order_id():
    """Generate a short, unique order ID like DH-XXXXXXXX."""
    return "DH-" + uuid.uuid4().hex[:8].upper()


def _get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


# ---------------------------------------------------------------------------
# Step 1 — Checkout Address
# ---------------------------------------------------------------------------

@registration_login_required
def checkout_address_view(request):
    """
    Displays shipping address form.
    On POST, stores the address in the session and proceeds to payment.
    """
    user = get_logged_in_registration(request)
    cart_items = (
        Cart.objects.filter(user=user)
        .select_related("product", "product__category")
        .order_by("-added_at")
    )

    if not cart_items.exists():
        messages.info(request, "Your cart is empty.")
        return redirect("core:cart")

    grand_total = Cart.calculate_grand_total(cart_items)
    total_quantity = sum(item.quantity for item in cart_items)

    if request.method == "POST":
        fullname = request.POST.get("fullname", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()
        pincode = request.POST.get("pincode", "").strip()

        errors = []
        if not fullname:
            errors.append("Full name is required.")
        if not phone:
            errors.append("Phone number is required.")
        if not address:
            errors.append("Address is required.")
        if not city:
            errors.append("City is required.")
        if not state:
            errors.append("State is required.")
        if not pincode:
            errors.append("Pincode is required.")

        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            request.session["checkout_address"] = {
                "fullname": fullname,
                "phone": phone,
                "address": address,
                "city": city,
                "state": state,
                "pincode": pincode,
            }
            return redirect("core:checkout_payment")

    # Pre-fill from user profile
    saved = request.session.get("checkout_address", {})
    context = {
        "cart_items": cart_items,
        "grand_total": grand_total,
        "total_quantity": total_quantity,
        "form_data": {
            "fullname": saved.get("fullname", user.fullname),
            "phone": saved.get("phone", user.mobile),
            "address": saved.get("address", user.address),
            "city": saved.get("city", user.city),
            "state": saved.get("state", user.state),
            "pincode": saved.get("pincode", user.pincode),
        },
    }
    return render(request, "core/checkout_address.html", context)


# ---------------------------------------------------------------------------
# Step 2 — Payment Method
# ---------------------------------------------------------------------------

@registration_login_required
def checkout_payment_view(request):
    """
    Choose between COD and Online (Razorpay).
    For online payment, creates a Razorpay order.
    """
    user = get_logged_in_registration(request)
    cart_items = (
        Cart.objects.filter(user=user)
        .select_related("product", "product__category")
        .order_by("-added_at")
    )

    if not cart_items.exists():
        messages.info(request, "Your cart is empty.")
        return redirect("core:cart")

    checkout_address = request.session.get("checkout_address")
    if not checkout_address:
        messages.error(request, "Please fill your shipping address first.")
        return redirect("core:checkout_address")

    grand_total = Cart.calculate_grand_total(cart_items)
    total_quantity = sum(item.quantity for item in cart_items)

    # Create a Razorpay order (amount in paise)
    razorpay_order = None
    try:
        client = _get_razorpay_client()
        razorpay_order = client.order.create({
            "amount": int(grand_total * 100),
            "currency": "INR",
            "payment_capture": "1",
        })
    except Exception:
        razorpay_order = None

    context = {
        "cart_items": cart_items,
        "grand_total": grand_total,
        "total_quantity": total_quantity,
        "checkout_address": checkout_address,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": razorpay_order["id"] if razorpay_order else "",
        "razorpay_amount": int(grand_total * 100),
        "user": user,
    }
    return render(request, "core/checkout_payment.html", context)


# ---------------------------------------------------------------------------
# COD Order Placement
# ---------------------------------------------------------------------------

@registration_login_required
def place_order_cod_view(request):
    """Handle Cash on Delivery order placement."""
    if request.method != "POST":
        return redirect("core:checkout_payment")

    user = get_logged_in_registration(request)
    cart_items = (
        Cart.objects.filter(user=user)
        .select_related("product")
        .order_by("-added_at")
    )

    if not cart_items.exists():
        messages.info(request, "Your cart is empty.")
        return redirect("core:cart")

    checkout_address = request.session.get("checkout_address")
    if not checkout_address:
        messages.error(request, "Please fill your shipping address first.")
        return redirect("core:checkout_address")

    grand_total = Cart.calculate_grand_total(cart_items)
    full_address = f"{checkout_address['address']}, {checkout_address['city']}, {checkout_address['state']} - {checkout_address['pincode']}"

    order = Order.objects.create(
        user=user,
        order_id=_generate_order_id(),
        total_amount=grand_total,
        shipping_address=full_address,
        shipping_city=checkout_address["city"],
        shipping_state=checkout_address["state"],
        shipping_pincode=checkout_address["pincode"],
        shipping_phone=checkout_address["phone"],
        payment_method="Cash on Delivery",
        is_paid=False,
        order_status=Order.STATUS_PENDING,
    )

    # Create order items & deduct stock
    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            product_name=item.product.product_name,
            unit_price=item.product.price,
            quantity=item.quantity,
            line_total=item.line_total,
        )
        item.product.stock -= item.quantity
        if item.product.stock <= 0:
            item.product.is_available = False
        item.product.save(update_fields=["stock", "is_available"])

    # Clear cart & session
    cart_items.delete()
    request.session.pop("checkout_address", None)

    messages.success(request, "Order placed successfully!")
    return redirect("core:order_confirmation", order_id=order.order_id)


# ---------------------------------------------------------------------------
# Razorpay Payment Verification (AJAX)
# ---------------------------------------------------------------------------

@csrf_exempt
def razorpay_payment_verify_view(request):
    """
    Verify Razorpay payment signature, create order, clear cart.
    Called via AJAX from the frontend after payment completion.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request."}, status=400)

    user_id = request.session.get("registration_id")
    if not user_id:
        return JsonResponse({"status": "error", "message": "Not logged in."}, status=403)

    from .models import Registration
    user = Registration.objects.filter(pk=user_id).first()
    if not user:
        return JsonResponse({"status": "error", "message": "User not found."}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON."}, status=400)

    razorpay_payment_id = data.get("razorpay_payment_id", "")
    razorpay_order_id = data.get("razorpay_order_id", "")
    razorpay_signature = data.get("razorpay_signature", "")

    if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
        return JsonResponse({"status": "error", "message": "Missing payment data."}, status=400)

    # Verify signature
    client = _get_razorpay_client()
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({"status": "error", "message": "Payment verification failed."}, status=400)

    # Payment is verified — create the order
    cart_items = (
        Cart.objects.filter(user=user)
        .select_related("product")
        .order_by("-added_at")
    )

    if not cart_items.exists():
        return JsonResponse({"status": "error", "message": "Cart is empty."}, status=400)

    checkout_address = request.session.get("checkout_address", {})
    grand_total = Cart.calculate_grand_total(cart_items)
    full_address = f"{checkout_address.get('address', '')}, {checkout_address.get('city', '')}, {checkout_address.get('state', '')} - {checkout_address.get('pincode', '')}"

    order = Order.objects.create(
        user=user,
        order_id=_generate_order_id(),
        total_amount=grand_total,
        shipping_address=full_address,
        shipping_city=checkout_address.get("city", ""),
        shipping_state=checkout_address.get("state", ""),
        shipping_pincode=checkout_address.get("pincode", ""),
        shipping_phone=checkout_address.get("phone", ""),
        payment_method="Online (Razorpay)",
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_signature=razorpay_signature,
        is_paid=True,
        order_status=Order.STATUS_CONFIRMED,
    )

    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            product_name=item.product.product_name,
            unit_price=item.product.price,
            quantity=item.quantity,
            line_total=item.line_total,
        )
        item.product.stock -= item.quantity
        if item.product.stock <= 0:
            item.product.is_available = False
        item.product.save(update_fields=["stock", "is_available"])

    cart_items.delete()
    request.session.pop("checkout_address", None)

    return JsonResponse({
        "status": "success",
        "order_id": order.order_id,
        "redirect_url": f"/order-confirmation/{order.order_id}/",
    })


# ---------------------------------------------------------------------------
# Order Confirmation
# ---------------------------------------------------------------------------

@registration_login_required
def order_confirmation_view(request, order_id):
    """Show a beautiful order confirmation / thank you page."""
    user = get_logged_in_registration(request)
    order = get_object_or_404(Order, order_id=order_id, user=user)
    order_items = order.items.select_related("product").all()

    context = {
        "order": order,
        "order_items": order_items,
    }
    return render(request, "core/order_confirmation.html", context)
