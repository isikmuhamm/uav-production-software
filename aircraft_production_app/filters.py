# aircraft_production_app/filters.py
import django_filters
from .models import WorkOrder, AircraftModel, Team, User, WorkOrderStatusChoices, DefinedTeamTypes

class WorkOrderFilter(django_filters.FilterSet):
    # Model alanlarına göre filtreler
    aircraft_model = django_filters.ModelChoiceFilter(queryset=AircraftModel.objects.all())
    status = django_filters.MultipleChoiceFilter(choices=WorkOrderStatusChoices.choices)
    assigned_to_assembly_team = django_filters.ModelChoiceFilter(
        queryset=Team.objects.filter(team_type=DefinedTeamTypes.ASSEMBLY_TEAM)
    )
    created_by = django_filters.ModelChoiceFilter(queryset=User.objects.filter(is_staff=True)) # Sadece staff kullanıcılar

    # İlişkili alanların isimlerine göre metin bazlı filtreler
    aircraft_model_name = django_filters.CharFilter(field_name='aircraft_model__name', lookup_expr='icontains')
    assigned_to_assembly_team_name = django_filters.CharFilter(field_name='assigned_to_assembly_team__name', lookup_expr='icontains')
    created_by_username = django_filters.CharFilter(field_name='created_by__username', lookup_expr='icontains')
    
    # Tarih aralığı filtreleri
    created_at_after = django_filters.DateFilter(field_name='created_at', lookup_expr='date__gte')
    created_at_before = django_filters.DateFilter(field_name='created_at', lookup_expr='date__lte')
    
    target_completion_date_after = django_filters.DateFilter(field_name='target_completion_date', lookup_expr='date__gte')
    target_completion_date_before = django_filters.DateFilter(field_name='target_completion_date', lookup_expr='date__lte')

    # Genel arama için bir alan (DRF SearchFilter ile birlikte kullanılabilir veya burada tanımlanabilir)
    # search = django_filters.CharFilter(method='custom_search_filter') # Örnek

    class Meta:
        model = WorkOrder
        fields = [ # API'de ?field_name=value şeklinde kullanılabilecek alanlar
            'aircraft_model', 'status', 'assigned_to_assembly_team', 'created_by',
            'aircraft_model_name', 'assigned_to_assembly_team_name', 'created_by_username',
            'created_at_after', 'created_at_before',
            'target_completion_date_after', 'target_completion_date_before',
            'quantity' # Miktar için de filtre eklenebilir (örn: exact, gte, lte)
        ]

    # Örnek custom search metodu (eğer DRF SearchFilter yerine kullanılacaksa)
    # def custom_search_filter(self, queryset, name, value):
    #     return queryset.filter(
    #         Q(notes__icontains=value) |
    #         Q(id__icontains=value) | # ID'ye göre arama için
    #         Q(aircraft_model__name__icontains=value)
    #     )
