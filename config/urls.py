# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Django Starter API",
        default_version='v1',
        description="API documentation for Django Starter project",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="mostafa.bachir.agb@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/accounts/', include('apps.accounts.urls')),
    
    # API Documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]
# Ajouter les apps selon les features activées
if settings.INOVOCB_FEATURES.get('OCR_CORE'):
    urlpatterns.append(path('receipts/', include('apps.receipts.urls')))
if settings.INOVOCB_FEATURES.get('GEOLOCATION'):
    urlpatterns.append(path('locations/', include('apps.locations.urls')))

if settings.INOVOCB_FEATURES.get('REWARDS_SYSTEM'):
    urlpatterns.append(path('rewards/', include('apps.rewards.urls')))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)