# apps/receipts/models.py
from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.conf import settings
import uuid
import hashlib


class Merchant(models.Model):
    """
    Marchands partenaires InovoCB
    """
    MERCHANT_TYPES = [
        ('grocery', 'Épicerie'),
        ('restaurant', 'Restaurant'),
        ('pharmacy', 'Pharmacie'),
        ('gas', 'Station-service'),
        ('retail', 'Détail'),
        ('entertainment', 'Divertissement'),
        ('travel', 'Voyage'),
        ('online', 'En ligne'),
        ('other', 'Autre'),
    ]
    
    # Identité
    name = models.CharField(
        max_length=255,
        verbose_name="Nom"
    )
    display_name = models.CharField(
        max_length=255,
        verbose_name="Nom d'affichage"
    )
    slug = models.SlugField(
        unique=True,
        max_length=255
    )
    
    # Type et catégorie
    merchant_type = models.CharField(
        max_length=20,
        choices=MERCHANT_TYPES,
        default='other'
    )
    category = models.ForeignKey(
        'Category',
        on_delete=models.SET_NULL,
        null=True,
        related_name='merchants'
    )
    
    # Logo et branding
    logo = models.ImageField(
        upload_to='merchants/logos/',
        null=True,
        blank=True
    )
    brand_color = models.CharField(
        max_length=7,
        default='#000000',
        help_text="Couleur hex"
    )
    
    # Partenariat InovoCB
    is_partner = models.BooleanField(
        default=False,
        verbose_name="Partenaire"
    )
    cashback_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Taux cashback %"
    )
    bonus_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Taux bonus %"
    )
    
    # Géolocalisation (pour validation)
    locations = gis_models.MultiPointField(
        null=True,
        blank=True,
        help_text="Emplacements physiques"
    )
    
    # Métadonnées
    tax_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Numéro TPS/TVQ"
    )
    website = models.URLField(
        blank=True,
        verbose_name="Site web"
    )
    
    # Statistiques
    total_receipts = models.IntegerField(default=0)
    total_cashback_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    # Activation
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Marchand"
        verbose_name_plural = "Marchands"
        db_table = 'receipts_merchant'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_partner', 'is_active']),
        ]
    
    def __str__(self):
        return self.display_name
    
    def calculate_cashback(self, amount):
        """Calcule le cashback pour un montant donné"""
        base_cashback = amount * (self.cashback_rate / 100)
        bonus = amount * (self.bonus_rate / 100) if self.is_partner else 0
        return base_cashback + bonus


class Category(models.Model):
    """
    Catégories de dépenses
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nom"
    )
    slug = models.SlugField(
        unique=True,
        max_length=100
    )
    icon = models.CharField(
        max_length=50,
        default='category',
        verbose_name="Icône"
    )
    color = models.CharField(
        max_length=7,
        default='#6B7280',
        verbose_name="Couleur"
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='subcategories'
    )
    
    # Pour analytics
    budget_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="% du budget recommandé"
    )
    
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        db_table = 'receipts_category'
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Receipt(models.Model):
    """
    Modèle principal des reçus
    """
    OCR_STATUSES = [
        ('pending', 'En attente'),
        ('processing', 'Traitement'),
        ('completed', 'Complété'),
        ('failed', 'Échoué'),
        ('manual_review', 'Révision manuelle'),
    ]
    
    OCR_PROVIDERS = [
        ('gemini', 'Google Gemini'),
        ('gpt', 'OpenAI GPT'),
        ('xai', 'xAI'),
        ('manual', 'Saisie manuelle'),
    ]
    
    # Identifiant unique
    receipt_uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=True,
        unique=True
    )
    
    # Utilisateur
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='receipts'
    )
    
    # Images
    original_image = models.ImageField(
        upload_to='receipts/originals/%Y/%m/%d/',
        verbose_name="Image originale"
    )
    processed_image = models.ImageField(
        upload_to='receipts/processed/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="Image traitée"
    )
    thumbnail = models.ImageField(
        upload_to='receipts/thumbnails/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="Miniature"
    )
    
    # Hash pour déduplication
    image_hash = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        help_text="SHA256 de l'image"
    )
    
    # Statut OCR
    ocr_status = models.CharField(
        max_length=20,
        choices=OCR_STATUSES,
        default='pending'
    )
    ocr_provider = models.CharField(
        max_length=20,
        choices=OCR_PROVIDERS,
        null=True,
        blank=True
    )
    ocr_confidence = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    
    # Données extraites
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='receipts'
    )
    merchant_name_raw = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nom marchand brut"
    )
    
    # Montants
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Sous-total"
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Taxes"
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Total"
    )
    currency = models.CharField(
        max_length=3,
        default='CAD',
        verbose_name="Devise"
    )
    
    # Date et heure
    purchase_date = models.DateField(
        verbose_name="Date d'achat"
    )
    purchase_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Heure d'achat"
    )
    
    # Catégorisation
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='receipts'
    )
    tags = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        default=list,
        verbose_name="Tags"
    )
    
    # Géolocalisation
    location = gis_models.PointField(
        null=True,
        blank=True,
        spatial_index=True,
        verbose_name="Localisation"
    )
    location_accuracy = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Précision GPS (m)"
    )
    address = models.TextField(
        blank=True,
        verbose_name="Adresse"
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ville"
    )
    province = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Province"
    )
    postal_code = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="Code postal"
    )
    
    # Cashback
    cashback_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Taux cashback appliqué %"
    )
    cashback_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name="Montant cashback"
    )
    bonus_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name="Bonus"
    )
    points_earned = models.IntegerField(
        default=0,
        verbose_name="Points gagnés"
    )
    
    # Données OCR brutes
    ocr_raw_response = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Réponse OCR brute"
    )
    extracted_text = models.TextField(
        blank=True,
        verbose_name="Texte extrait"
    )
    
    # Métadonnées
    notes = models.TextField(
        blank=True,
        verbose_name="Notes"
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Vérifié"
    )
    is_duplicate = models.BooleanField(
        default=False,
        verbose_name="Duplicata"
    )
    duplicate_of = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='duplicates'
    )
    
    # Device info
    uploaded_via = models.CharField(
        max_length=20,
        choices=[
            ('mobile', 'Mobile'),
            ('web', 'Web'),
            ('api', 'API'),
        ],
        default='mobile'
    )
    device_info = models.JSONField(
        default=dict,
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-purchase_date', '-created_at']
        verbose_name = "Reçu"
        verbose_name_plural = "Reçus"
        db_table = 'receipts_receipt'
        indexes = [
            models.Index(fields=['user', '-purchase_date']),
            models.Index(fields=['merchant', '-purchase_date']),
            models.Index(fields=['ocr_status']),
            models.Index(fields=['image_hash']),
        ]
    
    def __str__(self):
        return f"Reçu {self.merchant_name_raw or 'Sans nom'} - {self.total_amount} {self.currency}"
    
    def save(self, *args, **kwargs):
        # Calculer le hash de l'image si nouvelle
        if not self.image_hash and self.original_image:
            self.image_hash = self.calculate_image_hash()
            
        # Calculer le cashback si pas déjà fait
        if self.total_amount and not self.cashback_amount and self.merchant:
            self.cashback_amount = self.merchant.calculate_cashback(self.total_amount)
            self.cashback_rate = self.merchant.cashback_rate
            
        super().save(*args, **kwargs)
    
    def calculate_image_hash(self):
        """Calcule le hash SHA256 de l'image"""
        if self.original_image:
            sha256_hash = hashlib.sha256()
            for chunk in self.original_image.chunks():
                sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        return None
    
    def mark_as_processed(self):
        """Marque le reçu comme traité"""
        self.ocr_status = 'completed'
        self.processed_at = timezone.now()
        self.save(update_fields=['ocr_status', 'processed_at'])
        
        # Mettre à jour les stats utilisateur
        self.user.total_receipts_scanned += 1
        self.user.add_cashback(self.cashback_amount)
        self.user.save()


class ReceiptItem(models.Model):
    """
    Items individuels d'un reçu
    """
    receipt = models.ForeignKey(
        Receipt,
        on_delete=models.CASCADE,
        related_name='items'
    )
    
    # Description
    name = models.CharField(
        max_length=255,
        verbose_name="Nom"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )
    
    # Quantité et prix
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=1,
        verbose_name="Quantité"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Prix unitaire"
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Prix total"
    )
    
    # Catégorisation
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Codes produit
    sku = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="SKU"
    )
    barcode = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Code-barres"
    )
    
    # Flags
    is_taxable = models.BooleanField(
        default=True,
        verbose_name="Taxable"
    )
    is_refundable = models.BooleanField(
        default=True,
        verbose_name="Remboursable"
    )
    
    # Ordre d'affichage
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Article de reçu"
        verbose_name_plural = "Articles de reçu"
        db_table = 'receipts_receipt_item'
    
    def __str__(self):
        return f"{self.name} x{self.quantity}"


class ReceiptImage(models.Model):
    """
    Images supplémentaires d'un reçu (multi-pages)
    """
    receipt = models.ForeignKey(
        Receipt,
        on_delete=models.CASCADE,
        related_name='additional_images'
    )
    
    image = models.ImageField(
        upload_to='receipts/additional/%Y/%m/%d/'
    )
    
    page_number = models.IntegerField(
        default=1,
        verbose_name="Numéro de page"
    )
    
    extracted_text = models.TextField(
        blank=True,
        verbose_name="Texte extrait"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['page_number']
        unique_together = ['receipt', 'page_number']
        verbose_name = "Image additionnelle"
        verbose_name_plural = "Images additionnelles"
        db_table = 'receipts_receipt_image'


class MerchantAlias(models.Model):
    """
    Alias de marchands pour la reconnaissance
    """
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name='aliases'
    )
    
    alias = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Alias"
    )
    
    confidence = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name="Confiance"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-confidence']
        verbose_name = "Alias marchand"
        verbose_name_plural = "Alias marchands"
        db_table = 'receipts_merchant_alias'


class OCRProcessingLog(models.Model):
    """
    Log des traitements OCR
    """
    receipt = models.ForeignKey(
        Receipt,
        on_delete=models.CASCADE,
        related_name='ocr_logs'
    )
    
    provider = models.CharField(
        max_length=20,
        choices=Receipt.OCR_PROVIDERS
    )
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    processing_time = models.FloatField(
        null=True,
        blank=True,
        help_text="Temps en secondes"
    )
    
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    
    confidence_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    
    # Coûts API
    api_credits_used = models.IntegerField(default=0)
    api_cost = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        default=0
    )
    
    class Meta:
        ordering = ['-started_at']
        verbose_name = "Log OCR"
        verbose_name_plural = "Logs OCR"
        db_table = 'receipts_ocr_log'
        indexes = [
            models.Index(fields=['receipt', '-started_at']),
        ]