from django.contrib import admin
from django.utils.html import format_html
from .models import Device, TelemetryData, DeviceEvent, DataProcessingStatus, SystemStats


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['imei', 'name', 'is_active', 'last_seen', 'created_at']
    list_filter = ['is_active', 'created_at', 'last_seen']
    search_fields = ['imei', 'name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_seen']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('imei', 'name', 'description', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_seen'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TelemetryData)
class TelemetryDataAdmin(admin.ModelAdmin):
    list_display = ['device_imei', 'device_timestamp', 'has_gps', 'ignition_status', 'movement_status', 'speed', 'battery_level']
    list_filter = ['ignition', 'movement', 'gnss_status', 'device_timestamp']
    search_fields = ['device__imei']
    readonly_fields = ['id', 'server_timestamp', 'processed_at', 'raw_packet']
    date_hierarchy = 'device_timestamp'
    
    def device_imei(self, obj):
        return obj.device.imei
    device_imei.short_description = 'IMEI'
    
    def has_gps(self, obj):
        if obj.latitude and obj.longitude:
            return format_html('<span style="color: green;">✓ GPS</span>')
        return format_html('<span style="color: red;">✗ No GPS</span>')
    has_gps.short_description = 'GPS Status'
    
    def ignition_status(self, obj):
        if obj.ignition is True:
            return format_html('<span style="color: green;">ON</span>')
        elif obj.ignition is False:
            return format_html('<span style="color: red;">OFF</span>')
        return '-'
    ignition_status.short_description = 'Ignition'
    
    def movement_status(self, obj):
        if obj.movement is True:
            return format_html('<span style="color: blue;">Moving</span>')
        elif obj.movement is False:
            return format_html('<span style="color: gray;">Stopped</span>')
        return '-'
    movement_status.short_description = 'Movement'
    
    fieldsets = (
        ('Device & Timestamps', {
            'fields': ('device', 'device_timestamp', 'server_timestamp', 'processed_at')
        }),
        ('GPS Data', {
            'fields': ('latitude', 'longitude', 'altitude', 'angle', 'speed', 'satellites')
        }),
        ('Core Parameters', {
            'fields': ('ignition', 'movement', 'gsm_signal', 'gnss_status')
        }),
        ('Power & Battery', {
            'fields': ('external_voltage', 'battery_voltage', 'battery_current', 'battery_level')
        }),
        ('Additional Data', {
            'fields': ('total_odometer', 'io_data', 'raw_packet'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DeviceEvent)
class DeviceEventAdmin(admin.ModelAdmin):
    list_display = ['device_imei', 'event_type', 'event_time', 'description_short']
    list_filter = ['event_type', 'event_time']
    search_fields = ['device__imei', 'description']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'event_time'
    
    def device_imei(self, obj):
        return obj.device.imei
    device_imei.short_description = 'IMEI'
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Description'


@admin.register(DataProcessingStatus)
class DataProcessingStatusAdmin(admin.ModelAdmin):
    list_display = ['device_imei', 'processed_status', 'processing_attempts', 'last_attempt', 'error_short']
    list_filter = ['processed', 'processing_attempts', 'created_at']
    search_fields = ['device_imei', 'error_message']
    readonly_fields = ['id', 'created_at', 'last_attempt']
    
    def processed_status(self, obj):
        if obj.processed:
            return format_html('<span style="color: green;">✓ Processed</span>')
        else:
            return format_html('<span style="color: red;">✗ Failed</span>')
    processed_status.short_description = 'Status'
    
    def error_short(self, obj):
        return obj.error_message[:100] + '...' if len(obj.error_message) > 100 else obj.error_message
    error_short.short_description = 'Error'


@admin.register(SystemStats)
class SystemStatsAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'total_devices', 'active_devices', 'total_records', 'records_last_24h']
    list_filter = ['timestamp']
    readonly_fields = ['id', 'timestamp']
    date_hierarchy = 'timestamp'
