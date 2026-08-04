from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = False

    dependencies = [
        ("core", "0004_cart"),
    ]

    operations = [
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_id", models.CharField(max_length=20, unique=True)),
                ("total_amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("shipping_address", models.TextField()),
                ("payment_method", models.CharField(max_length=30)),
                (
                    "order_status",
                    models.CharField(
                        choices=[
                            ("Pending", "Pending"),
                            ("Confirmed", "Confirmed"),
                            ("Shipped", "Shipped"),
                            ("Delivered", "Delivered"),
                            ("Cancelled", "Cancelled"),
                        ],
                        default="Pending",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="orders",
                        to="core.registration",
                    ),
                ),
            ],
            options={
                "verbose_name": "Order",
                "verbose_name_plural": "Orders",
                "ordering": ["-created_at"],
            },
        ),
    ]

