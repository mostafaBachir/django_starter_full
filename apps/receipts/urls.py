# apps/receipts/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ReceiptViewSet, MerchantViewSet, CategoryViewSet,
    ReceiptUploadView, OCRStatusView, ReceiptStatsView
)

app_name = 'receipts'

router = DefaultRouter()
router.register(r'receipts', ReceiptViewSet, basename='receipt')
router.register(r'merchants', MerchantViewSet, basename='merchant')
router.register(r'categories', CategoryViewSet, basename='category')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # Custom endpoints
    path('upload/', ReceiptUploadView.as_view(), name='receipt-upload'),
    path('ocr-status/<uuid:receipt_uuid>/', OCRStatusView.as_view(), name='ocr-status'),
    path('stats/', ReceiptStatsView.as_view(), name='receipt-stats'),
]