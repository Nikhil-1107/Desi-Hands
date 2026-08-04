from django.contrib import admin

from .models import Cart, Category, Product, Registration, Review



@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("fullname", "email", "mobile", "city", "state", "created_at")
    list_filter = ("city", "state", "created_at")
    search_fields = ("fullname", "email", "mobile", "city", "state")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name_en", "name_hi", "created_at")
    search_fields = ("name_en", "name_hi", "description_en", "description_hi")
    readonly_fields = ("created_at",)
    ordering = ("name_en",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "product_name_en",
        "product_name_hi",
        "category",
        "price",
        "stock",
        "seller_name",
        "is_available",
        "created_at",
    )
    list_filter = ("category", "is_available", "created_at")
    search_fields = ("product_name_en", "product_name_hi", "description_en", "description_hi", "seller_name")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "quantity", "added_at")
    list_filter = ("added_at",)
    search_fields = ("user__fullname", "user__email", "product__product_name_en", "product__product_name_hi")
    readonly_fields = ("added_at",)
    ordering = ("-added_at",)






@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "created_at")

    list_filter = ("rating", "created_at")
    search_fields = ("user__fullname", "user__email", "product__product_name_en", "product__product_name_hi", "review")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
