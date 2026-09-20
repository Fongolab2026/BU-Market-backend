from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class AdminPageNumberPagination(PageNumberPagination):
    """Format de pagination attendu par l'interface admin :
    { results, total, totalPages, page, perPage }
    """

    page_size = 20
    page_size_query_param = "perPage"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                [
                    ("results", data),
                    ("total", self.page.paginator.count),
                    ("totalPages", self.page.paginator.num_pages),
                    ("page", self.page.number),
                    ("perPage", self.get_page_size(self.request)),
                ]
            )
        )