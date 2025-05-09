from django.contrib import admin, messages 
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
    list_display = ('__str__', 'aircraft_model', 'quantity', 'status', 'created_by', 'assigned_to_assembly_team', 'created_at')
    list_filter = ('status', 'aircraft_model', 'assigned_to_assembly_team', 'created_by')
    search_fields = ('aircraft_model__name', 'notes', 'id')
    # 'status' ve 'created_by' modelde editable=False olduğu için zaten formda görünmeyecek.
    # Onları burada göstermek için readonly_fields'e ekliyoruz.
    readonly_fields = ('created_by', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        # Yeni bir obje ise (change=False) ve created_by henüz atanmamışsa:
        if not obj.pk:
            obj.created_by = request.user
            # İlk durum ataması artık modelin save() metodunda yapılıyor.
            # if obj.assigned_to_assembly_team:
            #     obj.status = WorkOrderStatusChoices.ASSIGNED
            # else:
            #     obj.status = WorkOrderStatusChoices.PENDING
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """Tek bir WorkOrder silinirken çağrılır."""
        obj.delete() # Modelin override edilmiş delete() metodunu çağırır (iptal etme)

    def delete_queryset(self, request, queryset):
        """Birden fazla WorkOrder seçilip silinirken çağrılır."""
        for obj in queryset:
            obj.delete() # Her bir obje için modelin override edilmiş delete() metodunu çağır


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ('serial_number','part_type','aircraft_model_compatibility','status','produced_by_team','created_by_personnel','production_date','get_installed_aircraft_info', 'updated_at')
    list_filter = ('status', 'part_type', 'aircraft_model_compatibility', 'produced_by_team','created_by_personnel')
    search_fields = ('serial_number', 'part_type__category', 'aircraft_model_compatibility__name')
    readonly_fields = ('serial_number', 'production_date', 'updated_at', # YENİ
        'created_by_personnel', 'get_installed_aircraft_info')

    def get_form(self, request, obj=None, **kwargs):
        # ... (mevcut get_form metodunuz) ...
        # Eğer work_order'ı Part modelinden kaldırdıysanız,
        # bu metodun aircraft_model_compatibility ile ilgili kısmı da
        # artık work_order'a referans vermemeli. Bu kısmı kontrol edin.
        # Şimdilik o kısmı olduğu gibi bırakıyorum, ama Part.work_order kaldırıldıysa
        # obj and obj.work_order koşulu çalışmayacaktır.
        form = super().get_form(request, obj, **kwargs)
        # if obj and obj.work_order: # Part modelinde work_order artık yok.
        #     form.base_fields['aircraft_model_compatibility'].initial = obj.work_order.aircraft_model
        #     form.base_fields['aircraft_model_compatibility'].disabled = True
        return form

    # produced_by_team için dinamik filtreleme (formfield_for_foreignkey ile denenebilir ama karmaşık olabilir):
    # def formfield_for_foreignkey(self, db_field, request, **kwargs):
    #     if db_field.name == "produced_by_team":
    #         # Burada request.POST veya request.GET üzerinden o an seçili part_type alınmaya çalışılabilir
    #         # ancak form ilk yüklenirken bu bilgi olmayabilir.
    #         # Ya da bir JS çözümü gerekir.
    #         # Şimdilik modeldeki clean() ile yetiniyoruz.
    #         pass
    #     return super().formfield_for_foreignkey(db_field, request, **kwargs)
    def delete_model(self, request, obj):
        """Tek bir Part silinirken çağrılır."""
        obj.delete() # Modelin override edilmiş delete() metodunu çağırır (yumuşak silme)

    def delete_queryset(self, request, queryset):
        """Birden fazla Part seçilip silinirken çağrılır."""
        for obj in queryset:
            obj.delete() # Her bir obje için modelin override edilmiş delete() metodunu çağır
        # Daha verimli bir toplu güncelleme de düşünülebilir, ama modeldeki delete()
        # karmaşık mantık içeriyorsa tek tek çağırmak daha güvenli olabilir.
        # queryset.update(status=PartStatusChoices.RECYCLED) # Eğer delete() sadece status değiştiriyorsa bu daha hızlı olur.
        # Ancak bizim Part.delete() metodumuzda USED kontrolü vardı, o yüzden tek tek çağırmak daha doğru.

    def save_model(self, request, obj, form, change):
        if not obj.pk: # Eğer yeni bir obje (parça) oluşturuluyorsa
            try:
                # Giriş yapan kullanıcıya karşılık gelen Personel nesnesini bul
                personnel_instance = Personnel.objects.get(user=request.user)
                obj.created_by_personnel = personnel_instance
            except Personnel.DoesNotExist:
                # Eğer giriş yapan kullanıcı bir Personel değilse (örn: sadece superuser)
                # created_by_personnel alanı null kalır (modelde null=True izin veriyor)
                pass
        super().save_model(request, obj, form, change) # Asıl kaydetme işlemi

@admin.register(Aircraft)
class AircraftAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'aircraft_model', 'status', 'assembled_by_team','assembled_by_personnel', 'assembly_date', 'updated_at','work_order')
    list_filter = ('aircraft_model', 'status', 'assembled_by_team', 'assembled_by_personnel', 'work_order')
    search_fields = ('serial_number', 'aircraft_model__name')
    readonly_fields = ('serial_number', 'assembly_date', 'updated_at', 'assembled_by_personnel')
    # autocomplete_fields = ['work_order', 'aircraft_model', 'assembled_by_team', 'wing', 'fuselage', 'tail', 'avionics']

    # Bir Aircraft oluşturulurken veya düzenlenirken:
    # Eğer bir 'work_order' seçilmişse, 'aircraft_model' alanını
    # o iş emrindeki uçak modeline göre otomatik doldur ve salt okunur yap.
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Yeni obje ekleme formunda veya var olan obje düzenleme formunda
        # Eğer obj (mevcut uçak) varsa ve iş emri atanmışsa
        if obj and obj.work_order:
            form.base_fields['aircraft_model'].initial = obj.work_order.aircraft_model
            form.base_fields['aircraft_model'].disabled = True # Salt okunur yapar
        # Yeni obje eklenirken, eğer URL'den work_order_id geliyorsa (bu özel bir implementasyon gerektirir)
        # veya kullanıcı work_order seçtiğinde JS ile aircraft_model'i doldurmak idealdir.
        # Şimdilik modeldeki clean() metodu bu kuralı zorunlu kılacak.
        return form
    
    def delete_model(self, request, obj):
        """Tek bir Aircraft silinirken çağrılır."""
        obj.delete() # Modelin override edilmiş delete() metodunu çağırır (geri dönüştürme)

    def delete_queryset(self, request, queryset):
        """Birden fazla Aircraft seçilip silinirken çağrılır."""
        # ÖNEMLİ: Aircraft silinirken pre_delete sinyali parçaları AVAILABLE yapar.
        # Bu sinyalin her bir obje için tetiklenmesi adına burada da tek tek siliyoruz.
        for obj in queryset:
            obj.delete() # Her bir obje için modelin override edilmiş delete() metodunu çağır

    def save_model(self, request, obj, form, change):
        if not obj.pk: # Eğer yeni bir obje (uçak) oluşturuluyorsa
            try:
                personnel_instance = Personnel.objects.get(user=request.user)
                obj.assembled_by_personnel = personnel_instance
            except Personnel.DoesNotExist:
                pass
        # Modelin kendi save() metodu (seri no atama, parça durum güncelleme vb.)
        # super().save_model() tarafından zaten çağrılacaktır.
        super().save_model(request, obj, form, change)

@admin.register(AircraftModel)
class AircraftModelAdmin(admin.ModelAdmin):
    list_display = ('name',) # Sadece listelensin
    # Bu model için ekleme, değiştirme ve silme yetkilerini kaldırıyoruz
    # çünkü bunlar data migration ile sabit olarak eklendi.
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False # Değiştirmeyi de engelle
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(PartType)
class PartTypeAdmin(admin.ModelAdmin):
    list_display = ('category',) # Sadece listelensin
    # Bu model için de ekleme, değiştirme ve silme yetkilerini kaldırıyoruz.
    # Kategori isimleri sabit.
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        # Eğer PartType'ın 'producible_by_team_type' gibi admin tarafından
        # ayarlanabilir bir alanı olsaydı, has_change_permission True kalabilirdi.
        # Ama şu anki modelimizde PartType sadece 'category' içeriyor ve o da sabit.
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    
@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'team_type',
        'get_produced_item_count',
        'personnel_count',
        'display_personnel_names'  # YENİ EKLENDİ
    )
    list_filter = ('team_type',)
    search_fields = ('name',)
    # Eğer personel sayısı veya isimlerine göre sıralama yapmak isterseniz,
    # bu metotlar doğrudan veritabanı alanı olmadığı için ek ayar gerekir (admin_order_field).
    # Şimdilik bu kadar yeterli olacaktır.


@admin.register(Personnel)
class PersonnelAdmin(admin.ModelAdmin):
    # Personnel.user alanı OneToOneField ve primary_key olduğu için __str__ metodu user.username'i gösterir.
    # Bu yüzden doğrudan 'user' veya '__str__' kullanılabilir.
    list_display = ('user', 'get_full_name', 'team', 'get_team_type') # 'team' alanını ekledik
    list_filter = ('team__team_type', 'team') # Takıma ve takım tipine göre filtreleme
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'team__name') # Kullanıcı ve takım adına göre arama
    autocomplete_fields = ['user', 'team'] # Seçim için arama kutusu (çok sayıda kullanıcı/takım varsa kullanışlı)

    @admin.display(description='Tam Adı', ordering='user__first_name')
    def get_full_name(self, obj):
        return obj.user.get_full_name() if obj.user.get_full_name() else obj.user.username

    @admin.display(description='Takım Tipi', ordering='team__team_type')
    def get_team_type(self, obj):
        if obj.team:
            return obj.team.get_team_type_display()
        return "-"