# apps/notifications/utils.py
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification


def send_notification(user, title, message, notification_type='info'):
    """
    Créer une notification et l'envoyer via WebSocket
    """
    # Créer la notification dans la base de données
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        type=notification_type
    )
    
    # Préparer les données de la notification
    notification_data = {
        'id': str(notification.id),
        'title': notification.title,
        'message': notification.message,
        'type': notification.type,
        'created_at': notification.created_at.isoformat(),
        'read': notification.read
    }
    
    # Envoyer via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"notifications_{user.id}",
        {
            'type': 'notification_message',
            'notification': notification_data
        }
    )
    
    return notification


# Exemple d'utilisation dans une vue ou une tâche Celery:
# from apps.notifications.utils import send_notification
# send_notification(user, "Bienvenue !", "Votre compte a été créé avec succès", "success")