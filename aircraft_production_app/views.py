from rest_framework.decorators import api_view, permission_classes, authentication_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView # APIView'ı import et
from rest_framework import viewsets, filters, permissions, status as drf_status, serializers # permissions'ı import et
from django_filters.rest_framework import DjangoFilterBackend # Bunu da import edin

from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError # Django'dan gelen ValidationError
from django.db import transaction, models # transaction ve models'ı import et

from .models import Part, PartType, AircraftModel, Aircraft, Team, Personnel, PartCategory, DefinedTeamTypes, PartStatusChoices, AircraftStatusChoices, WorkOrder, WorkOrderStatusChoices # Modelleri import et
from .serializers import AircraftModelSerializer, AircraftSerializer, AircraftAssemblySerializer, PartTypeSerializer, TeamSerializer, PersonnelSerializer, PartSerializer, WorkOrderSerializer # Mevcut serializer'lar
from .permissions import IsAdminOrReadOnly, IsOwnerTeamOrAdminForPart,  IsAssemblyTeamMemberOrAdminForAircraft, CanAssembleAircraft, IsNotAssemblyTeamForCreate
from .filters import WorkOrderFilter, PartFilter, AircraftFilter


def frontend_login_view(request):
    """Personel giriş sayfasını sunar."""
    return render(request, 'aircraft_production_app/login.html')

def frontend_dashboard_view(request): # Tek bir dashboard view'ı, JS rolü yönetecek
    return render(request, 'aircraft_production_app/dashboard_admin.html') # Hepsi aynı ana şablonu kullanacak

def frontend_register_view(request):
    """Yeni kullanıcı kayıt sayfasını sunar."""
    return render(request, 'aircraft_production_app/register.html')


# === YENİ KAYIT İÇİN SERIALIZER VE VIEW ===
from django.contrib.auth.models import User # User modelini import et

class UserRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, style={'input_type': 'password'}, label="Confirm password")

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Bu kullanıcı adı zaten mevcut.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Bu e-posta adresi zaten kayıtlı.")
        return value

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password2": "Şifreler eşleşmiyor."})
        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'] # create_user şifreyi hashler
        )
        # Yeni kullanıcı için otomatik olarak bir Personel kaydı oluştur, takım atama.
        Personnel.objects.create(user=user, team=None)
        return user

class UserRegisterAPIView(APIView):
    permission_classes = [permissions.AllowAny] # Herkes kayıt olabilir

    def post(self, request, *args, **kwargs):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Başarılı kayıt sonrası token döndürmek yerine sadece başarı mesajı
            return Response(
                {"message": f"Kullanıcı '{user.username}' başarıyla oluşturuldu. Lütfen giriş yapın."},
                status=drf_status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)


# Oturum açmış kullanıcı bilgilerini döndürür
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user_info(request):
    """
    Giriş yapmış kullanıcının temel bilgilerini ve personel profilini döndürür.
    """
    user = request.user
    try:
        personnel = user.personnel # OneToOneField ile erişim
        personnel_data = PersonnelSerializer(personnel).data
    except Personnel.DoesNotExist:
        personnel_data = None
    
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'personnel_profile': personnel_data
    })

class AircraftModelViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Hava Aracı Modellerini listeler ve detaylarını görüntüler.
    Bu veriler sabit olduğu için sadece okuma.
    """
    queryset = AircraftModel.objects.all()
    serializer_class = AircraftModelSerializer
    permission_classes = [permissions.IsAuthenticated]

class PartTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Parça Tiplerini (Kategorilerini) listeler ve detaylarını görüntüler.
    Bu veriler sabit olduğu için sadece okuma.
    """
    queryset = PartType.objects.all()
    serializer_class = PartTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

class TeamViewSet(viewsets.ModelViewSet): # ReadOnlyModelViewSet -> ModelViewSet
    """
    Takımları listeler ve detaylarını görüntüler.
    Adminler CRUD yapabilir.
    """
    queryset = Team.objects.all().prefetch_related('members') # Performans için
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAdminUser] # Sadece adminler CRUD yapabilsin

    def get_queryset(self):
        """
        İsteğe bağlı olarak 'team_type' query parametresine göre takımları filtreler.
        """
        queryset = Team.objects.all().prefetch_related('members') # Temel queryset
        
        team_type_filter = self.request.query_params.get('team_type')
        if team_type_filter:
            # Gelen team_type_filter değerinin DefinedTeamTypes içinde geçerli bir key olup olmadığını kontrol edebiliriz.
            # Örneğin: if team_type_filter in DefinedTeamTypes.values:
            # Şimdilik doğrudan filtrelemeye çalışıyoruz.
            # DefinedTeamTypes.ASSEMBLY_TEAM gibi bir enum key'i bekleniyor.
            queryset = queryset.filter(team_type=team_type_filter)
            
        return queryset

class PersonnelViewSet(viewsets.ModelViewSet):
    """
    Personelleri listeler ve detaylarını görüntüler.
    Adminler personellerin takımlarını atayabilir/değiştirebilir ve personelleri silebilir.
    """
    queryset = Personnel.objects.select_related('user', 'team').all()
    serializer_class = PersonnelSerializer
    permission_classes = [permissions.IsAdminUser] # Sadece adminler bu işlemleri yapabilsin
    lookup_field = 'user' # URL'de /api/personnel/{user_id}/ şeklinde erişim için

    def perform_create(self, serializer):
        # Bu endpoint üzerinden yeni User + Personnel oluşturulması beklenmiyor.
        # UserRegisterAPIView bu işi yapıyor.
        # Eğer bir User var ama Personnel'i yoksa ve buraya bir istek gelirse,
        # serializer'ın create metodu (eğer varsa) bunu yönetebilir.
        # Şimdilik, bu endpoint'ten yeni personel oluşturmayı engelliyoruz.
        raise serializers.ValidationError({"detail": "Yeni personel oluşturma bu endpoint üzerinden desteklenmiyor. Lütfen kayıt sayfasını kullanın ve ardından buradan takım atayın."})

class PartViewSet(viewsets.ModelViewSet):
    """
    Üretilmiş Parçaları yönetmek için API endpoint'i.
    - Üretimci kendi takımının ürettiği parçaları listeler.
    - Üretimci kendi takımının uzmanlığına göre yeni parça üretebilir.
    - Üretimci kendi takımının ürettiği parçaları geri dönüştürebilir.
    """
    serializer_class = PartSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_class = PartFilter # Özel FilterSet'imiz

    ordering_fields = [ # API üzerinden hangi alanlara göre sıralama yapılabileceği
        'id', 
        'serial_number',
        'part_type__category', 
        'aircraft_model_compatibility__name', 
        'status', 
        'produced_by_team__name', 
        'production_date',
        'created_by_personnel__user__username'
    ]
    search_fields = [ # Genel arama (DataTable'ın sağ üstündeki arama kutusu) hangi alanlarda çalışsın?
        'id',
        'serial_number', 
        'part_type__category', # PartType'ın category alanı üzerinden
        'aircraft_model_compatibility__name', # AircraftModel'in name alanı üzerinden
        'produced_by_team__name',
        'created_by_personnel__user__username'
    ]

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            # Admin, Montajcı (tüm parçalar), Üretimci (kendi parçaları)
            if self.request.user.is_authenticated:
                if self.request.user.is_staff or self.request.user.is_superuser:
                    self.permission_classes = [permissions.IsAdminUser]
                elif hasattr(self.request.user, 'personnel') and self.request.user.personnel.team and self.request.user.personnel.team.can_perform_assembly():
                    self.permission_classes = [permissions.IsAuthenticated] # Montajcı tüm parçaları geri dönüştürebilir
                else: # Üretimci için
                    self.permission_classes = [permissions.IsAuthenticated, IsOwnerTeamOrAdminForPart]
            else:
                self.permission_classes = [permissions.IsAuthenticated] # Fallback
        elif self.action == 'create':
            self.permission_classes = [permissions.IsAuthenticated, IsNotAssemblyTeamForCreate]
        else: # list, retrieve
            self.permission_classes = [permissions.IsAuthenticated] # Herkes listeleyebilir (get_queryset filtreler)
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        # Temel queryset, tüm parçaları içerir. Filtreleme backend'leri bunu daraltacak.
        queryset = Part.objects.all().select_related(
            'part_type', 
            'aircraft_model_compatibility', 
            'produced_by_team', 
            'created_by_personnel__user' # Kullanıcı adına erişim için
        )

        if user.is_superuser or user.is_staff: # Adminler tümünü (filtrelenmişse filtrelenmiş halini) görür
            return queryset.order_by('-production_date')
        
        try:
            personnel = user.personnel
            if personnel.team:
                if personnel.team.can_perform_assembly(): # Montajcı tüm parçaları (filtrelenmişse filtrelenmiş halini) görür
                    # Filtreleme DjangoFilterBackend tarafından yapılacak.
                    if not self.request.query_params.get('status'):
                         return queryset.filter(status=PartStatusChoices.AVAILABLE).order_by('-production_date')
                    return queryset.order_by('-production_date') # Status filtresi varsa, tümünü bu filtreye göre döndür
                else: # Üretim takımı ise sadece kendi ürettiklerini (tüm durumlar filtrelenebilir)
                    return queryset.filter(produced_by_team=personnel.team).order_by('-production_date')
        except Personnel.DoesNotExist:
            return queryset.none() # Personel profili olmayanlar (admin değilse)
            
        return queryset.none() # Diğer tüm durumlar için

    def perform_create(self, serializer):
        user = self.request.user
        try:
            personnel = user.personnel
            if not personnel or not personnel.team:
                raise serializers.ValidationError("Parça üretebilmek için bir takıma atanmış olmalısınız.")
            
            team = personnel.team

            # Takımın üretebileceği parça kategorisini bul
            producible_category_enum_member = team.get_producible_part_category()
            if not producible_category_enum_member and not (user.is_staff or user.is_superuser): # Adminler için bu kontrol esnetilebilir
                raise serializers.ValidationError(f"Takımınızın ({team.name}) üretebileceği bir parça kategorisi tanımlanmamış.")
            
            part_type_instance = get_object_or_404(PartType, category=producible_category_enum_member.value)
            
            if not team.members.exists(): # Modelin clean() metodu da kontrol ediyor ama burada da edebiliriz.
                 raise serializers.ValidationError(f"Takımınızda ({team.name}) kayıtlı personel bulunmamaktadır. Üretim yapabilmek için önce personel ekleyiniz.")

            # aircraft_model_compatibility serializer.validated_data'dan gelecek
            serializer.save(
                part_type=part_type_instance,
                produced_by_team=team,
                created_by_personnel=personnel,
                status=PartStatusChoices.AVAILABLE # Yeni üretilen parça direkt mevcut olsun
            )
        except Personnel.DoesNotExist:
            raise serializers.ValidationError("Bu işlemi yapmak için geçerli bir personel kaydınız bulunmuyor.")




    def perform_destroy(self, instance):
        """
        Bir parçayı silmek yerine durumunu 'RECYCLED' yapar (yumuşak silme).
        Modelin kendi delete() metodu bu işi yapıyordu.
        """
        try:
            instance.delete() # Modeldeki override edilmiş delete() metodunu çağırır
        except DjangoValidationError as e: # Modelin delete metodundan gelebilecek validasyon hatası
            error_messages = e.messages if hasattr(e, 'messages') else str(e)
            raise serializers.ValidationError(error_messages)


class AssembleAircraftAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, CanAssembleAircraft]
    serializer_class = AircraftAssemblySerializer # Gelen isteği doğrulamak için

    @transaction.atomic # Tüm işlemler ya başarılı olmalı ya da geri alınmalı
    def post(self, request, *args, **kwargs):
        serializer = AircraftAssemblySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        aircraft_model_id = validated_data.get('aircraft_model_id')
        work_order_id = validated_data.get('work_order_id')

        try:
            personnel = request.user.personnel
            # İzin sınıfı zaten kontrol ediyor ama burada da bir güvence olabilir.
            if not personnel.team or not personnel.team.can_perform_assembly():
                return Response({"error": "Bu işlemi yapmak için yetkili bir montaj takımına üye olmalısınız."}, status=drf_status.HTTP_403_FORBIDDEN)
            assembling_team = personnel.team
        except Personnel.DoesNotExist:
            return Response({"error": "Geçerli bir personel kaydınız bulunmuyor."}, status=drf_status.HTTP_403_FORBIDDEN)

        target_aircraft_model = get_object_or_404(AircraftModel, id=aircraft_model_id)
        target_work_order = None
        if work_order_id:
            target_work_order = get_object_or_404(WorkOrder, id=work_order_id)
            if target_work_order.aircraft_model != target_aircraft_model:
                return Response({"error": "İş emrindeki uçak modeli ile seçilen montaj modeli uyuşmuyor."}, status=drf_status.HTTP_400_BAD_REQUEST)
            if target_work_order.status in [WorkOrderStatusChoices.COMPLETED, WorkOrderStatusChoices.CANCELLED]:
                return Response({"error": "Bu iş emri tamamlanmış veya iptal edilmiş, yeni uçak monte edilemez."}, status=drf_status.HTTP_400_BAD_REQUEST)


        # Gerekli parçaları bulma mantığı
        required_parts = {}
        missing_parts_info = []

        part_categories_map = {
            'wing': PartCategory.WING,
            'fuselage': PartCategory.FUSELAGE,
            'tail': PartCategory.TAIL,
            'avionics': PartCategory.AVIONICS,
        }

        for slot_name, category_value in part_categories_map.items():
            part_type_for_slot = get_object_or_404(PartType, category=category_value)

            available_part = Part.objects.filter(
                part_type=part_type_for_slot,
                aircraft_model_compatibility=target_aircraft_model,
                status=PartStatusChoices.AVAILABLE
            ).order_by('production_date').first() # FIFO: İlk üretilen uygun parçayı al

            if not available_part:
                missing_parts_info.append(f"{target_aircraft_model.get_name_display()} için {part_type_for_slot.get_category_display()}")
            else:
                required_parts[slot_name] = available_part

        if missing_parts_info:
            return Response(
                {"error": "Montaj için yeterli parça bulunamadı.", "missing_parts": missing_parts_info},
                status=drf_status.HTTP_400_BAD_REQUEST
            )

        # Tüm parçalar bulundu, uçağı oluştur
        try:
            new_aircraft = Aircraft(
                aircraft_model=target_aircraft_model,
                assembled_by_team=assembling_team,
                assembled_by_personnel=personnel,
                work_order=target_work_order, # None olabilir
                wing=required_parts.get('wing'),
                fuselage=required_parts.get('fuselage'),
                tail=required_parts.get('tail'),
                avionics=required_parts.get('avionics')
            )
            new_aircraft.full_clean() # Modelin clean() metodunu çalıştır (parça uyumluluğu vs.)
            new_aircraft.save() # Bu, seri no atama ve parça durumlarını USED yapma mantığını tetikler

            # Başarılı cevap için uçağı serialize et
            response_serializer = AircraftSerializer(new_aircraft)
            return Response(response_serializer.data, status=drf_status.HTTP_201_CREATED)

        except DjangoValidationError as e:
            return Response({"error": "Uçak oluşturulurken doğrulama hatası.", "details": e.message_dict if hasattr(e, 'message_dict') else e.messages},
                            status=drf_status.HTTP_400_BAD_REQUEST)
        except Exception as e: # Beklenmedik diğer hatalar için
            return Response({"error": "Uçak montajı sırasında bir hata oluştu.", "details": str(e)},
                            status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)


class AircraftViewSet(viewsets.ModelViewSet):
    serializer_class = AircraftSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_class = AircraftFilter
    ordering_fields = [
        'id', 'serial_number', 'aircraft_model__name', 'status',
        'assembly_date', 'assembled_by_team__name', 'work_order__id'
    ]
    search_fields = [
        'id', 'serial_number', 'aircraft_model__name',
        'assembled_by_team__name', 'work_order__id'
    ]

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            # Admin ve uçağı monte eden takımın üyesi geri dönüştürebilir/güncelleyebilir.
            self.permission_classes = [permissions.IsAuthenticated, IsAssemblyTeamMemberOrAdminForAircraft]
        elif self.action == 'create': 
            # Uçak oluşturma normalde AssembleAircraftAPIView ile yapılır.
            # Bu ViewSet üzerinden direkt uçak oluşturma sadece adminlere açık olmalı (manuel kayıt için).
            self.permission_classes = [permissions.IsAdminUser] 
        elif self.action in ['list', 'retrieve']:
            # Adminler ve Montajcılar listeleyebilir. Üretimciler göremez.
            self.permission_classes = [permissions.IsAuthenticated]
        else: # list, retrieve
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        queryset = Aircraft.objects.all().select_related(
            'aircraft_model', 'assembled_by_team', 
            'assembled_by_personnel__user', 'work_order',
            'wing', 'fuselage', 'tail', 'avionics' 
        )
        
        # DjangoFilterBackend filtrelemeyi yapacak.

        if user.is_superuser or user.is_staff:
            return queryset.order_by('-assembly_date')
        
        try:
            personnel = user.personnel
            if personnel and personnel.team and personnel.team.can_perform_assembly():
                # Montajcı kendi takımının monte ettiği uçakları (filtrelenmişse filtrelenmiş halini) görür
                return queryset.filter(assembled_by_team=personnel.team).order_by('-assembly_date')
        except Personnel.DoesNotExist:
            return queryset.none() # Personel profili yoksa (ve admin değilse)
        
        return queryset.none() # Üretimciler veya takımı olmayan personel (admin değilse) uçak listesi görmez
    
    def perform_destroy(self, instance):
        """
        Bir uçağı fiziksel olarak silmek yerine 'RECYCLED' yapar (yumuşak silme).
        Modelin kendi delete() metodu bu işi yapıyordu.
        """
        try:
            instance.delete() # Modeldeki override edilmiş delete() metodunu çağırır
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.detail if hasattr(e, 'detail') else e.messages)
        

class WorkOrderViewSet(viewsets.ModelViewSet): # CRUD işlemleri için ModelViewSet
    serializer_class = WorkOrderSerializer

    filter_backends = [
        DjangoFilterBackend,      # django-filter ile özel filtreleme için
        filters.OrderingFilter,   # ?ordering=alan_adi ile sıralama için
        filters.SearchFilter      # ?search=arama_terimi ile genel arama için
    ]
    filterset_class = WorkOrderFilter # aircraft_production_app/filters.py içinde tanımlayacağız
    
    ordering_fields = [ # API üzerinden hangi alanlara göre sıralama yapılabileceği
        'id', 
        'aircraft_model__name', 
        'quantity', 
        'status', 
        'created_at', 
        'target_completion_date', 
        'assigned_to_assembly_team__name'
    ]
    search_fields = [ # Genel arama (DataTable'ın sağ üstündeki arama kutusu) hangi alanlarda çalışsın?
        'id', 
        'aircraft_model__name', 
        'notes', 
        'assigned_to_assembly_team__name', 
        'created_by__username'
    ]

    def get_permissions(self):
        """
        Action'a göre farklı izinler ata.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [permissions.IsAdminUser] # Sadece adminler iş emri oluşturabilir/değiştirebilir/silebilir
        elif self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.IsAuthenticated] # Adminler ve Montajcılar listeleyebilir
        else:
            self.permission_classes = [permissions.IsAdminUser]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        queryset = WorkOrder.objects.all().select_related(
            'aircraft_model', 
            'created_by', 
            'assigned_to_assembly_team'
        )

        # DjangoFilterBackend filtrelemeyi yapacak.

        if user.is_superuser or user.is_staff: # Adminler (filtrelenmişse) tümünü görebilir
            return queryset.order_by('-created_at')
        
        try:
            personnel = user.personnel
            if personnel and personnel.team and personnel.team.can_perform_assembly(): # Eğer kullanıcı bir Montaj Takımı üyesi ise
                # Montajcılar, kendilerine atanmış veya henüz atanmamış (PENDING, IN_PROGRESS)
                # ve tamamlanmamış/iptal edilmemiş iş emirlerini görür.
                # WorkOrderFilter sınıfı bu filtrelemeyi daha detaylı yapabilir.
                # Şimdilik, montajcıya tüm iş emirlerini (filtrelenmişse filtrelenmiş) gösterelim.
                # Eğer status filtresi varsa, o filtre öncelikli olur.
                visibility_filter = models.Q(assigned_to_assembly_team=personnel.team) | models.Q(assigned_to_assembly_team__isnull=True, status=WorkOrderStatusChoices.PENDING) | models.Q(assigned_to_assembly_team__isnull=True, status=WorkOrderStatusChoices.IN_PROGRESS)

                return queryset.filter(visibility_filter).distinct().order_by('-created_at')
            else: # Diğer roller (örn: Üretimciler) iş emirlerini bu viewset üzerinden görmez.
                return queryset.none()
            
        except Personnel.DoesNotExist:
            return queryset.none() # Personel profili olmayanlar (admin değilse)
        
        return queryset.none() # Diğer tüm durumlar için (örn: üretimci)

    def perform_create(self, serializer):
        # API üzerinden yeni iş emri oluşturulursa, oluşturan kişiyi otomatik ata
        # Status ataması modelin save() metodunda (PENDING/ASSIGNED)
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        """
        Bir iş emrini silmek yerine durumunu 'CANCELLED' yapar ve uçak bağlantılarını keser.
        Modelin kendi delete() metodu bu işi yapıyordu.
        """
        try:
            instance.delete() # Modeldeki override edilmiş delete() metodunu çağırır
        except DjangoValidationError as e:
            error_messages = e.messages if hasattr(e, 'messages') else str(e)
            raise serializers.ValidationError(error_messages)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def StockLevelsAPIView(request):
    """
    Parça veya uçak stok seviyelerini DataTable uyumlu formatta döndürür.
    Query Params:
        - stock_type (str, zorunlu): 'parts' veya 'aircrafts'
        - aircraft_model_id (int, isteğe bağlı): Belirli bir uçak modelini filtreler.
        - part_category_id (int, PartType ID, isteğe bağlı): Belirli bir parça kategorisini filtreler.
        - (DataTable standart parametreleri: draw, start, length, search[value], order[0][column], order[0][dir])
    """
    stock_type = request.query_params.get('stock_type')
    if stock_type not in ['parts', 'aircrafts']:
        return Response({"error": "Geçerli bir 'stock_type' parametresi ('parts' veya 'aircrafts') gereklidir."}, status=drf_status.HTTP_400_BAD_REQUEST)

    user = request.user
    user_personnel = None
    user_team = None
    user_is_admin = user.is_staff or user.is_superuser
    user_can_assemble = False
    user_producible_category_value = None

    try:
        user_personnel = user.personnel
        if user_personnel.team:
            user_team = user_personnel.team
            user_can_assemble = user_team.can_perform_assembly()
            if not user_can_assemble: # Montajcı değilse, üretimcidir
                producible_category_enum = user_team.get_producible_part_category()
                if producible_category_enum:
                    user_producible_category_value = producible_category_enum.value
    except Personnel.DoesNotExist:
        if not user_is_admin: # Admin değilse ve personel profili yoksa boş döner
            return Response({'draw': int(request.query_params.get('draw', 0)), 'recordsTotal': 0, 'recordsFiltered': 0, 'data': []}, status=drf_status.HTTP_200_OK)

    # DataTable parametreleri
    draw = int(request.query_params.get('draw', 0))
    start = int(request.query_params.get('start', 0))
    length = int(request.query_params.get('length', 10))
    if length == -1: # "Tümü" seçeneği için
        length = 999999 

    # Genel filtreler
    aircraft_model_id_filter = request.query_params.get('aircraft_model_id')

    data_list = []
    records_total = 0
    records_filtered = 0

    if stock_type == 'parts':
        part_category_id_filter = request.query_params.get('part_category_id')

        part_types_to_query = PartType.objects.all()
        if not user_is_admin and not user_can_assemble and user_producible_category_value:
            part_types_to_query = part_types_to_query.filter(category=user_producible_category_value)
        if part_category_id_filter:
            part_types_to_query = part_types_to_query.filter(id=part_category_id_filter)

        aircraft_models_for_parts = AircraftModel.objects.all()
        if aircraft_model_id_filter:
            aircraft_models_for_parts = aircraft_models_for_parts.filter(id=aircraft_model_id_filter)

        # Tüm olası (model, part_type) kombinasyonlarını oluştur
        all_combinations = []
        if aircraft_models_for_parts.exists() and part_types_to_query.exists():
            for am_part in aircraft_models_for_parts:
                for pt in part_types_to_query:
                    all_combinations.append({'am_id': am_part.id, 'am_name': am_part.get_name_display(), 
                                             'pt_id': pt.id, 'pt_name': pt.get_category_display()})
        
        records_total = len(all_combinations) # Başlangıçta toplam kayıt sayısı bu

        # Gerçek stok sayılarını al
        part_stock_query = Part.objects
        if aircraft_model_id_filter:
            part_stock_query = part_stock_query.filter(aircraft_model_compatibility_id=aircraft_model_id_filter)
        if part_category_id_filter:
            part_stock_query = part_stock_query.filter(part_type_id=part_category_id_filter)
        
        # Üretimci sadece kendi ürettiği kategorideki parçaların stoğunu görür
        if not user_is_admin and not user_can_assemble and user_producible_category_value:
            part_stock_query = part_stock_query.filter(part_type__category=user_producible_category_value)

        raw_part_stock_data = part_stock_query.values(
            'aircraft_model_compatibility_id', 'part_type_id', 'status'
        ).annotate(count=models.Count('id')).order_by() # order_by() gruplamayı temizler

        # Stok sayılarını (model_id, part_type_id) -> {status: count} şeklinde işle
        processed_part_counts = {} # (am_id, pt_id) -> {status: count}
        for item in raw_part_stock_data:
            key = (item['aircraft_model_compatibility_id'], item['part_type_id'])
            if key not in processed_part_counts: processed_part_counts[key] = {}
            processed_part_counts[key][item['status']] = item['count']

        for combo in all_combinations:
            current_key = (combo['am_id'], combo['pt_id'])
            counts_for_this_combo = processed_part_counts.get(current_key, {})
            
            row_data = {
                "aircraft_model_name": combo['am_name'],
                "part_type_category_display": combo['pt_name'],
                "warning_zero_stock": counts_for_this_combo.get(PartStatusChoices.AVAILABLE.value, 0) == 0
            }
            for status_choice, status_label in PartStatusChoices.choices:
                row_data[status_choice] = counts_for_this_combo.get(status_choice, 0)
            
            data_list.append(row_data)
        
        records_filtered = len(data_list) # Filtreleme sonrası (şimdilik tüm kombinasyonlar)
        # Burada DataTable search ve ordering uygulanabilir, şimdilik basit tutuyoruz.
        data_list = data_list[start : start + length]

    elif stock_type == 'aircrafts':
        if not (user_is_admin or user_can_assemble): # Üretimciler uçak stoğu görmez
            return Response({'draw': draw, 'recordsTotal': 0, 'recordsFiltered': 0, 'data': []}, status=drf_status.HTTP_200_OK)

        aircraft_models_for_stock = AircraftModel.objects.all()
        if aircraft_model_id_filter:
            aircraft_models_for_stock = aircraft_models_for_stock.filter(id=aircraft_model_id_filter)

        all_aircraft_model_combos = []
        if aircraft_models_for_stock.exists():
            for am_stock in aircraft_models_for_stock:
                 all_aircraft_model_combos.append({'am_id': am_stock.id, 'am_name': am_stock.get_name_display()})
        
        records_total = len(all_aircraft_model_combos)

        aircraft_stock_query = Aircraft.objects
        if aircraft_model_id_filter:
            aircraft_stock_query = aircraft_stock_query.filter(aircraft_model_id=aircraft_model_id_filter)
        
        # Montajcı sadece kendi takımının monte ettiği uçakların stoğunu görür
        if user_can_assemble and not user_is_admin and user_team:
            aircraft_stock_query = aircraft_stock_query.filter(assembled_by_team=user_team)

        raw_aircraft_stock_data = aircraft_stock_query.values(
            'aircraft_model_id', 'status'
        ).annotate(count=models.Count('id')).order_by()

        processed_aircraft_counts = {} # am_id -> {status: count}
        for item in raw_aircraft_stock_data:
            key = item['aircraft_model_id']
            if key not in processed_aircraft_counts: processed_aircraft_counts[key] = {}
            processed_aircraft_counts[key][item['status']] = item['count']

        for combo in all_aircraft_model_combos:
            counts_for_this_model = processed_aircraft_counts.get(combo['am_id'], {})
            row_data = {"aircraft_model_name": combo['am_name']}
            for status_choice, status_label in AircraftStatusChoices.choices:
                row_data[status_choice] = counts_for_this_model.get(status_choice, 0)
            data_list.append(row_data)

        records_filtered = len(data_list)
        data_list = data_list[start : start + length]

    return Response({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data_list
    }, status=drf_status.HTTP_200_OK)
