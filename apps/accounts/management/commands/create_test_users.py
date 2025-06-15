from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Créer des utilisateurs de test pour chaque rôle'
    
    def handle(self, *args, **kwargs):
        # S'assurer que les groupes existent
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        manager_group, _ = Group.objects.get_or_create(name='Manager')
        user_group, _ = Group.objects.get_or_create(name='User')
        
        # Créer un superadmin
        if not User.objects.filter(email='admin@example.com').exists():
            admin = User.objects.create_superuser(
                email='admin@example.com',
                password='admin123',
                first_name='Admin',
                last_name='User'
            )
            admin.groups.add(admin_group)
            self.stdout.write(
                self.style.SUCCESS(f'Superadmin créé : admin@example.com / admin123')
            )
        
        # Créer un manager
        if not User.objects.filter(email='manager@example.com').exists():
            manager = User.objects.create_user(
                email='manager@example.com',
                password='manager123',
                first_name='Manager',
                last_name='User'
            )
            manager.groups.add(manager_group)
            self.stdout.write(
                self.style.SUCCESS(f'Manager créé : manager@example.com / manager123')
            )
        
        # Créer un utilisateur normal
        if not User.objects.filter(email='user@example.com').exists():
            user = User.objects.create_user(
                email='user@example.com',
                password='user123',
                first_name='Normal',
                last_name='User'
            )
            user.groups.add(user_group)
            self.stdout.write(
                self.style.SUCCESS(f'User créé : user@example.com / user123')
            )