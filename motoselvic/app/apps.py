# app/apps.py
from django.apps import AppConfig

class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'  # Change 'app' to your actual app name

    def ready(self):
        import app.signals  # This will register your signals
