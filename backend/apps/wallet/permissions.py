from allauth.account.models import EmailAddress
from rest_framework.exceptions import APIException
from rest_framework.permissions import BasePermission


class EmailNotVerified(APIException):
    status_code = 403
    default_detail = "Thibitisha barua pepe yako kabla ya kutumia pochi."
    default_code = "email_not_verified"


class IsEmailVerified(BasePermission):
    def has_permission(self, request, view):
        if not EmailAddress.objects.filter(user=request.user, verified=True).exists():
            raise EmailNotVerified()
        return True
