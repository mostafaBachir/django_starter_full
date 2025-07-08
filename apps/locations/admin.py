# apps/locations/admin.py
from django.contrib import admin
from django.contrib.gis import admin as gis_admin
from django.contrib.gis.forms import widgets as gis_widgets
from django.utils.html import format_html
from .models import (
    Zone, BonusZone, UserLocation, MerchantLocation,
    HeatmapData, UserMovementPattern, PlaceOfInterest,
    LocationValidation
)


@admin.register(Zone)
class ZoneAdmin(gis_admin.GISModelAdmin):
    list_display = ['name', 'zone_type', 'parent', 'population', 'area_sq_km', 'is_active']
    list_filter = ['zone_type', 'is_active', 'parent']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['zone_type', 'name']
    
    # Configuration pour OpenStreetMap
    gis_widget = gis_widgets.OSMWidget
    gis_widget_kwargs = {
        'attrs': {
            'default_lon': -73.5673,  # Montréal
            'default_lat': 45.5017,
            'default_zoom': 12,
        }
    }


@admin.register(BonusZone)
class BonusZoneAdmin(gis_admin.GISModelAdmin):
    list_display = [
        'name', 'bonus_type', 'bonus_value', 'get_status',
        'times_used', 'budget_used', 'total_budget'
    ]
    list_filter = ['bonus_type', 'is_active', 'start_date']
    search_fields = ['name', 'description']
    filter_horizontal = ['merchants', 'categories']
    readonly_fields = ['times_used', 'total_bonus_paid', 'budget_used']
    
    # Configuration pour OpenStreetMap
    gis_widget = gis_widgets.OSMWidget
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('name', 'description', 'zone', 'geofence', 'radius_meters')
        }),
        ('Configuration bonus', {
            'fields': (
                'bonus_type', 'bonus_value', 'max_bonus_per_receipt',
                'daily_limit', 'total_budget', 'budget_used'
            )
        }),
        ('Restrictions', {
            'fields': ('merchants', 'categories', 'time_restrictions')
        }),
        ('Période', {
            'fields': ('start_date', 'end_date')
        }),
        ('Affichage', {
            'fields': ('color', 'icon', 'is_active', 'requires_notification')
        }),
        ('Statistiques', {
            'fields': ('times_used', 'total_bonus_paid'),
            'classes': ('collapse',)
        })
    )
    
    def get_status(self, obj):
        if obj.is_currently_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    get_status.short_description = 'Statut'


@admin.register(UserLocation)
class UserLocationAdmin(gis_admin.GISModelAdmin):
    list_display = ['user', 'source', 'accuracy', 'zone', 'city', 'recorded_at']
    list_filter = ['source', 'zone', 'recorded_at']
    search_fields = ['user__email', 'address', 'city']
    readonly_fields = ['recorded_at']
    date_hierarchy = 'recorded_at'
    
    # Configuration pour OpenStreetMap
    gis_widget = gis_widgets.OSMWidget
    gis_widget_kwargs = {
        'attrs': {
            'default_lon': -73.5673,
            'default_lat': 45.5017,
            'default_zoom': 12,
        }
    }


@admin.register(MerchantLocation)
class MerchantLocationAdmin(gis_admin.GISModelAdmin):
    list_display = [
        'merchant', 'name', 'store_number', 'city',
        'receipts_count', 'is_active'
    ]
    list_filter = ['merchant', 'city', 'province', 'is_active']
    search_fields = ['name', 'store_number', 'address', 'city']
    readonly_fields = ['receipts_count', 'average_basket']
    
    # Configuration pour OpenStreetMap
    gis_widget = gis_widgets.OSMWidget
    
    fieldsets = (
        ('Identification', {
            'fields': ('merchant', 'name', 'store_number')
        }),
        ('Localisation', {
            'fields': ('location', 'address', 'city', 'province', 'postal_code', 'country', 'zone')
        }),
        ('Contact', {
            'fields': ('phone', 'email')
        }),
        ('Caractéristiques', {
            'fields': (
                'opening_hours', 'has_parking', 'is_accessible',
                'accepts_cash', 'accepts_cards'
            )
        }),
        ('Validation', {
            'fields': ('validation_radius',)
        }),
        ('Statistiques', {
            'fields': ('receipts_count', 'average_basket'),
            'classes': ('collapse',)
        })
    )


@admin.register(HeatmapData)
class HeatmapDataAdmin(admin.ModelAdmin):
    list_display = [
        'zone', 'aggregation_type', 'period_start',
        'receipts_count', 'unique_users', 'total_amount',
        'density_score'
    ]
    list_filter = ['aggregation_type', 'zone', 'period_start']
    date_hierarchy = 'period_start'
    readonly_fields = ['created_at']


@admin.register(UserMovementPattern)
class UserMovementPatternAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'pattern_type', 'confidence',
        'times_confirmed', 'is_active'
    ]
    list_filter = ['pattern_type', 'is_active']
    search_fields = ['user__email']
    filter_horizontal = ['frequent_zones']


@admin.register(PlaceOfInterest)
class PlaceOfInterestAdmin(gis_admin.GISModelAdmin):
    list_display = ['name', 'poi_type', 'zone', 'popularity_score', 'is_active']
    list_filter = ['poi_type', 'zone', 'is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['merchants']
    
    # Configuration pour OpenStreetMap
    gis_widget = gis_widgets.OSMWidget


@admin.register(LocationValidation)
class LocationValidationAdmin(admin.ModelAdmin):
    list_display = [
        'receipt', 'is_valid', 'validation_score',
        'distance_meters', 'validation_method', 'validated_at'
    ]
    list_filter = ['is_valid', 'validation_method', 'validated_at']
    search_fields = ['receipt__receipt_uuid']
    readonly_fields = ['validated_at']
    date_hierarchy = 'validated_at'