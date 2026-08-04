from .models import Cart
from .currency_utils import get_user_currency


def cart_count(request):
    """
    Adds `cart_count` to every template context.
    Matches the variable name already used in base.html:
        {{ cart_count|default:0 }}
    """
    registration_id = request.session.get("registration_id")

    if not registration_id:
        return {"cart_count": 0}

    quantities = Cart.objects.filter(user_id=registration_id).values_list(
        "quantity", flat=True
    )
    return {"cart_count": sum(quantities)}


def currency_context(request):
    """
    Adds global currency variables to every template context.
    """
    currency = get_user_currency(request)
    return {
        "currency_code": currency["code"],
        "currency_symbol": currency["symbol"],
        "currency_rate": currency["rate"],
    }