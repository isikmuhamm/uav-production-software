# aircraft_production_app/urls.py (veya api_urls.py)
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    # ViewSet'ler
    AircraftModelViewSet, PartTypeViewSet, TeamViewSet, PersonnelViewSet, 
    PartViewSet, WorkOrderViewSet, AircraftViewSet,
    # APIView'lar ve Fonksiyon Bazlı View'lar
    AssembleAircraftAPIView, UserRegisterAPIView, StockLevelsAPIView, 
    current_user_info, 
    # Frontend View'ları
    frontend_login_view, frontend_dashboard_view, frontend_register_view 
)

# === API Router Tanımlaması ===
# ModelViewSet tabanlı endpoint'ler için standart URL'leri otomatik olarak oluşturur.
api_router = DefaultRouter()
api_router.register(r'aircraft-models', AircraftModelViewSet, basename='aircraftmodel') # Hava aracı modelleri (sabit veri)
api_router.register(r'part-types', PartTypeViewSet, basename='parttype') # Parça tipleri/kategorileri (sabit veri)
api_router.register(r'teams', TeamViewSet, basename='team') # Takım yönetimi (CRUD)
api_router.register(r'personnel', PersonnelViewSet, basename='personnel') # Personel yönetimi (takım atama, listeleme)
api_router.register(r'work-orders', WorkOrderViewSet, basename='workorder') # İş emri yönetimi (CRUD)
api_router.register(r'parts', PartViewSet, basename='part') # Parça yönetimi (üretim, listeleme, geri dönüşüm)
api_router.register(r'aircraft', AircraftViewSet, basename='aircraft') # Uçak yönetimi (listeleme, geri dönüşüm)

# === API URL Pattern'leri ===
api_urlpatterns = [
    path('', include(api_router.urls)), # Router URL'leri buraya dahil ediliyor
    path('user/me/', current_user_info, name='current-user-api'),
    path('assembly/assemble-aircraft/', AssembleAircraftAPIView.as_view(), name='assemble-aircraft-api'),
    path('inventory/stock-levels/', StockLevelsAPIView, name='stock-levels-api'),
    path('auth/register/', UserRegisterAPIView.as_view(), name='api_user_register'),
]

# === Frontend URL Pattern'leri ===
# Tarayıcı üzerinden erişilecek HTML sayfaları için.
frontend_urlpatterns = [
    path('login/', frontend_login_view, name='frontend_login'), # Giriş sayfası
    path('dashboard/', frontend_dashboard_view, name='frontend_dashboard'), # Ana yönetim paneli
    path('register/', frontend_register_view, name='frontend_register') # Kayıt sayfası
]

urlpatterns = [
    # API endpoint'leri proje kök URL'sinden sonra /api/ ön ekiyle başlar (örn: /api/teams/)
    path('api/', include((api_urlpatterns, 'api'), namespace='api')),
    # Frontend sayfaları proje kök URL'sinden sonra /app/ ön ekiyle başlar (örn: /app/dashboard/)
    path('app/', include((frontend_urlpatterns, 'app'), namespace='app')),
]