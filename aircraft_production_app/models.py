# aircraft_production_app/models.py
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction # Atomik işlemler için
from django.db.models import Max # Max'ı import ettiğinizden emin olun


# === SABİT TANIMLI BİLGİLER ===

class DefinedTeamTypes(models.TextChoices):
    WING_TEAM = "WING_TEAM", "Kanat Takımı"
    FUSELAGE_TEAM = "FUSELAGE_TEAM", "Gövde Takımı"
    TAIL_TEAM = "TAIL_TEAM", "Kuyruk Takımı"
    AVIONICS_TEAM = "AVIONICS_TEAM", "Aviyonik Takımı"
    ASSEMBLY_TEAM = "ASSEMBLY_TEAM", "Montaj Takımı"

class PartCategory(models.TextChoices): # Bu zaten vardı ve doğru
    WING = "WING", "Kanat"
    FUSELAGE = "FUSELAGE", "Gövde"
    TAIL = "TAIL", "Kuyruk"
    AVIONICS = "AVIONICS", "Aviyonik"

class AircraftModelChoices(models.TextChoices): # Uçak Modelleri için
    TB2 = "TB2", "TB2"
    TB3 = "TB3", "TB3"
    AKINCI = "AKINCI", "AKINCI"
    KIZILELMA = "KIZILELMA", "KIZILELMA"


class PartStatusChoices(models.TextChoices):    # ÜRETİLEN TEKİL PARÇALAR İÇİN DURUM SEÇENEKLERİ
    AVAILABLE = "AVAILABLE", "Kullanıma Hazır"
    USED = "USED", "Kullanıldı"
    RECYCLED = "RECYCLED", "Geri Dönüştürüldü"

class AircraftStatusChoices(models.TextChoices):
    ACTIVE = "AVAILABLE", "Hazır"
    RECYCLED = "RECYCLED", "Geri dönüştürüldü"
    SOLD = "SOLD", "Satıldı"
    MAINTENANCE = "MAINTENANCE", "Bakımda"

# === MODELLER ===

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Takım Adı")
    team_type = models.CharField(
        max_length=50,
        choices=DefinedTeamTypes.choices,
        verbose_name="Takım Tipi"
    )

    def __str__(self):
        return f"{self.name} ({self.get_team_type_display()})"

    # Montaj yapıp yapamayacağı team_type'a göre belirlenecek
    def can_perform_assembly(self):
        return self.team_type == DefinedTeamTypes.ASSEMBLY_TEAM
    
    def get_producible_part_category(self):
        """Bu takım tipi hangi parça kategorisini üretebilir?"""
        if self.team_type == DefinedTeamTypes.WING_TEAM:
            return PartCategory.WING
        if self.team_type == DefinedTeamTypes.FUSELAGE_TEAM:
            return PartCategory.FUSELAGE
        if self.team_type == DefinedTeamTypes.TAIL_TEAM:
            return PartCategory.TAIL
        if self.team_type == DefinedTeamTypes.AVIONICS_TEAM:
            return PartCategory.AVIONICS
        return None # Montaj takımı veya tanımsız bir tip ise None döner
    
    def get_produced_item_count(self):
        """
        Takımın tipine göre ürettiği toplam ürün (uçak veya parça) sayısını döndürür.
        Tüm durumlar dahildir.
        """
        if self.team_type == DefinedTeamTypes.ASSEMBLY_TEAM:
            # Aircraft modelinde assembled_by_team alanı Team'e ForeignKey
            # Eğer related_name belirtilmediyse, Django otomatik olarak 'aircraft_set' oluşturur.
            # Veya Aircraft.objects.filter(assembled_by_team=self).count() da kullanılabilir.
            if hasattr(self, 'aircraft_set'): # Django'nun otomatik oluşturduğu related_name
                return self.aircraft_set.count()
            else: # Eğer related_name farklıysa veya emin olmak için doğrudan filtreleme
                from .models import Aircraft # Circular import önlemek için metod içinde import
                return Aircraft.objects.filter(assembled_by_team=self).count()
        else:
            # Part modelinde produced_by_team alanı Team'e ForeignKey ve related_name='produced_parts' idi.
            return self.produced_parts.count()
    get_produced_item_count.short_description = "Üretilen Ürün Sayısı" # Admin panelindeki sütun başlığı

    
    def personnel_count(self):
        """Bu takımdaki personel sayısını döndürür."""
        # Personnel modelindeki 'team' ForeignKey'inin related_name'i 'members' idi.
        return self.members.count()
    personnel_count.short_description = "Personel Sayısı" # Admin panelindeki sütun başlığı

    def display_personnel_names(self):
        """Bu takımdaki personellerin kullanıcı adlarını virgülle ayrılmış string olarak döndürür."""
        # Personnel.user bir OneToOneField olduğu için user.username ile erişiyoruz.
        return ", ".join([personnel.user.username for personnel in self.members.all()])
    display_personnel_names.short_description = "Kayıtlı Personeller" # Admin panelindeki sütun başlığı

    class Meta:
        verbose_name = "Takım"
        verbose_name_plural = "Takımlar"

class Personnel(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True, verbose_name="Kullanıcı",         limit_choices_to={'is_staff': False, 'is_superuser': False})
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="members", verbose_name="Takım")

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name = "Personel"
        verbose_name_plural = "Personeller"

class PartType(models.Model):
    category = models.CharField(
        max_length=50,
        choices=PartCategory.choices,
        unique=True,
        verbose_name="Parça Tipi"
    )



    def __str__(self):
        return self.get_category_display()

    class Meta:
        verbose_name = "Parça Tipi"
        verbose_name_plural = "Parça Tipleri"


class AircraftModel(models.Model):
    name = models.CharField(
        max_length=50,
        choices=AircraftModelChoices.choices, # Sabit seçenekler
        unique=True,
        verbose_name="Hava Aracı Modeli"
    )

    def __str__(self):
        return self.get_name_display() # choices kullandığımız için get_X_display() daha iyi

    class Meta:
        verbose_name = "Hava Aracı Modeli"
        verbose_name_plural = "Hava Aracı Modelleri"


# İŞ EMRİ YÖNETİMİ
class WorkOrderStatusChoices(models.TextChoices):
    PENDING = "PENDING", "Beklemede"
    ASSIGNED = "ASSIGNED", "Atandı" # Montaj takımına atandı
    IN_PROGRESS = "IN_PROGRESS", "Üretimde"
    COMPLETED = "COMPLETED", "Tamamlandı"
    CANCELLED = "CANCELLED", "İptal Edildi"

class WorkOrder(models.Model):
    aircraft_model = models.ForeignKey(AircraftModel, on_delete=models.PROTECT, verbose_name="Üretilecek Hava Aracı Modeli")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Miktar")
    status = models.CharField(
        max_length=20,
        choices=WorkOrderStatusChoices.choices,
        default=WorkOrderStatusChoices.PENDING,
        verbose_name="Durum",
        editable=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_work_orders",
        verbose_name="Oluşturan Yönetici",
        editable=False
    )
    assigned_to_assembly_team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_work_orders",
        verbose_name="Atanan Montaj Takımı",
        limit_choices_to={'team_type': DefinedTeamTypes.ASSEMBLY_TEAM}
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Notlar")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncellenme Tarihi")
    target_completion_date = models.DateField(null=True, blank=True, verbose_name="Hedef Tamamlanma Tarihi")

    def save(self, *args, **kwargs):
        # Yeni bir iş emri oluşturuluyorsa (henüz pk'sı yoksa)
        if not self.pk:
            if self.assigned_to_assembly_team:
                self.status = WorkOrderStatusChoices.ASSIGNED
            else:
                self.status = WorkOrderStatusChoices.PENDING
        super().save(*args, **kwargs) # Asıl kaydetme işlemini yap


    @transaction.atomic
    def delete(self, *args, **kwargs):
        # İlişkili uçakların work_order alanını None yap
        # related_name='completed_aircrafts_for_order' idi Aircraft modelindeki work_order alanı için
        for aircraft in self.completed_aircrafts_for_order.all():
            aircraft.work_order = None
            aircraft.save()

        self.status = WorkOrderStatusChoices.CANCELLED
        self.save() # Durumu güncelle, fiziksel olarak silme
        print(f"WorkOrder ID: {self.id} status set to CANCELLED and unlinked from aircraft (soft delete).")

    def __str__(self):
        return f"İş Emri #{self.id} - {self.aircraft_model.name} ({self.quantity} adet) - {self.get_status_display()}"

    class Meta:
        verbose_name = "İş Emri"
        verbose_name_plural = "İş Emirleri"
        ordering = ['-created_at']




class Part(models.Model):
    # Bu part_type, PartType modeline (Kategori: Kanat, Gövde vb.) bir referanstır.
    part_type = models.ForeignKey(
        PartType,
        on_delete=models.PROTECT,
        verbose_name="Parça Tipi"
    )
    aircraft_model_compatibility = models.ForeignKey(
        AircraftModel,
        on_delete=models.PROTECT,
        verbose_name="Uyumlu Araç"
    )
    serial_number = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Seri Numarası",
        blank=True, # Otomatik atanacağı için başlangıçta boş olabilir
        editable=False
    )

    produced_by_team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT, # Üreten takım silinirse parça kaydı kalmalı, takım silinmemeli.
        related_name="produced_parts",
        verbose_name="Üreten Takım",
        limit_choices_to=~models.Q(team_type=DefinedTeamTypes.ASSEMBLY_TEAM),
        # İleride daha detaylı bir limit_choices_to eklenebilir:
        # Sadece PartType'ın producible_by_team_type'ına uygun takımlar seçilebilmeli.
        # Bu, form/admin seviyesinde veya model save'de kontr2ol edilebilir.
        # Şimdilik adminin doğru takımı seçtiğini varsayıyoruz.
    )

    production_date = models.DateTimeField(auto_now_add=True, verbose_name="Üretim Tarihi")
    status = models.CharField(
        max_length=20,
        choices=PartStatusChoices.choices,
        default=PartStatusChoices.AVAILABLE,
        verbose_name="Parça Durumu"
    )

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Son Değiştirilme Tarihi") # YENİ
    created_by_personnel = models.ForeignKey( # YENİ
        Personnel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True, # Admin gibi bir personel olmayan kullanıcı oluşturursa diye
        editable=False, # Formda görünmesin, otomatik atansın
        related_name="created_parts",
        verbose_name="Üreten Personel"
    )

    def get_part_type_abbreviation(self):
        abbreviations = {
            PartCategory.AVIONICS: "AVY",
            PartCategory.WING: "KNT",
            PartCategory.FUSELAGE: "GVD",
            PartCategory.TAIL: "KYR",
        }
        # PartType modelimizdeki category alanı PartCategory enum'ını kullanıyor.
        return abbreviations.get(self.part_type.category, "XXX") # Eşleşme yoksa XXX

    def save(self, *args, **kwargs):
        if not self.serial_number: # Sadece seri numarası yoksa ata (yeni kayıt veya boş bırakılmışsa)
            # Parça tipi ve uçak modeline göre son seri numarasını bul
            # Örn: TB2-AVY-0001
            prefix = f"{self.aircraft_model_compatibility.name}-{self.get_part_type_abbreviation()}-"

            # Bu prefix ile başlayan son parçayı bulup numarasını artıracağız.
            # Daha sağlam bir yöntem için bir "sequence" tablosu veya atomik işlemler gerekebilir
            # yüksek eşzamanlılıkta, ama basitlik için şimdilik Max() kullanabiliriz.
            # Bu yöntem küçük/orta ölçekli uygulamalar için yeterlidir.

            # Basit bir sıralı numara için:
            # Aynı model ve parça tipindeki parça sayısını alıp bir fazlasını kullanabiliriz.
            last_part_count = Part.objects.filter(
                aircraft_model_compatibility=self.aircraft_model_compatibility,
                part_type=self.part_type
            ).exclude(pk=self.pk).count() # Kendisi hariç (güncelleme durumu için)

            new_sequence_no = last_part_count + 1
            self.serial_number = f"{prefix}{new_sequence_no:05d}" # 0001, 0002 gibi formatlama

        super().save(*args, **kwargs) # Asıl kaydetme işlemini yap


    @transaction.atomic
    def delete(self, *args, **kwargs):
        # Parça bir uçağa takılıysa (yani durumu USED ise) doğrudan "silinmemeli" (geri dönüştürülemez).
        # Bu kontrolü "Geri Dönüştür" action'ı veya arayüzü yaparken ayrıca düşünmeliyiz.
        # Şimdilik, eğer bir "silme" komutu gelirse, durumu RECYCLED yapıyoruz.
        # Eğer parça bir uçağa takılıysa (status=USED), bu işlem normalde engellenmeli
        # veya önce uçaktan sökülmeli. pre_delete sinyali uçağı silerken parçayı AVAILABLE yapar.
        # Bu delete metodu, "AVAILABLE" veya "DEFECTIVE" bir parçanın geri dönüştürülmesi için daha uygun.
        if self.status == PartStatusChoices.USED:
            # Bu durum, bir uçağa bağlı parçanın doğrudan silinmeye/geri dönüştürülmeye çalışılmasıdır.
            # Uçak silinirken parçalar zaten AVAILABLE yapılıyor.
            # Belki burada bir hata vermek daha doğru olur veya hiçbir şey yapmamak.
            # Şimdilik, doğrudan USED bir parçayı RECYCLED yapmasına izin vermeyelim.
            # Kullanıcı önce uçağı "geri dönüştürmeli" veya parçayı uçaktan "sökmeli" (bu senaryo dışı).
            raise ValidationError(f"'{self.serial_number}' seri numaralı parça şu anda bir uçağa takılı (Kullanımda). Doğrudan geri dönüştürülemez/silinemez.")

        self.status = PartStatusChoices.RECYCLED
        self.save() # Durumu güncelle, fiziksel olarak silme
        print(f"Part SN: {self.serial_number} status set to RECYCLED (soft delete).")

            
    def clean(self):
        super().clean()
        # Kural 1: Üreten takım ve parça tipi seçilmiş olmalı
        if not self.part_type:
            # Bu durum genellikle form validasyonu ile yakalanır ama ek bir güvence
            raise ValidationError({'part_type': "Parça tipi seçilmelidir."})
        
        if not self.produced_by_team:
            # Bu durum genellikle form validasyonu ile yakalanır ama ek bir güvence
            raise ValidationError({'produced_by_team': "Üreten takım seçilmelidir."})

        # Kural 2: Üreten takımın tipi, seçilen parça kategorisini üretebilecek yetenekte olmalı.
        # (Bu kontrol zaten vardı, onu koruyoruz ve biraz daha netleştiriyoruz)
        expected_category_for_team = self.produced_by_team.get_producible_part_category()
        
        if expected_category_for_team is None: # Montaj takımı gibi parça üretemeyen bir takım
            raise ValidationError({
                'produced_by_team': (
                    f"Seçilen takım ({self.produced_by_team}) parça üretemez, çünkü bu takım tipi parça üretimi için tanımlanmamıştır (örn: Montaj Takımı)."
                )
            })
        # PartType modelindeki category alanı PartCategory enum'ından bir string değerdir.
        # Team modelindeki get_producible_part_category() metodu da PartCategory enum üyesini döndürür.
        # Doğrudan enum üyesinin value'su (string hali) ile karşılaştırma yapabiliriz.
        elif expected_category_for_team.value != self.part_type.category: 
            raise ValidationError({
                'produced_by_team': (
                    f"Seçilen takım ({self.produced_by_team}) '{self.part_type.get_category_display()}' kategorisinde parça üretemez. "
                    f"Bu takım sadece '{expected_category_for_team.label}' kategorisinde parça üretebilir."
                )
            })

        # YENİ KURAL: Üretim yapacak takımda en az bir personel olmalı.
        # Personnel modeli 'members' related_name ile Team'e bağlı.
        if not self.produced_by_team.members.exists():
            raise ValidationError({
                'produced_by_team': f"Seçilen takımda ({self.produced_by_team.name}) kayıtlı personel bulunmamaktadır. Üretim yapabilmesi için önce o takıma personel ekleyiniz."
            })

    def get_installed_aircraft_info(self):
        if self.status == PartStatusChoices.USED:
            try:
                # OneToOneField'ların related_name'lerini kontrol et
                if hasattr(self, 'aircraft_as_wing') and self.aircraft_as_wing:
                    return f"{self.aircraft_as_wing}"
                elif hasattr(self, 'aircraft_as_fuselage') and self.aircraft_as_fuselage:
                    return f"{self.aircraft_as_fuselage}"
                elif hasattr(self, 'aircraft_as_tail') and self.aircraft_as_tail:
                    return f"{self.aircraft_as_tail}"
                elif hasattr(self, 'aircraft_as_avionics') and self.aircraft_as_avionics:
                    return f"{self.aircraft_as_avionics}"
            except Aircraft.DoesNotExist: # Bu aslında OneToOneField'larda pek olmaz ama genel bir try-except
                pass
        return "Takılı Değil"
    get_installed_aircraft_info.short_description = "Takılı Olduğu Uçak" # Admin panelinde görünecek başlık

    def __str__(self):
        return f"{self.part_type.get_category_display()} - SN: {self.serial_number} ({self.aircraft_model_compatibility.name} için)"

    class Meta:
        verbose_name = "Üretilmiş Parça"
        verbose_name_plural = "Üretilmiş Parçalar"
        ordering = ['-production_date']

# MONTE EDİLMİŞ HAVA ARAÇLARI
class Aircraft(models.Model):
    aircraft_model = models.ForeignKey(
        AircraftModel,
        on_delete=models.PROTECT,
        verbose_name="Hava Aracı Modeli"
    )
    serial_number = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Hava Aracı Seri Numarası",
        blank=True, # Otomatik atanacağı için
        editable=False
    )
    status = models.CharField( # YENİ ALAN
        max_length=20,
        choices=AircraftStatusChoices.choices,
        default=AircraftStatusChoices.ACTIVE,
        verbose_name="Uçak Durumu"
    )
    # Bu uçak hangi iş emri üzerine monte edildi.
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True, # Stoktan üretim veya iş emri dışı montaj için
        related_name="completed_aircrafts_for_order",
        verbose_name="İlgili İş Emri (Montaj)",
        limit_choices_to=~models.Q(status=WorkOrderStatusChoices.CANCELLED)
    )
    assembly_date = models.DateTimeField(auto_now_add=True, verbose_name="Montaj Tarihi")
    assembled_by_team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        verbose_name="Montajı Yapan Takım",
        limit_choices_to={'team_type': DefinedTeamTypes.ASSEMBLY_TEAM} # Sadece montaj yetkisi olan takım tipine sahip takımlar
    )

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Son Güncellenme Tarihi") # YENİ
    assembled_by_personnel = models.ForeignKey( # YENİ
        Personnel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True, # Admin gibi bir personel olmayan kullanıcı oluşturursa diye
        editable=False, # Formda görünmesin, otomatik atansın
        related_name="assembled_aircrafts",
        verbose_name="Montajı Yapan Personel"
    )

    # Montaj mantığı: Her ana parça kategorisinden bir adet.
    # OneToOneField, bir Part nesnesinin sadece bir Aircraft'ın belirli bir slotunda kullanılmasını sağlar.
    # limit_choices_to, admin formunda doğru kategorideki parçaların seçilmesine yardımcı olur.
    # Asıl 'AVAILABLE' durum kontrolü ve montaj sonrası Part.status='USED' yapılması view/serializer'da olacak.
    wing = models.OneToOneField(
        Part, on_delete=models.SET_NULL, null=True, blank=True, # DEĞİŞTİ
        related_name="aircraft_as_wing", verbose_name="Kanat (Parça SN)",
        limit_choices_to={'part_type__category': PartCategory.WING}
    )
    fuselage = models.OneToOneField(
        Part, on_delete=models.SET_NULL, null=True, blank=True, # DEĞİŞTİ
        related_name="aircraft_as_fuselage", verbose_name="Gövde (Parça SN)",
        limit_choices_to={'part_type__category': PartCategory.FUSELAGE}
    )
    tail = models.OneToOneField(
        Part, on_delete=models.SET_NULL, null=True, blank=True, # DEĞİŞTİ
        related_name="aircraft_as_tail", verbose_name="Kuyruk (Parça SN)",
        limit_choices_to={'part_type__category': PartCategory.TAIL}
    )
    avionics = models.OneToOneField(
        Part, on_delete=models.SET_NULL, null=True, blank=True, # DEĞİŞTİ
        related_name="aircraft_as_avionics", verbose_name="Aviyonik Sistem (Parça SN)",
        limit_choices_to={'part_type__category': PartCategory.AVIONICS}
    )

    @transaction.atomic
    def delete(self, *args, **kwargs):
        # pre_delete sinyali zaten parçaları AVAILABLE yapacak.
        # Bu metot çağrıldığında, sinyal çalışmış olmalı.

        # Uçağın parça bağlantılarını None yap (SET_NULL sayesinde otomatik de olabilir ama garanti olsun)
        self.wing = None
        self.fuselage = None
        self.tail = None
        self.avionics = None

        self.status = AircraftStatusChoices.RECYCLED # Uçağın durumunu güncelle
        self.save(update_fields=['wing', 'fuselage', 'tail', 'avionics', 'status']) # Değişiklikleri kaydet, fiziksel olarak silme
        print(f"Aircraft SN: {self.serial_number} status set to RECYCLED and parts unlinked (soft delete).")

    def __str__(self):
        return f"{self.aircraft_model.name if self.aircraft_model else 'Model Belirtilmemiş'} - SN: {self.serial_number or 'Henüz Yok'}"

    class Meta:
        verbose_name = "Hazır Hava Aracı"
        verbose_name_plural = "Hazır Hava Araçları"
        ordering = ['-assembly_date']


    def clean(self):
        super().clean()

        # Kural 1: İş emri varsa, uçak modeli iş emrindekiyle eşleşmeli.
        if self.work_order and self.aircraft_model:
            if self.aircraft_model != self.work_order.aircraft_model:
                raise ValidationError({
                    'aircraft_model': (
                        f"Seçilen iş emri ({self.work_order}) için belirtilen hava aracı modeli "
                        f"({self.work_order.aircraft_model}) ile bu kayıttaki model ({self.aircraft_model}) eşleşmiyor."
                    )
                })

        # Kural 2: Tamamlanmış bir iş emrine yeni uçak atanamaz veya mevcut uçağın iş emri tamamlanmış bir tane ile değiştirilemez.
        if self.work_order and self.work_order.status == WorkOrderStatusChoices.COMPLETED:
            is_new_assignment_to_completed_wo = False
            if not self.pk: # Yeni uçak oluşturuluyor
                is_new_assignment_to_completed_wo = True
            else: # Mevcut uçak güncelleniyor
                try:
                    original_aircraft = Aircraft.objects.get(pk=self.pk)
                    if original_aircraft.work_order != self.work_order: # İş emri değiştiriliyor
                        is_new_assignment_to_completed_wo = True
                except Aircraft.DoesNotExist:
                    pass # Yeni uçak, ilk koşulda yakalanır.
            
            if is_new_assignment_to_completed_wo:
                raise ValidationError({
                    'work_order': f"Seçilen iş emri ({self.work_order}) zaten '{WorkOrderStatusChoices.COMPLETED.label}' statüsünde. Bu iş emrine uçak atanamaz/değiştirilemez."
                })

        # YENİ KURAL: İptal edilmiş bir iş emrine uçak atanamaz.
        if self.work_order and self.work_order.status == WorkOrderStatusChoices.CANCELLED:
            raise ValidationError({
                'work_order': "İptal edilmiş bir iş emrine uçak atanamaz."
            })

        part_slots = {
            'wing': self.wing,
            'fuselage': self.fuselage,
            'tail': self.tail,
            'avionics': self.avionics
        }

        original_parts = {}
        if self.pk: # Eğer obje güncelleniyorsa, orijinal parçaları al
            try:
                original_aircraft_db = Aircraft.objects.get(pk=self.pk)
                original_parts = {
                    'wing': original_aircraft_db.wing,
                    'fuselage': original_aircraft_db.fuselage,
                    'tail': original_aircraft_db.tail,
                    'avionics': original_aircraft_db.avionics
                }
            except Aircraft.DoesNotExist:
                pass # Yeni oluşturuluyorsa buraya girmez

        for slot_name, current_part in part_slots.items():
            if not current_part: # Eğer slot boşsa (parça seçilmemişse) kontrol etmeye gerek yok
                continue

            # Kural 3: Parçanın uçak modeli uyumluluğu
            if self.aircraft_model and current_part.aircraft_model_compatibility != self.aircraft_model:
                raise ValidationError({
                    slot_name: f"Seçilen {current_part.part_type.get_category_display()} (SN: {current_part.serial_number}) bu uçak modeli ({self.aircraft_model}) ile uyumlu değil. "
                               f"Parça {current_part.aircraft_model_compatibility} modeli için üretilmiş."
                })

            # Kural 4: Slota yeni atanan parçanın durumu AVAILABLE olmalı
            original_part_in_slot = original_parts.get(slot_name)
            if current_part != original_part_in_slot: # Parça değişmiş veya ilk kez atanıyorsa
                if current_part.status != PartStatusChoices.AVAILABLE:
                    raise ValidationError({
                        slot_name: f"Seçilen {current_part.part_type.get_category_display()} (SN: {current_part.serial_number}) montaj için '{PartStatusChoices.AVAILABLE.label}' durumda değil. Mevcut durumu: {current_part.get_status_display()}."
                    })
        # YENİ KONTROLLER: Aktif bir uçak için tüm parçalar seçilmiş olmalı.

        if self.status == AircraftStatusChoices.ACTIVE:
            if not self.wing:
                raise ValidationError({'wing': "Aktif bir uçak için Kanat seçilmelidir."})
            if not self.fuselage:
                raise ValidationError({'fuselage': "Aktif bir uçak için Gövde seçilmelidir."})
            if not self.tail:
                raise ValidationError({'tail': "Aktif bir uçak için Kuyruk seçilmelidir."})
            if not self.avionics:
                raise ValidationError({'avionics': "Aktif bir uçak için Aviyonik sistem seçilmelidir."})


    @transaction.atomic
    def save(self, *args, **kwargs):
        # === SERİ NUMARASI ATAMA MANTIĞI (GÜNCELLENDİ) ===
        if not self.pk:  # Sadece yeni bir instance ise (henüz primary key'i yoksa) seri numarası ata.
            if not self.aircraft_model:
                # Bu durum normalde form validasyonu veya clean() ile engellenmeli.
                # Eğer aircraft_model None ise seri numarası üretemeyiz.
                # Hata vermek veya olduğu gibi kaydetmeye çalışmak (DB hatası alabilir) bir seçenek.
                # Şimdilik, aircraft_model'in dolu olduğunu varsayıyoruz (formdan zorunlu gelmeli).
                pass # Ya da burada bir Exception raise edilebilir.

            # aircraft_model.name, AircraftModelChoices enum'ının value'sunu (örn: "TB2") verir.
            prefix = f"{self.aircraft_model.name}-" 
            
            # Bu prefix ile başlayan ve sonu sayı olan seri numaralarından en büyüğünü bul
            # (Bir önceki IntegrityError çözümü için önerilen Max tabanlı mantık)
            last_serial_obj = Aircraft.objects.filter(
                serial_number__startswith=prefix
            ).aggregate(max_sn_suffix=Max('serial_number'))
            
            max_suffix_num = 0
            if last_serial_obj and last_serial_obj.get('max_sn_suffix'):
                try:
                    # Son tireden sonraki kısmı alıp integer'a çevir
                    suffix_str = last_serial_obj['max_sn_suffix'].split('-')[-1]
                    max_suffix_num = int(suffix_str)
                except (IndexError, ValueError, TypeError):
                    pass # Hata durumunda max_suffix_num = 0 kalır
            
            new_sequence_no = max_suffix_num + 1
            self.serial_number = f"{prefix}{new_sequence_no:04d}" # Örn: TB2-00001

        # Parça Durum Güncelleme Mantığı (Geliştirilmiş)
        # Django'da OneToOneField'lar kaydedildiğinde, eski ilişki otomatik olarak null yapılır (eğer nullable ise).
        # Bizim parçalarımız PROTECT olduğu için önce manuel olarak eski parçayı ayırmamız gerekmiyor.
        # Sadece durumlarını güncelleyeceğiz.

        original_parts_to_make_available = []
        if self.pk: # Eğer obje güncelleniyorsa
            try:
                # Veritabanındaki güncel (kaydetmeden önceki) halini al
                original_aircraft_db = Aircraft.objects.select_related('wing', 'fuselage', 'tail', 'avionics').get(pk=self.pk)
                
                # Mevcut formdaki parçalarla karşılaştır
                if original_aircraft_db.wing and original_aircraft_db.wing != self.wing:
                    original_parts_to_make_available.append(original_aircraft_db.wing)
                if original_aircraft_db.fuselage and original_aircraft_db.fuselage != self.fuselage:
                    original_parts_to_make_available.append(original_aircraft_db.fuselage)
                if original_aircraft_db.tail and original_aircraft_db.tail != self.tail:
                    original_parts_to_make_available.append(original_aircraft_db.tail)
                if original_aircraft_db.avionics and original_aircraft_db.avionics != self.avionics:
                    original_parts_to_make_available.append(original_aircraft_db.avionics)
            except Aircraft.DoesNotExist:
                pass # Yeni oluşturuluyorsa bu kısım atlanır

        # Önce uçağı kaydet (ilişkilerin güncellenmesi için)
        super().save(*args, **kwargs)

        # Şimdi çıkarılan eski parçaların durumunu 'AVAILABLE' yap
        for old_part in original_parts_to_make_available:
            if old_part: # None değilse
                old_part.status = PartStatusChoices.AVAILABLE
                old_part.save()

        # Şimdi uçağa yeni takılan/atanan parçaların durumunu 'USED' yap ve iş emrini ata
        current_parts_to_mark_used = [self.wing, self.fuselage, self.tail, self.avionics]
        for current_part in current_parts_to_mark_used:
            if current_part: # None değilse
                # Sadece durumu gerçekten değişmesi gerekiyorsa güncelle (performans için)
                if current_part.status != PartStatusChoices.USED:
                    current_part.status = PartStatusChoices.USED
                
                current_part.save() # Parçanın son halini kaydet