from django.apps import AppConfig


class AircraftProductionAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'aircraft_production_app'

    def ready(self):
        import aircraft_production_app.signals # Sinyalleri import et