import csv
from datetime import timedelta
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.http import HttpResponse, Http404
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext as _
from django.utils.translation import get_language
# Ensure `_` is always defined in this module.
# Django's i18n will provide translations when available; otherwise it's an identity.



from django.core.mail import send_mail
from .models import Registration, Category, Product, Order, OrderItem, Review, ContactMessage
from .forms import CategoryForm, ProductForm, RegistrationForm


def localized_order_status(status):
    return _(status)


def localized_bool_status(enabled, true_label, false_label):
    return _(true_label if enabled else false_label)

# ---------- Decorators ----------
def custom_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("is_admin_logged_in"):
            messages.error(request, _("Please login as admin to access this panel."))
            return redirect("core:admin_login")
        return view_func(request, *args, **kwargs)
    return wrapper

# ---------- Admin Auth Views ----------
def admin_login(request):
    if request.session.get("is_admin_logged_in"):
        return redirect("core:admin_dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # Authenticate against Django's built-in User table
        user = User.objects.filter(username=username).first()
        if user and (user.is_staff or user.is_superuser) and check_password(password, user.password):
            request.session["is_admin_logged_in"] = True
            request.session["admin_username"] = user.username
            messages.success(request, _("Logged in successfully to admin panel."))
            return redirect("core:admin_dashboard")
        
        messages.error(request, _("Invalid admin credentials or unauthorized account."))
    else:
        # Clear any lingering messages on GET request so they don't leak onto the admin login page.
        # Use a different loop variable name to avoid any accidental `_` shadowing.
        storage = messages.get_messages(request)
        for msg in storage:
            pass

    return render(request, "admin_panel/login.html")

def admin_logout(request):
    if "is_admin_logged_in" in request.session:
        del request.session["is_admin_logged_in"]
    if "admin_username" in request.session:
        del request.session["admin_username"]
    messages.success(request, _("Logged out successfully from admin panel."))
    return redirect("core:admin_login")

# ---------- Dashboard View ----------
@custom_admin_required
def admin_dashboard(request):
    # Stats
    total_users = Registration.objects.count()
    total_categories = Category.objects.count()
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    
    # Revenue should reflect paid orders. Online payments are paid before delivery,
    # while COD enters revenue only after the admin marks it as paid.
    paid_orders_qs = Order.objects.filter(is_paid=True)
    total_revenue = paid_orders_qs.aggregate(s=Sum("total_amount")).get("s") or 0
    total_revenue = float(total_revenue)

    # Order Status counts
    pending_orders = Order.objects.filter(order_status=Order.STATUS_PENDING).count()
    delivered_orders = Order.objects.filter(order_status=Order.STATUS_DELIVERED).count()
    cancelled_orders = Order.objects.filter(order_status=Order.STATUS_CANCELLED).count()

    # Time-based revenue calculations (paid orders)
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)
    year_start = today_start - timedelta(days=365)

    daily_revenue = float(paid_orders_qs.filter(created_at__gte=today_start).aggregate(s=Sum("total_amount")).get("s") or 0)
    weekly_revenue = float(paid_orders_qs.filter(created_at__gte=week_start).aggregate(s=Sum("total_amount")).get("s") or 0)
    monthly_revenue = float(paid_orders_qs.filter(created_at__gte=month_start).aggregate(s=Sum("total_amount")).get("s") or 0)
    yearly_revenue = float(paid_orders_qs.filter(created_at__gte=year_start).aggregate(s=Sum("total_amount")).get("s") or 0)

    # Recent activity lists
    latest_orders = Order.objects.select_related("user").order_by("-created_at")[:5]
    latest_users = Registration.objects.order_by("-created_at")[:5]
    latest_products = Product.objects.select_related("category").order_by("-created_at")[:5]

    # Chart.js Data
    # 1. Last 7 Days Orders & Revenue
    day_labels = []
    orders_values = []
    revenue_values = []
    for i in range(7):
        day_date = today_start - timedelta(days=6-i)
        day_end = day_date + timedelta(days=1)
        day_labels.append(day_date.strftime("%b %d"))

        orders_count = Order.objects.filter(created_at__gte=day_date, created_at__lt=day_end).count()
        orders_values.append(orders_count)

        revenue_sum = paid_orders_qs.filter(created_at__gte=day_date, created_at__lt=day_end).aggregate(s=Sum("total_amount")).get("s") or 0
        revenue_values.append(float(revenue_sum))

    # 2. Category Sales Distribution
    category_name_field = "product__category__name_hi" if get_language() == "hi" else "product__category__name_en"
    cat_sales = (
        OrderItem.objects.filter(order__is_paid=True)
        .values(category_name_field)
        .annotate(total_sales=Sum("line_total"))
        .order_by("-total_sales")
    )
    cat_labels = [c[category_name_field] or _("Unknown") for c in cat_sales]
    cat_values = [float(c["total_sales"] or 0) for c in cat_sales]


    # 3. Monthly Sales (Paid)
    monthly_sales_labels = []
    monthly_sales_values = []
    for i in range(6):
        month_date = today_start - timedelta(days=30*(5-i))
        m_start = month_date.replace(day=1)
        m_end = (m_start + timedelta(days=32)).replace(day=1)
        monthly_sales_labels.append(m_start.strftime("%B"))
        
        m_rev = paid_orders_qs.filter(created_at__gte=m_start, created_at__lt=m_end).aggregate(s=Sum("total_amount")).get("s") or 0
        monthly_sales_values.append(float(m_rev))

    context = {
        "stats": {
            "total_users": total_users,
            "total_categories": total_categories,
            "total_products": total_products,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "pending_orders": pending_orders,
            "delivered_orders": delivered_orders,
            "cancelled_orders": cancelled_orders,
            "daily_revenue": daily_revenue,
            "weekly_revenue": weekly_revenue,
            "monthly_revenue": monthly_revenue,
            "yearly_revenue": yearly_revenue,
        },
        "latest_orders": latest_orders,
        "latest_users": latest_users,
        "latest_products": latest_products,
        
        # Chart JSON arrays
        "day_labels": day_labels,
        "orders_values": orders_values,
        "revenue_values": revenue_values,
        "cat_labels": cat_labels,
        "cat_values": cat_values,
        "monthly_sales_labels": monthly_sales_labels,
        "monthly_sales_values": monthly_sales_values,
    }

    return render(request, "admin_panel/dashboard.html", context)

# ---------- Categories CRUD ----------
@custom_admin_required
def admin_category_list(request):
    query = request.GET.get("q", "").strip()
    categories_qs = Category.objects.annotate(prod_count=Count("products")).order_by("name_en")
    if query:
        categories_qs = categories_qs.filter(Q(name_en__icontains=query) | Q(name_hi__icontains=query))
    
    return render(request, "admin_panel/categories/list.html", {"categories": categories_qs, "query": query})

@custom_admin_required
def admin_category_add(request):
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _("Category added successfully."))
            return redirect("core:admin_category_list")
        messages.error(request, _("Please correct the errors below."))
    else:
        form = CategoryForm()
    return render(request, "admin_panel/categories/add.html", {"form": form})

@custom_admin_required
def admin_category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, _("Category updated successfully."))
            return redirect("core:admin_category_list")
        messages.error(request, _("Please correct the errors below."))
    else:
        form = CategoryForm(instance=category)
    return render(request, "admin_panel/categories/edit.html", {"form": form, "category": category})

@custom_admin_required
def admin_category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.delete()
    messages.success(request, _("Category deleted successfully."))
    return redirect("core:admin_category_list")

# ---------- Products CRUD ----------
@custom_admin_required
def admin_product_list(request):
    query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "")
    status_filter = request.GET.get("status", "")

    products_qs = Product.objects.select_related("category").order_by("-created_at")

    if query:
        products_qs = products_qs.filter(Q(product_name_en__icontains=query) | Q(product_name_hi__icontains=query) | Q(seller_name__icontains=query))
    if category_id:
        products_qs = products_qs.filter(category_id=category_id)
    if status_filter:
        if status_filter == "available":
            products_qs = products_qs.filter(is_available=True)
        elif status_filter == "unavailable":
            products_qs = products_qs.filter(is_available=False)

    categories = Category.objects.all()

    context = {
        "products": products_qs,
        "query": query,
        "categories": categories,
        "selected_category": category_id,
        "selected_status": status_filter,
    }
    return render(request, "admin_panel/products/list.html", context)

@custom_admin_required
def admin_product_add(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _("Product added successfully."))
            return redirect("core:admin_product_list")
        messages.error(request, _("Please correct the errors below."))
    else:
        form = ProductForm()
    return render(request, "admin_panel/products/add.html", {"form": form})

@custom_admin_required
def admin_product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, _("Product updated successfully."))
            return redirect("core:admin_product_list")
        messages.error(request, _("Please correct the errors below."))
    else:
        form = ProductForm(instance=product)
    return render(request, "admin_panel/products/edit.html", {"form": form, "product": product})

@custom_admin_required
def admin_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.success(request, _("Product deleted successfully."))
    return redirect("core:admin_product_list")

@custom_admin_required
def admin_product_toggle(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_available = not product.is_available
    product.save()
    messages.success(
        request,
        _("Product status updated to %(status)s.") % {
            "status": localized_bool_status(product.is_available, "Available", "Unavailable")
        },
    )
    return redirect("core:admin_product_list")

# ---------- User Management ----------
@custom_admin_required
def admin_user_list(request):
    query = request.GET.get("q", "").strip()
    users_qs = Registration.objects.all().order_by("-created_at")

    if query:
        users_qs = users_qs.filter(Q(fullname__icontains=query) | Q(email__icontains=query) | Q(mobile__icontains=query))

    return render(request, "admin_panel/users/list.html", {"users": users_qs, "query": query})

@custom_admin_required
def admin_user_add(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _("User added successfully."))
            return redirect("core:admin_user_list")
        messages.error(request, _("Please correct the errors below."))
    else:
        form = RegistrationForm()

    return render(request, "admin_panel/users/add.html", {"form": form})

@custom_admin_required
def admin_user_details(request, pk):
    user_obj = get_object_or_404(Registration, pk=pk)
    orders = Order.objects.filter(user=user_obj).order_by("-created_at")
    return render(request, "admin_panel/users/details.html", {"user_obj": user_obj, "orders": orders})

@custom_admin_required
def admin_user_toggle_block(request, pk):
    user_obj = get_object_or_404(Registration, pk=pk)
    user_obj.is_blocked = not user_obj.is_blocked
    user_obj.save()
    messages.success(
        request,
        _("User status updated to %(status)s.") % {
            "status": localized_bool_status(user_obj.is_blocked, "Blocked", "Active")
        },
    )
    return redirect("core:admin_user_details", pk=pk)

@custom_admin_required
def admin_user_delete(request, pk):
    user_obj = get_object_or_404(Registration, pk=pk)
    user_obj.delete()
    messages.success(request, _("User deleted successfully."))
    return redirect("core:admin_user_list")

# ---------- Order Management ----------
@custom_admin_required
def admin_order_list(request):
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "")

    orders_qs = Order.objects.select_related("user").all().order_by("-created_at")

    if query:
        orders_qs = orders_qs.filter(Q(order_id__icontains=query) | Q(user__fullname__icontains=query))
    if status_filter:
        orders_qs = orders_qs.filter(order_status=status_filter)

    context = {
        "orders": orders_qs,
        "query": query,
        "selected_status": status_filter,
        "status_choices": Order.ORDER_STATUS_CHOICES,
    }
    return render(request, "admin_panel/orders/list.html", context)

@custom_admin_required
def admin_order_details(request, pk):
    order = get_object_or_404(Order, pk=pk)
    items = order.items.all()
    
    if request.method == "POST":
        new_status = request.POST.get("order_status")
        if new_status in dict(Order.ORDER_STATUS_CHOICES):
            order.order_status = new_status
            order.save()
            messages.success(
                request,
                _("Order status updated to %(status)s.") % {
                    "status": localized_order_status(new_status)
                },
            )
            return redirect("core:admin_order_details", pk=pk)
        messages.error(request, _("Invalid status choice."))

    return render(request, "admin_panel/orders/details.html", {"order": order, "items": items, "status_choices": Order.ORDER_STATUS_CHOICES})

@custom_admin_required
def admin_order_mark_paid(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if request.method != "POST":
        return redirect("core:admin_order_details", pk=pk)

    if order.is_paid:
        messages.info(
            request,
            _("Order %(order_id)s is already marked as paid.") % {"order_id": order.order_id},
        )
    elif order.payment_method == "Cash on Delivery":
        order.is_paid = True
        if order.order_status == Order.STATUS_PENDING:
            order.order_status = Order.STATUS_CONFIRMED
            order.save(update_fields=["is_paid", "order_status"])
        else:
            order.save(update_fields=["is_paid"])
        messages.success(
            request,
            _("COD payment for order %(order_id)s marked as paid.") % {"order_id": order.order_id},
        )
    else:
        messages.error(request, _("Only unpaid COD orders can be manually marked as paid."))

    next_url = request.POST.get("next")
    if next_url == "list":
        return redirect("core:admin_order_list")
    return redirect("core:admin_order_details", pk=pk)

# ---------- Review Management ----------
@custom_admin_required
def admin_review_list(request):
    rating_filter = request.GET.get("rating", "")
    query = request.GET.get("q", "").strip()

    reviews_qs = Review.objects.select_related("user", "product").all().order_by("-created_at")

    if rating_filter:
        reviews_qs = reviews_qs.filter(rating=rating_filter)
    if query:
        reviews_qs = reviews_qs.filter(
            Q(review__icontains=query)
            | Q(product__product_name_en__icontains=query)
            | Q(product__product_name_hi__icontains=query)
            | Q(user__fullname__icontains=query)
        )

    return render(request, "admin_panel/reviews/list.html", {"reviews": reviews_qs, "selected_rating": rating_filter, "query": query})

@custom_admin_required
def admin_review_delete(request, pk):
    review = get_object_or_404(Review, pk=pk)
    review.delete()
    messages.success(request, _("Review deleted successfully."))
    return redirect("core:admin_review_list")

# ---------- Reports Module ----------
@custom_admin_required
def admin_reports_revenue(request):
    export_csv = request.GET.get("export", "") == "csv"

    # Paid orders are revenue, regardless of fulfilment status.
    orders_qs = Order.objects.filter(is_paid=True).order_by("-created_at")

    if export_csv:
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="revenue_report.csv"'
        writer = csv.writer(response)
        writer.writerow([_("Order ID"), _("Customer Name"), _("Total Amount"), _("Payment Method"), _("Date")])
        for o in orders_qs:
            writer.writerow([o.order_id, o.user.fullname, o.total_amount, o.payment_method, o.created_at.strftime("%Y-%m-%d %H:%M")])
        return response

    return render(request, "admin_panel/reports/revenue.html", {"orders": orders_qs})

@custom_admin_required
def admin_reports_sales(request):
    export_csv = request.GET.get("export", "") == "csv"

    # Top selling products calculation
    product_sales = (
        OrderItem.objects.filter(order__is_paid=True)
        .values(
            "product__product_name_en",
            "product__product_name_hi",
            "product__seller_name",
            "product__category__name_en",
            "product__category__name_hi",
        )
        .annotate(
            items_sold=Sum("quantity"),
            total_revenue=Sum("line_total"),
        )
        .order_by("-items_sold")
    )
    product_sales = [
        {
            **item,
            "product_name": (
                item["product__product_name_hi"] or item["product__product_name_en"]
                if get_language() == "hi"
                else item["product__product_name_en"] or item["product__product_name_hi"]
            ),
            "category_name": (
                item["product__category__name_hi"] or item["product__category__name_en"]
                if get_language() == "hi"
                else item["product__category__name_en"] or item["product__category__name_hi"]
            ),
        }
        for item in product_sales
    ]


    if export_csv:
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="sales_report.csv"'
        writer = csv.writer(response)
        writer.writerow([_("Product Name"), _("Category"), _("Seller Name"), _("Quantity Sold"), _("Total Revenue")])
        for p in product_sales:
            writer.writerow([
                p["product_name"],
                p["category_name"],
                p["product__seller_name"],
                p["items_sold"],
                p["total_revenue"],
            ])

        return response


    return render(request, "admin_panel/reports/sales.html", {"product_sales": product_sales})

# ---------- Settings View ----------
@custom_admin_required
def admin_settings(request):
    if request.method == "POST":
        messages.success(request, _("Admin Settings updated successfully."))
        return redirect("core:admin_settings")
    return render(request, "admin_panel/settings.html")


# ---------- Contact Message Module ----------
@custom_admin_required
def admin_contact_message_list(request):
    messages_qs = ContactMessage.objects.all().order_by("-created_at")
    return render(request, "admin_panel/contacts/list.html", {"contact_messages": messages_qs})

@custom_admin_required
def admin_contact_message_detail(request):
    msg_id = request.GET.get("id")
    msg = get_object_or_404(ContactMessage, id=msg_id)
    if not msg.is_read:
        msg.is_read = True
        msg.save()
    return render(request, "admin_panel/contacts/detail.html", {"msg": msg})

@custom_admin_required
def admin_contact_message_reply(request, msg_id):
    msg = get_object_or_404(ContactMessage, id=msg_id)
    if request.method == "POST":
        reply_text = request.POST.get("reply_message", "").strip()
        if reply_text:
            try:
                # Send email using configured SMTP settings
                subject = f"Re: {msg.subject} - DesiHands Support"
                body = (
                    f"Hello {msg.name},\n\n"
                    f"Thank you for contacting us. Regarding your query:\n"
                    f"\"{msg.message}\"\n\n"
                    f"{reply_text}\n\n"
                    f"Best regards,\n"
                    f"DesiHands Support Team"
                )
                send_mail(
                    subject,
                    body,
                    None, # Uses DEFAULT_FROM_EMAIL automatically
                    [msg.email],
                    fail_silently=False,
                )
                
                # Update database record
                msg.replied = True
                msg.reply_message = reply_text
                msg.save()
                messages.success(
                    request,
                    _("Reply email sent successfully to %(email)s.") % {"email": msg.email},
                )
            except Exception as e:
                messages.error(request, _("Failed to send email: %(error)s") % {"error": str(e)})
        else:
            messages.error(request, _("Reply message cannot be empty."))
    return redirect(f"/custom-admin/contacts/detail/?id={msg.id}")

@custom_admin_required
def admin_contact_message_delete(request, msg_id):
    msg = get_object_or_404(ContactMessage, id=msg_id)
    msg.delete()
    messages.success(request, _("Contact message deleted successfully."))
    return redirect("core:admin_contact_message_list")
