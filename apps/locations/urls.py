# apps/locations/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ZoneViewSet, BonusZoneViewSet, MerchantLocationViewSet,
    PlaceOfInterestViewSet, NearbySearchView, ValidateLocationView,
    HeatmapDataView
)

app_name = 'locations'

router = DefaultRouter()
router.register(r'zones', ZoneViewSet, basename='zone')
router.register(r'bonus-zones', BonusZoneViewSet, basename='bonus-zone')
router.register(r'merchant-locations', MerchantLocationViewSet, basename='merchant-location')
router.register(r'places', PlaceOfInterestViewSet, basename='place')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # Custom endpoints
    path('nearby/', NearbySearchView.as_view(), name='nearby-search'),
    path('validate/', ValidateLocationView.as_view(), name='validate-location'),
    path('heatmap/', HeatmapDataView.as_view(), name='heatmap-data'),
]