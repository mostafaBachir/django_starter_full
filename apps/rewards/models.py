from django.db import models

# Create your models here.
# apps/rewards/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
import uuid
import random
from datetime import timedelta


class RewardProgram(models.Model):
    """
    Programmes de récompenses (pour support multi-programmes futurs)
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nom du programme"
    )
    slug = models.SlugField(
        unique=True,
        max_length=100
    )
    description = models.TextField(
        verbose_name="Description"
    )
    
    # Configuration des points
    points_per_dollar = models.IntegerField(
        default=10,
        verbose_name="Points par dollar"
    )
    points_per_receipt = models.IntegerField(
        default=5,
        verbose_name="Points par reçu"
    )
    
    # Limites
    daily_receipt_limit = models.IntegerField(
        default=20,
        verbose_name="Limite reçus/jour"
    )
    monthly_receipt_limit = models.IntegerField(
        default=500,
        verbose_name="Limite reçus/mois"
    )
    
    # Statut
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Programme de récompenses"
        verbose_name_plural = "Programmes de récompenses"
        db_table = 'rewards_program'
    
    def __str__(self):
        return self.name


class UserLevel(models.Model):
    """
    Niveaux utilisateur avec avantages
    """
    level = models.IntegerField(
        unique=True,
        verbose_name="Niveau"
    )
    name = models.CharField(
        max_length=50,
        verbose_name="Nom"
    )
    icon = models.CharField(
        max_length=50,
        default='star',
        verbose_name="Icône"
    )
    color = models.CharField(
        max_length=7,
        default='#FFD700',
        verbose_name="Couleur"
    )
    
    # Seuils
    points_required = models.IntegerField(
        verbose_name="Points requis"
    )
    receipts_required = models.IntegerField(
        default=0,
        verbose_name="Reçus requis"
    )
    
    # Avantages
    cashback_bonus = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Bonus cashback %"
    )
    points_multiplier = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=1.0,
        verbose_name="Multiplicateur points"
    )
    daily_bonus_spins = models.IntegerField(
        default=0,
        verbose_name="Spins bonus/jour"
    )
    
    # Privilèges
    perks = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Avantages"
    )
    
    class Meta:
        ordering = ['level']
        verbose_name = "Niveau utilisateur"
        verbose_name_plural = "Niveaux utilisateur"
        db_table = 'rewards_user_level'
    
    def __str__(self):
        return f"Niveau {self.level} - {self.name}"


class UserReward(models.Model):
    """
    Statut des récompenses utilisateur
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reward_status'
    )
    
    # Points
    points_balance = models.IntegerField(
        default=0,
        verbose_name="Solde points"
    )
    lifetime_points = models.IntegerField(
        default=0,
        verbose_name="Points totaux gagnés"
    )
    
    # Niveau
    current_level = models.ForeignKey(
        UserLevel,
        on_delete=models.PROTECT,
        null=True,
        verbose_name="Niveau actuel"
    )
    level_progress = models.IntegerField(
        default=0,
        verbose_name="Progression niveau"
    )
    
    # Spins (machine à sous)
    spins_available = models.IntegerField(
        default=3,
        verbose_name="Spins disponibles"
    )
    last_daily_spin = models.DateField(
        null=True,
        blank=True,
        verbose_name="Dernier spin quotidien"
    )
    total_spins_used = models.IntegerField(
        default=0,
        verbose_name="Total spins utilisés"
    )
    
    # Statistiques
    total_rewards_claimed = models.IntegerField(default=0)
    last_reward_date = models.DateTimeField(null=True, blank=True)
    streak_days = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    
    # Limites quotidiennes
    receipts_today = models.IntegerField(default=0)
    points_earned_today = models.IntegerField(default=0)
    last_reset_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Statut récompenses"
        verbose_name_plural = "Statuts récompenses"
        db_table = 'rewards_user_reward'
    
    def add_points(self, amount, source='receipt'):
        """Ajoute des points avec multiplicateur de niveau"""
        if self.current_level:
            amount = int(amount * self.current_level.points_multiplier)
        
        self.points_balance += amount
        self.lifetime_points += amount
        self.points_earned_today += amount
        self.save()
        
        # Créer transaction
        PointTransaction.objects.create(
            user=self.user,
            amount=amount,
            transaction_type='earn',
            source=source
        )
        
        # Vérifier progression niveau
        self.check_level_up()
        
        return amount
    
    def check_level_up(self):
        """Vérifie et applique le passage de niveau"""
        next_level = UserLevel.objects.filter(
            points_required__lte=self.lifetime_points
        ).order_by('-level').first()
        
        if next_level and next_level != self.current_level:
            old_level = self.current_level
            self.current_level = next_level
            self.save()
            
            # Créer notification
            LevelUpNotification.objects.create(
                user=self.user,
                old_level=old_level,
                new_level=next_level
            )
            
            # Bonus de niveau
            if next_level.daily_bonus_spins > 0:
                self.spins_available += next_level.daily_bonus_spins
                self.save()
    
    def reset_daily_limits(self):
        """Reset les limites quotidiennes"""
        today = timezone.now().date()
        if self.last_reset_date != today:
            self.receipts_today = 0
            self.points_earned_today = 0
            self.last_reset_date = today
            
            # Spin quotidien gratuit
            if self.last_daily_spin != today:
                self.spins_available += 1
                self.last_daily_spin = today
                
            self.save()
    
    def update_streak(self):
        """Met à jour la série de jours actifs"""
        today = timezone.now().date()
        
        if self.last_activity_date:
            days_diff = (today - self.last_activity_date).days
            
            if days_diff == 1:
                self.streak_days += 1
                if self.streak_days > self.longest_streak:
                    self.longest_streak = self.streak_days
            elif days_diff > 1:
                self.streak_days = 1
        else:
            self.streak_days = 1
            
        self.last_activity_date = today
        self.save()


class PointTransaction(models.Model):
    """
    Historique des transactions de points
    """
    TRANSACTION_TYPES = [
        ('earn', 'Gain'),
        ('spend', 'Dépense'),
        ('bonus', 'Bonus'),
        ('expire', 'Expiration'),
        ('adjust', 'Ajustement'),
    ]
    
    transaction_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='point_transactions'
    )
    
    amount = models.IntegerField(
        verbose_name="Montant"
    )
    
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES
    )
    
    source = models.CharField(
        max_length=50,
        verbose_name="Source"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )
    
    # Référence
    receipt = models.ForeignKey(
        'receipts.Receipt',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    
    reward = models.ForeignKey(
        'Reward',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    
    # Solde après transaction
    balance_after = models.IntegerField(
        verbose_name="Solde après"
    )
    
    # Expiration des points
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Expire le"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Transaction de points"
        verbose_name_plural = "Transactions de points"
        db_table = 'rewards_point_transaction'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['expires_at']),
        ]


class Reward(models.Model):
    """
    Récompenses échangeables contre points
    """
    REWARD_TYPES = [
        ('cashback', 'Cashback'),
        ('gift_card', 'Carte cadeau'),
        ('product', 'Produit'),
        ('donation', 'Don charité'),
        ('sweepstake', 'Tirage'),
        ('discount', 'Rabais'),
    ]
    
    # Identité
    name = models.CharField(
        max_length=200,
        verbose_name="Nom"
    )
    slug = models.SlugField(
        unique=True,
        max_length=200
    )
    description = models.TextField(
        verbose_name="Description"
    )
    
    # Type et catégorie
    reward_type = models.CharField(
        max_length=20,
        choices=REWARD_TYPES
    )
    category = models.CharField(
        max_length=50,
        blank=True
    )
    
    # Visuels
    image = models.ImageField(
        upload_to='rewards/images/',
        null=True,
        blank=True
    )
    icon = models.CharField(
        max_length=50,
        default='gift'
    )
    
    # Coût et valeur
    points_cost = models.IntegerField(
        verbose_name="Coût en points"
    )
    cash_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Valeur monétaire"
    )
    
    # Stock et limites
    stock_quantity = models.IntegerField(
        default=-1,
        help_text="-1 pour illimité",
        verbose_name="Stock"
    )
    limit_per_user = models.IntegerField(
        default=0,
        help_text="0 pour pas de limite",
        verbose_name="Limite par utilisateur"
    )
    
    # Niveau requis
    required_level = models.ForeignKey(
        UserLevel,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Niveau requis"
    )
    
    # Partenaire
    partner_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Partenaire"
    )
    partner_logo = models.ImageField(
        upload_to='rewards/partners/',
        null=True,
        blank=True
    )
    
    # Validité
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    available_from = models.DateTimeField(null=True, blank=True)
    available_until = models.DateTimeField(null=True, blank=True)
    
    # Métadonnées
    terms_conditions = models.TextField(
        blank=True,
        verbose_name="Conditions"
    )
    delivery_info = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Info livraison"
    )
    
    # Statistiques
    times_redeemed = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['points_cost', 'name']
        verbose_name = "Récompense"
        verbose_name_plural = "Récompenses"
        db_table = 'rewards_reward'
        indexes = [
            models.Index(fields=['reward_type', 'is_active']),
            models.Index(fields=['points_cost']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.points_cost} points)"
    
    @property
    def is_available(self):
        """Vérifie si la récompense est disponible"""
        now = timezone.now()
        
        if not self.is_active:
            return False
            
        if self.available_from and now < self.available_from:
            return False
            
        if self.available_until and now > self.available_until:
            return False
            
        if self.stock_quantity == 0:
            return False
            
        return True
    
    def can_redeem(self, user):
        """Vérifie si un utilisateur peut échanger cette récompense"""
        if not self.is_available:
            return False, "Récompense non disponible"
            
        user_reward = user.reward_status
        
        if user_reward.points_balance < self.points_cost:
            return False, "Points insuffisants"
            
        if self.required_level and user_reward.current_level.level < self.required_level.level:
            return False, f"Niveau {self.required_level.level} requis"
            
        if self.limit_per_user > 0:
            redemptions = RewardRedemption.objects.filter(
                user=user,
                reward=self,
                status='completed'
            ).count()
            
            if redemptions >= self.limit_per_user:
                return False, "Limite atteinte"
                
        return True, "OK"


class RewardRedemption(models.Model):
    """
    Échanges de récompenses
    """
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'Traitement'),
        ('completed', 'Complété'),
        ('delivered', 'Livré'),
        ('cancelled', 'Annulé'),
        ('failed', 'Échoué'),
    ]
    
    redemption_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reward_redemptions'
    )
    
    reward = models.ForeignKey(
        Reward,
        on_delete=models.PROTECT,
        related_name='redemptions'
    )
    
    points_spent = models.IntegerField(
        verbose_name="Points dépensés"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Détails de livraison
    delivery_method = models.CharField(
        max_length=50,
        blank=True
    )
    delivery_details = models.JSONField(
        default=dict,
        blank=True
    )
    
    # Pour cartes cadeaux / codes
    redemption_code = models.CharField(
        max_length=100,
        blank=True,
        unique=True,
        null=True
    )
    
    # Tracking
    notes = models.TextField(blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='processed_redemptions'
    )
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Échange de récompense"
        verbose_name_plural = "Échanges de récompenses"
        db_table = 'rewards_redemption'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', 'created_at']),
        ]


class SpinWheel(models.Model):
    """
    Configuration de la roue de fortune
    """
    name = models.CharField(
        max_length=100,
        default="Roue InovoCB"
    )
    
    is_active = models.BooleanField(default=True)
    
    # Coût d'un spin
    points_cost = models.IntegerField(
        default=0,
        help_text="0 pour gratuit"
    )
    
    # Configuration visuelle
    theme = models.JSONField(
        default=dict,
        blank=True,
        help_text="Couleurs, animations, etc."
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Roue de fortune"
        verbose_name_plural = "Roues de fortune"
        db_table = 'rewards_spin_wheel'


class SpinWheelPrize(models.Model):
    """
    Prix de la roue de fortune
    """
    wheel = models.ForeignKey(
        SpinWheel,
        on_delete=models.CASCADE,
        related_name='prizes'
    )
    
    # Prix
    name = models.CharField(
        max_length=100,
        verbose_name="Nom du prix"
    )
    prize_type = models.CharField(
        max_length=20,
        choices=[
            ('points', 'Points'),
            ('cashback', 'Cashback'),
            ('spin', 'Spin gratuit'),
            ('multiplier', 'Multiplicateur'),
            ('nothing', 'Rien'),
        ]
    )
    prize_value = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    
    # Probabilité
    probability = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Probabilité en %"
    )
    
    # Visuel
    color = models.CharField(
        max_length=7,
        default='#FFD700'
    )
    icon = models.CharField(
        max_length=50,
        default='star'
    )
    
    # Limites
    daily_limit = models.IntegerField(
        default=0,
        help_text="0 pour illimité"
    )
    total_limit = models.IntegerField(
        default=0,
        help_text="0 pour illimité"
    )
    
    # Compteurs
    times_won_today = models.IntegerField(default=0)
    times_won_total = models.IntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        verbose_name = "Prix de roue"
        verbose_name_plural = "Prix de roue"
        db_table = 'rewards_spin_prize'


class SpinHistory(models.Model):
    """
    Historique des spins
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='spin_history'
    )
    
    wheel = models.ForeignKey(
        SpinWheel,
        on_delete=models.CASCADE
    )
    
    prize = models.ForeignKey(
        SpinWheelPrize,
        on_delete=models.SET_NULL,
        null=True
    )
    
    points_spent = models.IntegerField(default=0)
    prize_value = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    
    spun_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-spun_at']
        verbose_name = "Historique spin"
        verbose_name_plural = "Historiques spin"
        db_table = 'rewards_spin_history'
        indexes = [
            models.Index(fields=['user', '-spun_at']),
        ]


class Challenge(models.Model):
    """
    Défis et missions
    """
    CHALLENGE_TYPES = [
        ('daily', 'Quotidien'),
        ('weekly', 'Hebdomadaire'),
        ('monthly', 'Mensuel'),
        ('special', 'Spécial'),
    ]
    
    # Identité
    name = models.CharField(
        max_length=200,
        verbose_name="Nom"
    )
    slug = models.SlugField(
        unique=True,
        max_length=200
    )
    description = models.TextField()
    
    # Type et configuration
    challenge_type = models.CharField(
        max_length=20,
        choices=CHALLENGE_TYPES
    )
    
    # Objectif
    target_type = models.CharField(
        max_length=50,
        choices=[
            ('receipts_count', 'Nombre de reçus'),
            ('receipts_amount', 'Montant total'),
            ('category_count', 'Reçus par catégorie'),
            ('merchant_count', 'Marchands différents'),
            ('streak_days', 'Jours consécutifs'),
        ]
    )
    target_value = models.IntegerField()
    target_category = models.ForeignKey(
        'receipts.Category',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    
    # Récompenses
    points_reward = models.IntegerField(default=0)
    cashback_reward = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )
    bonus_spins = models.IntegerField(default=0)
    
    # Période
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Visuel
    icon = models.CharField(
        max_length=50,
        default='target'
    )
    color = models.CharField(
        max_length=7,
        default='#10B981'
    )
    
    # Statut
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-start_date']
        verbose_name = "Défi"
        verbose_name_plural = "Défis"
        db_table = 'rewards_challenge'
        indexes = [
            models.Index(fields=['challenge_type', 'is_active']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def is_current(self):
        now = timezone.now()
        return self.start_date <= now <= self.end_date


class UserChallenge(models.Model):
    """
    Progression des défis utilisateur
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='challenges'
    )
    
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE
    )
    
    progress = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    reward_claimed = models.BooleanField(default=False)
    
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'challenge']
        verbose_name = "Défi utilisateur"
        verbose_name_plural = "Défis utilisateur"
        db_table = 'rewards_user_challenge'
        indexes = [
            models.Index(fields=['user', 'completed']),
            models.Index(fields=['challenge', 'completed']),
        ]
    
    def update_progress(self, amount=1):
        """Met à jour la progression du défi"""
        self.progress += amount
        
        if self.progress >= self.challenge.target_value and not self.completed:
            self.completed = True
            self.completed_at = timezone.now()
            
        self.save()
    
    def claim_reward(self):
        """Réclame la récompense du défi"""
        if not self.completed or self.reward_claimed:
            return False
            
        user_reward = self.user.reward_status
        
        # Ajouter les récompenses
        if self.challenge.points_reward > 0:
            user_reward.add_points(
                self.challenge.points_reward,
                source=f"challenge_{self.challenge.slug}"
            )
            
        if self.challenge.cashback_reward > 0:
            self.user.add_cashback(
                self.challenge.cashback_reward,
                source=f"challenge_{self.challenge.slug}"
            )
            
        if self.challenge.bonus_spins > 0:
            user_reward.spins_available += self.challenge.bonus_spins
            user_reward.save()
            
        self.reward_claimed = True
        self.save()
        
        return True


class LevelUpNotification(models.Model):
    """
    Notifications de passage de niveau
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='level_notifications'
    )
    
    old_level = models.ForeignKey(
        UserLevel,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+'
    )
    
    new_level = models.ForeignKey(
        UserLevel,
        on_delete=models.SET_NULL,
        null=True
    )
    
    seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification niveau"
        verbose_name_plural = "Notifications niveau"
        db_table = 'rewards_levelup_notification'