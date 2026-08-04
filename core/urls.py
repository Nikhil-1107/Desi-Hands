from django.urls import path

from . import views
from . import views_admin
from . import views_checkout

app_name = "core"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("about/", views.about_view, name="about"),
    path("contact/", views.contact_view, name="contact"),
    path("categories/", views.category_list_view, name="category_list"),
    path("categories/add/", views.category_create_view, name="category_add"),
    path("categories/<int:pk>/edit/", views.category_update_view, name="category_edit"),
    path("categories/<int:pk>/delete/", views.category_delete_view, name="category_delete"),
    path("products/", views.product_list_view, name="product_list"),
    path("products/add/", views.product_create_view, name="product_add"),
    path("products/<int:pk>/", views.product_detail_view, name="product_detail"),
    path("products/<int:pk>/reviews/", views.product_reviews_view, name="product_reviews"),
    path("products/<int:pk>/edit/", views.product_update_view, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete_view, name="product_delete"),
    path("cart/", views.cart_detail_view, name="cart"),
    path("cart/add/<int:pk>/", views.cart_add_view, name="cart_add"),
    path("cart/<int:pk>/remove/", views.cart_remove_view, name="cart_remove"),
    path("cart/<int:pk>/update/", views.cart_update_view, name="cart_update"),
    path("profile/", views.profile_view, name="profile"),
    path("products/<int:pk>/reviews/add/", views.review_add_view, name="review_add"),

    path("products/<int:pk>/reviews/<int:review_id>/edit/", views.review_edit_view, name="review_edit"),
    path("products/<int:pk>/reviews/<int:review_id>/delete/", views.review_delete_view, name="review_delete"),

    # Checkout & Payment
    path("checkout/address/", views_checkout.checkout_address_view, name="checkout_address"),
    path("checkout/payment/", views_checkout.checkout_payment_view, name="checkout_payment"),
    path("checkout/place-order-cod/", views_checkout.place_order_cod_view, name="place_order_cod"),
    path("checkout/razorpay-verify/", views_checkout.razorpay_payment_verify_view, name="razorpay_verify"),
    path("order-confirmation/<str:order_id>/", views_checkout.order_confirmation_view, name="order_confirmation"),

    # Custom Admin Panel urls
    path("custom-admin/login/", views_admin.admin_login, name="admin_login"),
    path("custom-admin/logout/", views_admin.admin_logout, name="admin_logout"),
    path("custom-admin/dashboard/", views_admin.admin_dashboard, name="admin_dashboard"),
    path("custom-admin/categories/", views_admin.admin_category_list, name="admin_category_list"),
    path("custom-admin/categories/add/", views_admin.admin_category_add, name="admin_category_add"),
    path("custom-admin/categories/<int:pk>/edit/", views_admin.admin_category_edit, name="admin_category_edit"),
    path("custom-admin/categories/<int:pk>/delete/", views_admin.admin_category_delete, name="admin_category_delete"),
    path("custom-admin/products/", views_admin.admin_product_list, name="admin_product_list"),
    path("custom-admin/products/add/", views_admin.admin_product_add, name="admin_product_add"),
    path("custom-admin/products/<int:pk>/edit/", views_admin.admin_product_edit, name="admin_product_edit"),
    path("custom-admin/products/<int:pk>/delete/", views_admin.admin_product_delete, name="admin_product_delete"),
    path("custom-admin/products/<int:pk>/toggle/", views_admin.admin_product_toggle, name="admin_product_toggle"),
    path("custom-admin/users/", views_admin.admin_user_list, name="admin_user_list"),
    path("custom-admin/users/add/", views_admin.admin_user_add, name="admin_user_add"),
    path("custom-admin/users/<int:pk>/", views_admin.admin_user_details, name="admin_user_details"),
    path("custom-admin/users/<int:pk>/toggle-block/", views_admin.admin_user_toggle_block, name="admin_user_toggle_block"),
    path("custom-admin/users/<int:pk>/delete/", views_admin.admin_user_delete, name="admin_user_delete"),
    path("custom-admin/orders/", views_admin.admin_order_list, name="admin_order_list"),
    path("custom-admin/orders/<int:pk>/", views_admin.admin_order_details, name="admin_order_details"),
    path("custom-admin/orders/<int:pk>/mark-paid/", views_admin.admin_order_mark_paid, name="admin_order_mark_paid"),
    path("custom-admin/reviews/", views_admin.admin_review_list, name="admin_review_list"),
    path("custom-admin/reviews/<int:pk>/delete/", views_admin.admin_review_delete, name="admin_review_delete"),
    path("custom-admin/reports/revenue/", views_admin.admin_reports_revenue, name="admin_reports_revenue"),
    path("custom-admin/reports/sales/", views_admin.admin_reports_sales, name="admin_reports_sales"),
    path("custom-admin/settings/", views_admin.admin_settings, name="admin_settings"),
    path("custom-admin/contacts/", views_admin.admin_contact_message_list, name="admin_contact_message_list"),
    path("custom-admin/contacts/detail/", views_admin.admin_contact_message_detail, name="admin_contact_message_detail"),
    path("custom-admin/contacts/<int:msg_id>/reply/", views_admin.admin_contact_message_reply, name="admin_contact_message_reply"),
    path("custom-admin/contacts/<int:msg_id>/delete/", views_admin.admin_contact_message_delete, name="admin_contact_message_delete"),
]
