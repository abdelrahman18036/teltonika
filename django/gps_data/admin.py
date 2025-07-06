from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Device, GPSRecord, DeviceStatus, APILog


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['imei', 'device_name', 'is_active', 'created_at', 'record_count', 'status_indicator']
    list_filter = ['is_active', 'created_at']
    search_fields = ['imei', 'device_name']
    readonly_fields = ['created_at', 'updated_at']
    
    def record_count(self, obj):
        count = obj.gps_records.count()
        url = reverse('admin:gps_data_gpsrecord_changelist') + f'?device__id__exact={obj.id}'
        return format_html('<a href="{}">{} records</a>', url, count)
    record_count.short_description = 'GPS Records'
    
    def status_indicator(self, obj):
        try:
            status = obj.status
            if status.is_online:
                return format_html('<span style="color: green;">●</span> Online')
            else:
                return format_html('<span style="color: red;">●</span> Offline')
        except DeviceStatus.DoesNotExist:
            return format_html('<span style="color: gray;">●</span> Unknown')
    status_indicator.short_description = 'Status'


@admin.register(GPSRecord)
class GPSRecordAdmin(admin.ModelAdmin):
    list_display = [
        'device', 'timestamp', 'coordinates', 'speed', 'satellites', 
        'ignition_status', 'movement_status', 'created_at'
    ]
    list_filter = [
        'device', 'timestamp', 'ignition', 'movement', 
        'gnss_status', 'created_at'
    ]
    search_fields = ['device__imei', 'device__device_name']
    readonly_fields = ['created_at', 'formatted_coordinates']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('device', 'timestamp', 'priority', 'event_io_id', 'created_at')
        }),
        ('GPS Data', {
            'fields': (
                'formatted_coordinates', 'latitude', 'longitude', 
                'altitude', 'speed', 'angle', 'satellites'
            )
        }),
        ('GNSS Status', {
            'fields': ('gnss_status', 'gnss_pdop', 'gnss_hdop')
        }),
        ('Vehicle Status', {
            'fields': ('ignition', 'movement')
        }),
        ('GSM/Cellular', {
            'fields': ('gsm_signal', 'active_gsm_operator', 'iccid1', 'iccid2')
        }),
        ('Digital I/O', {
            'fields': (
                'digital_input_1', 'digital_output_1', 
                'digital_output_2', 'digital_output_3'
            )
        }),
        ('Power & Battery', {
            'fields': (
                'external_voltage', 'battery_voltage', 
                'battery_level', 'battery_current'
            )
        }),
        ('Vehicle Information', {
            'fields': ('total_odometer', 'program_number', 'door_status')
        }),
        ('Other Data', {
            'fields': ('other_io_data',),
            'classes': ('collapse',)
        })
    )
    
    def coordinates(self, obj):
        if obj.has_valid_coordinates:
            # Create Google Maps link with proper decimal conversion
            lat = float(obj.latitude)
            lon = float(obj.longitude)
            maps_url = f"https://www.google.com/maps?q={lat},{lon}"
            # Format coordinates outside of format_html to avoid SafeString issues
            lat_formatted = f"{lat:.6f}"
            lon_formatted = f"{lon:.6f}"
            return format_html(
                '<a href="{}" target="_blank">{}, {}</a>',
                maps_url, lat_formatted, lon_formatted
            )
        return "No coordinates"
    coordinates.short_description = 'Location'
    
    def ignition_status(self, obj):
        if obj.ignition is None:
            return "Unknown"
        return "ON" if obj.ignition else "OFF"
    ignition_status.short_description = 'Ignition'
    
    def movement_status(self, obj):
        if obj.movement is None:
            return "Unknown"
        return "Moving" if obj.movement else "Stopped"
    movement_status.short_description = 'Movement'


@admin.register(DeviceStatus)
class DeviceStatusAdmin(admin.ModelAdmin):
    list_display = [
        'device', 'is_online', 'last_seen', 'last_gps_record', 
        'total_records', 'connection_count', 'last_ip_address'
    ]
    list_filter = ['is_online', 'last_seen', 'last_connection_at']
    search_fields = ['device__imei', 'device__device_name', 'last_ip_address']
    readonly_fields = [
        'last_seen', 'last_gps_record', 'total_records', 
        'connection_count', 'last_connection_at', 'last_disconnection_at'
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('device')


# API logs removed as requested by user


# Customize admin site
admin.site.site_header = "Teltonika GPS Management"
admin.site.site_title = "Teltonika GPS Admin"
admin.site.index_title = "GPS Data Management"
