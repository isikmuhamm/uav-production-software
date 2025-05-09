# aircraft_production_app/management/commands/create_random_parts.py
import random
from django.core.management.base import BaseCommand
from django.db import transaction
from aircraft_production_app.models import (
    Part, PartType, AircraftModel, Team, Personnel,
    PartStatusChoices, PartCategory, DefinedTeamTypes
)

class Command(BaseCommand):
    help = 'Creates 100 random Part instances for testing.'

    @transaction.atomic # Tüm işlemlerin başarılı olmasını veya hiçbirinin olmamasını sağlar
    def handle(self, *args, **options):
        self.stdout.write("Fetching prerequisites...")

        # 1. Mevcut Parça Tiplerini (Kategorilerini) ve Uçak Modellerini Al
        # Bunların data migration veya AppConfig.ready() ile oluşturulduğunu varsayıyoruz.
        part_types = list(PartType.objects.all())
        aircraft_models = list(AircraftModel.objects.all())

        if not part_types:
            self.stderr.write(self.style.ERROR("No PartType (categories) found in the database. Please populate them first."))
            return
        if not aircraft_models:
            self.stderr.write(self.style.ERROR("No AircraftModel found in the database. Please populate them first."))
            return

        # 2. Üretim Yapabilecek Takımları Al (Personeli olan ve montaj takımı olmayan)
        # Her parça kategorisi için uygun üretim takımlarını bulalım
        producible_teams_map = {}
        for pt_category_value, pt_category_label in PartCategory.choices:
            # Bu kategoriye uygun takım tipini bul
            team_type_for_category = None
            if pt_category_value == PartCategory.WING.value:
                team_type_for_category = DefinedTeamTypes.WING_TEAM
            elif pt_category_value == PartCategory.FUSELAGE.value:
                team_type_for_category = DefinedTeamTypes.FUSELAGE_TEAM
            elif pt_category_value == PartCategory.TAIL.value:
                team_type_for_category = DefinedTeamTypes.TAIL_TEAM
            elif pt_category_value == PartCategory.AVIONICS.value:
                team_type_for_category = DefinedTeamTypes.AVIONICS_TEAM
            
            if team_type_for_category:
                # Bu takım tipine sahip ve en az bir personeli olan takımları al
                suitable_teams = list(Team.objects.filter(
                    team_type=team_type_for_category,
                    members__isnull=False # Personeli olan takımlar (Personnel.team related_name='members')
                ).distinct()) # distinct() önemli olabilir eğer bir personel birden fazla kez sayılırsa (gerçi OneToOne)
                
                if suitable_teams:
                    producible_teams_map[pt_category_value] = suitable_teams
                else:
                    self.stdout.write(self.style.WARNING(
                        f"Warning: No suitable teams (with personnel) found for PartCategory '{pt_category_label}' "
                        f"(expected TeamType: {DefinedTeamTypes(team_type_for_category).label}). "
                        f"Parts of this category might not be created if no team is found."
                    ))
        
        if not producible_teams_map:
            self.stderr.write(self.style.ERROR(
                "No production teams with personnel found for any part category. "
                "Please create teams, assign them appropriate production types, and add personnel to them."
            ))
            return

        self.stdout.write("Starting part creation process...")
        parts_created_count = 0
        for i in range(100): # 100 adet parça oluştur
            selected_part_type = random.choice(part_types)
            selected_aircraft_model = random.choice(aircraft_models)

            # Seçilen parça tipi için uygun takımları al
            suitable_teams_for_part_type = producible_teams_map.get(selected_part_type.category)
            
            if not suitable_teams_for_part_type:
                self.stdout.write(self.style.WARNING(
                    f"Skipping part creation for category '{selected_part_type.get_category_display()}' as no suitable team was found."
                ))
                continue # Bu parça için uygun takım yoksa atla

            selected_team = random.choice(suitable_teams_for_part_type)

            try:
                # Part.save() metodu seri numarasını otomatik atayacak
                # Part.clean() metodu takım ve parça tipi uyumluluğunu (ve personel varlığını) kontrol edecek
                # (Aslında personel varlığını yukarıda zaten filtreledik ama clean() bir daha bakar)
                part = Part.objects.create(
                    part_type=selected_part_type,
                    aircraft_model_compatibility=selected_aircraft_model,
                    produced_by_team=selected_team,
                    status=PartStatusChoices.AVAILABLE # Test için çoğunlukla 'AVAILABLE' yapalım
                )
                parts_created_count += 1
                if (i + 1) % 10 == 0: # Her 10 parçada bir bilgi ver
                    self.stdout.write(f"  Created {parts_created_count} parts so far (SN: {part.serial_number})...")
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error creating part {i+1}: {e}"))
                self.stderr.write(self.style.ERROR(
                    f"  Details: PartType='{selected_part_type}', Model='{selected_aircraft_model}', Team='{selected_team}'"
                ))


        self.stdout.write(self.style.SUCCESS(f"Successfully created {parts_created_count} random Part instances."))