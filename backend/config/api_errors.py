from rest_framework import status
from rest_framework.views import exception_handler

ERROR_MESSAGES = {
    "validation_error": "Please check the information you entered.",
    "not_authenticated": "Please log in to continue.",
    "permission_denied": "You are not allowed to make this request.",
    "email_not_verified": "Verify your email before using the wallet.",
    "not_found": "That item could not be found.",
    "insufficient_balance": "Insufficient wallet balance.",
    "duplicate_request": "This request has already been processed.",
    "request_error": "The request could not be completed.",
    "rate_limited": "You have reached the request limit. Try again later.",
    "payment_provider_error": "The payment service is unavailable. Try again later.",
    "generation_paused": "Music generation is temporarily paused.",
    "lyrics_limit_reached": "You have reached today's lyrics limit.",
}


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    exception_code = str(getattr(exc, "default_code", ""))
    if exception_code in {
        "email_not_verified",
        "insufficient_balance",
        "duplicate_request",
        "rate_limited",
        "payment_provider_error",
        "generation_paused",
        "lyrics_limit_reached",
    }:
        code = exception_code
    elif response.status_code == status.HTTP_401_UNAUTHORIZED:
        code = "not_authenticated"
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        code = "not_found"
    elif response.status_code == status.HTTP_403_FORBIDDEN:
        code = "permission_denied"
    elif response.status_code == status.HTTP_400_BAD_REQUEST:
        code = "validation_error"
    elif response.status_code == status.HTTP_402_PAYMENT_REQUIRED:
        code = "insufficient_balance"
    elif response.status_code == status.HTTP_409_CONFLICT:
        code = "duplicate_request"
    else:
        code = "request_error"

    data = response.data
    if isinstance(data, dict) and "detail" in data and len(data) == 1:
        fields = {}
    elif isinstance(data, dict):
        fields = data
    else:
        fields = {"non_field_errors": data}

    response.data = {
        "error": {
            "code": code,
            "message": ERROR_MESSAGES[code],
            "fields": fields,
        }
    }
    return response
