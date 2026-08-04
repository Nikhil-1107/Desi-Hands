from django import template
from core.currency_utils import convert_price

register = template.Library()

@register.filter(name='convert_price')
def convert_price_filter(value, request=None):
    """
    Django template filter to convert and format a price from INR to the user's active currency.
    Usage: {{ product.price|convert_price:request }}
    """
    return convert_price(value, request)
