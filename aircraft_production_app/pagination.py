# aircraft_production_app/pagination.py
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from collections import OrderedDict

class StandardDataTablePagination(LimitOffsetPagination):
    """
    Django Rest Framework için DataTable'ın sunucu taraflı işlemleriyle
    uyumlu özel pagination sınıfı.
    'draw', 'recordsFiltered', 'recordsTotal' ve 'data' anahtarlarını döndürür.
    """
    default_limit = 10 # PAGE_SIZE ile aynı olabilir
    limit_query_param = 'length' # DataTable 'length' gönderir
    offset_query_param = 'start' # DataTable 'start' gönderir

    def get_paginated_response(self, data):
        # DataTable'ın 'draw' parametresini request'ten alıp echo'lamamız gerekiyor.
        draw = 0
        if self.request and self.request.query_params.get('draw'):
            try:
                draw = int(self.request.query_params.get('draw'))
            except ValueError:
                # draw parametresi sayı değilse veya yoksa, varsayılan olarak 0 kalır.
                # DataTable bunu bir hata olarak algılamaz ama senkronizasyon için önemlidir.
                pass

        return Response(OrderedDict([
            ('draw', draw),
            ('recordsFiltered', self.count), # DRF'in count'u zaten filtrelenmiş toplamı verir
            ('recordsTotal', self.count),    # Gerçek filtrelenmemiş toplam için ek bir sorgu veya
                                             # viewset'ten bu bilgiyi almanın bir yolu gerekebilir.
                                             # Şimdilik, filtrelenmiş toplamı her ikisi için de kullanıyoruz.
                                             # Daha doğru bir recordsTotal için, filtrelenmemiş queryset'in
                                             # count'unu viewset'ten bu pagination sınıfına iletmek gerekebilir.
                                             # Veya en basit haliyle, recordsFiltered ile aynı tutulur.
            ('data', data)                   # DRF 'results' yerine DataTable 'data' anahtarını bekler
        ]))

    def get_paginated_response_schema(self, schema):
        # Swagger/OpenAPI şeması için (isteğe bağlı ama iyi bir pratik)
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
                    'example': self.default_limit, # Örnek değer
                    'description': "Filtreleme uygulandıktan sonraki toplam kayıt sayısı."
                },
                'recordsTotal': {
                    'type': 'integer',
                    'example': 100, # Örnek değer
                    'description': "Filtreleme uygulanmadan önceki toplam kayıt sayısı."
                },
                'data': schema, # Bu, serializer'ınızın şeması olacak (kayıt listesi)
            },
        }
