# apps/accounts/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from .models import User, PasswordResetToken


@shared_task
def send_password_reset_email(user_id, token):
    """
    Envoyer un email de réinitialisation de mot de passe
    """
    try:
        user = User.objects.get(id=user_id)
        
        # URL de réinitialisation (à adapter selon votre frontend)
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        
        # Contexte pour le template
        context = {
            'user': user,
            'reset_url': reset_url,
            'site_name': 'Django Starter',
        }
        
        # Message HTML
        html_message = f"""
        <h2>Réinitialisation de mot de passe</h2>
        <p>Bonjour {user.get_full_name()},</p>
        <p>Vous avez demandé une réinitialisation de votre mot de passe.</p>
        <p>Cliquez sur le lien ci-dessous pour réinitialiser votre mot de passe :</p>
        <p><a href="{reset_url}">Réinitialiser mon mot de passe</a></p>
        <p>Ce lien est valide pendant 24 heures.</p>
        <p>Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.</p>
        <br>
        <p>Cordialement,<br>L'équipe Django Starter</p>
        """
        
        # Message texte
        text_message = f"""
        Réinitialisation de mot de passe
        
        Bonjour {user.get_full_name()},
        
        Vous avez demandé une réinitialisation de votre mot de passe.
        
        Cliquez sur le lien ci-dessous pour réinitialiser votre mot de passe :
        {reset_url}
        
        Ce lien est valide pendant 24 heures.
        
        Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.
        
        Cordialement,
        L'équipe Django Starter
        """
        
        send_mail(
            subject='Réinitialisation de votre mot de passe',
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f"Email de réinitialisation envoyé à {user.email}"
    
    except User.DoesNotExist:
        return f"Utilisateur avec l'ID {user_id} introuvable"
    except Exception as e:
        return f"Erreur lors de l'envoi de l'email: {str(e)}"


@shared_task
def send_welcome_email(user_id):
    """
    Envoyer un email de bienvenue après l'inscription
    """
    try:
        user = User.objects.get(id=user_id)
        
        html_message = f"""
        <h2>Bienvenue sur Django Starter !</h2>
        <p>Bonjour {user.get_full_name()},</p>
        <p>Nous sommes ravis de vous compter parmi nous.</p>
        <p>Votre compte a été créé avec succès avec l'email : {user.email}</p>
        <p>Vous pouvez maintenant vous connecter et profiter de toutes nos fonctionnalités.</p>
        <br>
        <p>Cordialement,<br>L'équipe Django Starter</p>
        """
        
        text_message = f"""
        Bienvenue sur Django Starter !
        
        Bonjour {user.get_full_name()},
        
        Nous sommes ravis de vous compter parmi nous.
        
        Votre compte a été créé avec succès avec l'email : {user.email}
        
        Vous pouvez maintenant vous connecter et profiter de toutes nos fonctionnalités.
        
        Cordialement,
        L'équipe Django Starter
        """
        
        send_mail(
            subject='Bienvenue sur Django Starter',
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f"Email de bienvenue envoyé à {user.email}"
    
    except User.DoesNotExist:
        return f"Utilisateur avec l'ID {user_id} introuvable"
    except Exception as e:
        return f"Erreur lors de l'envoi de l'email: {str(e)}"


@shared_task
def cleanup_expired_password_reset_tokens():
    """
    Nettoyer les tokens de réinitialisation expirés
    Tâche périodique exécutée tous les jours
    """
    expired_tokens = PasswordResetToken.objects.filter(
        created_at__lt=timezone.now() - timezone.timedelta(hours=24)
    )
    count = expired_tokens.count()
    expired_tokens.delete()
    
    return f"{count} tokens expirés supprimés"


@shared_task
def send_daily_notification_summary():
    """
    Exemple de tâche périodique : envoyer un résumé quotidien
    """
    active_users = User.objects.filter(is_active=True, is_staff=True)
    
    for user in active_users:
        # Ici vous pouvez ajouter la logique pour créer un résumé
        # Par exemple, compter les nouvelles inscriptions, etc.
        
        html_message = f"""
        <h2>Résumé quotidien</h2>
        <p>Bonjour {user.get_full_name()},</p>
        <p>Voici votre résumé quotidien :</p>
        <ul>
            <li>Nombre total d'utilisateurs : {User.objects.count()}</li>
            <li>Nouveaux utilisateurs aujourd'hui : {User.objects.filter(date_joined__date=timezone.now().date()).count()}</li>
        </ul>
        <br>
        <p>Bonne journée !</p>
        """
        
        send_mail(
            subject='Résumé quotidien - Django Starter',
            message='Voir la version HTML',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=True,
        )
    
    return f"Résumé envoyé à {active_users.count()} utilisateurs"