from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class APIPagination(PageNumberPagination):
    page_size = 20

    def get_paginated_response(self, data):
        next_page = self.page.next_page_number() if self.page.has_next() else None
        return Response(
            {
                "results": data,
                "next": next_page,
                "count": self.page.paginator.count,
            }
        )
