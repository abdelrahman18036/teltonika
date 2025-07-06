from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'devices', views.DeviceViewSet)
router.register(r'gps-records', views.GPSRecordViewSet)
router.register(r'events', views.DeviceEventViewSet)
router.register(r'io-parameters', views.IOParameterViewSet)

# Define URL patterns
urlpatterns = [
    # Router URLs
    path('api/', include(router.urls)),
    
    # Custom API endpoints
    path('api/gps/create/', views.create_gps_record, name='create-gps-record'),
    path('api/gps/bulk-create/', views.bulk_create_gps_records, name='bulk-create-gps-records'),
    path('api/statistics/', views.device_statistics, name='device-statistics'),
    path('api/devices/<str:imei>/location-history/', views.device_location_history, name='device-location-history'),
    path('api/devices/live-status/', views.device_live_status, name='device-live-status'),
] 