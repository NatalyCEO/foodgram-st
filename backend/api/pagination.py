from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from typing import Any


class PageLimitPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'limit'
    max_page_size = 100

    def get_paginated_response(self, data: Any) -> Response:
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })

    def paginate_queryset(self, queryset, request, view=None):
        if 'limit' in request.query_params:
            try:
                self.page_size = int(request.query_params['limit'])
            except (TypeError, ValueError):
                pass
        return super().paginate_queryset(queryset, request, view)