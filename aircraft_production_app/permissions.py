from rest_framework import permissions
from .models import Personnel # Personnel modelini import ediyoruz

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Sadece okunabilir (GET, HEAD, OPTIONS) isteklere herkes için izin verir (giriş yapmışlarsa).
    Yazma (POST, PUT, PATCH, DELETE) isteklerine sadece admin (staff) kullanıcılara izin verir.
    """
    def has_permission(self, request, view):
        # Okuma isteklerine (GET, HEAD, OPTIONS) her zaman izin ver (IsAuthenticated ile birlikte kullanılırsa giriş yapmış olmaları gerekir)
        if request.method in permissions.SAFE_METHODS:
            return True
        # Yazma istekleri için kullanıcının staff (admin) olması gerekir.
        return request.user and request.user.is_staff

class IsOwnerTeamOrAdminForPart(permissions.BasePermission):
    """
    Objeye özel izin:
    - Adminler her zaman tam yetkilidir.
    - Diğer kullanıcılar (personel) sadece kendi takımlarının ürettiği parçalar üzerinde
      değişiklik veya silme yapabilir.
    - Listeleme ve detay görme (okuma) için bu izin doğrudan kullanılmaz,
      genellikle queryset view içinde filtrelenir. Bu daha çok update/delete için.
    """
    def has_object_permission(self, request, view, obj):
        # Okuma isteklerine her zaman izin ver (IsAuthenticated ile birlikte kullanılırsa giriş yapmış olmaları gerekir)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Yazma/Silme istekleri için:
        if request.user and request.user.is_staff: # Admin her zaman yetkili
            return True
        
        # Diğer kullanıcılar için, objenin (Part) üreten takımı ile kullanıcının takımı eşleşmeli
        try:
            personnel = request.user.personnel
            return obj.produced_by_team == personnel.team
        except Personnel.DoesNotExist:
            return False # Personel profili olmayan kullanıcılar (admin değillerse) yazma yapamaz.
        except AttributeError: # request.user.personnel yoksa (anonim kullanıcı gibi)
            return False


class IsAssemblyTeamMemberOrAdminForAircraft(permissions.BasePermission):
    """
    Objeye özel izin:
    - Adminler her zaman tam yetkilidir.
    - Diğer kullanıcılar (personel) sadece kendi montaj takımlarının monte ettiği uçaklar
      üzerinde değişiklik veya "geri dönüştürme" (silme) yapabilir.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True # Okuma için izin

        if request.user and request.user.is_staff:
            return True
        
        try:
            personnel = request.user.personnel
            # Uçağı monte eden takım ile personelin takımı aynı olmalı VE personelin takımı montaj takımı olmalı
            return obj.assembled_by_team == personnel.team and personnel.team.can_perform_assembly()
        except Personnel.DoesNotExist:
            return False
        except AttributeError:
            return False


class CanAssembleAircraft(permissions.BasePermission):
    """
    Kullanıcının (personelin) bir montaj takımına üye olup olmadığını kontrol eder.
    AssembleAircraftAPIView için kullanılacak.
    """
    message = "Bu işlemi yapmak için yetkili bir montaj takımına üye olmalısınız."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            personnel = request.user.personnel
            return personnel.team and personnel.team.can_perform_assembly()
        except Personnel.DoesNotExist:
            return False # Personel profili yoksa montaj yapamaz
        except AttributeError: # request.user.personnel yoksa
            return False

class IsNotAssemblyTeamForCreate(permissions.BasePermission):
    """
    Sadece montaj takımı olmayan personelin belirli işlemleri (örn: create)
    yapabilmesini sağlar.
    """
    message = "Montaj takımları parça üretim işlemini gerçekleştiremez."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            personnel = request.user.personnel
            # Eğer personelin takımı yoksa veya takımı montaj takımı değilse izin ver.
            return not (personnel.team and personnel.team.can_perform_assembly())
        except Personnel.DoesNotExist:
            # Personel profili olmayan bir kullanıcı (admin değilse ve bu izin uygulanıyorsa)
            # bu işlemi yapamamalı. Ancak genellikle IsAuthenticated daha önce kontrol eder.
            return False # Veya True, duruma göre. Şimdilik False daha güvenli.
        except AttributeError: # request.user.personnel yoksa
            return False