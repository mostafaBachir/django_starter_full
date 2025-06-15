from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Créer les groupes par défaut avec leurs permissions'
    
    def handle(self, *args, **kwargs):
        # Créer les groupes
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        manager_group, _ = Group.objects.get_or_create(name='Manager')
        user_group, _ = Group.objects.get_or_create(name='User')
        
        # Obtenir le content type pour le modèle User
        user_content_type = ContentType.objects.get_for_model(User)
        
        # Définir les permissions pour chaque groupe
        # Admin - toutes les permissions
        admin_permissions = Permission.objects.filter(
            content_type__app_label='accounts'
        )
        admin_group.permissions.set(admin_permissions)
        
        # Manager - peut voir et éditer les utilisateurs
        manager_permissions = Permission.objects.filter(
            content_type=user_content_type,
            codename__in=['view_user', 'change_user']
        )
        manager_group.permissions.set(manager_permissions)
        
        # User - permissions de base (aucune permission spéciale)
        user_group.permissions.clear()
        
        self.stdout.write(
            self.style.SUCCESS('Groupes créés avec succès : Admin, Manager, User')
        )