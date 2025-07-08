from django.contrib import admin

# Register your models here.
# apps/receipts/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum
from .models import (
    Merchant, Category, Receipt, ReceiptItem,
    ReceiptImage, MerchantAlias, OCRProcessingLog
)


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = [
        'display_name', 'merchant_type', 'is_partner',
        'cashback_rate', 'total_receipts', 'total_cashback_paid'
    ]
    list_filter = ['merchant_type', 'is_partner', 'is_active']
    search_fields = ['name', 'display_name', 'tax_number']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['total_receipts', 'total_cashback_paid']
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('name', 'display_name', 'slug', 'merchant_type', 'category')
        }),
        ('Branding', {
            'fields': ('logo', 'brand_color')
        }),
        ('Partenariat', {
            'fields': ('is_partner', 'cashback_rate', 'bonus_rate')
        }),
        ('Localisation', {
            'fields': ('locations',)
        }),
        ('Statistiques', {
            'fields': ('total_receipts', 'total_cashback_paid'),
            'classes': ('collapse',)
        })
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'icon', 'color', 'budget_percentage', 'is_active']
    list_filter = ['parent', 'is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['parent__name', 'order', 'name']


class ReceiptItemInline(admin.TabularInline):
    model = ReceiptItem
    extra = 0
    fields = ['name', 'quantity', 'unit_price', 'total_price', 'category']


class ReceiptImageInline(admin.TabularInline):
    model = ReceiptImage
    extra = 0
    fields = ['image', 'page_number']


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = [
        'receipt_uuid', 'user', 'merchant_name_raw', 'total_amount',
        'cashback_amount', 'ocr_status', 'purchase_date', 'created_at'
    ]
    list_filter = [
        'ocr_status', 'ocr_provider', 'is_verified',
        'is_duplicate', 'purchase_date', 'created_at'
    ]
    search_fields = [
        'receipt_uuid', 'user__email', 'merchant_name_raw',
        'merchant__name', 'extracted_text'
    ]
    readonly_fields = [
        'receipt_uuid', 'image_hash', 'ocr_confidence',
        'created_at', 'processed_at'
    ]
    date_hierarchy = 'purchase_date'
    inlines = [ReceiptItemInline, ReceiptImageInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'merchant', 'category'
        ).prefetch_related('items')
    
    fieldsets = (
        ('Identification', {
            'fields': ('receipt_uuid', 'user', 'image_hash')
        }),
        ('Images', {
            'fields': ('original_image', 'processed_image', 'thumbnail')
        }),
        ('OCR', {
            'fields': (
                'ocr_status', 'ocr_provider', 'ocr_confidence',
                'extracted_text', 'ocr_raw_response'
            ),
            'classes': ('collapse',)
        }),
        ('Données extraites', {
            'fields': (
                'merchant', 'merchant_name_raw', 'total_amount',
                'subtotal', 'tax_amount', 'currency',
                'purchase_date', 'purchase_time'
            )
        }),
        ('Cashback', {
            'fields': (
                'cashback_rate', 'cashback_amount', 'bonus_amount', 'points_earned'
            )
        }),
        ('Métadonnées', {
            'fields': (
                'category', 'tags', 'notes', 'is_verified',
                'is_duplicate', 'duplicate_of'
            )
        })
    )


@admin.register(ReceiptItem)
class ReceiptItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'receipt', 'quantity', 'unit_price', 'total_price', 'category']
    list_filter = ['category', 'is_taxable']
    search_fields = ['name', 'description', 'sku', 'barcode']


@admin.register(MerchantAlias)
class MerchantAliasAdmin(admin.ModelAdmin):
    list_display = ['alias', 'merchant', 'confidence', 'created_at']
    list_filter = ['confidence', 'created_at']
    search_fields = ['alias', 'merchant__name']


@admin.register(OCRProcessingLog)
class OCRProcessingLogAdmin(admin.ModelAdmin):
    list_display = [
        'receipt', 'provider', 'success', 'processing_time',
        'confidence_score', 'api_cost', 'started_at'
    ]
    list_filter = ['provider', 'success', 'started_at']
    readonly_fields = ['started_at', 'completed_at']
    date_hierarchy = 'started_at'