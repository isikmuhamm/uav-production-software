# aircraft_production_app/migrations/XXXX_populate_fixed_types.py
from django.db import migrations

# Sabit seçeneklerimizi model dosyasından buraya kopyalayabiliriz veya import edebiliriz.
# Bağımlılıkları azaltmak için doğrudan string değerleri kullanmak bazen daha iyidir
# veya migration'ın bağımlı olduğu önceki migration'dan modelleri almak.
# Şimdilik enumları doğrudan kullanacağız (model dosyanızdaki tanımlarla aynı olmalı).

# Model dosyanızdaki enum tanımlarını buraya referans olarak alalım:
# class AircraftModelChoices(models.TextChoices):
#     TB2 = "TB2", "TB2"
#     TB3 = "TB3", "TB3"
#     AKINCI = "AKINCI", "AKINCI"
#     KIZILELMA = "KIZILELMA", "KIZILELMA"

# class PartCategory(models.TextChoices):
#     WING = "WING", "Kanat"
#     FUSELAGE = "FUSELAGE", "Gövde"
#     TAIL = "TAIL", "Kuyruk"
#     AVIONICS = "AVIONICS", "Aviyonik"

AIRCRAFT_MODELS = [
    ("TB2", "TB2"),
    ("TB3", "TB3"),
    ("AKINCI", "AKINCI"),
    ("KIZILELMA", "KIZILELMA"),
]

PART_CATEGORIES = [
    ("WING", "Kanat"),
    ("FUSELAGE", "Gövde"),
    ("TAIL", "Kuyruk"),
    ("AVIONICS", "Aviyonik"),
]

def populate_initial_data(apps, schema_editor):
    AircraftModel = apps.get_model('aircraft_production_app', 'AircraftModel')
    PartType = apps.get_model('aircraft_production_app', 'PartType')
    db_alias = schema_editor.connection.alias

    print("\nPopulating Aircraft Models...")
    for value, label in AIRCRAFT_MODELS:
        obj, created = AircraftModel.objects.using(db_alias).get_or_create(name=value)
        if created:
            print(f"  Created AircraftModel: {label}")
        else:
            print(f"  AircraftModel already exists: {label}")

    print("\nPopulating Part Types (Categories)...")
    for value, label in PART_CATEGORIES:
        # PartType modelinde 'category' alanı unique=True ve choices kullanıyor.
        # Değer olarak enum'ın 'value' kısmını (örn: "WING") kullanmalıyız.
        obj, created = PartType.objects.using(db_alias).get_or_create(category=value)
        if created:
            print(f"  Created PartType: {label} (Category: {value})")
        else:
            print(f"  PartType already exists: {label} (Category: {value})")

def reverse_populate_data(apps, schema_editor):
    # Bu migration geri alınırsa, eklenen verileri silmek isteyebiliriz.
    # Ancak get_or_create kullandığımız için, eğer bu veriler başka bir şekilde de
    # oluşmuş olabilecekse, silmek riskli olabilir. Şimdilik basitçe pass geçebiliriz.
    # Veya sadece bu migration'ın eklediği bilinen değerleri sileriz.
    AircraftModel = apps.get_model('aircraft_production_app', 'AircraftModel')
    PartType = apps.get_model('aircraft_production_app', 'PartType')
    db_alias = schema_editor.connection.alias

    print("\nReversing initial data population (deleting specific entries if they exist)...")
    for value, _ in AIRCRAFT_MODELS:
        AircraftModel.objects.using(db_alias).filter(name=value).delete()
    
    for value, _ in PART_CATEGORIES:
        PartType.objects.using(db_alias).filter(category=value).delete()
    print("  Done reversing.")


class Migration(migrations.Migration):

    dependencies = [
        # Bu migration'ın, modellerinizin (AircraftModel, PartType) oluşturulduğu
        # bir önceki migration dosyasına bağımlı olduğundan emin olun.
        # Genellikle bu '0001_initial.py' veya modellerin son şema değişikliğini içeren dosyadır.
        # `python manage.py showmigrations aircraft_production_app` komutuyla son migration'ınızı görebilirsiniz.
        # Örneğin: ('aircraft_production_app', '0001_initial'),
        ('aircraft_production_app', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(populate_initial_data, reverse_code=reverse_populate_data),
    ]