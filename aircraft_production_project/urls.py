"""
URL configuration for aircraft_production_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken import views as authtoken_views
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
# from aircraft_production_app.views import frontend_dashboard_view # Eğer kök URL'de bir sayfa göstermek isterseniz

urlpatterns = [
    # Django Admin Paneli
    path('admin/', admin.site.urls),

    # API Token Kimlik Doğrulama Endpoint'i
    path('api-token-auth/', authtoken_views.obtain_auth_token, name='api_token_auth'),
    
    # Ana Uygulama URL'leri (API ve Frontend view'larını içerir)
    # Kök path ('') aircraft_production_app.urls'e yönlendiriliyor.
    # Eğer kök path'te özel bir sayfa göstermek isterseniz (örn: bir landing page veya direkt dashboard),
    # buraya `path('', frontend_dashboard_view, name='home'),` gibi bir ekleme yapabilirsiniz.
    path('', include('aircraft_production_app.urls')), 

    # drf-spectacular URL'leri (API Dokümantasyonu için)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'), # OpenAPI şemasını (YAML/JSON) sunar
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'), # Swagger UI arayüzü
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'), # ReDoc arayüzü
]
