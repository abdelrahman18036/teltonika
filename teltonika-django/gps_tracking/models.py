from django.db import models
import uuid


class Device(models.Model):
    """Model for tracking individual Teltonika devices"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    imei = models.CharField(max_length=20, unique=True, db_index=True)
    device_name = models.CharField(max_length=100, blank=True, null=True)
    vehicle_plate = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'devices'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Device {self.imei} - {self.device_name or 'Unnamed'}"


class GPSRecord(models.Model):
    """Main model for storing GPS tracking data from Teltonika devices"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='gps_records')
    
    # Timestamp
    timestamp = models.DateTimeField(db_index=True)
    received_at = models.DateTimeField(auto_now_add=True)
    
    # Core GPS Data
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    altitude = models.IntegerField(null=True, blank=True)  # meters
    speed = models.IntegerField(null=True, blank=True)  # km/h
    satellites = models.IntegerField(null=True, blank=True)
    
    # GNSS Data
    gnss_status = models.CharField(max_length=20, null=True, blank=True)  # Off/No Fix/2D Fix/3D Fix
    gnss_pdop = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # IO181
    gnss_hdop = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # IO182
    
    # Vehicle Status
    ignition = models.BooleanField(null=True, blank=True)  # IO239
    movement = models.BooleanField(null=True, blank=True)  # IO240
    
    # Communication
    gsm_signal = models.IntegerField(null=True, blank=True)  # IO021 (0-5)
    active_gsm_operator = models.BigIntegerField(null=True, blank=True)  # IO241
    
    # Digital I/O
    digital_input_1 = models.BooleanField(null=True, blank=True)  # IO001
    digital_output_1 = models.BooleanField(null=True, blank=True)  # IO179
    digital_output_2 = models.BooleanField(null=True, blank=True)  # IO180
    digital_output_3 = models.BooleanField(null=True, blank=True)  # IO380
    
    # Power Management
    external_voltage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # IO066 (V)
    battery_voltage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # IO067 (V)
    battery_level = models.IntegerField(null=True, blank=True)  # IO113 (%)
    battery_current = models.IntegerField(null=True, blank=True)  # IO068 (mA)
    
    # Vehicle Data
    total_odometer = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)  # IO016 (km)
    
    # SIM Card Data
    iccid1 = models.CharField(max_length=20, null=True, blank=True)  # IO011
    iccid2 = models.CharField(max_length=20, null=True, blank=True)  # IO014
    
    # Device Configuration
    program_number = models.IntegerField(null=True, blank=True)  # IO100
    
    # CAN Bus Data
    door_status = models.CharField(max_length=200, null=True, blank=True)  # IO090
    
    # Additional Parameters (for extensibility)
    additional_parameters = models.JSONField(default=dict, blank=True)  # Store any other IO parameters
    
    # Metadata
    priority = models.IntegerField(null=True, blank=True)
    event_io_id = models.IntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'gps_records'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', '-timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['received_at']),
            models.Index(fields=['latitude', 'longitude']),
        ]
    
    def __str__(self):
        return f"GPS Record {self.device.imei} at {self.timestamp}"


class IOParameter(models.Model):
    """Model for storing IO parameter definitions and descriptions"""
    io_id = models.IntegerField(unique=True, primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=20, blank=True)
    data_type = models.CharField(max_length=20, choices=[
        ('boolean', 'Boolean'),
        ('integer', 'Integer'),
        ('decimal', 'Decimal'),
        ('string', 'String'),
        ('hex', 'Hexadecimal'),
    ])
    min_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'io_parameters'
        ordering = ['io_id']
    
    def __str__(self):
        return f"IO{self.io_id}: {self.name}"


class DeviceEvent(models.Model):
    """Model for storing device events and alerts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='events')
    timestamp = models.DateTimeField()
    event_type = models.CharField(max_length=50, choices=[
        ('ignition_on', 'Ignition On'),
        ('ignition_off', 'Ignition Off'),
        ('movement_start', 'Movement Started'),
        ('movement_stop', 'Movement Stopped'),
        ('geofence_enter', 'Geofence Enter'),
        ('geofence_exit', 'Geofence Exit'),
        ('overspeed', 'Overspeed'),
        ('low_battery', 'Low Battery'),
        ('power_disconnected', 'Power Disconnected'),
        ('crash_detection', 'Crash Detection'),
        ('jamming', 'Signal Jamming'),
        ('panic_button', 'Panic Button'),
        ('custom', 'Custom Event'),
    ])
    description = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'device_events'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', '-timestamp']),
            models.Index(fields=['event_type']),
            models.Index(fields=['acknowledged']),
        ]
    
    def __str__(self):
        return f"Event {self.event_type} for {self.device.imei} at {self.timestamp}"


class DeviceStatus(models.Model):
    """Model for tracking latest device status for quick access"""
    device = models.OneToOneField(Device, on_delete=models.CASCADE, primary_key=True, related_name='status')
    last_seen = models.DateTimeField()
    is_online = models.BooleanField(default=False)
    last_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    last_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    last_speed = models.IntegerField(null=True, blank=True)
    last_ignition = models.BooleanField(null=True, blank=True)
    last_movement = models.BooleanField(null=True, blank=True)
    last_battery_level = models.IntegerField(null=True, blank=True)
    last_gsm_signal = models.IntegerField(null=True, blank=True)
    total_distance = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # km
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'device_status'
    
    def __str__(self):
        return f"Status for {self.device.imei} - {'Online' if self.is_online else 'Offline'}"
