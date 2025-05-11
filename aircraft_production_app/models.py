# aircraft_production_app/models.py
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction # Atomik işlemler için
from django.db.models import Max # Max'ı import ettiğinizden emin olun
from django.templatetags.static import static
from django.core.exceptions import ValidationError as DjangoValidationError 


# === SABİT TANIMLI BİLGİLER ===

class DefinedTeamTypes(models.TextChoices):
    """
    Sistemdeki farklı takım tiplerini tanımlar.
    """
    WING_TEAM = "WING_TEAM", "Kanat Takımı"
    FUSELAGE_TEAM = "FUSELAGE_TEAM", "Gövde Takımı"
    TAIL_TEAM = "TAIL_TEAM", "Kuyruk Takımı"
    AVIONICS_TEAM = "AVIONICS_TEAM", "Aviyonik Takımı"
    ASSEMBLY_TEAM = "ASSEMBLY_TEAM", "Montaj Takımı"

class PartCategory(models.TextChoices): # Bu zaten vardı ve doğru
    """
    Üretilebilecek ana parça kategorilerini tanımlar.
    """
    WING = "WING", "Kanat"
    FUSELAGE = "FUSELAGE", "Gövde"
    TAIL = "TAIL", "Kuyruk"
    AVIONICS = "AVIONICS", "Aviyonik"

class AircraftModelChoices(models.TextChoices): # Uçak Modelleri için
    """
    Sistemde üretilebilen hava aracı modellerini tanımlar.
    """
    TB2 = "TB2", "TB2"
    TB3 = "TB3", "TB3"
    AKINCI = "AKINCI", "AKINCI"
    KIZILELMA = "KIZILELMA", "KIZILELMA"


class PartStatusChoices(models.TextChoices):
    """
    Üretilen tekil parçaların sahip olabileceği durumları tanımlar.
    """
    AVAILABLE = "AVAILABLE", "Kullanıma Hazır"
    USED = "USED", "Kullanıldı"
    RECYCLED = "RECYCLED", "Geri Dönüştürüldü"
    # IN_PRODUCTION ve DEFECTIVE gibi durumlar eklenebilir, şimdilik bunlar kullanılıyor.

class AircraftStatusChoices(models.TextChoices):
    """
    Monte edilmiş hava araçlarının sahip olabileceği durumları tanımlar.
    """
    ACTIVE = "AVAILABLE", "Hazır"
    SOLD = "SOLD", "Satıldı"
    MAINTENANCE = "MAINTENANCE", "Bakımda"
    RECYCLED = "RECYCLED", "Geri dönüştürüldü"

# === MODELLER ===

class Team(models.Model):
    """
    Üretim veya montaj takımlarını temsil eder.
    Her takımın bir adı ve DefinedTeamTypes enum'ından bir tipi vardır.
    """
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
        """
        Takımın montaj yapabilme yeteneğini döndürür.
        Sadece 'ASSEMBLY_TEAM' tipindeki takımlar montaj yapabilir.
        """
        return self.team_type == DefinedTeamTypes.ASSEMBLY_TEAM
    
    def get_producible_part_category(self):
        """
        Takım tipine göre üretebileceği parça kategorisini (PartCategory enum üyesi) döndürür.
        Eğer takım parça üretemiyorsa (örn: Montaj Takımı) None döner.
        """
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
            # Aircraft modelindeki 'assembled_aircrafts' related_name'i kullanılıyor.
            if hasattr(self, 'aircraft_set'):
                return self.aircraft_set.count()
        else:
            # Part modelindeki 'produced_parts' related_name'i kullanılıyor.
            return self.produced_parts.count()
    get_produced_item_count.short_description = "Üretilen Ürün Sayısı" # Admin panelindeki sütun başlığı

    def personnel_count(self):
        """
        Bu takımdaki kayıtlı personel sayısını döndürür.
        """
        # Personnel modelindeki 'team' ForeignKey'inin related_name'i 'members' idi.
        return self.members.count()
    personnel_count.short_description = "Personel Sayısı" # Admin panelindeki sütun başlığı

    def display_personnel_names(self):
        """
        Bu takımdaki personellerin kullanıcı adlarını virgülle ayrılmış bir string olarak döndürür.
        Eğer personel yoksa boş string döner.
        """
        # Personnel.user bir OneToOneField olduğu için user.username ile erişiyoruz.
        return ", ".join([personnel.user.username for personnel in self.members.all()])
    display_personnel_names.short_description = "Kayıtlı Personeller" # Admin panelindeki sütun başlığı

    class Meta:
        """Meta seçenekleri."""
        verbose_name = "Takım"
        verbose_name_plural = "Takımlar"

class Personnel(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True, verbose_name="Kullanıcı",         limit_choices_to={'is_staff': False, 'is_superuser': False})
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="members", verbose_name="Takım")

    """
    Sistemdeki personelleri temsil eder. Her personel bir Django User ile birebir ilişkilidir.
    Bir personel bir takıma atanabilir veya takımsız olabilir.
    """

    def __str__(self):
        """
        Personel nesnesinin string temsilini döndürür (kullanıcı adı).
        """
        return self.user.username

    class Meta:
        """Meta seçenekleri."""
        verbose_name = "Personel"
        verbose_name_plural = "Personeller"

class PartType(models.Model):
    """
    Üretilebilecek ana parça kategorilerini (Kanat, Gövde vb.) tanımlar.
    Bu veriler genellikle sistem başlangıcında data migration ile yüklenir ve sabittir.
    """
    category = models.CharField(
        max_length=50,
        choices=PartCategory.choices, # PartCategory enum'ından gelir
        unique=True,
        verbose_name="Parça Tipi"
    )



    def __str__(self):
        """
        Parça tipi nesnesinin string temsilini döndürür (okunabilir kategori adı).
        """
        return self.get_category_display()

    class Meta:
        """Meta seçenekleri."""
        verbose_name = "Parça Tipi"
        verbose_name_plural = "Parça Tipleri"

class AircraftModel(models.Model):
    """
    Sistemde üretilebilen farklı hava aracı modellerini (TB2, AKINCI vb.) tanımlar.
    Her modelin bir adı ve ilişkili bir görseli olabilir.
    """
    name = models.CharField(
        max_length=50,
        choices=AircraftModelChoices.choices, # Sabit seçenekler
        unique=True,
        verbose_name="Hava Aracı Modeli Adı"
    )

    def __str__(self):
        """
        Hava aracı modeli nesnesinin string temsilini döndürür (okunabilir model adı).
        """
        return self.get_name_display()

    @property
    def image_filename(self):
        """
        Modele ait resim dosyasının adını döndürür.
        Resimlerin aircraft_production_app/static/aircraft_production_app/images/
        klasöründe modelin 'name' alanı (enum value, örn: "TB2") ile aynı isimde
        ve .png uzantılı olduğunu varsayar (örn: tb2.png, akinci.png).
        """
        if self.name:
            return f"{self.name.lower()}.png"
        return None

    @property
    def image_url(self):
        """
        Modele ait resmin tam statik URL'sini döndürür.
        Eğer modele özel resim yoksa, varsayılan bir placeholder resmi döndürür.
        """
        filename = self.image_filename
        if filename:
            # static() fonksiyonu 'app_name:path/to/file' formatını beklemez,
            # doğrudan 'path/to/file' şeklinde alır ve STATICFILES_DIRS veya
            # uygulama static klasörlerinden bulur.
            # Klasör yapımız: aircraft_production_app/static/aircraft_production_app/images/
            return static(f'aircraft_production_app/images/{filename}')
        return static('aircraft_production_app/images/placeholder.png') # Varsayılan bir resim

    class Meta:
        """Meta seçenekleri."""
        verbose_name = "Hava Aracı Modeli"
        verbose_name_plural = "Hava Aracı Modelleri"


# İŞ EMRİ YÖNETİMİ
class WorkOrderStatusChoices(models.TextChoices):
    """
    İş emirlerinin sahip olabileceği durumları tanımlar.
    - PENDING: İş emri oluşturuldu, henüz bir takıma atanmadı.
    - ASSIGNED: İş emri bir montaj takımına atandı.
    - IN_PROGRESS: Atanan takım iş emri üzerinde çalışmaya başladı (montaj yapıyor).
    - COMPLETED: İş emri kapsamındaki tüm hava araçları monte edildi.
    - CANCELLED: İş emri iptal edildi.
    """
    PENDING = "PENDING", "Beklemede"
    ASSIGNED = "ASSIGNED", "Atandı" # Montaj takımına atandı
    IN_PROGRESS = "IN_PROGRESS", "Üretimde"
    COMPLETED = "COMPLETED", "Tamamlandı"
    CANCELLED = "CANCELLED", "İptal Edildi"

class WorkOrder(models.Model):
    """
    Belirli bir modelden belirli sayıda hava aracının üretilmesi için oluşturulan iş emirlerini temsil eder.
    İş emirleri yöneticiler tarafından oluşturulur ve montaj takımlarına atanabilir.
    """
    aircraft_model = models.ForeignKey(AircraftModel, on_delete=models.PROTECT, verbose_name="Üretilecek Hava Aracı Modeli")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Miktar")
    status = models.CharField(
        max_length=20,
        choices=WorkOrderStatusChoices.choices,
        default=WorkOrderStatusChoices.PENDING,
        verbose_name="Durum",
        editable=True # Admin panelinden durumu manuel değiştirmeye izin verir (dikkatli kullanılmalı)
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_work_orders",
        verbose_name="Oluşturan Yönetici",
        editable=False # Otomatik atanır, formda görünmez/değiştirilemez
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
        """
        İş emri kaydedilirken özel mantık uygular:
        - Yeni oluşturulan bir iş emri ise ve bir montaj takımına atanmışsa durumunu 'ASSIGNED',
          atanmamışsa 'PENDING' olarak ayarlar.
        """
        if not self.pk:
            if self.assigned_to_assembly_team:
                self.status = WorkOrderStatusChoices.ASSIGNED
            else:
                self.status = WorkOrderStatusChoices.PENDING
        super().save(*args, **kwargs) # Asıl kaydetme işlemini yap

    @transaction.atomic
    def delete(self, *args, **kwargs):
        """
        İş emrini fiziksel olarak silmek yerine "yumuşak silme" (soft delete) uygular:
        - İş emrinin durumunu 'CANCELLED' olarak günceller.
        - Bu iş emriyle ilişkili tüm monte edilmiş hava araçlarının 'work_order' alanını None yapar,
          böylece uçaklar iş emrinden ayrılır ancak var olmaya devam eder.
        """
        for aircraft in self.completed_aircrafts_for_order.all():
            aircraft.work_order = None
            aircraft.save()

        self.status = WorkOrderStatusChoices.CANCELLED
        self.save() # Durumu güncelle, fiziksel olarak silme
        print(f"WorkOrder ID: {self.id} status set to CANCELLED and unlinked from aircraft (soft delete).")

    def __str__(self):
        """
        İş emri nesnesinin string temsilini döndürür.
        """
        return f"İş Emri #{self.id} - {self.aircraft_model.name} ({self.quantity} adet) - {self.get_status_display()}"

    class Meta:
        """Meta seçenekleri."""
        verbose_name = "İş Emri"
        verbose_name_plural = "İş Emirleri"
        ordering = ['-created_at'] # Varsayılan sıralama: en yeni iş emri en üstte

class Part(models.Model):
    """
    Üretilmiş tekil parçaları temsil eder.
    Her parça bir parça tipine (kategori), uyumlu olduğu bir hava aracı modeline,
    üreten takıma ve personele sahiptir. Otomatik olarak bir seri numarası atanır.
    Durumu (Kullanıma Hazır, Kullanıldı, Geri Dönüştürüldü) takip edilir.
    """
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
        blank=True, # Otomatik atanacağı için formda boş bırakılabilir
        editable=False
    )

    produced_by_team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT, # Üreten takım silinirse parça kaydı kalmalı, takım silinmemeli.
        related_name="produced_parts",
        verbose_name="Üreten Takım",
        limit_choices_to=~models.Q(team_type=DefinedTeamTypes.ASSEMBLY_TEAM),
    )

    production_date = models.DateTimeField(auto_now_add=True, verbose_name="Üretim Tarihi")
    status = models.CharField(
        max_length=20,
        choices=PartStatusChoices.choices,
        default=PartStatusChoices.AVAILABLE,
        verbose_name="Parça Durumu"
    )

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Son Değiştirilme Tarihi")
    created_by_personnel = models.ForeignKey(
        Personnel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True, # Eğer üreten personel sistemden silinirse veya atanmamışsa
        editable=False, # Formda görünmesin, otomatik atansın
        related_name="created_parts",
        verbose_name="Üreten Personel"
    )

    def get_part_type_abbreviation(self):
        """
        Parça kategorilerine göre seri numarasında kullanılacak kısaltmaları döndürür.
        """
        abbreviations = {
            PartCategory.AVIONICS: "AVY",
            PartCategory.WING: "KNT",
            PartCategory.FUSELAGE: "GVD",
            PartCategory.TAIL: "KYR",
        }
        # PartType modelimizdeki category alanı PartCategory enum'ını kullanıyor.
        return abbreviations.get(self.part_type.category, "XXX") # Eşleşme yoksa XXX

    def save(self, *args, **kwargs):
        """
        Parça kaydedilirken özel mantık uygular:
        - Eğer yeni bir parça ise (veya seri numarası boşsa), otomatik olarak bir seri numarası atar.
          Seri numarası formatı: <UçakModelAdı>-<ParçaTipiKısaltması>-<SıraNo> (örn: TB2-KNT-00001).
        """
        if not self.serial_number: # Sadece seri numarası yoksa ata (yeni kayıt veya boş bırakılmışsa)
            prefix = f"{self.aircraft_model_compatibility.name}-{self.get_part_type_abbreviation()}-"

            # Aynı model ve parça tipindeki mevcut parça sayısını alıp bir fazlasını sıra numarası olarak kullan.
            # Bu, basit bir sıralama sağlar. Yüksek eşzamanlılık durumları için daha karmaşık bir
            # sequence yönetimi gerekebilir.
            last_part_count = Part.objects.filter(
                aircraft_model_compatibility=self.aircraft_model_compatibility,
                part_type=self.part_type
            ).exclude(pk=self.pk).count() # Kendisi hariç (güncelleme durumu için)

            new_sequence_no = last_part_count + 1
            self.serial_number = f"{prefix}{new_sequence_no:05d}" # 5 haneli, başı sıfırla doldurulmuş sıra no

        super().save(*args, **kwargs) # Asıl kaydetme işlemini yap

    @transaction.atomic
    def delete(self, *args, **kwargs):
        """
        Parçayı fiziksel olarak silmek yerine "yumuşak silme" (soft delete) uygular:
        - Parçanın durumunu 'RECYCLED' olarak günceller.
        - Eğer parça 'USED' (bir uçağa takılı) durumdaysa, bu işlem engellenir ve bir
          ValidationError fırlatılır. Parçanın önce uçaktan sökülmesi (bu senaryo dışı)
          veya uçağın geri dönüştürülmesi gerekir.
        """
        if self.status == PartStatusChoices.USED:
            raise ValidationError(f"'{self.serial_number}' seri numaralı parça şu anda bir uçağa takılı (Kullanımda). Doğrudan geri dönüştürülemez/silinemez.")

        self.status = PartStatusChoices.RECYCLED
        self.save() # Durumu güncelle, fiziksel olarak silme
        print(f"Part SN: {self.serial_number} status set to RECYCLED (soft delete).")

            
    def clean(self):
        """
        Model kaydedilmeden önce ek doğrulamalar yapar:
        - Parça tipi ve üreten takım seçilmiş olmalıdır.
        - Üreten takımın tipi, seçilen parça kategorisini üretebilecek yetenekte olmalıdır.
        - Üretim yapacak takımda en az bir personel kayıtlı olmalıdır.
        """
        super().clean()
        # Kural 1: Üreten takım ve parça tipi seçilmiş olmalı
        if not self.part_type:
            raise ValidationError({'part_type': "Parça tipi seçilmelidir."})
        if not self.produced_by_team:
            raise ValidationError({'produced_by_team': "Üreten takım seçilmelidir."})

        # Kural 2: Üreten takımın tipi, seçilen parça kategorisini üretebilecek yetenekte olmalı.
        # (Bu kontrol zaten vardı, onu koruyoruz ve biraz daha netleştiriyoruz)
        expected_category_for_team = self.produced_by_team.get_producible_part_category()
        
        if expected_category_for_team is None: # Montaj takımı gibi parça üretemeyen bir takım
            raise ValidationError({
                'produced_by_team': (
                    f"Seçilen takım ({self.produced_by_team}) parça üretemez (örn: Montaj Takımı)."
                )
            })
        elif expected_category_for_team.value != self.part_type.category: 
            raise ValidationError({
                'produced_by_team': (
                    f"Seçilen takım ({self.produced_by_team}) '{self.part_type.get_category_display()}' kategorisinde parça üretemez. "
                    f"Bu takım sadece '{expected_category_for_team.label}' kategorisinde parça üretebilir."
                )
            })

        # Kural 3: Üretim yapacak takımda en az bir personel olmalı.
        if not self.produced_by_team.members.exists():
            raise ValidationError({
                'produced_by_team': f"Seçilen takımda ({self.produced_by_team.name}) kayıtlı personel bulunmamaktadır. Üretim yapabilmesi için önce o takıma personel ekleyiniz."
            })

    def get_installed_aircraft_info(self):
        """
        Eğer parça 'USED' durumdaysa, takılı olduğu uçağın string temsilini döndürür.
        Aksi halde "Takılı Değil" string'ini döndürür.
        """
        if self.status == PartStatusChoices.USED:
            try:
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
        return "-" # "Takılı Değil" yerine daha kısa bir ifade
    get_installed_aircraft_info.short_description = "Takılı Olduğu Uçak" # Admin panelinde görünecek başlık

    def __str__(self):
        """
        Parça nesnesinin string temsilini döndürür.
        """
        return f"{self.part_type.get_category_display()} - SN: {self.serial_number} ({self.aircraft_model_compatibility.name} için)"

    class Meta:
        """Meta seçenekleri."""
        verbose_name = "Üretilmiş Parça"
        verbose_name_plural = "Üretilmiş Parçalar"
        ordering = ['-production_date'] # Varsayılan sıralama: en yeni üretilen parça en üstte

# MONTE EDİLMİŞ HAVA ARAÇLARI
class Aircraft(models.Model):
    """
    Monte edilmiş hava araçlarını temsil eder.
    Her hava aracı bir modele, otomatik atanan bir seri numarasına, montaj tarihine,
    montajı yapan takıma/personele ve takılı olan ana parçalara (kanat, gövde vb.) sahiptir.
    Bir iş emriyle ilişkilendirilebilir ve durumu (Hazır, Satıldı vb.) takip edilir.
    """
    aircraft_model = models.ForeignKey(
        AircraftModel,
        on_delete=models.PROTECT,
        verbose_name="Hava Aracı Modeli"
    )
    serial_number = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Hava Aracı Seri Numarası",
        blank=True, # Otomatik atanacağı için formda boş bırakılabilir
        editable=False
    )
    status = models.CharField(
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

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Son Güncellenme Tarihi")
    assembled_by_personnel = models.ForeignKey(
        Personnel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True, # Admin gibi bir personel olmayan kullanıcı oluşturursa diye
        editable=False, # Formda görünmesin, otomatik atansın
        related_name="assembled_aircrafts",
        verbose_name="Montajı Yapan Personel"
    )

    # Montaj mantığı: Her ana parça kategorisinden bir adet.
    wing = models.OneToOneField(
        Part, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="aircraft_as_wing", verbose_name="Kanat (Parça SN)",
        limit_choices_to={'part_type__category': PartCategory.WING, 'status': PartStatusChoices.AVAILABLE}
    )
    fuselage = models.OneToOneField(
        Part, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="aircraft_as_fuselage", verbose_name="Gövde (Parça SN)",
        limit_choices_to={'part_type__category': PartCategory.FUSELAGE, 'status': PartStatusChoices.AVAILABLE}
    )
    tail = models.OneToOneField(
        Part, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="aircraft_as_tail", verbose_name="Kuyruk (Parça SN)",
        limit_choices_to={'part_type__category': PartCategory.TAIL, 'status': PartStatusChoices.AVAILABLE}
    )
    avionics = models.OneToOneField(
        Part, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="aircraft_as_avionics", verbose_name="Aviyonik Sistem (Parça SN)",
        limit_choices_to={'part_type__category': PartCategory.AVIONICS, 'status': PartStatusChoices.AVAILABLE}
    )

    @transaction.atomic
    def delete(self, *args, **kwargs):
        """
        Hava aracını fiziksel olarak silmek yerine "yumuşak silme" (soft delete) uygular:
        - Uçağa takılı olan tüm ana parçaların (kanat, gövde vb.) durumunu 'AVAILABLE' yapar.
        - Uçağın parça bağlantılarını (wing, fuselage vb.) None yapar.
        - Uçağın durumunu 'RECYCLED' olarak günceller.
        """
        parts_to_make_available = [self.wing, self.fuselage, self.tail, self.avionics]
        for part in parts_to_make_available:
            if part:
                part.status = PartStatusChoices.AVAILABLE
                part.save()

        self.wing = None
        self.fuselage = None
        self.tail = None
        self.avionics = None

        self.status = AircraftStatusChoices.RECYCLED # Uçağın durumunu güncelle
        self.save(update_fields=['wing', 'fuselage', 'tail', 'avionics', 'status']) # Sadece belirtilen alanları güncelle
        print(f"Aircraft SN: {self.serial_number} status set to RECYCLED and parts unlinked (soft delete).")

    def __str__(self):
        return f"{self.aircraft_model.name if self.aircraft_model else 'Model Belirtilmemiş'} - SN: {self.serial_number or 'Henüz Yok'}"

    class Meta:
        """Meta seçenekleri."""
        verbose_name = "Üretilmiş Hava Aracı"
        verbose_name_plural = "Üretilmiş Hava Araçları"
        ordering = ['-assembly_date'] # Varsayılan sıralama: en yeni monte edilen uçak en üstte

    def clean(self):
        """
        Model kaydedilmeden önce ek doğrulamalar yapar:
        - Eğer bir iş emriyle ilişkilendirilmişse, uçak modelinin iş emrindeki modelle eşleştiğini kontrol eder.
        - Tamamlanmış veya iptal edilmiş bir iş emrine uçak atanamayacağını/değiştirilemeyeceğini kontrol eder.
        - Takılan parçaların uçağın modeliyle uyumlu olup olmadığını kontrol eder.
        - Uçağa yeni takılan bir parçanın durumunun 'AVAILABLE' (Kullanıma Hazır) olup olmadığını kontrol eder.
        - Eğer uçağın durumu 'ACTIVE' (Hazır) ise, tüm ana parça slotlarının (kanat, gövde vb.) dolu olmasını zorunlu kılar.
        """
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

        # Kural 2: Tamamlanmış bir iş emrine yeni uçak atanamaz/değiştirilemez.
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

        # Kural 3: İptal edilmiş bir iş emrine uçak atanamaz.
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

            # Kural 4: Parçanın uçak modeli uyumluluğu
            if self.aircraft_model and current_part.aircraft_model_compatibility != self.aircraft_model:
                raise ValidationError({
                    slot_name: f"Seçilen {current_part.part_type.get_category_display()} (SN: {current_part.serial_number}) bu uçak modeli ({self.aircraft_model}) ile uyumlu değil. "
                               f"Parça {current_part.aircraft_model_compatibility} modeli için üretilmiş."
                })

            # Kural 5: Slota yeni atanan parçanın durumu AVAILABLE olmalı
            original_part_in_slot = original_parts.get(slot_name)
            if current_part != original_part_in_slot: # Parça değişmiş veya ilk kez atanıyorsa
                if current_part.status != PartStatusChoices.AVAILABLE:
                    raise ValidationError({
                        slot_name: f"Seçilen {current_part.part_type.get_category_display()} (SN: {current_part.serial_number}) montaj için '{PartStatusChoices.AVAILABLE.label}' durumda değil. Mevcut durumu: {current_part.get_status_display()}."
                    })
        # Kural 6: Aktif bir uçak için tüm ana parçalar seçilmiş olmalı.
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
        """
        Hava aracı kaydedilirken özel mantık uygular:
        - Eğer yeni bir hava aracı ise, otomatik olarak bir seri numarası atar.
          Seri numarası formatı: <UçakModelAdı>-<SıraNo> (örn: TB2-0001).
        - Uçaktan çıkarılan eski parçaların durumunu 'AVAILABLE' yapar.
        - Uçağa yeni takılan parçaların durumunu 'USED' yapar.
        """
        if not self.pk:  # Sadece yeni bir instance ise (henüz primary key'i yoksa) seri numarası ata.
            if not self.aircraft_model:
                # aircraft_model None ise seri numarası üretemeyiz. clean() bunu engellemeli.
                raise DjangoValidationError("Seri numarası atamak için hava aracı modeli belirtilmelidir.")

            prefix = f"{self.aircraft_model.name}-" 
            
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
            self.serial_number = f"{prefix}{new_sequence_no:04d}" # 4 haneli, başı sıfırla doldurulmuş sıra no

        # Parça Durum Güncelleme Mantığı
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

        super().save(*args, **kwargs)

        # Çıkarılan eski parçaların durumunu 'AVAILABLE' yap
        for old_part in original_parts_to_make_available:
            if old_part: # None değilse
                old_part.status = PartStatusChoices.AVAILABLE
                old_part.save()

        # Uçağa yeni takılan/atanan parçaların durumunu 'USED' yap
        current_parts_to_mark_used = [self.wing, self.fuselage, self.tail, self.avionics]
        for current_part in current_parts_to_mark_used:
            if current_part: # None değilse
                if current_part.status != PartStatusChoices.USED:
                    current_part.status = PartStatusChoices.USED
                current_part.save() # Parçanın son halini kaydet