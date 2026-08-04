def get_currency_from_phone(mobile):
    """
    Returns a dict containing code, symbol, and conversion rate from INR
    based on the country dial code of the international mobile number.
    """
    if not mobile:
        return {"code": "INR", "symbol": "₹", "rate": 1.0}

    mobile = mobile.strip()
    if mobile.startswith("+91"):
        return {"code": "INR", "symbol": "₹", "rate": 1.0}
    elif mobile.startswith("+44"):
        return {"code": "GBP", "symbol": "£", "rate": 0.0094}
    elif mobile.startswith("+971"):
        return {"code": "AED", "symbol": "د.إ", "rate": 0.044}
    elif mobile.startswith("+61"):
        return {"code": "AUD", "symbol": "A$", "rate": 0.018}
    elif mobile.startswith("+64"):
        return {"code": "NZD", "symbol": "NZ$", "rate": 0.020}
    elif mobile.startswith("+1"):
        # US or Canada area code detection
        is_canada = False
        clean_num = mobile.replace("+1", "").strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        for prefix in ["204", "226", "236", "249", "250", "289", "306", "343", "365", "367", "403", "416", "418", "431", "437", "438", "450", "474", "506", "514", "519", "548", "579", "581", "587", "604", "613", "639", "705", "709", "742", "778", "780", "782", "807", "819", "825", "867", "873", "902", "905"]:
            if clean_num.startswith(prefix):
                is_canada = True
                break
        if is_canada:
            return {"code": "CAD", "symbol": "C$", "rate": 0.016}
        return {"code": "USD", "symbol": "$", "rate": 0.012}

    # Default fallback
    return {"code": "INR", "symbol": "₹", "rate": 1.0}


def get_user_currency(request):
    """
    Retrieves user's active currency details (code, symbol, rate) from the session.
    If not in session, attempts to detect it from the logged-in user's mobile number,
    or falls back to default INR.
    """
    if not request:
        return {"code": "INR", "symbol": "₹", "rate": 1.0}

    if "currency_code" in request.session:
        return {
            "code": request.session["currency_code"],
            "symbol": request.session["currency_symbol"],
            "rate": request.session["currency_rate"],
        }

    # Detect from user profile if logged in
    registration_id = request.session.get("registration_id")
    if registration_id:
        from core.models import Registration
        user = Registration.objects.filter(pk=registration_id).first()
        if user and user.mobile:
            currency = get_currency_from_phone(user.mobile)
            request.session["currency_code"] = currency["code"]
            request.session["currency_symbol"] = currency["symbol"]
            request.session["currency_rate"] = currency["rate"]
            return currency

    # Fallback to default
    return {"code": "INR", "symbol": "₹", "rate": 1.0}


def convert_price(amount, request=None):
    """
    Converts a price in INR to the user's active currency and returns a formatted string.
    """
    if amount is None:
        return ""
    try:
        amount_float = float(amount)
    except (ValueError, TypeError):
        return amount

    currency = get_user_currency(request)
    converted = amount_float * currency["rate"]

    if currency["code"] == "INR":
        return f"{currency['symbol']} {int(round(converted))}"
    else:
        return f"{currency['symbol']} {converted:.2f}"
