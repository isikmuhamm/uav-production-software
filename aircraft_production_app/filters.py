# aircraft_production_app/filters.py
import django_filters
from .models import WorkOrder, AircraftModel, Team, User, WorkOrderStatusChoices, DefinedTeamTypes, Part, PartType, PartStatusChoices, PartCategory, Aircraft, AircraftStatusChoices

class StatusInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    """Statü değerlerini virgüllerle ayrılmış biçimde filtrelemek için özel sınıf."""
    pass

class WorkOrderFilter(django_filters.FilterSet):
    """
    WorkOrder modelini filtrelemek için kullanılır.
    Hava aracı modeline, statü durumuna, atanan montaj ekibine
    ve oluşturma tarihine göre arama yapmaya imkân tanır.
    """
    aircraft_model = django_filters.ModelChoiceFilter(queryset=AircraftModel.objects.all())
    status = StatusInFilter(field_name='status', lookup_expr='in')
    assigned_to_assembly_team = django_filters.ModelChoiceFilter(
        queryset=Team.objects.filter(team_type=DefinedTeamTypes.ASSEMBLY_TEAM)
    )
    created_by = django_filters.ModelChoiceFilter(queryset=User.objects.filter(is_staff=True)) # Sadece staff kullanıcılar

    aircraft_model_name = django_filters.CharFilter(field_name='aircraft_model__name', lookup_expr='icontains')
    assigned_to_assembly_team_name = django_filters.CharFilter(field_name='assigned_to_assembly_team__name', lookup_expr='icontains')
    created_by_username = django_filters.CharFilter(field_name='created_by__username', lookup_expr='icontains')
    
    created_at_after = django_filters.DateFilter(field_name='created_at', lookup_expr='date__gte')
    created_at_before = django_filters.DateFilter(field_name='created_at', lookup_expr='date__lte')
    
    target_completion_date_after = django_filters.DateFilter(field_name='target_completion_date', lookup_expr='date__gte')
    target_completion_date_before = django_filters.DateFilter(field_name='target_completion_date', lookup_expr='date__lte')

    class Meta:
        model = WorkOrder
        fields = [
            'aircraft_model', 'status', 'assigned_to_assembly_team', 'created_by',
            'aircraft_model_name', 'assigned_to_assembly_team_name', 'created_by_username',
            'created_at_after', 'created_at_before',
            'target_completion_date_after', 'target_completion_date_before',
            'quantity'
        ]

class PartFilter(django_filters.FilterSet):
    """
    Part modelini filtrelemek için kullanılır.
    Parça tipi, üretim ekibi, durum ve üretim tarihi gibi alanları filtreler.
    """
    part_type = django_filters.ModelChoiceFilter(
        queryset=PartType.objects.all(),
        field_name='part_type',
        label='Parça Tipi (Kategori)'
    )
    aircraft_model_compatibility = django_filters.ModelChoiceFilter(
        queryset=AircraftModel.objects.all(),
        field_name='aircraft_model_compatibility',
        label='Uyumlu Uçak Modeli'
    )
    status = StatusInFilter(field_name='status', lookup_expr='in')
    produced_by_team = django_filters.ModelChoiceFilter(
        queryset=Team.objects.exclude(team_type=DefinedTeamTypes.ASSEMBLY_TEAM),
        field_name='produced_by_team',
        label='Üreten Takım'
    )

    part_type_category_name = django_filters.CharFilter(field_name='part_type__category', lookup_expr='icontains', label='Parça Kategori Adı (içerir)')
    aircraft_model_compatibility_name = django_filters.CharFilter(field_name='aircraft_model_compatibility__name', lookup_expr='icontains', label='Uyumlu Model Adı (içerir)')
    produced_by_team_name = django_filters.CharFilter(field_name='produced_by_team__name', lookup_expr='icontains', label='Üreten Takım Adı (içerir)')
    created_by_personnel_username = django_filters.CharFilter(field_name='created_by_personnel__user__username', lookup_expr='icontains', label='Üreten Personel Kullanıcı Adı (içerir)')
    serial_number = django_filters.CharFilter(lookup_expr='icontains', label='Seri Numarası (içerir)')

    production_date_after = django_filters.DateFilter(field_name='production_date', lookup_expr='date__gte')
    production_date_before = django_filters.DateFilter(field_name='production_date', lookup_expr='date__lte')

    class Meta:
        model = Part
        fields = [
            'part_type', 
            'aircraft_model_compatibility', 
            'status', 
            'produced_by_team',
            'serial_number',
            'part_type_category_name',
            'aircraft_model_compatibility_name',
            'produced_by_team_name',
            'created_by_personnel_username',
            'production_date_after',
            'production_date_before',
        ]

class AircraftFilter(django_filters.FilterSet):
    """
    Aircraft modelini filtrelemek için kullanılır.
    Hava aracı modeli, montaj ekibi ve montaj tarihi gibi alanları filtreler.
    """
    aircraft_model = django_filters.ModelChoiceFilter(queryset=AircraftModel.objects.all())
    status = StatusInFilter(field_name='status', lookup_expr='in')
    assembled_by_team = django_filters.ModelChoiceFilter(
        queryset=Team.objects.filter(team_type=DefinedTeamTypes.ASSEMBLY_TEAM)
    )
    work_order = django_filters.ModelChoiceFilter(queryset=WorkOrder.objects.all())

    aircraft_model_name = django_filters.CharFilter(field_name='aircraft_model__name', lookup_expr='icontains')
    assembled_by_team_name = django_filters.CharFilter(field_name='assembled_by_team__name', lookup_expr='icontains')
    serial_number = django_filters.CharFilter(lookup_expr='icontains')
    work_order_id = django_filters.NumberFilter(field_name='work_order__id')

    assembly_date_after = django_filters.DateFilter(field_name='assembly_date', lookup_expr='date__gte')
    assembly_date_before = django_filters.DateFilter(field_name='assembly_date', lookup_expr='date__lte')

    class Meta:
        model = Aircraft
        fields = [
            'aircraft_model', 'status', 'assembled_by_team', 'work_order',
            'serial_number', 'aircraft_model_name', 'assembled_by_team_name', 'work_order_id',
            'assembly_date_after', 'assembly_date_before',
        ]
