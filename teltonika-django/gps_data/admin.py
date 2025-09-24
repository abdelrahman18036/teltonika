from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Device, GPSRecord, DeviceStatus, APILog, DeviceCommand


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
        'ignition_status', 'movement_status', 'security_summary', 'created_at'
    ]
    list_filter = [
        'device', 'timestamp', 'ignition', 'movement', 
        'digital_input_1', 'digital_input_2', 'digital_input_3',
        'gnss_status', 'created_at'
    ]
    search_fields = ['device__imei', 'device__device_name']
    readonly_fields = [
        'created_at', 'formatted_coordinates', 'security_flags_summary', 'security_summary',
        'analog_voltage_1', 'analog_voltage_2', 'accelerometer_summary',
        'dallas_temp_1_formatted', 'binary_flags_summary', 'decoded_flags_display',
        'security_state_flags', 'security_state_flags_p4', 
        'control_state_flags_p4', 'indicator_state_flags_p4'
    ]
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
                'digital_input_1', 'digital_input_2', 'digital_input_3',
                'digital_output_1', 'digital_output_2', 'digital_output_3'
            )
        }),
        ('Analog Inputs', {
            'fields': ('analog_input_1', 'analog_voltage_1', 'analog_input_2', 'analog_voltage_2'),
            'description': 'Analog input values in mV and converted to volts'
        }),
        ('Accelerometer Data', {
            'fields': ('axis_x', 'axis_y', 'axis_z', 'accelerometer_summary'),
            'description': 'Accelerometer readings in milliG (mG)'
        }),
        ('Temperature Sensors', {
            'fields': ('dallas_temperature_1', 'dallas_temp_1_formatted', 'dallas_temperature_id_4'),
            'description': 'Dallas temperature sensor values and IDs'
        }),
        ('State Flags', {
            'fields': (
                'security_summary',
                'binary_flags_summary',
                'decoded_flags_display'
            ),
            'description': 'Security, control, and indicator state flags (binary data) with decoded meanings according to Teltonika specification'
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
        ('Vehicle CAN/OBD Data', {
            'fields': (
                'vehicle_speed_can', 'accelerator_pedal_position', 'engine_rpm_can',
                'total_mileage_can', 'fuel_level_can', 'total_mileage_counted'
            )
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

    def security_summary(self, obj):
        """Display security flags summary in admin list - matches service log format"""
        if obj.security_state_flags is None:
            return "IO132: Security State Flags = No data"
        try:
            flags = int.from_bytes(obj.security_state_flags, byteorder='little')
            if flags:
                # Show active bits for IO132 Security flags
                active_bits = []
                for i in range(128):  # Check all 128 bits (16 bytes)
                    if flags & (1 << i):
                        active_bits.append(f"bit{i}")
                
                if active_bits:
                    return f"IO132: Security State Flags = Security: {', '.join(active_bits)} (0x{flags:032X})"
                else:
                    return "IO132: Security State Flags = Security: No flags active"
            else:
                return "IO132: Security State Flags = Security: No flags active"
        except:
            return "IO132: Security State Flags = Error"
    security_summary.short_description = 'IO132 Security'
    
    def analog_voltage_1(self, obj):
        """Display analog input 1 voltage"""
        if obj.analog_input_1 is None:
            return "N/A"
        return f"{obj.analog_input_1/1000:.3f}V"
    analog_voltage_1.short_description = 'Analog 1'
    
    def analog_voltage_2(self, obj):
        """Display analog input 2 voltage"""
        if obj.analog_input_2 is None:
            return "N/A"
        return f"{obj.analog_input_2/1000:.3f}V"
    analog_voltage_2.short_description = 'Analog 2'
    
    def accelerometer_summary(self, obj):
        """Display accelerometer readings summary"""
        if all(x is None for x in [obj.axis_x, obj.axis_y, obj.axis_z]):
            return "N/A"
        
        x = obj.axis_x if obj.axis_x is not None else 0
        y = obj.axis_y if obj.axis_y is not None else 0
        z = obj.axis_z if obj.axis_z is not None else 0
        
        return f"X:{x} Y:{y} Z:{z} mG"
    accelerometer_summary.short_description = 'Accelerometer'
    
    def dallas_temp_1_formatted(self, obj):
        """Display Dallas Temperature 1 in Celsius"""
        if obj.dallas_temperature_1 is None:
            return "N/A"
        return f"{obj.dallas_temperature_1/10:.1f}°C"
    dallas_temp_1_formatted.short_description = 'Dallas Temp 1'
    
    def binary_flags_summary(self, obj):
        """Display P4 flags summary matching service log format"""
        summaries = []
        
        # Security State Flags P4 (IO517)
        if obj.security_state_flags_p4:
            try:
                flags = int.from_bytes(obj.security_state_flags_p4, byteorder='little')
                if flags:
                    active_bits = []
                    for i in range(128):  # Check all 128 bits (16 bytes)
                        if flags & (1 << i):
                            active_bits.append(f"bit{i}")
                    
                    if active_bits:
                        summaries.append(f"IO517: Security State Flags P4 = Security P4: {', '.join(active_bits)} (0x{flags:032X})")
                    else:
                        summaries.append("IO517: Security State Flags P4 = Security P4: No flags active")
                else:
                    summaries.append("IO517: Security State Flags P4 = Security P4: No flags active")
            except:
                summaries.append("IO517: Security State Flags P4 = Error")
        else:
            summaries.append("IO517: Security State Flags P4 = No data")
                
        # Control State Flags P4 (IO518)
        if obj.control_state_flags_p4:
            try:
                flags = int.from_bytes(obj.control_state_flags_p4, byteorder='little')
                if flags:
                    active_bits = []
                    for i in range(128):  # Check all 128 bits (16 bytes)
                        if flags & (1 << i):
                            active_bits.append(f"bit{i}")
                    
                    if active_bits:
                        summaries.append(f"IO518: Control State Flags P4 = Control P4: {', '.join(active_bits)} (0x{flags:032X})")
                    else:
                        summaries.append("IO518: Control State Flags P4 = Control P4: No flags active")
                else:
                    summaries.append("IO518: Control State Flags P4 = Control P4: No flags active")
            except:
                summaries.append("IO518: Control State Flags P4 = Error")
        else:
            summaries.append("IO518: Control State Flags P4 = No data")
                
        # Indicator State Flags P4 (IO519)
        if obj.indicator_state_flags_p4:
            try:
                flags = int.from_bytes(obj.indicator_state_flags_p4, byteorder='little')
                if flags:
                    active_bits = []
                    for i in range(128):  # Check all 128 bits (16 bytes)
                        if flags & (1 << i):
                            active_bits.append(f"bit{i}")
                    
                    if active_bits:
                        summaries.append(f"IO519: Indicator State Flags P4 = Indicator P4: {', '.join(active_bits)} (0x{flags:032X})")
                    else:
                        summaries.append("IO519: Indicator State Flags P4 = Indicator P4: No flags active")
                else:
                    summaries.append("IO519: Indicator State Flags P4 = Indicator P4: No flags active")
            except:
                summaries.append("IO519: Indicator State Flags P4 = Error")
        else:
            summaries.append("IO519: Indicator State Flags P4 = No data")
        
        if summaries:
            return format_html('<br>'.join(summaries))
        else:
            return "No P4 flags data"
    binary_flags_summary.short_description = 'P4 Flags'
    
    def decoded_flags_display(self, obj):
        """Display decoded flags according to Teltonika CAN adapter specification"""
        from .teltonika_decoder import (
            decode_security_state_flags_io132,
            decode_security_state_flags_p4,
            decode_control_state_flags_p4,
            decode_indicator_state_flags_p4,
            format_flags_summary
        )
        
        sections = []
        
        # IO132 Security State Flags
        if obj.security_state_flags:
            decoded = decode_security_state_flags_io132(obj.security_state_flags)
            if decoded:
                active_flags = []
                for flag_name, flag_info in decoded.items():
                    if flag_info.get('active', False):
                        active_flags.append(f"• {flag_info['description']} (bit {flag_info['bit_position']})")
                
                if active_flags:
                    sections.append(f"<strong>IO132 Security State Flags:</strong><br>{'<br>'.join(active_flags)}")
                else:
                    sections.append("<strong>IO132 Security State Flags:</strong><br>• No flags active")
        
        # IO517 Security State Flags P4
        if obj.security_state_flags_p4:
            decoded = decode_security_state_flags_p4(obj.security_state_flags_p4)
            if decoded:
                active_flags = []
                for flag_name, flag_info in decoded.items():
                    if flag_info.get('active', False):
                        bit_info = f" (bit {flag_info['bit_position']})" if 'bit_position' in flag_info else ""
                        active_flags.append(f"• {flag_info['description']}{bit_info}")
                
                if active_flags:
                    sections.append(f"<strong>IO517 Security State Flags P4:</strong><br>{'<br>'.join(active_flags)}")
                else:
                    sections.append("<strong>IO517 Security State Flags P4:</strong><br>• No flags active")
        
        # IO518 Control State Flags P4
        if obj.control_state_flags_p4:
            decoded = decode_control_state_flags_p4(obj.control_state_flags_p4)
            if decoded:
                active_flags = []
                for flag_name, flag_info in decoded.items():
                    if flag_info.get('active', False):
                        active_flags.append(f"• {flag_info['description']} (bit {flag_info['bit_position']})")
                
                if active_flags:
                    sections.append(f"<strong>IO518 Control State Flags P4:</strong><br>{'<br>'.join(active_flags)}")
                else:
                    sections.append("<strong>IO518 Control State Flags P4:</strong><br>• No flags active")
        
        # IO519 Indicator State Flags P4
        if obj.indicator_state_flags_p4:
            decoded = decode_indicator_state_flags_p4(obj.indicator_state_flags_p4)
            if decoded:
                active_flags = []
                for flag_name, flag_info in decoded.items():
                    if flag_info.get('active', False):
                        active_flags.append(f"• {flag_info['description']} (bit {flag_info['bit_position']})")
                
                if active_flags:
                    sections.append(f"<strong>IO519 Indicator State Flags P4:</strong><br>{'<br>'.join(active_flags)}")
                else:
                    sections.append("<strong>IO519 Indicator State Flags P4:</strong><br>• No flags active")
        
        if sections:
            return format_html('<br><br>'.join(sections))
        else:
            return "No flag data available"
    
    decoded_flags_display.short_description = 'Decoded Flags (Teltonika Spec)'


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


@admin.register(APILog)
class APILogAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp', 'endpoint', 'method', 'status_code', 
        'device_imei', 'request_size_kb', 'response_time_ms'
    ]
    list_filter = [
        'method', 'status_code', 'timestamp', 'endpoint'
    ]
    search_fields = ['endpoint', 'device_imei', 'error_message']
    readonly_fields = [
        'timestamp', 'endpoint', 'method', 'status_code',
        'device_imei', 'request_size', 'response_time', 'error_message'
    ]
    date_hierarchy = 'timestamp'
    
    def request_size_kb(self, obj):
        if obj.request_size:
            return f"{obj.request_size / 1024:.1f} KB"
        return "N/A"
    request_size_kb.short_description = 'Request Size'
    
    def response_time_ms(self, obj):
        if obj.response_time:
            return f"{obj.response_time * 1000:.0f} ms"
        return "N/A"
    response_time_ms.short_description = 'Response Time'
    
    def has_add_permission(self, request):
        return False  # Don't allow manual creation of API logs


@admin.register(DeviceCommand)
class DeviceCommandAdmin(admin.ModelAdmin):
    list_display = [
        'device', 'command_type', 'command_name', 'status', 
        'created_at', 'sent_at', 'completed_at', 'retry_count', 'duration_display'
    ]
    list_filter = [
        'command_type', 'command_name', 'status', 'created_at', 'sent_at'
    ]
    search_fields = ['device__imei', 'device__device_name', 'command_text', 'device_response']
    readonly_fields = [
        'created_at', 'sent_at', 'completed_at', 'duration', 'device_response', 'command_text'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Command Information', {
            'fields': ('device', 'command_type', 'command_name', 'command_text')
        }),
        ('Status & Timing', {
            'fields': ('status', 'created_at', 'sent_at', 'completed_at', 'duration')
        }),
        ('Response & Errors', {
            'fields': ('device_response', 'error_message')
        }),
        ('Retry Management', {
            'fields': ('retry_count', 'max_retries')
        })
    )
    
    def duration_display(self, obj):
        """Display command duration in a readable format"""
        duration = obj.duration
        if duration is not None:
            return f"{duration:.2f}s"
        return "N/A"
    duration_display.short_description = 'Duration'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('device')
    
    def save_model(self, request, obj, form, change):
        """Auto-populate command_text when saving"""
        if not obj.command_text:
            obj.command_text = DeviceCommand.get_command_text(obj.command_type, obj.command_name)
        super().save_model(request, obj, form, change)


# Customize admin site
admin.site.site_header = "Teltonika GPS Management"
admin.site.site_title = "Teltonika GPS Admin"
admin.site.index_title = "GPS Data Management"
