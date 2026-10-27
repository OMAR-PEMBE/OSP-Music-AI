import uuid

from django.contrib.auth import logout
from django.core.files.storage import default_storage
from django.db import DatabaseError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import MeSerializer

MAX_AVATAR_BYTES = 2 * 1024 * 1024
AVATAR_TYPES = {
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".png": "png",
    ".webp": "webp",
}


def avatar_format(upload):
    if upload.size > MAX_AVATAR_BYTES:
        raise ValidationError(
            {"avatar": ["Picha lazima iwe na ukubwa wa MB 2 au chini."]}
        )

    filename = upload.name or ""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    extension = f".{extension}"
    kind = AVATAR_TYPES.get(extension)
    header = upload.read(12)
    upload.seek(0)

    valid = {
        "jpeg": header.startswith(b"\xff\xd8\xff"),
        "png": header.startswith(b"\x89PNG\r\n\x1a\n"),
        "webp": header.startswith(b"RIFF") and header[8:12] == b"WEBP",
    }
    if kind is None or not valid[kind]:
        raise ValidationError({"avatar": ["Tumia picha ya JPG, PNG au WEBP."]})
    return "jpg" if kind == "jpeg" else kind


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user, context={"request": request}).data)

    def patch(self, request):
        serializer = MeSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AvatarView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("avatar")
        if upload is None:
            raise ValidationError({"avatar": ["Chagua picha ya wasifu."]})

        extension = avatar_format(upload)
        key = f"avatars/{request.user.pk}/{uuid.uuid4().hex}.{extension}"
        previous_key = request.user.avatar
        saved_key = default_storage.save(key, upload)
        try:
            with transaction.atomic():
                request.user.avatar = saved_key
                request.user.save(update_fields=["avatar"])
        except DatabaseError:
            default_storage.delete(saved_key)
            raise

        if previous_key:
            default_storage.delete(previous_key)
        return Response(
            MeSerializer(request.user, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        password = request.data.get("password", "")
        if not isinstance(password, str) or not request.user.check_password(password):
            raise ValidationError({"password": ["Nenosiri si sahihi."]})

        user = request.user
        user_id = user.pk
        old_avatar = user.avatar
        # DATABASE.md limits display names to 30 chars. A UUID hex prefix gives
        # a unique 88-bit anonymized name while respecting that limit.
        suffix = user_id.hex[:22]
        user.email = f"deleted-{user_id}@deleted.local"
        user.first_name = ""
        user.last_name = ""
        user.display_name = f"deleted-{suffix}"
        user.avatar = None
        user.phone_last_used = None
        user.is_active = False
        user.deleted_at = timezone.now()
        user.save(
            update_fields=[
                "email",
                "first_name",
                "last_name",
                "display_name",
                "avatar",
                "phone_last_used",
                "is_active",
                "deleted_at",
            ]
        )
        from allauth.account.models import EmailAddress

        EmailAddress.objects.filter(user=user).delete()
        if old_avatar:
            default_storage.delete(old_avatar)
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
