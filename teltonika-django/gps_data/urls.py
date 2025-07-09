from django.urls import path
from . import views

app_name = 'gps_data'

urlpatterns = [
    # Main GPS data ingestion endpoint
    path('gps/', views.TeltonikaGPSDataView.as_view(), name='teltonika_gps_data'),
    path('store/', views.store_gps_record, name='store_gps_record'),
    
    # Device management
    path('devices/', views.DeviceListView.as_view(), name='device_list'),
    path('devices/<str:imei>/', views.DeviceDetailView.as_view(), name='device_detail'),
    path('devices/<str:imei>/records/', views.DeviceGPSRecordsView.as_view(), name='device_gps_records'),
    path('devices/<str:imei>/status/', views.update_device_status, name='update_device_status'),
    
    # Command management
    path('devices/<str:imei>/commands/', views.DeviceCommandView.as_view(), name='device_commands'),
    path('commands/<int:command_id>/', views.command_status, name='command_status'),
    path('commands/update/', views.update_command_status, name='update_command_status'),
    
    # GPS data access
    path('records/latest/', views.LatestGPSRecordsView.as_view(), name='latest_gps_records'),
    
    # Device status
    path('status/', views.DeviceStatusView.as_view(), name='device_status'),
    
    # Statistics and monitoring
    path('stats/', views.api_stats, name='api_stats'),
    path('health/', views.health_check, name='health_check'),
] 