from rest_framework.authentication import SessionAuthentication


class SessionCookieAuthentication(SessionAuthentication):
    def authenticate_header(self, request):
        return "Session"
