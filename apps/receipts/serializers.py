# apps/receipts/serializers.py
from rest_framework import serializers
from django.contrib.gis.geos import Point
from .models import (
    Merchant, Category, Receipt, ReceiptItem,
    ReceiptImage, MerchantAlias, OCRProcessingLog
)


class MerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merchant
        fields = [
            'id', 'name', 'display_name', 'slug', 'merchant_type',
            'category', 'logo', 'brand_color', 'is_partner',
            'cashback_rate', 'bonus_rate', 'website'
        ]


class CategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'icon', 'color',
            'parent', 'parent_name', 'budget_percentage'
        ]


class ReceiptItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = ReceiptItem
        fields = [
            'id', 'name', 'description', 'quantity', 'unit_price',
            'total_price', 'category', 'category_name', 'sku',
            'barcode', 'is_taxable', 'order'
        ]


class ReceiptImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceiptImage
        fields = ['id', 'image', 'page_number', 'extracted_text']


class ReceiptSerializer(serializers.ModelSerializer):
    merchant_name = serializers.CharField(source='merchant.display_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    items = ReceiptItemSerializer(many=True, read_only=True)
    additional_images = ReceiptImageSerializer(many=True, read_only=True)
    total_cashback = serializers.SerializerMethodField()
    
    class Meta:
        model = Receipt
        fields = [
            'id', 'receipt_uuid', 'original_image', 'processed_image',
            'thumbnail', 'ocr_status', 'merchant', 'merchant_name',
            'merchant_name_raw', 'total_amount', 'subtotal', 'tax_amount',
            'currency', 'purchase_date', 'purchase_time', 'category',
            'category_name', 'tags', 'cashback_rate', 'cashback_amount',
            'bonus_amount', 'points_earned', 'total_cashback', 'items',
            'additional_images', 'notes', 'is_verified', 'created_at'
        ]
        read_only_fields = [
            'receipt_uuid', 'processed_image', 'thumbnail', 'ocr_status',
            'cashback_amount', 'bonus_amount', 'points_earned'
        ]
    
    def get_total_cashback(self, obj):
        return obj.cashback_amount + obj.bonus_amount


class ReceiptCreateSerializer(serializers.ModelSerializer):
    location_latitude = serializers.FloatField(required=False, allow_null=True)
    location_longitude = serializers.FloatField(required=False, allow_null=True)
    location_accuracy = serializers.FloatField(required=False, allow_null=True)
    
    class Meta:
        model = Receipt
        fields = [
            'original_image', 'location_latitude', 'location_longitude',
            'location_accuracy', 'notes', 'uploaded_via'
        ]
    
    def create(self, validated_data):
        # Extraire les données de localisation
        lat = validated_data.pop('location_latitude', None)
        lng = validated_data.pop('location_longitude', None)
        accuracy = validated_data.pop('location_accuracy', None)
        
        # Créer le point géographique
        if lat and lng:
            validated_data['location'] = Point(lng, lat, srid=4326)
            validated_data['location_accuracy'] = accuracy
        
        # Ajouter l'utilisateur
        validated_data['user'] = self.context['request'].user
        
        # Créer le reçu
        receipt = Receipt.objects.create(**validated_data)
        
        # Déclencher le traitement OCR (via Celery)
        from apps.receipts.tasks import process_receipt_ocr
        process_receipt_ocr.delay(receipt.id)
        
        return receipt


class ReceiptListSerializer(serializers.ModelSerializer):
    merchant_name = serializers.CharField(source='merchant.display_name', read_only=True)
    total_cashback = serializers.SerializerMethodField()
    
    class Meta:
        model = Receipt
        fields = [
            'id', 'receipt_uuid', 'thumbnail', 'merchant_name',
            'merchant_name_raw', 'total_amount', 'currency',
            'purchase_date', 'total_cashback', 'ocr_status',
            'created_at'
        ]
    
    def get_total_cashback(self, obj):
        return obj.cashback_amount + obj.bonus_amount


class OCRStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = ['id', 'receipt_uuid', 'ocr_status', 'ocr_confidence']


class MerchantAliasSerializer(serializers.ModelSerializer):
    class Meta:
        model = MerchantAlias
        fields = ['id', 'merchant', 'alias', 'confidence']