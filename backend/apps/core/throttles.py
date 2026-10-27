from rest_framework.throttling import SimpleRateThrottle


class SupportIPRateThrottle(SimpleRateThrottle):
    scope = "support"

    def get_cache_key(self, request, view):
        del view
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }
