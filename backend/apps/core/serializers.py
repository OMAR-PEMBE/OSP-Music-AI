from rest_framework import serializers

from .models import SupportMessage


class SupportMessageSerializer(serializers.ModelSerializer):
    message = serializers.CharField(min_length=10, max_length=2000)

    class Meta:
        model = SupportMessage
        fields = ("name", "email", "message")
