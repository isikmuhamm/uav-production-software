from rest_framework import permissions
from .models import Personnel

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Sadece okunabilir (GET, HEAD, OPTIONS) isteklere izin verir.
    Yazma (POST, PUT, PATCH, DELETE) isteklerine sadece admin (staff) kullanıcılara izin verir.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

class IsNotAssemblyTeamForCreate(permissions.BasePermission):
    """
    Montaj takımı olmayan personelin belirli (örn: create) işlemleri yapmasına izin verir.
    """
    message = "Montaj takımları parça üretim işlemini gerçekleştiremez."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            personnel = request.user.personnel
            return not (personnel.team and personnel.team.can_perform_assembly())
        except Personnel.DoesNotExist:
            return False
        except AttributeError:
            return False

class IsOwnerTeamOrAdminForPart(permissions.BasePermission):
    """
    - Adminler her zaman tam yetkilidir.
    - Diğer kullanıcılar ekiplerinin ürettiği parçalarda güncelleme/silme iznine sahiptir.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user and request.user.is_staff:
            return True
        try:
            personnel = request.user.personnel
            return obj.produced_by_team == personnel.team
        except Personnel.DoesNotExist:
            return False
        except AttributeError:
            return False

class IsAssemblyTeamMemberOrAdminForAircraft(permissions.BasePermission):
    """
    - Adminler her zaman tam yetkilidir.
    - Montaj ekibindeki personel, kendi takımlarının monte ettiği uçaklarda değişiklik yapabilir.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user and request.user.is_staff:
            return True
        try:
            personnel = request.user.personnel
            return obj.assembled_by_team == personnel.team and personnel.team.can_perform_assembly()
        except Personnel.DoesNotExist:
            return False
        except AttributeError:
            return False

class CanAssembleAircraft(permissions.BasePermission):
    """
    Kullanıcının bir montaj takımına üye olup olmadığını doğrular.
    """
    message = "Bu işlemi yapmak için yetkili bir montaj takımına üye olmalısınız."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            personnel = request.user.personnel
            return personnel.team and personnel.team.can_perform_assembly()
        except Personnel.DoesNotExist:
            return False
        except AttributeError:
            return False