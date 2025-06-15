from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User
from .tasks import send_welcome_email
from apps.notifications.utils import send_notification


@receiver(post_save, sender=User)
def user_created_handler(sender, instance, created, **kwargs):
    if created:
        # Envoyer un email de bienvenue
        send_welcome_email.delay(instance.id)
        
        # Créer une notification de bienvenue
        send_notification(
            user=instance,
            title="Bienvenue sur Django Starter !",
            message="Votre compte a été créé avec succès. Découvrez toutes nos fonctionnalités.",
            notification_type="success"
        )