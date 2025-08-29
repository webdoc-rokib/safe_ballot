from django.apps import AppConfig

class ElectionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'elections'

    def ready(self):
        # import signals to auto-create Profile when User is created
        import elections.signals  # noqa: F401
