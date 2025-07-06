from django.contrib import admin
from django.utils.html import format_html
from .models import Device, GPSRecord, DeviceEvent, DeviceStatus, IOParameter


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['imei', 'device_name', 'vehicle_plate', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['imei', 'device_name', 'vehicle_plate']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Device Information', {
            'fields': ('imei', 'device_name', 'vehicle_plate', 'is_active')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(GPSRecord)
class GPSRecordAdmin(admin.ModelAdmin):
    list_display = ['device_imei', 'timestamp', 'latitude', 'longitude', 'speed', 'ignition', 'movement']
    list_filter = ['timestamp', 'ignition', 'movement', 'device']
    search_fields = ['device__imei', 'device__device_name']
    readonly_fields = ['id', 'received_at']
    date_hierarchy = 'timestamp'
    list_per_page = 50
    
    def device_imei(self, obj):
        return obj.device.imei
    device_imei.short_description = 'IMEI'
    device_imei.admin_order_field = 'device__imei'
    
    fieldsets = (
        ('Device & Time', {
            'fields': ('device', 'timestamp', 'received_at', 'priority', 'event_io_id')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'altitude', 'speed', 'satellites')
        }),
        ('GNSS Data', {
            'fields': ('gnss_status', 'gnss_pdop', 'gnss_hdop')
        }),
        ('Vehicle Status', {
            'fields': ('ignition', 'movement')
        }),
        ('Communication', {
            'fields': ('gsm_signal', 'active_gsm_operator')
        }),
        ('Digital I/O', {
            'fields': ('digital_input_1', 'digital_output_1', 'digital_output_2', 'digital_output_3')
        }),
        ('Power Management', {
            'fields': ('external_voltage', 'battery_voltage', 'battery_level', 'battery_current')
        }),
        ('Vehicle Data', {
            'fields': ('total_odometer', 'door_status', 'program_number')
        }),
        ('SIM Card Data', {
            'fields': ('iccid1', 'iccid2')
        }),
        ('Additional Parameters', {
            'fields': ('additional_parameters',),
            'classes': ('collapse',)
        }),
    )


@admin.register(DeviceEvent)
class DeviceEventAdmin(admin.ModelAdmin):
    list_display = ['device_imei', 'event_type', 'timestamp', 'acknowledged', 'acknowledged_by']
    list_filter = ['event_type', 'acknowledged', 'timestamp', 'device']
    search_fields = ['device__imei', 'event_type', 'description']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'timestamp'
    
    def device_imei(self, obj):
        return obj.device.imei
    device_imei.short_description = 'IMEI'
    device_imei.admin_order_field = 'device__imei'
    
    fieldsets = (
        ('Event Information', {
            'fields': ('device', 'event_type', 'timestamp', 'description')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude')
        }),
        ('Acknowledgment', {
            'fields': ('acknowledged', 'acknowledged_at', 'acknowledged_by')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DeviceStatus)
class DeviceStatusAdmin(admin.ModelAdmin):
    list_display = ['device_imei', 'last_seen', 'is_online', 'last_ignition', 'last_movement', 'last_battery_level']
    list_filter = ['is_online', 'last_ignition', 'last_movement', 'last_seen']
    search_fields = ['device__imei', 'device__device_name']
    readonly_fields = ['updated_at']
    
    def device_imei(self, obj):
        return obj.device.imei
    device_imei.short_description = 'IMEI'
    device_imei.admin_order_field = 'device__imei'
    
    def is_online(self, obj):
        if obj.is_online:
            return format_html('<span style="color: green;">●</span> Online')
        else:
            return format_html('<span style="color: red;">●</span> Offline')
    is_online.short_description = 'Status'
    
    fieldsets = (
        ('Device Status', {
            'fields': ('device', 'last_seen', 'is_online')
        }),
        ('Last Known Location', {
            'fields': ('last_latitude', 'last_longitude')
        }),
        ('Last Known Status', {
            'fields': ('last_speed', 'last_ignition', 'last_movement', 'last_battery_level', 'last_gsm_signal')
        }),
        ('Statistics', {
            'fields': ('total_distance',)
        }),
        ('Metadata', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(IOParameter)
class IOParameterAdmin(admin.ModelAdmin):
    list_display = ['io_id', 'name', 'data_type', 'unit', 'min_value', 'max_value']
    list_filter = ['data_type']
    search_fields = ['io_id', 'name', 'description']
    readonly_fields = ['created_at']
    ordering = ['io_id']
    
    fieldsets = (
        ('Parameter Information', {
            'fields': ('io_id', 'name', 'description')
        }),
        ('Data Configuration', {
            'fields': ('data_type', 'unit', 'min_value', 'max_value')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


# Customize admin site headers
admin.site.site_header = 'Teltonika GPS Tracker Admin'
admin.site.site_title = 'Teltonika GPS Admin'
admin.site.index_title = 'GPS Tracking Administration'
