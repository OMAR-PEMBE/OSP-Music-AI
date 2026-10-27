from django.urls import path

from .views import AvatarView, DeleteAccountView, MeView

urlpatterns = [
    path("me", MeView.as_view(), name="me"),
    path("me/avatar", AvatarView.as_view(), name="me-avatar"),
    path("me/delete", DeleteAccountView.as_view(), name="me-delete"),
]
