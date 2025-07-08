# apps/locations/models.py
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point, Polygon
from django.contrib.gis.measure import Distance
from django.contrib.postgres.fields import ArrayField

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.conf import settings
import uuid
from datetime import timedelta


class Zone(models.Model):
    """
    Zones géographiques pour organisation et analytics
    """
    ZONE_TYPES = [
        ('city', 'Ville'),
        ('district', 'Quartier'),
        ('region', 'Région'),
        ('province', 'Province'),
        ('country', 'Pays'),
        ('custom', 'Personnalisé'),
    ]
    
    name = models.CharField(
        max_length=200,
        verbose_name="Nom"
    )
    slug = models.SlugField(
        unique=True,
        max_length=200
    )
    
    zone_type = models.CharField(
        max_length=20,
        choices=ZONE_TYPES,
        default='custom'
    )
    
    # Géométrie de la zone
    boundary = gis_models.PolygonField(
        spatial_index=True,
        verbose_name="Limites"
    )
    center = gis_models.PointField(
        spatial_index=True,
        verbose_name="Centre"
    )
    
    # Hiérarchie
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='subzones'
    )
    
    # Métadonnées
    population = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Population"
    )
    area_sq_km = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Superficie km²"
    )
    
    # Pour l'affichage
    zoom_level = models.IntegerField(
        default=12,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        verbose_name="Niveau zoom carte"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['zone_type', 'name']
        verbose_name = "Zone"
        verbose_name_plural = "Zones"
        db_table = 'locations_zone'
        indexes = [
            models.Index(fields=['zone_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_zone_type_display()})"
    
    def contains_point(self, point):
        """Vérifie si un point est dans la zone"""
        return self.boundary.contains(point)


class BonusZone(models.Model):
    """
    Zones avec cashback bonus (geofencing)
    """
    BONUS_TYPES = [
        ('percentage', 'Pourcentage'),
        ('fixed', 'Montant fixe'),
        ('multiplier', 'Multiplicateur'),
    ]
    
    name = models.CharField(
        max_length=200,
        verbose_name="Nom"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )
    
    # Zone géographique
    zone = models.ForeignKey(
        Zone,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='bonus_zones'
    )
    
    # Ou géofence personnalisée
    geofence = gis_models.PolygonField(
        null=True,
        blank=True,
        spatial_index=True,
        verbose_name="Géofence"
    )
    radius_meters = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(10), MaxValueValidator(10000)],
        help_text="Rayon en mètres si zone circulaire"
    )
    
    # Configuration bonus
    bonus_type = models.CharField(
        max_length=20,
        choices=BONUS_TYPES,
        default='percentage'
    )
    bonus_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Valeur bonus"
    )
    max_bonus_per_receipt = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Bonus max par reçu"
    )
    
    # Limites
    daily_limit = models.IntegerField(
        default=0,
        help_text="0 pour illimité",
        verbose_name="Limite quotidienne"
    )
    total_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Budget total"
    )
    budget_used = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Budget utilisé"
    )
    
    # Marchands spécifiques
    merchants = models.ManyToManyField(
        'receipts.Merchant',
        blank=True,
        related_name='bonus_zones'
    )
    categories = models.ManyToManyField(
        'receipts.Category',
        blank=True,
        related_name='bonus_zones'
    )
    
    # Période de validité
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Horaires (pour happy hours)
    time_restrictions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Restrictions horaires"
    )
    
    # Visuel pour la carte
    color = models.CharField(
        max_length=7,
        default='#10B981',
        verbose_name="Couleur"
    )
    icon = models.CharField(
        max_length=50,
        default='location_on',
        verbose_name="Icône"
    )
    
    # Activation
    is_active = models.BooleanField(default=True)
    requires_notification = models.BooleanField(
        default=True,
        verbose_name="Notifier utilisateurs"
    )
    
    # Statistiques
    times_used = models.IntegerField(default=0)
    total_bonus_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
        verbose_name = "Zone bonus"
        verbose_name_plural = "Zones bonus"
        db_table = 'locations_bonus_zone'
        indexes = [
            models.Index(fields=['is_active', 'start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.name} (+{self.bonus_value})"
    
    @property
    def is_currently_active(self):
        """Vérifie si la zone est active maintenant"""
        now = timezone.now()
        return (
            self.is_active and
            self.start_date <= now <= self.end_date and
            (not self.total_budget or self.budget_used < self.total_budget)
        )
    
    def contains_location(self, point):
        """Vérifie si une localisation est dans la zone bonus"""
        if self.zone:
            return self.zone.contains_point(point)
        elif self.geofence:
            return self.geofence.contains(point)
        return False
    
    def calculate_bonus(self, receipt_amount):
        """Calcule le bonus pour un montant donné"""
        if self.bonus_type == 'percentage':
            bonus = receipt_amount * (self.bonus_value / 100)
        elif self.bonus_type == 'fixed':
            bonus = self.bonus_value
        elif self.bonus_type == 'multiplier':
            bonus = receipt_amount * (self.bonus_value - 1)
        else:
            bonus = 0
            
        # Appliquer le maximum
        if self.max_bonus_per_receipt:
            bonus = min(bonus, self.max_bonus_per_receipt)
            
        return bonus


class UserLocation(models.Model):
    """
    Historique des localisations utilisateur (pour analytics)
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='locations'
    )
    
    location = gis_models.PointField(
        spatial_index=True,
        verbose_name="Localisation"
    )
    
    accuracy = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Précision (m)"
    )
    
    # Source
    source = models.CharField(
        max_length=20,
        choices=[
            ('gps', 'GPS'),
            ('network', 'Réseau'),
            ('ip', 'Adresse IP'),
            ('manual', 'Manuel'),
        ],
        default='gps'
    )
    
    # Contexte
    receipt = models.ForeignKey(
        'receipts.Receipt',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='user_locations'
    )
    
    # Zone détectée
    zone = models.ForeignKey(
        Zone,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    
    # Adresse reverse geocoded
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    # Device
    device_id = models.CharField(
        max_length=255,
        blank=True
    )
    
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-recorded_at']
        verbose_name = "Localisation utilisateur"
        verbose_name_plural = "Localisations utilisateur"
        db_table = 'locations_user_location'
        indexes = [
            models.Index(fields=['user', '-recorded_at']),
            models.Index(fields=['zone']),
        ]


class MerchantLocation(models.Model):
    """
    Emplacements physiques des marchands
    """
    merchant = models.ForeignKey(
        'receipts.Merchant',
        on_delete=models.CASCADE,
        related_name='merchant_locations'
    )
    
    # Identité
    name = models.CharField(
        max_length=200,
        verbose_name="Nom succursale"
    )
    store_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Numéro magasin"
    )
    
    # Localisation
    location = gis_models.PointField(
        spatial_index=True,
        verbose_name="Localisation"
    )
    
    # Adresse
    address = models.TextField(verbose_name="Adresse")
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=50)
    postal_code = models.CharField(max_length=10)
    country = models.CharField(max_length=2, default='CA')
    
    # Zone
    zone = models.ForeignKey(
        Zone,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    
    # Contact
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    # Horaires
    opening_hours = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Heures d'ouverture"
    )
    
    # Caractéristiques
    has_parking = models.BooleanField(default=True)
    is_accessible = models.BooleanField(default=True)
    accepts_cash = models.BooleanField(default=True)
    accepts_cards = models.BooleanField(default=True)
    
    # Validation radius (pour matching reçus)
    validation_radius = models.IntegerField(
        default=200,
        help_text="Rayon de validation en mètres",
        validators=[MinValueValidator(50), MaxValueValidator(1000)]
    )
    
    # Statistiques
    receipts_count = models.IntegerField(default=0)
    average_basket = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['merchant', 'name']
        verbose_name = "Emplacement marchand"
        verbose_name_plural = "Emplacements marchands"
        db_table = 'locations_merchant_location'
        indexes = [
            models.Index(fields=['merchant', 'is_active']),
            models.Index(fields=['city']),
        ]
    
    def __str__(self):
        return f"{self.merchant.name} - {self.name}"
    
    def validate_receipt_location(self, receipt_location):
        """Valide si un reçu a été scanné près de ce magasin"""
        if not receipt_location:
            return False
            
        distance = self.location.distance(receipt_location)
        return distance.m <= self.validation_radius


class HeatmapData(models.Model):
    """
    Données agrégées pour heatmaps
    """
    AGGREGATION_TYPES = [
        ('hourly', 'Horaire'),
        ('daily', 'Quotidien'),
        ('weekly', 'Hebdomadaire'),
        ('monthly', 'Mensuel'),
    ]
    
    zone = models.ForeignKey(
        Zone,
        on_delete=models.CASCADE,
        related_name='heatmap_data'
    )
    
    aggregation_type = models.CharField(
        max_length=20,
        choices=AGGREGATION_TYPES
    )
    
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # Métriques
    receipts_count = models.IntegerField(default=0)
    unique_users = models.IntegerField(default=0)
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total_cashback = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    # Top catégories
    top_categories = models.JSONField(
        default=list,
        blank=True
    )
    
    # Densité pour visualisation
    density_score = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['zone', 'aggregation_type', 'period_start']
        ordering = ['-period_start']
        verbose_name = "Donnée heatmap"
        verbose_name_plural = "Données heatmap"
        db_table = 'locations_heatmap_data'
        indexes = [
            models.Index(fields=['zone', 'aggregation_type', '-period_start']),
        ]


class UserMovementPattern(models.Model):
    """
    Patterns de déplacement utilisateur (pour suggestions)
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='movement_patterns'
    )
    
    # Pattern détecté
    pattern_type = models.CharField(
        max_length=50,
        choices=[
            ('commute', 'Trajet domicile-travail'),
            ('shopping_route', 'Circuit shopping'),
            ('weekend_routine', 'Routine weekend'),
            ('lunch_spots', 'Lieux déjeuner'),
        ]
    )
    
    # Zones fréquentes
    frequent_zones = models.ManyToManyField(
        Zone,
        related_name='user_patterns'
    )
    
    # Jours/heures typiques
    typical_days = ArrayField(
        models.IntegerField(),
        default=list,
        blank=True,
        help_text="0=Lundi, 6=Dimanche"
    )
    typical_hours = ArrayField(
        models.IntegerField(),
        default=list,
        blank=True
    )
    
    # Confiance du pattern
    confidence = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    
    # Données du pattern
    pattern_data = models.JSONField(
        default=dict,
        blank=True
    )
    
    first_detected = models.DateTimeField(auto_now_add=True)
    last_confirmed = models.DateTimeField(auto_now=True)
    times_confirmed = models.IntegerField(default=1)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'pattern_type']
        verbose_name = "Pattern de mouvement"
        verbose_name_plural = "Patterns de mouvement"
        db_table = 'locations_movement_pattern'


class PlaceOfInterest(models.Model):
    """
    Lieux d'intérêt pour suggestions et analytics
    """
    POI_TYPES = [
        ('mall', 'Centre commercial'),
        ('market', 'Marché'),
        ('restaurant_zone', 'Zone restaurants'),
        ('business_district', 'Quartier affaires'),
        ('tourist_spot', 'Lieu touristique'),
        ('transport_hub', 'Hub transport'),
    ]
    
    name = models.CharField(
        max_length=200,
        verbose_name="Nom"
    )
    slug = models.SlugField(
        unique=True,
        max_length=200
    )
    
    poi_type = models.CharField(
        max_length=20,
        choices=POI_TYPES
    )
    
    # Localisation
    location = gis_models.PointField(spatial_index=True)
    boundary = gis_models.PolygonField(
        null=True,
        blank=True,
        spatial_index=True
    )
    
    # Zone parent
    zone = models.ForeignKey(
        Zone,
        on_delete=models.CASCADE,
        related_name='places_of_interest'
    )
    
    # Marchands associés
    merchants = models.ManyToManyField(
        'receipts.Merchant',
        blank=True,
        related_name='places_of_interest'
    )
    
    # Métadonnées
    description = models.TextField(blank=True)
    amenities = models.JSONField(
        default=list,
        blank=True
    )
    
    # Pour suggestions
    suggestion_radius = models.IntegerField(
        default=500,
        help_text="Rayon de suggestion en mètres"
    )
    peak_hours = models.JSONField(
        default=dict,
        blank=True
    )
    
    # Statistiques
    popularity_score = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Lieu d'intérêt"
        verbose_name_plural = "Lieux d'intérêt"
        db_table = 'locations_place_of_interest'


class LocationValidation(models.Model):
    """
    Validation des localisations de reçus
    """
    receipt = models.OneToOneField(
        'receipts.Receipt',
        on_delete=models.CASCADE,
        related_name='location_validation'
    )
    
    # Localisation déclarée
    declared_location = gis_models.PointField(
        null=True,
        blank=True
    )
    
    # Marchant trouvé
    matched_merchant_location = models.ForeignKey(
        MerchantLocation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    
    # Distance de validation
    distance_meters = models.FloatField(
        null=True,
        blank=True
    )
    
    # Résultat
    is_valid = models.BooleanField(default=False)
    validation_score = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    
    # Raisons
    validation_method = models.CharField(
        max_length=50,
        choices=[
            ('gps_match', 'Correspondance GPS'),
            ('zone_match', 'Correspondance zone'),
            ('pattern_match', 'Pattern utilisateur'),
            ('manual', 'Validation manuelle'),
            ('failed', 'Échec validation'),
        ]
    )
    
    notes = models.TextField(blank=True)
    
    validated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Validation localisation"
        verbose_name_plural = "Validations localisation"
        db_table = 'locations_validation'
        indexes = [
            models.Index(fields=['is_valid']),
        ]


# Signaux pour traitement automatique
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='receipts.Receipt')
def validate_receipt_location(sender, instance, created, **kwargs):
    """Valide automatiquement la localisation d'un reçu"""
    if created and instance.location and instance.merchant:
        # Chercher le merchant location le plus proche
        from django.contrib.gis.measure import D
        
        nearby_locations = MerchantLocation.objects.filter(
            merchant=instance.merchant,
            location__distance_lte=(instance.location, D(m=1000))
        ).order_by('location')
        
        if nearby_locations.exists():
            closest = nearby_locations.first()
            distance = instance.location.distance(closest.location).m
            
            LocationValidation.objects.create(
                receipt=instance,
                declared_location=instance.location,
                matched_merchant_location=closest,
                distance_meters=distance,
                is_valid=distance <= closest.validation_radius,
                validation_score=max(0, 1 - (distance / closest.validation_radius)),
                validation_method='gps_match'
            )
            
            # Vérifier les zones bonus
            active_bonus_zones = BonusZone.objects.filter(
                is_active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now()
            )
            
            for bonus_zone in active_bonus_zones:
                if bonus_zone.contains_location(instance.location):
                    # Appliquer le bonus
                    bonus_amount = bonus_zone.calculate_bonus(instance.total_amount)
                    instance.bonus_amount = bonus_amount
                    instance.save(update_fields=['bonus_amount'])
                    
                    # Mettre à jour les stats de la zone
                    bonus_zone.times_used += 1
                    bonus_zone.total_bonus_paid += bonus_amount
                    bonus_zone.budget_used += bonus_amount
                    bonus_zone.save()
                    
                    break  # Appliquer seulement le premier bonus trouvé