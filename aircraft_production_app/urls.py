# aircraft_production_app/urls.py (veya api_urls.py)
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AircraftModelViewSet, PartTypeViewSet, TeamViewSet, PersonnelViewSet, PartViewSet, WorkOrderViewSet, AssembleAircraftAPIView, AircraftViewSet, StockLevelsAPIView # ViewSet'leri import et

# Router'ı oluştur ve ViewSet'leri kaydet
router = DefaultRouter()
router.register(r'aircraft-models', AircraftModelViewSet, basename='aircraftmodel')
router.register(r'part-types', PartTypeViewSet, basename='parttype')
router.register(r'teams', TeamViewSet, basename='team') # İleride kullanmak için
router.register(r'personnel', PersonnelViewSet, basename='personnel') # İleride kullanmak için
router.register(r'parts', PartViewSet, basename='part') # YENİ EKLENDİ
router.register(r'aircraft', AircraftViewSet, basename='aircraft') # YENİ
router.register(r'work-orders', WorkOrderViewSet, basename='workorder') # YENİ EKLENDİ



urlpatterns = [
    path('', include(router.urls)),
    # Diğer API endpoint'leriniz buraya eklenebilir (örn: login, current_user_info)
    path('assembly/assemble-aircraft/', AssembleAircraftAPIView.as_view(), name='assemble-aircraft'), # YENİ
    path('inventory/stock-levels/', StockLevelsAPIView, name='stock-levels'), # YENİ STOK API'Sİ
]
