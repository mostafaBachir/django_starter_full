import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Notification

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            await self.close()
            return
        
        self.user_group_name = f"notifications_{self.user.id}"
        
        # Rejoindre le groupe de notifications de l'utilisateur
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Envoyer les notifications non lues
        unread_notifications = await self.get_unread_notifications()
        await self.send(text_data=json.dumps({
            'type': 'unread_notifications',
            'notifications': unread_notifications
        }))
    
    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'mark_read':
            notification_id = data.get('notification_id')
            await self.mark_notification_read(notification_id)
            
            await self.send(text_data=json.dumps({
                'type': 'notification_marked_read',
                'notification_id': notification_id
            }))
        
        elif message_type == 'mark_all_read':
            await self.mark_all_notifications_read()
            
            await self.send(text_data=json.dumps({
                'type': 'all_notifications_marked_read'
            }))
    
    async def notification_message(self, event):
        """
        Recevoir une notification du groupe
        """
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': event['notification']
        }))
    
    @database_sync_to_async
    def get_unread_notifications(self):
        notifications = Notification.objects.filter(
            user=self.user,
            read=False
        ).values(
            'id', 'title', 'message', 'type', 'created_at'
        )
        
        return list(notifications)
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=self.user
            )
            notification.read = True
            notification.save()
            return True
        except Notification.DoesNotExist:
            return False
    
    @database_sync_to_async
    def mark_all_notifications_read(self):
        Notification.objects.filter(
            user=self.user,
            read=False
        ).update(read=True)
