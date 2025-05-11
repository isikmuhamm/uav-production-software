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
from .serializers import AircraftModelSerializer, AircraftSerializer, AircraftAssemblySerializer, PartTypeSerializer, TeamSerializer, PersonnelSerializer, PartSerializer, WorkOrderSerializer, serializers # Serializer'ları import et
from .permissions import IsAdminOrReadOnly, IsOwnerTeamOrAdminForPart,  IsAssemblyTeamMemberOrAdminForAircraft, CanAssembleAircraft, IsNotAssemblyTeamForCreate
from .filters import WorkOrderFilter


def frontend_login_view(request):
    """Personel giriş sayfasını sunar."""
    return render(request, 'aircraft_production_app/login.html')

def frontend_dashboard_view(request): # Tek bir dashboard view'ı, JS rolü yönetecek
    return render(request, 'aircraft_production_app/dashboard_admin.html') # Hepsi aynı ana şablonu kullanacak


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

class TeamViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Takımları listeler ve detaylarını görüntüler.
    Admin panelinden yönetildiği için API'den şimdilik sadece okuma.
    """
    queryset = Team.objects.all().prefetch_related('members') # Performans için
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly] # Daha sonra IsAdminUser yapılabilir

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
    Admin panelinden yönetildiği için API'den şimdilik sadece okuma.
    """
    queryset = Personnel.objects.select_related('user', 'team').all()
    serializer_class = PersonnelSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly] # Sadece adminler personel kaydı oluşturup güncelleyebilsin

class PartViewSet(viewsets.ModelViewSet):
    """
    Üretilmiş Parçaları yönetmek için API endpoint'i.
    - Üretimci kendi takımının ürettiği parçaları listeler.
    - Üretimci kendi takımının uzmanlığına göre yeni parça üretebilir.
    - Üretimci kendi takımının ürettiği parçaları geri dönüştürebilir.
    """
    serializer_class = PartSerializer

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [permissions.IsAuthenticated, IsOwnerTeamOrAdminForPart]
        elif self.action == 'create':
            # Yeni parça oluşturmak için: giriş yapmış olmalı VE montaj takımı olmamalı
            self.permission_classes = [permissions.IsAuthenticated, IsNotAssemblyTeamForCreate] # GÜNCELLENDİ
        else: # list, retrieve
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

    def get_queryset(self):
        """
        Bu metot, isteği yapan kullanıcının takımına göre parçaları filtreler.
        Admin/Süper kullanıcı tüm parçaları görebilir.
        """
        user = self.request.user
        queryset = Part.objects.all().select_related(
            'part_type', 'aircraft_model_compatibility', 
            'produced_by_team', 'created_by_personnel__user'
        )

        # Durum filtresi (query parameter: ?status=AVAILABLE veya ?status=USED,RECYCLED)
        status_filter_param = self.request.query_params.get('status')
        if status_filter_param:
            statuses_to_filter = [status.strip().upper() for status in status_filter_param.split(',')]
            valid_statuses = [s_val for s_val, s_label in PartStatusChoices.choices if s_val in statuses_to_filter]
            if valid_statuses:
                queryset = queryset.filter(status__in=valid_statuses)

        if user.is_superuser or user.is_staff:
            return queryset.order_by('-production_date')
        
        try:
            personnel = user.personnel
            if personnel.team:
                if personnel.team.can_perform_assembly(): # Montajcı
                    # Montajcı varsayılan olarak 'AVAILABLE' parçaları görsün (montaj için)
                    # Ama filtreyle diğerlerini de görebilmeli
                    if not status_filter_param: # Eğer özel bir status filtresi yoksa
                        return queryset.filter(status=PartStatusChoices.AVAILABLE).order_by('-production_date')
                    else: # Status filtresi varsa, tüm parçalar arasından o statüdekileri görsün
                        return queryset.order_by('-production_date') 
                else: # Üretim takımı ise sadece kendi ürettiklerini (tüm durumlar filtrelenebilir)
                    return queryset.filter(produced_by_team=personnel.team).order_by('-production_date')
        except Personnel.DoesNotExist:
            return Part.objects.none() # Personel kaydı yoksa hiçbir şey göremez
        return Part.objects.none() # Takımı olmayan personel hiçbir şey göremez

    def perform_create(self, serializer):
        user = self.request.user
        try:
            personnel = user.personnel
            if not personnel.team:
                raise serializers.ValidationError("Parça üretebilmek için bir takıma atanmış olmalısınız.")
            
            team = personnel.team

            # Takımın üretebileceği parça kategorisini bul
            producible_category_enum_member = team.get_producible_part_category()
            if not producible_category_enum_member:
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
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [permissions.IsAuthenticated, IsAssemblyTeamMemberOrAdminForAircraft]
        elif self.action == 'create': 
            # Uçak oluşturma AssembleAircraftAPIView ile yapılıyor, buradaki create'i sadece adminlere açabiliriz.
            self.permission_classes = [permissions.IsAdminUser] 
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
        
        # Durum filtresi (query parameter: ?status=ACTIVE veya ?status=RECYCLED)
        status_filter_param = self.request.query_params.get('status')
        if status_filter_param:
            statuses_to_filter = [status.strip().upper() for status in status_filter_param.split(',')]
            valid_statuses = [s_val for s_val, s_label in AircraftStatusChoices.choices if s_val in statuses_to_filter]
            if valid_statuses:
                queryset = queryset.filter(status__in=valid_statuses)

        if user.is_superuser or user.is_staff:
            return queryset.order_by('-assembly_date')
        
        try:
            personnel = user.personnel
            if personnel.team and personnel.team.can_perform_assembly():
                # Montajcı kendi takımının monte ettiği TÜM DURUMDAKİ uçakları görsün
                return queryset.filter(assembled_by_team=personnel.team).order_by('-assembly_date')
        except Personnel.DoesNotExist:
            return Aircraft.objects.none()
        
        return Aircraft.objects.none() # Diğer roller (örn: üretimci) uçak listesi görmez
    
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
            self.permission_classes = [permissions.IsAdminUser]
        elif self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.IsAuthenticated]
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

        # Durum filtresi (query parameter: ?status=COMPLETED veya ?status=PENDING,ASSIGNED)
        status_filter_param = self.request.query_params.get('status')
        if status_filter_param:
            statuses_to_filter = [status.strip().upper() for status in status_filter_param.split(',')]
            # Gelen status değerlerinin WorkOrderStatusChoices içinde geçerli olup olmadığını kontrol et
            valid_statuses = [s_val for s_val, s_label in WorkOrderStatusChoices.choices if s_val in statuses_to_filter]
            if valid_statuses:
                queryset = queryset.filter(status__in=valid_statuses)
            # else:
                # Geçersiz status parametresi gönderilirse tümünü döndür veya hata ver. Şimdilik tümünü döndürsün.
                # pass

        if user.is_superuser or user.is_staff: # Adminler (filtrelenmişse) tümünü görebilir
            return queryset.order_by('-created_at')
        
        try:
            personnel = user.personnel
            if personnel.team and personnel.team.can_perform_assembly(): # Eğer kullanıcı bir Montaj Takımı üyesi ise
                # Kendi takımına atanmış VEYA henüz kimseye atanmamış (PENDING)
                # VE durumu "Tamamlandı" veya "İptal Edildi" OLMAYAN iş emirlerini varsayılan olarak görsün.
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
    Parça ve uçak stok seviyelerini, rol bazlı filtrelemelerle ve 
    parçalar için sıfır stok uyarılarıyla döndürür.
    Query Params:
        - aircraft_model_id (int, isteğe bağlı): Belirli bir uçak modelini filtreler.
        - part_category_id (int, PartType ID, isteğe bağlı): Belirli bir parça kategorisini filtreler.
    """
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
        if not user_is_admin:
            return Response({"part_stocks": [], "aircraft_stocks": []}, status=drf_status.HTTP_200_OK)

    # Filtreleri al
    aircraft_model_id_filter = request.query_params.get('aircraft_model_id')
    part_category_id_filter = request.query_params.get('part_category_id') # Bu PartType ID'si

    # --- Parça Stokları ---
    part_stock_report = []
    
    # Üretimcinin görebileceği parça tiplerini (kategorilerini) belirle
    part_types_to_query = PartType.objects.all()
    if not user_is_admin and not user_can_assemble and user_producible_category_value:
        part_types_to_query = part_types_to_query.filter(category=user_producible_category_value)
    
    # Eğer part_category_id filtresi varsa ve kullanıcının bu kategoriyi görme yetkisi yoksa (üretimci için)
    # o zaman part_types_to_query boş dönecektir, bu da doğru bir davranıştır.
    if part_category_id_filter:
        part_types_to_query = part_types_to_query.filter(id=part_category_id_filter)

    # Uçak modellerini belirle
    aircraft_models_for_parts = AircraftModel.objects.all()
    if aircraft_model_id_filter:
        aircraft_models_for_parts = aircraft_models_for_parts.filter(id=aircraft_model_id_filter)

    if aircraft_models_for_parts.exists() and part_types_to_query.exists():
        raw_part_stock_data = Part.objects.values(
            'aircraft_model_compatibility_id', 'part_type_id', 'status'
        ).annotate(count=models.Count('id')).order_by()

        processed_part_counts = {}
        for item in raw_part_stock_data:
            key = (item['aircraft_model_compatibility_id'], item['part_type_id'])
            if key not in processed_part_counts:
                processed_part_counts[key] = {}
            processed_part_counts[key][item['status']] = item['count']

        for am_part in aircraft_models_for_parts:
            for pt in part_types_to_query:
                current_key = (am_part.id, pt.id)
                counts_for_this_combo = processed_part_counts.get(current_key, {})
                
                status_counts_with_all_keys = {psc[0]: counts_for_this_combo.get(psc[0], 0) for psc in PartStatusChoices.choices}
                total_available = status_counts_with_all_keys.get(PartStatusChoices.AVAILABLE.value, 0)
                warning_zero_stock = (total_available == 0)

                part_stock_item = {
                    "aircraft_model_id": am_part.id,
                    "aircraft_model_name": am_part.get_name_display(),
                    "part_type_id": pt.id,
                    "part_type_category_display": pt.get_category_display(),
                    "status_counts": status_counts_with_all_keys,
                    "total_available": total_available,
                    "warning_zero_stock": warning_zero_stock
                }
                part_stock_report.append(part_stock_item)
    
    # --- Uçak Stokları ---
    aircraft_stock_report = []
    # Üretimciler uçak stoğu görmez
    if user_is_admin or user_can_assemble:
        aircraft_models_for_aircraft_stock = AircraftModel.objects.all()
        if aircraft_model_id_filter: # Uçak modeli filtresi uçak stoklarına da uygulanır
            aircraft_models_for_aircraft_stock = aircraft_models_for_aircraft_stock.filter(id=aircraft_model_id_filter)

        if aircraft_models_for_aircraft_stock.exists():
            raw_aircraft_stock_data_query = Aircraft.objects
            # Montajcı sadece 'ACTIVE' (hazır) uçakların sayısını görür
            if user_can_assemble and not user_is_admin:
                raw_aircraft_stock_data_query = raw_aircraft_stock_data_query.filter(status=AircraftStatusChoices.ACTIVE)
            
            raw_aircraft_stock_data = raw_aircraft_stock_data_query.values(
                'aircraft_model_id', 'status'
            ).annotate(count=models.Count('id')).order_by()

            processed_aircraft_counts = {}
            for item in raw_aircraft_stock_data:
                key = item['aircraft_model_id'] # Sadece model ID'si yeterli
                if key not in processed_aircraft_counts:
                    processed_aircraft_counts[key] = {}
                processed_aircraft_counts[key][item['status']] = item['count']

            for am_stock in aircraft_models_for_aircraft_stock:
                counts_for_this_model = processed_aircraft_counts.get(am_stock.id, {})
                
                # Admin tüm durumları, montajcı sadece ACTIVE durumunu (veya tümünü alıp frontend'de filtreleyebilir)
                # Burada montajcı için sadece ACTIVE dönecek şekilde sorguyu daralttık.
                # Eğer tüm durumları alıp sadece total_active göstermek istersek, sorguyu genişletip burada filtreleriz.
                
                status_counts_with_all_keys_ac = {asc[0]: counts_for_this_model.get(asc[0], 0) for asc in AircraftStatusChoices.choices}
                total_active = status_counts_with_all_keys_ac.get(AircraftStatusChoices.ACTIVE.value, 0)

                # Eğer montajcı ve admin değilse ve hiç aktif uçak yoksa bu modeli rapora eklemeyebiliriz.
                # Ama admin tüm modelleri ve durumlarını görmeli.
                # Montajcı için, eğer filtreleme sonucu hiç aktif uçak yoksa bu model için bir şey dönmeyebilir.
                # Şimdilik, eğer bir model için sorgu yapıldıysa ve o model için veri varsa (hangi durumda olursa olsun) gösteriyoruz.
                # Montajcının sorgusu zaten sadece ACTIVE olanları getirecek.

                if user_is_admin or (user_can_assemble and total_active > 0) or (user_can_assemble and not aircraft_model_id_filter and not counts_for_this_model): # Montajcı için, ya aktif uçak var ya da genel listede model için hiç veri yoksa bile modeli göster
                     # Son koşul, montajcı için, eğer hiç aktif uçak yoksa bile modelin listede görünmesi için (status_counts boş olabilir)
                    if not (user_can_assemble and not user_is_admin and not counts_for_this_model.get(AircraftStatusChoices.ACTIVE.value, 0) > 0 and aircraft_model_id_filter): # Eğer montajcı belirli bir model için filtreledi ve o modelde aktif uçak yoksa gösterme
                        aircraft_stock_item = {
                            "aircraft_model_id": am_stock.id,
                            "aircraft_model_name": am_stock.get_name_display(),
                            "status_counts": status_counts_with_all_keys_ac,
                            "total_active": total_active
                        }
                        aircraft_stock_report.append(aircraft_stock_item)


    # Eğer filtreler sonucu hiç veri bulunamadıysa (hem parça hem uçak için)
    if not part_stock_report and not aircraft_stock_report and (aircraft_model_id_filter or part_category_id_filter):
        return Response({"message": "Belirtilen filtrelerle eşleşen stok bulunamadı."}, status=drf_status.HTTP_404_NOT_FOUND)

    return Response({
        "part_stocks": part_stock_report,
        "aircraft_stocks": aircraft_stock_report
    }, status=drf_status.HTTP_200_OK)
