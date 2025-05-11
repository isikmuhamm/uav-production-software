from django.contrib import admin, messages
from django.core.exceptions import ValidationError as DjangoValidationError 
from .models import (
    Team,
    Personnel,
    PartType,
    AircraftModel,
    WorkOrder,
    Part,
    Aircraft, 
)


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    """WorkOrder modelini Admin arayüzünde yönetmek için özel ayarlar."""
    list_display = ('__str__', 'aircraft_model', 'quantity', 'status', 'created_by', 'assigned_to_assembly_team', 'created_at')
    list_filter = ('status', 'aircraft_model', 'assigned_to_assembly_team', 'created_by')
    search_fields = ('aircraft_model__name', 'notes', 'id')
    readonly_fields = ('created_by', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        """Yeni bir iş emri oluşturulurken created_by alanını ayarlar."""
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """Tek bir iş emrini iptal (delete override) eder."""
        obj.delete()

    def delete_queryset(self, request, queryset):
        """Birden fazla iş emrini toplu iptal (delete override) eder."""
        for obj in queryset:
            obj.delete()


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    """Part modelini Admin arayüzünde yönetmek için özel ayarlar."""
    list_display = ('serial_number','part_type','aircraft_model_compatibility','status','produced_by_team','created_by_personnel','production_date','get_installed_aircraft_info', 'updated_at')
    list_filter = ('status', 'part_type', 'aircraft_model_compatibility', 'produced_by_team','created_by_personnel')
    search_fields = ('serial_number', 'part_type__category', 'aircraft_model_compatibility__name')
    readonly_fields = ('serial_number', 'production_date', 'updated_at', 'created_by_personnel', 'get_installed_aircraft_info')

    def get_form(self, request, obj=None, **kwargs):
        """Form oluşturulurken özel logic eklemek için override."""
        form = super().get_form(request, obj, **kwargs)
        return form

    def delete_model(self, request, obj):
        """Tek bir parçayı geri dönüştürmek (delete override) için kullanılır."""
        try:
            obj.delete()
            self.message_user(request, f"'{obj}' başarıyla geri dönüştürüldü.", messages.SUCCESS)
        except DjangoValidationError as e:
            self.message_user(request, e.messages[0] if e.messages else str(e), messages.ERROR)

    def delete_queryset(self, request, queryset):
        """Birden fazla parçayı toplu geri dönüştürmek (delete override) için kullanılır."""
        deleted_count = 0
        errors = []
        for obj in queryset:
            try:
                obj.delete()
                deleted_count += 1
            except DjangoValidationError as e:
                errors.append(f"'{obj}': {e.messages[0] if e.messages else str(e)}")

        if deleted_count > 0:
            self.message_user(request, f"{deleted_count} parça başarıyla geri dönüştürüldü.", messages.SUCCESS)
        if errors:
            for error_msg in errors:
                self.message_user(request, error_msg, messages.ERROR)

    def save_model(self, request, obj, form, change):
        """Yeni parçaya created_by_personnel atamak için override."""
        if not obj.pk:
            try:
                personnel_instance = Personnel.objects.get(user=request.user)
                obj.created_by_personnel = personnel_instance
            except Personnel.DoesNotExist:
                pass
        super().save_model(request, obj, form, change)


@admin.register(Aircraft)
class AircraftAdmin(admin.ModelAdmin):
    """Aircraft modelini Admin arayüzünde yönetmek için özel ayarlar."""
    list_display = ('serial_number', 'aircraft_model', 'status', 'assembled_by_team','assembled_by_personnel', 'assembly_date', 'updated_at','work_order')
    list_filter = ('aircraft_model', 'status', 'assembled_by_team', 'assembled_by_personnel', 'work_order')
    search_fields = ('serial_number', 'aircraft_model__name')
    readonly_fields = ('serial_number', 'assembly_date', 'updated_at', 'assembled_by_personnel')

    def get_form(self, request, obj=None, **kwargs):
        """Form oluşturulurken iş emrine göre aircraft_model alanını otomatik ayarlar."""
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.work_order:
            form.base_fields['aircraft_model'].initial = obj.work_order.aircraft_model
            form.base_fields['aircraft_model'].disabled = True
        return form
    
    def delete_model(self, request, obj):
        """Tek bir hava aracını geri dönüştürmek (delete override) için kullanılır."""
        obj.delete()

    def delete_queryset(self, request, queryset):
        """Birden fazla hava aracını toplu geri dönüştürmek (delete override) için kullanılır."""
        for obj in queryset:
            obj.delete()

    def save_model(self, request, obj, form, change):
        """Yeni hava aracı oluştururken assembled_by_personnel alanını ayarlar."""
        if not obj.pk:
            try:
                personnel_instance = Personnel.objects.get(user=request.user)
                obj.assembled_by_personnel = personnel_instance
            except Personnel.DoesNotExist:
                pass
        super().save_model(request, obj, form, change)


@admin.register(AircraftModel)
class AircraftModelAdmin(admin.ModelAdmin):
    """AircraftModel kayıtlarını yalnızca görüntüleme amacıyla kullanılır."""
    list_display = ('name',)
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PartType)
class PartTypeAdmin(admin.ModelAdmin):
    """PartType kayıtlarını yalnızca görüntüleme amacıyla kullanılır."""
    list_display = ('category',)
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """Team modelini Admin arayüzünde yönetmek için özel ayarlar."""
    list_display = (
        'name',
        'team_type',
        'get_produced_item_count',
        'personnel_count',
        'display_personnel_names'
    )
    list_filter = ('team_type',)
    search_fields = ('name',)


@admin.register(Personnel)
class PersonnelAdmin(admin.ModelAdmin):
    """Personnel modelini Admin arayüzünde yönetmek için özel ayarlar."""
    list_display = ('user', 'get_full_name', 'team', 'get_team_type')
    list_filter = ('team__team_type', 'team')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'team__name')
    autocomplete_fields = ['user', 'team']

    @admin.display(description='Tam Adı', ordering='user__first_name')
    def get_full_name(self, obj):
        """Personelin tam adını döndürür, boşsa kullanıcı adını kullanır."""
        return obj.user.get_full_name() if obj.user.get_full_name() else obj.user.username

    @admin.display(description='Takım Tipi', ordering='team__team_type')
    def get_team_type(self, obj):
        """Personelin bağlı olduğu takımın tipini döndürür."""
        if obj.team:
            return obj.team.get_team_type_display()
        return "-"