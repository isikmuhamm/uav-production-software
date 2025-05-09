# aircraft_production_app/signals.py
from django.db.models.signals import post_save, pre_delete # pre_delete'i import et
from django.dispatch import receiver
from .models import Aircraft, WorkOrder, WorkOrderStatusChoices, Part, PartStatusChoices # Part ve PartStatusChoices'ı import et

@receiver(post_save, sender=Aircraft)
def update_work_order_status_on_aircraft_creation(sender, instance, created, **kwargs):
    if instance.work_order:  # Eğer uçak bir iş emrine bağlıysa
        work_order = instance.work_order

        # Sadece durumu "Tamamlandı" veya "İptal Edildi" olmayan iş emirlerini güncelle
        if work_order.status not in [WorkOrderStatusChoices.COMPLETED, WorkOrderStatusChoices.CANCELLED]:
            completed_aircraft_count = Aircraft.objects.filter(work_order=work_order).count()

            if completed_aircraft_count >= work_order.quantity:
                work_order.status = WorkOrderStatusChoices.COMPLETED
            elif completed_aircraft_count > 0: # En az bir uçak üretildiyse ama hedefe ulaşılmadıysa
                work_order.status = WorkOrderStatusChoices.IN_PROGRESS
            # Eğer completed_aircraft_count == 0 ise (örneğin ilk uçak silinirse ve sayı 0'a düşerse),
            # durum PENDING veya ASSIGNED'a geri dönebilir. Bu mantık eklenebilir veya
            # initial save metodundaki PENDING/ASSIGNED yeterli olabilir.
            # Şimdilik, 0'a düşerse durumunu değiştirmiyoruz, ilk atandığı gibi kalıyor.
            #Ya da PENDING/ASSIGNED'a geri döndürmek için:
            else: # completed_aircraft_count == 0
                if work_order.assigned_to_assembly_team:
                    work_order.status = WorkOrderStatusChoices.ASSIGNED
                else:
                    work_order.status = WorkOrderStatusChoices.PENDING
            work_order.save()


@receiver(pre_delete, sender=Aircraft)
def make_parts_available_on_aircraft_deletion(sender, instance, **kwargs):
    """
    Bir uçak silinmeden hemen önce, üzerinde bulunan parçaların durumunu
    'AVAILABLE' olarak günceller.
    """
    aircraft_being_deleted = instance
    parts_to_update = [
        aircraft_being_deleted.wing,
        aircraft_being_deleted.fuselage,
        aircraft_being_deleted.tail,
        aircraft_being_deleted.avionics
    ]

    for part_instance in parts_to_update:
        if part_instance: # Eğer slota bir parça atanmışsa
            # Parçanın uçağa olan bağlantısını koparmaya gerek yok, çünkü uçak zaten siliniyor.
            # Sadece durumunu güncellememiz yeterli.
            part_instance.status = PartStatusChoices.AVAILABLE
            part_instance.save()
            print(f"'{part_instance}' (SN: {part_instance.serial_number}) uçağı silindiği için durumu '{PartStatusChoices.AVAILABLE.label}' olarak güncellendi.") # Loglama/Debug için