from functools import wraps

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required

from .admin_dashboard import get_admin_dashboard_stats

from django.contrib.auth.hashers import check_password, make_password

from django.urls import reverse

from django.shortcuts import get_object_or_404, redirect, render

from django.db.models import Avg, Count, Q
from django.utils.http import url_has_allowed_host_and_scheme
    
from .forms import CategoryForm, LoginForm, ProductForm, RegistrationForm, ReviewForm
from .models import Cart, Category, Product, Registration, Review, ContactMessage


def get_logged_in_registration_id(request):
    return request.session.get("registration_id")


def is_registered_user_logged_in(request):

    return bool(request.session.get("registration_email"))


def get_logged_in_registration(request):
    registration_id = request.session.get("registration_id")
    if not registration_id:
        return None
    return Registration.objects.filter(pk=registration_id).first()


def registration_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_registered_user_logged_in(request):
            from django.urls import reverse
            messages.error(request, "Please login to continue.")
            return redirect(f"{reverse('core:login')}?next={request.path}")
        return view_func(request, *args, **kwargs)

    return wrapper


def home_view(request):
    featured_categories = Category.objects.all()
    latest_products = (
        Product.objects.select_related("category").filter(is_available=True)[:8]
    )
    context = {
        "featured_categories": featured_categories,
        "latest_products": latest_products,
    }
    return render(request, "core/home.html", context)

def about_view(request):
    return render(request, "core/about.html")

def contact_view(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        subject = request.POST.get("subject", "").strip()
        message = request.POST.get("message", "").strip()
        if name and email and subject and message:
            ContactMessage.objects.create(
                name=name,
                email=email,
                subject=subject,
                message=message
            )
            messages.success(request, f"Thank you, {name}! Your message has been sent successfully.")
        else:
            messages.error(request, "All fields are required.")
        return redirect("core:contact")
    return render(request, "core/contact.html")

def category_list_view(request):
    categories = Category.objects.all()
    return render(request, "core/category_list.html", {"categories": categories})


@staff_member_required
def category_create_view(request):
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Category added successfully.")
            return redirect("core:category_list")
        messages.error(request, "Please correct the errors below.")
    else:
        form = CategoryForm()

    return render(
        request,
        "core/category_form.html",
        {"form": form, "page_title": "Add Category", "button_text": "Add Category"},
    )


@staff_member_required
def category_update_view(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully.")
            return redirect("core:category_list")
        messages.error(request, "Please correct the errors below.")
    else:
        form = CategoryForm(instance=category)

    return render(
        request,
        "core/category_form.html",
        {"form": form, "page_title": "Edit Category", "button_text": "Update Category"},
    )


@staff_member_required
def category_delete_view(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if request.method == "POST":
        category.delete()
        messages.success(request, "Category deleted successfully.")
        return redirect("core:category_list")

    return render(request, "core/category_confirm_delete.html", {"category": category})


def product_list_view(request):
    search_query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "").strip()
    products = Product.objects.select_related("category").all()
    categories = Category.objects.all()

    if search_query:
        products = products.filter(Q(product_name_en__icontains=search_query) | Q(product_name_hi__icontains=search_query))

    if category_id:
        products = products.filter(category_id=category_id)

    context = {
        "products": products,
        "categories": categories,
        "search_query": search_query,
        "selected_category": category_id,
    }
    return render(request, "core/product_list.html", context)


def get_product_review_context(
    product,
    registration_id=None,
    preview_limit=None,
    rating_filter=None,
):
    reviews_qs = Review.objects.filter(product=product).select_related("user")
    average_rating = reviews_qs.aggregate(avg=Avg("rating"))["avg"]
    review_count = reviews_qs.count()
    average_rating_percent = (average_rating or 0) * 20
    rating_counts = {
        item["rating"]: item["count"]
        for item in reviews_qs.values("rating").annotate(count=Count("id"))
    }
    rating_breakdown = []
    for star in range(5, 0, -1):
        count = rating_counts.get(star, 0)
        percent = (count / review_count * 100) if review_count else 0
        rating_breakdown.append(
            {
                "star": star,
                "count": count,
                "percent": percent,
            }
        )
    visible_reviews_qs = reviews_qs
    if rating_filter:
        visible_reviews_qs = visible_reviews_qs.filter(rating=rating_filter)

    filtered_review_count = visible_reviews_qs.count()
    reviews = list(visible_reviews_qs)
    for review in reviews:
        review.rating_percent = review.rating * 20

    user_review = None
    if registration_id:
        user_review = reviews_qs.filter(user_id=registration_id).first()
        if user_review:
            user_review.rating_percent = user_review.rating * 20

    visible_reviews = reviews[:preview_limit] if preview_limit else reviews

    return {
        "reviews": visible_reviews,
        "average_rating": average_rating,
        "average_rating_percent": average_rating_percent,
        "rating_breakdown": rating_breakdown,
        "review_count": review_count,
        "filtered_review_count": filtered_review_count,
        "selected_rating": rating_filter,
        "has_more_reviews": preview_limit is not None and filtered_review_count > len(visible_reviews),
        "user_review": user_review,
    }


def get_review_redirect_url(request, product):
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        separator = "&" if "?" in next_url else "?"
        return f"{next_url}{separator}review_popup=1"
    return f"{reverse('core:product_detail', kwargs={'pk': product.pk})}?review_popup=1"


def product_detail_view(request, pk):
    product = get_object_or_404(Product.objects.select_related("category"), pk=pk)

    context = {
        "product": product,
        **get_product_review_context(
            product,
            registration_id=request.session.get("registration_id"),
            preview_limit=3,
        ),
    }
    return render(request, "core/product_detail.html", context)


def product_reviews_view(request, pk):
    product = get_object_or_404(Product.objects.select_related("category"), pk=pk)
    rating_filter = request.GET.get("rating", "").strip()
    rating_filter = int(rating_filter) if rating_filter in {"1", "2", "3", "4", "5"} else None
    context = {
        "product": product,
        **get_product_review_context(
            product,
            registration_id=request.session.get("registration_id"),
            rating_filter=rating_filter,
        ),
    }
    return render(request, "core/product_reviews.html", context)



@staff_member_required
def product_create_view(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Product added successfully.")
            return redirect("core:product_list")
        messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm()

    return render(
        request,
        "core/product_form.html",
        {"form": form, "page_title": "Add Product", "button_text": "Add Product"},
    )


@staff_member_required
def product_update_view(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully.")
            return redirect("core:product_detail", pk=product.pk)
        messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm(instance=product)

    return render(
        request,
        "core/product_form.html",
        {"form": form, "page_title": "Edit Product", "button_text": "Update Product"},
    )


@staff_member_required
def product_delete_view(request, pk):

    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        product.delete()
        messages.success(request, "Product deleted successfully.")
        return redirect("core:product_list")

    return render(request, "core/product_confirm_delete.html", {"product": product})


def register_view(request):
    if is_registered_user_logged_in(request):
        return redirect("core:home")

    if request.method == "POST":
        form = RegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration successful. Please login.")
            return redirect("core:login")
        messages.error(request, "Please correct the errors below.")
    else:
        form = RegistrationForm()

    return render(request, "core/register.html", {"form": form})


def login_view(request):
    if is_registered_user_logged_in(request):
        return redirect("core:home")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            password = form.cleaned_data["password"]
            registration = Registration.objects.filter(email__iexact=email).first()

            if registration and check_password(password, registration.password):
                if registration.is_blocked:
                    messages.error(request, "Your account has been blocked by the administrator.")
                    form.add_error(None, "Your account has been blocked.")
                else:
                    request.session["registration_id"] = registration.id
                    request.session["registration_name"] = registration.fullname
                    request.session["registration_email"] = registration.email
                    
                    # Set currency in session immediately on login
                    from .currency_utils import get_currency_from_phone
                    currency = get_currency_from_phone(registration.mobile)
                    request.session["currency_code"] = currency["code"]
                    request.session["currency_symbol"] = currency["symbol"]
                    request.session["currency_rate"] = currency["rate"]
                    
                    messages.success(request, "Login successful.")
                    next_url = request.GET.get("next") or request.POST.get("next")
                    if next_url:
                        return redirect(next_url)
                    return redirect("core:home")

            else:
                messages.error(request, "Invalid email or password.")
                form.add_error(None, "Invalid email or password.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = LoginForm()

    return render(request, "core/login.html", {"form": form})


@registration_login_required
def logout_view(request):
    request.session.flush()
    messages.success(request, "Logout successful.")
    return redirect("core:home")


@registration_login_required
def profile_view(request):
    registration = get_logged_in_registration(request)
    if not registration:
        return redirect("core:login")

    from .forms_profile import ChangePasswordForm, ProfileForm

    orders = []
    wishlist_items = []
    try:
        orders = list(registration.orders.all().order_by("-created_at"))
    except Exception:
        orders = []
    try:
        wishlist_items = list(registration.wishlists.select_related("product").select_related("product__category").order_by("-created_at"))
    except Exception:
        wishlist_items = []

    edit_profile_form = ProfileForm(instance=registration)
    change_password_form = ChangePasswordForm()

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "edit_profile":
            edit_profile_form = ProfileForm(request.POST, request.FILES, instance=registration)
            if edit_profile_form.is_valid():
                user = edit_profile_form.save()
                
                # Update currency immediately in session based on the new mobile number/country
                from .currency_utils import get_currency_from_phone
                currency = get_currency_from_phone(user.mobile)
                request.session["currency_code"] = currency["code"]
                request.session["currency_symbol"] = currency["symbol"]
                request.session["currency_rate"] = currency["rate"]
                
                messages.success(request, "Profile updated successfully.")
                return redirect("core:profile")
            messages.error(request, "Please correct the errors below.")

        elif action == "change_avatar":
            profile_image = request.FILES.get("profile_image")
            if profile_image:
                registration.profile_image = profile_image
                registration.save(update_fields=["profile_image"])
                messages.success(request, "Profile photo updated successfully.")
            else:
                messages.error(request, "No image file provided.")
            return redirect("core:profile")

        elif action == "change_password":
            change_password_form = ChangePasswordForm(request.POST)
            if change_password_form.is_valid():
                old_password = change_password_form.cleaned_data.get("old_password")
                new_password = change_password_form.cleaned_data.get("new_password")

                if not check_password(old_password, registration.password):
                    change_password_form.add_error("old_password", "Old password is incorrect.")
                else:
                    registration.password = make_password(new_password)
                    registration.save(update_fields=["password"])
                    messages.success(request, "Password changed successfully.")
                    return redirect("core:profile")
            else:
                messages.error(request, "Please correct the errors below.")

    context = {
        "registration": registration,
        "edit_profile_form": edit_profile_form,
        "change_password_form": change_password_form,
        "orders": orders,
        "wishlist_items": wishlist_items,
    }
    return render(request, "core/profile.html", context)


@registration_login_required
def cart_detail_view(request):

    user = get_logged_in_registration(request)
    cart_items = (
        Cart.objects.filter(user=user)
        .select_related("product", "product__category")
        .order_by("-added_at")
    )
    grand_total = Cart.calculate_grand_total(cart_items)
    total_quantity = sum(item.quantity for item in cart_items)
    context = {
        "cart_items": cart_items,
        "grand_total": grand_total,
        "total_quantity": total_quantity,
    }
    return render(request, "core/cart.html", context)


@registration_login_required
def cart_add_view(request, pk):
    user = get_logged_in_registration(request)
    product = get_object_or_404(Product, pk=pk)

    if request.method != "POST":
        return redirect("core:product_detail", pk=product.pk)

    if not product.is_available:
        messages.error(request, "This product is currently unavailable.")
        return redirect("core:product_detail", pk=product.pk)

    try:
        quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        quantity = 1

    if quantity < 1:
        messages.error(request, "Quantity must be at least 1.")
        return redirect("core:product_detail", pk=product.pk)

    if quantity > product.stock:
        messages.error(request, f"Only {product.stock} item(s) available in stock.")
        return redirect("core:product_detail", pk=product.pk)

    cart_item, created = Cart.objects.get_or_create(
        user=user,
        product=product,
        defaults={"quantity": quantity},
    )

    if not created:
        new_quantity = cart_item.quantity + quantity
        if new_quantity > product.stock:
            messages.error(
                request,
                f"Cannot add more. Only {product.stock} item(s) available in stock.",
            )
            return redirect("core:product_detail", pk=product.pk)
        cart_item.quantity = new_quantity
        cart_item.save(update_fields=["quantity"])

    messages.success(request, f"{product.product_name} added to cart.")
    next_url = request.POST.get("next")
    if next_url == "cart":
        return redirect("core:cart")
    return redirect("core:product_detail", pk=product.pk)


@registration_login_required
def cart_remove_view(request, pk):
    user = get_logged_in_registration(request)
    cart_item = get_object_or_404(Cart, pk=pk, user=user)

    if request.method == "POST":
        product_name = cart_item.product.product_name
        cart_item.delete()
        messages.success(request, f"{product_name} removed from cart.")

    return redirect("core:cart")


@registration_login_required
def cart_update_view(request, pk):

    user = get_logged_in_registration(request)

    cart_item = get_object_or_404(
        Cart.objects.select_related("product"),
        pk=pk,
        user=user,
    )

    if request.method != "POST":
        return redirect("core:cart")

    try:
        quantity = int(request.POST.get("quantity", cart_item.quantity))
    except (TypeError, ValueError):
        messages.error(request, "Please enter a valid quantity.")
        return redirect("core:cart")

    if quantity < 1:
        messages.error(request, "Quantity must be at least 1.")
        return redirect("core:cart")

    if quantity > cart_item.product.stock:
        messages.error(
            request,
            f"Only {cart_item.product.stock} item(s) available in stock.",
        )
        return redirect("core:cart")

    cart_item.quantity = quantity
    cart_item.save(update_fields=["quantity"])
    messages.success(request, "Cart quantity updated.")
    return redirect("core:cart")


@registration_login_required
def review_add_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    registration = get_logged_in_registration(request)

    if request.method != "POST":
        return redirect("core:product_detail", pk=product.pk)

    existing_review = Review.objects.filter(user=registration, product=product).first()
    form = ReviewForm(request.POST, instance=existing_review)

    if form.is_valid():
        review = form.save(commit=False)
        review.user = registration
        review.product = product
        review.save()
        messages.success(request, "Review saved successfully.")
        return redirect(get_review_redirect_url(request, product))

    messages.error(request, "Please correct the errors below.")
    return redirect("core:product_detail", pk=product.pk)


@registration_login_required
def review_edit_view(request, pk, review_id):
    product = get_object_or_404(Product, pk=pk)
    registration = get_logged_in_registration(request)

    review = get_object_or_404(Review, pk=review_id, user=registration, product=product)

    if request.method != "POST":
        return redirect("core:product_detail", pk=product.pk)

    form = ReviewForm(request.POST, instance=review)
    if form.is_valid():
        form.save()
        messages.success(request, "Review updated successfully.")
        return redirect(get_review_redirect_url(request, product))

    messages.error(request, "Please correct the errors below.")
    return redirect("core:product_detail", pk=product.pk)


@registration_login_required
def review_delete_view(request, pk, review_id):
    product = get_object_or_404(Product, pk=pk)
    registration = get_logged_in_registration(request)

    review = get_object_or_404(Review, pk=review_id, user=registration, product=product)

    if request.method == "POST":
        review.delete()
        messages.success(request, "Review deleted successfully.")

    return redirect("core:product_detail", pk=product.pk)


@staff_member_required
def admin_dashboard_view(request):
    if not (request.user.is_staff or request.user.is_superuser):
        # staff_member_required should cover this, but keep a hard guard.
        return redirect("/admin/")


    stats = get_admin_dashboard_stats(days=7)


    context = {
        "stats": stats,
        "orders_labels_json": stats.orders_overview_labels,
        "orders_values_json": stats.orders_overview_values,
        "revenue_labels_json": stats.revenue_overview_labels,
        "revenue_values_json": stats.revenue_overview_values,
    }

    return render(request, "core/admin_dashboard.html", context)
