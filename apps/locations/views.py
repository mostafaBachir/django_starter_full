# apps/locations/views.py
from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Zone, BonusZone, MerchantLocation, PlaceOfInterest
from .serializers import (
    ZoneSerializer, BonusZoneSerializer, 
    MerchantLocationSerializer, PlaceOfInterestSerializer
)


class ZoneViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Zone.objects.filter(is_active=True)
    serializer_class = ZoneSerializer
    permission_classes = [IsAuthenticated]


class BonusZoneViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BonusZoneSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return BonusZone.objects.filter(is_active=True)


class MerchantLocationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MerchantLocation.objects.filter(is_active=True)
    serializer_class = MerchantLocationSerializer
    permission_classes = [IsAuthenticated]


class PlaceOfInterestViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PlaceOfInterest.objects.filter(is_active=True)
    serializer_class = PlaceOfInterestSerializer
    permission_classes = [IsAuthenticated]


class NearbySearchView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # TODO: Implémenter la recherche par proximité
        return Response({"message": "Nearby search endpoint"})


class ValidateLocationView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # TODO: Implémenter la validation de localisation
        return Response({"message": "Location validation endpoint"})


class HeatmapDataView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # TODO: Implémenter les données de heatmap
        return Response({"message": "Heatmap data endpoint"})