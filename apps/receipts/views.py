# apps/receipts/views.py
from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Receipt, Merchant, Category
from .serializers import (
    ReceiptSerializer, MerchantSerializer, CategorySerializer
)


class ReceiptViewSet(viewsets.ModelViewSet):
    serializer_class = ReceiptSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Receipt.objects.filter(user=self.request.user)


class MerchantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Merchant.objects.filter(is_active=True)
    serializer_class = MerchantSerializer
    permission_classes = [IsAuthenticated]


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class ReceiptUploadView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # TODO: Implémenter l'upload de reçu
        return Response({"message": "Receipt upload endpoint"})


class OCRStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, receipt_uuid):
        # TODO: Implémenter le statut OCR
        return Response({"message": f"OCR status for {receipt_uuid}"})


class ReceiptStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # TODO: Implémenter les stats
        return Response({"message": "Receipt stats endpoint"})