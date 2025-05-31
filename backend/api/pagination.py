from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from typing import Any


class PageLimitPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'limit'
    max_page_size = 100

    def get_pagination_response(self, data: Any) -> Response:
        return Response({
            'count': self.page_paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'result': data        
        })