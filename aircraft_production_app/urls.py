# aircraft_production_app/urls.py (veya api_urls.py)
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AircraftModelViewSet, PartTypeViewSet, TeamViewSet, PersonnelViewSet, PartViewSet, WorkOrderViewSet, AssembleAircraftAPIView, AircraftViewSet,UserRegisterAPIView, StockLevelsAPIView, current_user_info, frontend_login_view, frontend_dashboard_view, frontend_register_view 


# API Router
api_router = DefaultRouter()
api_router.register(r'aircraft-models', AircraftModelViewSet, basename='aircraftmodel') # api-root için basename önemli
api_router.register(r'part-types', PartTypeViewSet, basename='parttype')
api_router.register(r'teams', TeamViewSet, basename='team')
api_router.register(r'personnel', PersonnelViewSet, basename='personnel')
api_router.register(r'work-orders', WorkOrderViewSet, basename='workorder')
api_router.register(r'parts', PartViewSet, basename='part')
api_router.register(r'aircraft', AircraftViewSet, basename='aircraft')

# API URL'leri
api_urlpatterns = [
    path('', include(api_router.urls)), # Router URL'leri buraya dahil ediliyor
    path('user/me/', current_user_info, name='current-user-api'),
    path('assembly/assemble-aircraft/', AssembleAircraftAPIView.as_view(), name='assemble-aircraft-api'),
    path('inventory/stock-levels/', StockLevelsAPIView, name='stock-levels-api'),
    path('api/auth/register/', UserRegisterAPIView.as_view(), name='api_user_register'),
]

# Frontend URL'leri
frontend_urlpatterns = [
    path('login/', frontend_login_view, name='frontend_login'),
    path('dashboard/', frontend_dashboard_view, name='frontend_dashboard'),
    path('register/', frontend_register_view, name='frontend_register')
]

urlpatterns = [
    # API endpoint'leri /api/ altında olacak
    path('api/', include((api_urlpatterns, 'api'), namespace='api')),
    # Frontend sayfaları /app/ altında olacak
    path('app/', include((frontend_urlpatterns, 'app'), namespace='app')),
]