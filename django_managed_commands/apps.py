from django.apps import AppConfig


class DjangoManagedCommandsConfig(AppConfig):
    """
    Django app configuration for django-managed-commands.
    
    Provides management command discovery and execution capabilities
    for Django projects.
    """
    name = "django_managed_commands"
    verbose_name = "Django Managed Commands"
    default_auto_field = "django.db.models.BigAutoField"
