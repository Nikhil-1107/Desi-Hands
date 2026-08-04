from django.db import models


class Registration(models.Model):
    fullname = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    mobile = models.CharField(max_length=15)
    password = models.CharField(max_length=128)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    profile_image = models.ImageField(upload_to="profile_images/", blank=True, null=True)
    is_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Registration"
        verbose_name_plural = "Registrations"

    def __str__(self):
        return self.fullname


class Category(models.Model):
    name_en = models.CharField(max_length=100)
    name_hi = models.CharField(max_length=100, blank=True, default="")
    image = models.ImageField(upload_to="category_images/", blank=True, null=True)
    description_en = models.TextField()
    description_hi = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name_en"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    @property
    def name(self):
        from django.utils.translation import get_language
        if get_language() == "hi":
            return self.name_hi or self.name_en
        return self.name_en or self.name_hi

    @property
    def description(self):
        from django.utils.translation import get_language
        if get_language() == "hi":
            return self.description_hi or self.description_en
        return self.description_en or self.description_hi

    def __str__(self):
        return self.name_en


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products",
    )
    product_name_en = models.CharField(max_length=150)
    product_name_hi = models.CharField(max_length=150, blank=True, default="")
    product_image = models.ImageField(
        upload_to="product_images/", blank=True, null=True
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    description_en = models.TextField()
    description_hi = models.TextField(blank=True, default="")
    seller_name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Product"
        verbose_name_plural = "Products"

    @property
    def product_name(self):
        from django.utils.translation import get_language
        if get_language() == "hi":
            return self.product_name_hi or self.product_name_en
        return self.product_name_en or self.product_name_hi

    @property
    def description(self):
        from django.utils.translation import get_language
        if get_language() == "hi":
            return self.description_hi or self.description_en
        return self.description_en or self.description_hi

    def __str__(self):
        return self.product_name_en


class Cart(models.Model):
    user = models.ForeignKey(
        Registration,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_entries",
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-added_at"]
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        unique_together = ("user", "product")

    def __str__(self):
        return f"{self.user.fullname} - {self.product.product_name} x {self.quantity}"

    @property
    def line_total(self):
        return self.product.price * self.quantity

    @classmethod
    def calculate_grand_total(cls, cart_items):
        return sum(item.line_total for item in cart_items)


class Wishlist(models.Model):
    user = models.ForeignKey(
        Registration,
        on_delete=models.CASCADE,
        related_name="wishlists",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="wishlist_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Wishlist"
        verbose_name_plural = "Wishlists"
        unique_together = ("user", "product")

    def __str__(self):
        return f"{self.user.fullname} - {self.product.product_name}"


class Order(models.Model):
    STATUS_PENDING = "Pending"
    STATUS_CONFIRMED = "Confirmed"
    STATUS_SHIPPED = "Shipped"
    STATUS_DELIVERED = "Delivered"
    STATUS_CANCELLED = "Cancelled"

    ORDER_STATUS_CHOICES = [
        (STATUS_PENDING, STATUS_PENDING),
        (STATUS_CONFIRMED, STATUS_CONFIRMED),
        (STATUS_SHIPPED, STATUS_SHIPPED),
        (STATUS_DELIVERED, STATUS_DELIVERED),
        (STATUS_CANCELLED, STATUS_CANCELLED),
    ]

    user = models.ForeignKey(
        Registration,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    order_id = models.CharField(max_length=20, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=100, blank=True, default="")
    shipping_state = models.CharField(max_length=100, blank=True, default="")
    shipping_pincode = models.CharField(max_length=10, blank=True, default="")
    shipping_phone = models.CharField(max_length=15, blank=True, default="")
    payment_method = models.CharField(max_length=30)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    is_paid = models.BooleanField(default=False)
    order_status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        return f"{self.order_id} ({self.user.fullname})"

    @property
    def estimated_delivery_start(self):
        from datetime import timedelta
        return self.created_at + timedelta(days=3)

    @property
    def estimated_delivery_end(self):
        from datetime import timedelta
        return self.created_at + timedelta(days=4)


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="order_items",
    )
    product_name = models.CharField(max_length=150)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-added_at"]
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


class Review(models.Model):

    user = models.ForeignKey(
        Registration,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(help_text="1 to 5")
    review = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        unique_together = ("user", "product")

    def __str__(self):
        return f"{self.user.fullname} - {self.product.product_name} ({self.rating})"


class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=250)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    replied = models.BooleanField(default=False)
    reply_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"

    def __str__(self):
        return f"{self.name} - {self.subject}"




