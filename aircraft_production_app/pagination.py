# aircraft_production_app/pagination.py
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from collections import OrderedDict

class StandardDataTablePagination(LimitOffsetPagination):
    """
    DataTable sunucu tarafı işlemleriyle uyumlu özel pagination sınıfı.
    Standart DRF pagination yerine 'draw', 'recordsFiltered', 'recordsTotal' ve 'data' alanlarını döndürür.
    """
    default_limit = 10
    limit_query_param = 'length'
    offset_query_param = 'start'

    def get_paginated_response(self, data):
        # Kısa bir açıklama: DataTable 'draw' parametresini gönderir, senk. için geri paslarız.
        draw = 0
        if self.request and self.request.query_params.get('draw'):
            try:
                draw = int(self.request.query_params.get('draw'))
            except ValueError:
                pass

        return Response(OrderedDict([
            ('draw', draw),
            ('recordsFiltered', self.count),
            ('recordsTotal', self.count),
            ('data', data)
        ]))

    def get_paginated_response_schema(self, schema):
        """
        OpenAPI şeması için bir çıktı sağlar. (drf-spectacular gibi araçlar bu bilgiyi otomatik kullanır.)
        """
        return {
            'type': 'object',
            'properties': {
                'draw': {
                    'type': 'integer',
                    'example': 1,
                    'description': "DataTable tarafından gönderilen ve senkronizasyon için geri gönderilen bir sayaç."
                },
                'recordsFiltered': {
                    'type': 'integer',
                    'example': self.default_limit,
                    'description': "Filtreleme uygulandıktan sonraki toplam kayıt sayısı."
                },
                'recordsTotal': {
                    'type': 'integer',
                    'example': 100,
                    'description': "Filtreleme uygulanmadan önceki toplam kayıt sayısı."
                },
                'data': schema,
            },
        }
