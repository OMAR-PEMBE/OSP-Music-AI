import uuid

from django.contrib.auth import logout
from django.core.files.storage import default_storage
from django.db import DatabaseError, transaction
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import MeSerializer
from .services import AccountDeletionStorageError, delete_account


class AccountDeletionUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "account_deletion_failed"


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
        raise ValidationError({"avatar": ["Use a JPG, PNG, or WEBP image."]})
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
            raise ValidationError({"avatar": ["Choose a profile picture."]})

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
        if not isinstance(password, str):
            raise ValidationError({"password": ["The password is incorrect."]})
        try:
            deleted = delete_account(request.user, password)
        except AccountDeletionStorageError:
            raise AccountDeletionUnavailable(
                detail="Account files could not be deleted. Please try again.",
                code="account_deletion_failed",
            )
        if not deleted:
            raise ValidationError({"password": ["The password is incorrect."]})
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
