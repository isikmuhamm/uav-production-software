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
from aircraft_production_app import views as app_views # current_user_info için

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Token Authentication Endpoint'i
    path('api/auth/login/', authtoken_views.obtain_auth_token, name='api_token_auth'),
    # current_user_info view'ını aircraft_production_app.views içine taşıdık/oluşturduk
    path('api/user/me/', app_views.current_user_info, name='current_user_info'), 
    
    # aircraft_production_app için API URL'lerini dahil et
    path('api/', include('aircraft_production_app.urls')), # Uygulama URL'lerini 'api/' altında topluyoruz
]