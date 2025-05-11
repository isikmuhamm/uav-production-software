from rest_framework import serializers
from .models import (
    AircraftModel, PartType, Team, Personnel, User, # User modelini de import edelim
    WorkOrder, Part, Aircraft, # İleride kullanacağımız diğer modeller
    DefinedTeamTypes, PartCategory, AircraftModelChoices, # Enum'lar
    WorkOrderStatusChoices, PartStatusChoices, AircraftStatusChoices
)

class AircraftModelSerializer(serializers.ModelSerializer):
    """
    Hava Aracı Modelleri için Serializer.
    Sabit verileri listelemek için kullanılacak.
    """
    # 'name' alanı choices kullandığı için, 'get_name_display' ile okunabilir etiketini de gönderiyoruz.
    name_display = serializers.CharField(source='get_name_display', read_only=True)

    class Meta:
        model = AircraftModel
        fields = ['id', 'name', 'name_display', 'image_filename', 'image_url']
        read_only_fields = fields # Bu serializer sadece okuma amaçlı olacak

class PartTypeSerializer(serializers.ModelSerializer):
    """
    Parça Tipleri (Kategorileri) için Serializer.
    Sabit verileri listelemek için kullanılacak.
    """
    # 'category' alanı choices kullandığı için, 'get_category_display' ile okunabilir etiketini de gönderiyoruz.
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = PartType
        fields = ['id', 'category', 'category_display']
        read_only_fields = fields # Bu serializer sadece okuma amaçlı olacak




# --- İlerleyen adımlarda detaylandırılacak diğer serializer'lar için taslaklar ---

class UserSerializer(serializers.ModelSerializer):
    """
    Django User modeli için basit bir serializer.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class PersonnelSerializer(serializers.ModelSerializer):
    """
    Personel modeli için serializer.
    """
    user = UserSerializer(read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True, allow_null=True)
    team_id = serializers.IntegerField(source='team.id', read_only=True, allow_null=True) # Takım ID'si de faydalı olabilir
    team_type = serializers.CharField(source='team.team_type', read_only=True, allow_null=True) # Enum key (örn: ASSEMBLY_TEAM)
    team_type_display = serializers.CharField(source='team.get_team_type_display', read_only=True, allow_null=True) # Okunabilir etiket

    class Meta:
        model = Personnel
        # user alanı OneToOne ve PK olduğu için user_id olarak da geçer
        fields = ['user', 'team_id', 'team_name', 'team_type', 'team_type_display']


class TeamSerializer(serializers.ModelSerializer):
    """
    Takım modeli için serializer.
    """
    team_type_display = serializers.CharField(source='get_team_type_display', read_only=True)
    personnel_count = serializers.IntegerField(read_only=True) # Modeldeki metodu kullan
    # display_personnel_names metodu çok uzun olabileceği için API'de doğrudan kullanmak yerine
    # personellere ayrı bir endpoint üzerinden erişim sağlamak daha iyi olabilir.

    class Meta:
        model = Team
        fields = ['id', 'name', 'team_type', 'team_type_display', 'can_perform_assembly', 'personnel_count']





class PartSerializer(serializers.ModelSerializer):
    part_type_display = serializers.CharField(source='part_type.get_category_display', read_only=True)
    aircraft_model_compatibility_name = serializers.CharField(source='aircraft_model_compatibility.get_name_display', read_only=True)
    produced_by_team_name = serializers.CharField(source='produced_by_team.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_personnel_username = serializers.CharField(source='created_by_personnel.user.username', read_only=True, allow_null=True)
    installed_aircraft_info = serializers.CharField(source='get_installed_aircraft_info', read_only=True) # Modeldeki metodu kullan

    # Üretimci parça oluştururken sadece aircraft_model_compatibility'yi gönderecek.
    aircraft_model_compatibility = serializers.PrimaryKeyRelatedField(queryset=AircraftModel.objects.all())
    # Diğerleri (part_type, produced_by_team, created_by_personnel) perform_create içinde atanacak.

    class Meta:
        model = Part
        fields = [
            'id', 'serial_number',
            'part_type', 'part_type_display',
            'aircraft_model_compatibility', 'aircraft_model_compatibility_name',
            'produced_by_team', 'produced_by_team_name',
            'created_by_personnel', 'created_by_personnel_username',
            'production_date', 'updated_at',
            'status', 'status_display',
            'installed_aircraft_info'
        ]
        read_only_fields = [
            'id', 'serial_number', 'production_date', 'updated_at',
            'part_type_display', 'aircraft_model_compatibility_name',
            'produced_by_team_name', 'status_display', 'created_by_personnel_username',
            'installed_aircraft_info',
            'part_type', 'produced_by_team', 'created_by_personnel', 'status' # Bunlar otomatik veya kontrollü atanacak
        ]

class AircraftAssemblySerializer(serializers.Serializer): # Bu zaten vardı
    aircraft_model_id = serializers.IntegerField(write_only=True, help_text="Monte edilecek AircraftModel ID'si")
    work_order_id = serializers.IntegerField(required=False, allow_null=True, write_only=True, help_text="İsteğe bağlı, montajın yapılacağı WorkOrder ID'si")

    def validate_aircraft_model_id(self, value):
        if not AircraftModel.objects.filter(id=value).exists():
            raise serializers.ValidationError("Geçersiz Hava Aracı Modeli ID'si.")
        return value

    def validate_work_order_id(self, value):
        if value: # Sadece ID gönderilmişse kontrol et
            try:
                work_order = WorkOrder.objects.get(id=value)
                if work_order.status in [WorkOrderStatusChoices.COMPLETED, WorkOrderStatusChoices.CANCELLED]:
                    raise serializers.ValidationError("Bu iş emri montaj için uygun durumda değil (tamamlanmış veya iptal edilmiş).")
            except WorkOrder.DoesNotExist:
                raise serializers.ValidationError("Geçersiz İş Emri ID'si.")
        return value


class AircraftSerializer(serializers.ModelSerializer):
    aircraft_model_name = serializers.CharField(source='aircraft_model.get_name_display', read_only=True)
    assembled_by_team_name = serializers.CharField(source='assembled_by_team.name', read_only=True, allow_null=True)
    assembled_by_personnel_username = serializers.CharField(source='assembled_by_personnel.user.username', read_only=True, allow_null=True)
    work_order_info = serializers.CharField(source='work_order.__str__', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    wing_sn = serializers.CharField(source='wing.serial_number', read_only=True, allow_null=True)
    fuselage_sn = serializers.CharField(source='fuselage.serial_number', read_only=True, allow_null=True)
    tail_sn = serializers.CharField(source='tail.serial_number', read_only=True, allow_null=True)
    avionics_sn = serializers.CharField(source='avionics.serial_number', read_only=True, allow_null=True)

    class Meta:
        model = Aircraft
        fields = [
            'id', 'serial_number', 'aircraft_model', 'aircraft_model_name', 'status', 'status_display',
            'assembly_date', 'updated_at',
            'assembled_by_team', 'assembled_by_team_name',
            'assembled_by_personnel', 'assembled_by_personnel_username',
            'work_order', 'work_order_info',
            'wing', 'wing_sn', 'fuselage', 'fuselage_sn',
            'tail', 'tail_sn', 'avionics', 'avionics_sn'
        ]
        read_only_fields = [
            'id', 'serial_number', 'assembly_date', 'updated_at',
            'aircraft_model_name', 'assembled_by_team_name',
            'assembled_by_personnel_username', 'work_order_info', 'status_display',
            'wing_sn', 'fuselage_sn', 'tail_sn', 'avionics_sn',
            # Uçak montajı özel bir endpoint ile yapıldığı için bu alanlar genelde read-only olur.
            'wing', 'fuselage', 'tail', 'avionics', 'status', 'assembled_by_team', 'assembled_by_personnel'
        ]

class WorkOrderSerializer(serializers.ModelSerializer):
    aircraft_model_name = serializers.CharField(source='aircraft_model.get_name_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_username = serializers.SerializerMethodField(read_only=True)
    assigned_to_assembly_team_name = serializers.SerializerMethodField(read_only=True)


    # PrimaryKeyRelatedField'ler POST/PUT isteklerinde ID almak için kullanılır.
    # Modelde null=True, blank=True ise, serializer'da da allow_null=True, required=False olmalı.
    aircraft_model = serializers.PrimaryKeyRelatedField(queryset=AircraftModel.objects.all())
    assigned_to_assembly_team = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), # Validasyonda montaj takımı olup olmadığını kontrol edeceğiz
        allow_null=True,
        required=False
    )
    # created_by alanı API'den gönderilmeyecek, perform_create içinde otomatik atanacak.
    # Bu yüzden fields listesinde olabilir ama read_only veya extra_kwargs ile belirtilmeli.

    class Meta:
        model = WorkOrder
        fields = [
            'id', 'aircraft_model', 'aircraft_model_name', 'quantity',
            'status', 'status_display',
            'created_by', 'created_by_username', # 'created_by' ID'yi, 'created_by_username' kullanıcı adını döndürür
            'assigned_to_assembly_team', 'assigned_to_assembly_team_name',
            'notes', 'created_at', 'updated_at', 'target_completion_date'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'aircraft_model_name', 'status_display',
            'created_by_username', 'assigned_to_assembly_team_name',
            'created_by', # API'den oluşturulurken otomatik atanacağı için read_only
            'status' # Modelin save() metodu veya admin tarafından yönetiliyor, API'den doğrudan set edilmemeli (şimdilik)
        ]


    def get_created_by_username(self, obj):
        if obj.created_by:
            return obj.created_by.username
        return None

    def get_assigned_to_assembly_team_name(self, obj):
        if obj.assigned_to_assembly_team:
            return obj.assigned_to_assembly_team.name
        return None

    def validate_assigned_to_assembly_team(self, value):
        if value and value.team_type != DefinedTeamTypes.ASSEMBLY_TEAM:
            raise serializers.ValidationError(f"Seçilen takım '{value.name}' bir montaj takımı değildir.")
        return value

    def validate(self, data):
        # Yeni iş emri oluşturulurken gerekli alan kontrolleri
        if not self.instance: # Sadece create sırasında
            if 'aircraft_model' not in data or data.get('aircraft_model') is None:
                raise serializers.ValidationError({"aircraft_model": "Hava aracı modeli zorunludur."})
            if 'quantity' not in data or data.get('quantity') is None:
                 raise serializers.ValidationError({"quantity": "Miktar zorunludur."})
            elif not isinstance(data.get('quantity'), int) or data.get('quantity') < 1:
                raise serializers.ValidationError({"quantity": "Miktar pozitif bir tam sayı olmalıdır."})
        return data
