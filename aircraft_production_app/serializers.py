from rest_framework import serializers
from .models import (
    AircraftModel, PartType, Team, Personnel, User,
    WorkOrder, Part, Aircraft,
    DefinedTeamTypes, PartCategory, AircraftModelChoices,
    WorkOrderStatusChoices, PartStatusChoices, AircraftStatusChoices
)

class AircraftModelSerializer(serializers.ModelSerializer):
    """
    AircraftModel modelini okuma amaçlı serileştirir.
    Kullanan View: AircraftModelViewSet (vs.)
    """
    name_display = serializers.CharField(
        source='get_name_display',
        read_only=True,
        help_text="Model adının okunabilir sürümü."
    )

    class Meta:
        model = AircraftModel
        fields = ['id', 'name', 'name_display', 'image_filename', 'image_url']
        read_only_fields = fields

class PartTypeSerializer(serializers.ModelSerializer):
    """
    PartType modelini okuma amaçlı serileştirir.
    """
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True,
        help_text="Parça kategorisinin okunabilir sürümü."
    )

    class Meta:
        model = PartType
        fields = ['id', 'category', 'category_display']
        read_only_fields = fields

class UserSerializer(serializers.ModelSerializer):
    """
    User modelini temel alan alanları sergileyen serializer.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class PersonnelSerializer(serializers.ModelSerializer):
    """
    Personnel modelini serileştirir ve Personelin takım/user bilgilerini yönetir.
    """
    user_username = serializers.CharField(
        source='user.username',
        read_only=True,
        help_text="Personel ile ilişkili kullanıcının kullanıcı adı."
    )
    user_email = serializers.EmailField(
        source='user.email',
        read_only=True,
        help_text="Personel ile ilişkili kullanıcının e-posta adresi."
    )
    team_name = serializers.CharField(
        source='team.name',
        read_only=True,
        allow_null=True,
        help_text="Personelin dahil olduğu takımın adı (isteğe bağlı)."
    )
    team_type = serializers.CharField(
        source='team.team_type',
        read_only=True,
        allow_null=True,
        help_text="Takım tipi (ör. ASSEMBLY_TEAM)."
    )
    team_type_display = serializers.CharField(
        source='team.get_team_type_display',
        read_only=True,
        allow_null=True,
        help_text="Takım tipinin okunabilir sürümü."
    )
    team = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(),
        allow_null=True,
        required=False,
        help_text="Takım ID'si."
    )

    class Meta:
        model = Personnel
        fields = [
            'user', 'user_username', 'user_email', 'team',
            'team_name', 'team_type', 'team_type_display'
        ]
        read_only_fields = [
            'user', 'user_username', 'user_email',
            'team_name', 'team_type', 'team_type_display'
        ]

class TeamSerializer(serializers.ModelSerializer):
    """
    Team modelini serileştirir ve takım bilgilerini gösterir.
    """
    team_type_display = serializers.CharField(
        source='get_team_type_display',
        read_only=True,
        help_text="Takım tipinin okunabilir sürümü (ör. Montaj Takımı)."
    )
    personnel_count = serializers.IntegerField(
        read_only=True,
        help_text="Takımda bulunan personel sayısı."
    )

    class Meta:
        model = Team
        fields = [
            'id', 'name', 'team_type', 'team_type_display',
            'can_perform_assembly', 'personnel_count'
        ]

class PartSerializer(serializers.ModelSerializer):
    """
    Part modelini serileştirir ve parça bilgilerini yönetir.
    """
    part_type_display = serializers.CharField(
        source='part_type.get_category_display',
        read_only=True,
        help_text="Parça tipinin okunabilir kategorisi."
    )
    aircraft_model_compatibility_name = serializers.CharField(
        source='aircraft_model_compatibility.get_name_display',
        read_only=True,
        help_text="Parçanın uyumlu olduğu hava aracı modelinin adı."
    )
    produced_by_team_name = serializers.CharField(
        source='produced_by_team.name',
        read_only=True,
        help_text="Parçayı üreten takımın adı."
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True,
        help_text="Parçanın durumunun okunabilir sürümü."
    )
    created_by_personnel_username = serializers.CharField(
        source='created_by_personnel.user.username',
        read_only=True,
        allow_null=True,
        help_text="Parçayı oluşturan personelin kullanıcı adı."
    )
    installed_aircraft_info = serializers.CharField(
        source='get_installed_aircraft_info',
        read_only=True,
        help_text="Parçanın monte edildiği hava aracı bilgisi."
    )
    aircraft_model_compatibility = serializers.PrimaryKeyRelatedField(
        queryset=AircraftModel.objects.all(),
        help_text="Parçanın uyumlu olduğu hava aracı modeli ID'si."
    )

    class Meta:
        model = Part
        fields = [
            'id', 'serial_number', 'part_type', 'part_type_display',
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
            'part_type', 'produced_by_team', 'created_by_personnel', 'status'
        ]

class AircraftAssemblySerializer(serializers.Serializer):
    """
    AircraftModel ID'si vb. alarak Hava Aracı montajını yönetmek için kullanılan serializer.
    """
    aircraft_model_id = serializers.IntegerField(
        write_only=True,
        help_text="Monte edilecek AircraftModel ID'si."
    )
    work_order_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True,
        help_text="İsteğe bağlı, montajın yapılacağı WorkOrder ID'si."
    )

    def validate_aircraft_model_id(self, value):
        """
        Model ID geçerliliğini kontrol eder.
        """
        if not AircraftModel.objects.filter(id=value).exists():
            raise serializers.ValidationError("Geçersiz Hava Aracı Modeli ID'si.")
        return value

    def validate_work_order_id(self, value):
        """
        İş emrinin montaj için uygun olup olmadığını kontrol eder.
        """
        if value:
            try:
                work_order = WorkOrder.objects.get(id=value)
                if work_order.status in [WorkOrderStatusChoices.COMPLETED, WorkOrderStatusChoices.CANCELLED]:
                    raise serializers.ValidationError("Bu iş emri montaj için uygun durumda değil (tamamlanmış veya iptal edilmiş).")
            except WorkOrder.DoesNotExist:
                raise serializers.ValidationError("Geçersiz İş Emri ID'si.")
        return value

class AircraftSerializer(serializers.ModelSerializer):
    """
    Aircraft modelini serileştirir ve montaj durumunu gösterir.
    """
    aircraft_model_name = serializers.CharField(
        source='aircraft_model.get_name_display',
        read_only=True,
        help_text="Hava aracının modeli (okunabilir)."
    )
    assembled_by_team_name = serializers.CharField(
        source='assembled_by_team.name',
        read_only=True,
        allow_null=True,
        help_text="Montajı yapan takımın adı."
    )
    assembled_by_personnel_username = serializers.CharField(
        source='assembled_by_personnel.user.username',
        read_only=True,
        allow_null=True,
        help_text="Montajı yapan personelin kullanıcı adı."
    )
    work_order_info = serializers.CharField(
        source='work_order.__str__',
        read_only=True,
        allow_null=True,
        help_text="İlgili iş emri bilgisi."
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True,
        help_text="Hava aracının durumunun okunabilir sürümü."
    )
    wing_sn = serializers.CharField(
        source='wing.serial_number',
        read_only=True,
        allow_null=True,
        help_text="Kanat parçasının seri numarası."
    )
    fuselage_sn = serializers.CharField(
        source='fuselage.serial_number',
        read_only=True,
        allow_null=True,
        help_text="Gövde parçasının seri numarası."
    )
    tail_sn = serializers.CharField(
        source='tail.serial_number',
        read_only=True,
        allow_null=True,
        help_text="Kuyruk parçasının seri numarası."
    )
    avionics_sn = serializers.CharField(
        source='avionics.serial_number',
        read_only=True,
        allow_null=True,
        help_text="Aviyonik parçasının seri numarası."
    )

    class Meta:
        model = Aircraft
        fields = [
            'id', 'serial_number', 'aircraft_model', 'aircraft_model_name',
            'status', 'status_display',
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
            'wing', 'fuselage', 'tail', 'avionics', 'status', 'assembled_by_team', 'assembled_by_personnel'
        ]

class WorkOrderSerializer(serializers.ModelSerializer):
    """
    WorkOrder modelini serileştirir ve iş emirlerini yönetir.
    """
    aircraft_model_name = serializers.CharField(
        source='aircraft_model.get_name_display',
        read_only=True,
        help_text="İş emri için belirtilen hava aracı modelinin okunabilir adı."
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True,
        help_text="İş emrinin durumunun okunabilir sürümü."
    )
    created_by_username = serializers.SerializerMethodField(
        read_only=True,
        help_text="İş emrini oluşturan kullanıcının kullanıcı adı."
    )
    assigned_to_assembly_team_name = serializers.SerializerMethodField(
        read_only=True,
        help_text="İş emri için atanan montaj takımının adı."
    )
    aircraft_model = serializers.PrimaryKeyRelatedField(
        queryset=AircraftModel.objects.all(),
        help_text="İş emri için hava aracı modeli ID'si."
    )
    assigned_to_assembly_team = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(),
        allow_null=True,
        required=False,
        help_text="İş emri için atanan montaj takımı ID'si."
    )

    class Meta:
        model = WorkOrder
        fields = [
            'id', 'aircraft_model', 'aircraft_model_name', 'quantity',
            'status', 'status_display',
            'created_by', 'created_by_username',
            'assigned_to_assembly_team', 'assigned_to_assembly_team_name',
            'notes', 'created_at', 'updated_at', 'target_completion_date'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'aircraft_model_name', 'status_display',
            'created_by_username', 'assigned_to_assembly_team_name',
            'created_by',
            'status'
        ]

    def get_created_by_username(self, obj):
        """Oluşturan kullanıcının adını döndürür."""
        if obj.created_by:
            return obj.created_by.username
        return None

    def get_assigned_to_assembly_team_name(self, obj):
        """İlgili montaj takımının adını döndürür."""
        if obj.assigned_to_assembly_team:
            return obj.assigned_to_assembly_team.name
        return None

    def validate_assigned_to_assembly_team(self, value):
        """
        Atanan takımın bir montaj takımı olup olmadığını doğrular.
        """
        if value and value.team_type != DefinedTeamTypes.ASSEMBLY_TEAM:
            raise serializers.ValidationError(f"Seçilen takım '{value.name}' bir montaj takımı değildir.")
        return value

    def validate(self, data):
        """
        Yeni iş emri oluştururken gerekli alanları ve değerleri doğrular.
        """
        if not self.instance:
            if 'aircraft_model' not in data or data.get('aircraft_model') is None:
                raise serializers.ValidationError({"aircraft_model": "Hava aracı modeli zorunludur."})
            if 'quantity' not in data or data.get('quantity') is None:
                raise serializers.ValidationError({"quantity": "Miktar zorunludur."})
            elif not isinstance(data.get('quantity'), int) or data.get('quantity') < 1:
                raise serializers.ValidationError({"quantity": "Miktar pozitif bir tam sayı olmalıdır."})
        return data
