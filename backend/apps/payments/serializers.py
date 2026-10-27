import re

from rest_framework import serializers

from .models import Payment


class StrictIntegerField(serializers.IntegerField):
    def to_internal_value(self, data):
        if type(data) is not int:
            self.fail("invalid")
        return super().to_internal_value(data)


def normalize_tanzanian_phone(value):
    phone = re.sub(r"[\s()-]", "", value)
    if phone.startswith("+255"):
        phone = phone[1:]
    if phone.startswith("0"):
        phone = "255" + phone[1:]
    if not re.fullmatch(r"255[67]\d{8}", phone):
        raise serializers.ValidationError("Enter a valid Tanzanian mobile number.")
    return phone


class TopupCreateSerializer(serializers.Serializer):
    amount_tzs = StrictIntegerField(min_value=1)
    phone = serializers.CharField(max_length=32, trim_whitespace=True)

    def validate_amount_tzs(self, value):
        from apps.core.models import get_app_settings

        app_settings = get_app_settings()
        if value < app_settings.min_topup_tzs or value > app_settings.max_topup_tzs:
            raise serializers.ValidationError(
                f"Amount must be between {app_settings.min_topup_tzs} and "
                f"{app_settings.max_topup_tzs} TZS."
            )
        return value

    def validate_phone(self, value):
        return normalize_tanzanian_phone(value)


class TopupPaymentSerializer(serializers.ModelSerializer):
    phone_masked = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "amount_tzs",
            "phone_masked",
            "status",
            "created_at",
            "completed_at",
        ]

    def get_phone_masked(self, payment):
        return f"••••{payment.phone[-4:]}"
