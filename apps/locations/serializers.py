# apps/locations/serializers.py
from rest_framework import serializers
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
from .models import (
    Zone, BonusZone, UserLocation, MerchantLocation,
    HeatmapData, UserMovementPattern, PlaceOfInterest,
    LocationValidation
)


class ZoneSerializer(serializers.ModelSerializer):
    center_coordinates = serializers.SerializerMethodField()
    
    class Meta:
        model = Zone
        fields = [
            'id', 'name', 'slug', 'zone_type', 'center_coordinates',
            'population', 'area_sq_km', 'zoom_level'
        ]
    
    def get_center_coordinates(self, obj):
        if obj.center:
            return {
                'latitude': obj.center.y,
                'longitude': obj.center.x
            }
        return None


class BonusZoneSerializer(serializers.ModelSerializer):
    is_currently_active = serializers.BooleanField(read_only=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    
    class Meta:
        model = BonusZone
        fields = [
            'id', 'name', 'description', 'zone', 'zone_name',
            'bonus_type', 'bonus_value', 'max_bonus_per_receipt',
            'start_date', 'end_date', 'color', 'icon',
            'is_currently_active'
        ]


class UserLocationSerializer(serializers.ModelSerializer):
    coordinates = serializers.SerializerMethodField()
    
    class Meta:
        model = UserLocation
        fields = [
            'id', 'coordinates', 'accuracy', 'source',
            'address', 'city', 'zone', 'recorded_at'
        ]
    
    def get_coordinates(self, obj):
        if obj.location:
            return {
                'latitude': obj.location.y,
                'longitude': obj.location.x
            }
        return None


class MerchantLocationSerializer(serializers.ModelSerializer):
    merchant_name = serializers.CharField(source='merchant.display_name', read_only=True)
    coordinates = serializers.SerializerMethodField()
    distance_from_user = serializers.SerializerMethodField()
    
    class Meta:
        model = MerchantLocation
        fields = [
            'id', 'merchant', 'merchant_name', 'name', 'store_number',
            'coordinates', 'address', 'city', 'province', 'postal_code',
            'phone', 'opening_hours', 'has_parking', 'is_accessible',
            'distance_from_user'
        ]
    
    def get_coordinates(self, obj):
        if obj.location:
            return {
                'latitude': obj.location.y,
                'longitude': obj.location.x
            }
        return None
    
    def get_distance_from_user(self, obj):
        request = self.context.get('request')
        if request and 'user_location' in request.query_params:
            try:
                lat, lng = request.query_params['user_location'].split(',')
                user_point = Point(float(lng), float(lat), srid=4326)
                distance = obj.location.distance(user_point)
                return {
                    'meters': int(distance.m),
                    'kilometers': round(distance.km, 2)
                }
            except:
                pass
        return None


class NearbyMerchantSerializer(serializers.ModelSerializer):
    merchant_name = serializers.CharField(source='merchant.display_name', read_only=True)
    merchant_logo = serializers.ImageField(source='merchant.logo', read_only=True)
    cashback_rate = serializers.DecimalField(source='merchant.cashback_rate', decimal_places=2, max_digits=5, read_only=True)
    distance = serializers.SerializerMethodField()
    
    class Meta:
        model = MerchantLocation
        fields = [
            'id', 'merchant', 'merchant_name', 'merchant_logo',
            'name', 'address', 'cashback_rate', 'distance'
        ]
    
    def get_distance(self, obj):
        # Distance est ajoutée par l'annotation dans la vue
        if hasattr(obj, 'distance'):
            return {
                'meters': int(obj.distance.m),
                'display': f"{int(obj.distance.m)}m" if obj.distance.m < 1000 else f"{round(obj.distance.km, 1)}km"
            }
        return None


class HeatmapDataSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    
    class Meta:
        model = HeatmapData
        fields = [
            'zone', 'zone_name', 'aggregation_type', 'period_start',
            'period_end', 'receipts_count', 'unique_users',
            'total_amount', 'total_cashback', 'density_score',
            'top_categories'
        ]


class PlaceOfInterestSerializer(serializers.ModelSerializer):
    coordinates = serializers.SerializerMethodField()
    nearby_merchants_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PlaceOfInterest
        fields = [
            'id', 'name', 'slug', 'poi_type', 'coordinates',
            'description', 'amenities', 'popularity_score',
            'nearby_merchants_count'
        ]
    
    def get_coordinates(self, obj):
        if obj.location:
            return {
                'latitude': obj.location.y,
                'longitude': obj.location.x
            }
        return None
    
    def get_nearby_merchants_count(self, obj):
        return obj.merchants.count()


class LocationValidationSerializer(serializers.ModelSerializer):
    receipt_uuid = serializers.CharField(source='receipt.receipt_uuid', read_only=True)
    merchant_name = serializers.CharField(
        source='matched_merchant_location.merchant.display_name',
        read_only=True
    )
    
    class Meta:
        model = LocationValidation
        fields = [
            'receipt', 'receipt_uuid', 'is_valid', 'validation_score',
            'distance_meters', 'validation_method', 'merchant_name',
            'notes', 'validated_at'
        ]


class LocationSearchSerializer(serializers.Serializer):
    latitude = serializers.FloatField(required=True)
    longitude = serializers.FloatField(required=True)
    radius = serializers.IntegerField(default=1000, min_value=100, max_value=10000)
    
    def validate(self, data):
        # Valider les coordonnées
        lat = data['latitude']
        lng = data['longitude']
        
        if not (-90 <= lat <= 90):
            raise serializers.ValidationError("Latitude invalide")
        if not (-180 <= lng <= 180):
            raise serializers.ValidationError("Longitude invalide")
        
        return data