from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import F, Sum
from django.utils import timezone

from .models import Category, Order, Product, Registration


@dataclass(frozen=True)
class DashboardStats:
    total_users: int
    total_products: int
    total_categories: int
    total_orders: int
    total_revenue: float

    latest_orders: list[dict]
    latest_users: list[dict]

    orders_overview_labels: list[str]
    orders_overview_values: list[int]

    revenue_overview_labels: list[str]
    revenue_overview_values: list[float]


def get_admin_dashboard_stats(*, days: int = 7) -> DashboardStats:
    now = timezone.now()
    start = now - timedelta(days=days - 1)

    total_users = Registration.objects.count()
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_orders = Order.objects.count()

    # Revenue includes all orders (per requirement)
    total_revenue = float(Order.objects.aggregate(s=Sum("total_amount")).get("s") or 0)

    latest_orders_qs = (
        Order.objects.select_related("user")
        .order_by("-created_at")[:5]
    )
    latest_orders = [
        {
            "order_id": o.order_id,
            "user": o.user.fullname,
            "order_status": o.order_status,
            "total_amount": float(o.total_amount),
            "created_at": o.created_at,
        }
        for o in latest_orders_qs
    ]

    latest_users_qs = Registration.objects.order_by("-created_at")[:5]
    latest_users = [
        {
            "fullname": u.fullname,
            "email": u.email,
            "mobile": u.mobile,
            "city": u.city,
            "created_at": u.created_at,
        }
        for u in latest_users_qs
    ]

    # Time series
    day_labels: list[str] = []
    orders_values: list[int] = []
    revenue_values: list[float] = []

    # Iterate day-by-day for a simple, predictable chart.
    for i in range(days):
        day_start = (start + timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        label = day_start.strftime("%b %d")
        day_labels.append(label)

        orders_count = Order.objects.filter(created_at__gte=day_start, created_at__lt=day_end).count()
        orders_values.append(orders_count)

        revenue_sum = (
            Order.objects.filter(created_at__gte=day_start, created_at__lt=day_end)
            .aggregate(s=Sum("total_amount"))
            .get("s")
        )
        revenue_values.append(float(revenue_sum or 0))

    return DashboardStats(
        total_users=total_users,
        total_products=total_products,
        total_categories=total_categories,
        total_orders=total_orders,
        total_revenue=total_revenue,
        latest_orders=latest_orders,
        latest_users=latest_users,
        orders_overview_labels=day_labels,
        orders_overview_values=orders_values,
        revenue_overview_labels=day_labels,
        revenue_overview_values=revenue_values,
    )

