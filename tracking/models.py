from django.db import models
from django.utils import timezone
import uuid


class Device(models.Model):
    """Model to store device information"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    imei = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'devices'
        indexes = [
            models.Index(fields=['imei']),
            models.Index(fields=['is_active']),
            models.Index(fields=['last_seen']),
        ]
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.imei} - {self.name or 'Unnamed Device'}"


class TelemetryData(models.Model):
    """Model to store telemetry data from Teltonika devices"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='telemetry_data')
    
    # Timestamp from device
    device_timestamp = models.DateTimeField(db_index=True)
    # Server receive timestamp
    server_timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    # GPS Data
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    altitude = models.IntegerField(null=True, blank=True)  # meters
    angle = models.IntegerField(null=True, blank=True)     # degrees
    speed = models.IntegerField(null=True, blank=True)     # km/h
    satellites = models.IntegerField(null=True, blank=True)
    
    # Core IO Parameters (frequently used ones as separate fields for performance)
    ignition = models.BooleanField(null=True, blank=True)           # IO239
    movement = models.BooleanField(null=True, blank=True)           # IO240
    gsm_signal = models.IntegerField(null=True, blank=True)         # IO21
    gnss_status = models.IntegerField(null=True, blank=True)        # IO69
    external_voltage = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)  # IO66 in V
    battery_voltage = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)   # IO67 in V
    battery_current = models.IntegerField(null=True, blank=True)    # IO68 in mA
    battery_level = models.IntegerField(null=True, blank=True)      # IO113 in %
    total_odometer = models.BigIntegerField(null=True, blank=True)  # IO16 in meters
    
    # All IO parameters as JSON for complete data storage
    io_data = models.JSONField(default=dict, blank=True)
    
    # Raw packet data (optional, for debugging)
    raw_packet = models.TextField(blank=True)
    
    # Processing status
    processed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'telemetry_data'
        indexes = [
            models.Index(fields=['device', '-device_timestamp']),
            models.Index(fields=['device', '-server_timestamp']),
            models.Index(fields=['-device_timestamp']),
            models.Index(fields=['-server_timestamp']),
            models.Index(fields=['ignition']),
            models.Index(fields=['movement']),
            models.Index(fields=['latitude', 'longitude']),
            # Composite indexes for common queries
            models.Index(fields=['device', 'ignition', '-device_timestamp']),
            models.Index(fields=['device', 'movement', '-device_timestamp']),
        ]
        ordering = ['-device_timestamp']
    
    def __str__(self):
        return f"{self.device.imei} - {self.device_timestamp}"
    
    @property
    def has_valid_gps(self):
        """Check if the record has valid GPS coordinates"""
        return self.latitude is not None and self.longitude is not None
    
    @property
    def is_moving(self):
        """Check if the device is currently moving"""
        return self.movement or (self.speed and self.speed > 0)


class DeviceEvent(models.Model):
    """Model to store significant device events for quick access"""
    EVENT_TYPES = [
        ('ignition_on', 'Ignition On'),
        ('ignition_off', 'Ignition Off'),
        ('movement_start', 'Movement Started'),
        ('movement_stop', 'Movement Stopped'),
        ('overspeed', 'Over Speed'),
        ('geofence_enter', 'Geofence Enter'),
        ('geofence_exit', 'Geofence Exit'),
        ('low_battery', 'Low Battery'),
        ('connection_lost', 'Connection Lost'),
        ('connection_restored', 'Connection Restored'),
        ('alarm', 'Alarm Triggered'),
        ('crash', 'Crash Detected'),
        ('jamming', 'Signal Jamming'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='events')
    telemetry = models.ForeignKey(TelemetryData, on_delete=models.CASCADE, null=True, blank=True)
    
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, db_index=True)
    event_time = models.DateTimeField(db_index=True)
    description = models.TextField(blank=True)
    additional_data = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'device_events'
        indexes = [
            models.Index(fields=['device', '-event_time']),
            models.Index(fields=['event_type', '-event_time']),
            models.Index(fields=['device', 'event_type', '-event_time']),
        ]
        ordering = ['-event_time']
    
    def __str__(self):
        return f"{self.device.imei} - {self.get_event_type_display()} - {self.event_time}"


class DataProcessingStatus(models.Model):
    """Model to track data processing status for fault tolerance"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_imei = models.CharField(max_length=20, db_index=True)
    packet_data = models.TextField()  # Raw packet hex data
    processing_attempts = models.IntegerField(default=0)
    last_attempt = models.DateTimeField(auto_now=True)
    error_message = models.TextField(blank=True)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'data_processing_status'
        indexes = [
            models.Index(fields=['processed', 'processing_attempts']),
            models.Index(fields=['device_imei', '-created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        status = "Processed" if self.processed else f"Failed ({self.processing_attempts} attempts)"
        return f"{self.device_imei} - {status}"


class SystemStats(models.Model):
    """Model to store system statistics"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Device statistics
    total_devices = models.IntegerField(default=0)
    active_devices = models.IntegerField(default=0)
    devices_last_24h = models.IntegerField(default=0)
    
    # Data statistics
    total_records = models.BigIntegerField(default=0)
    records_last_24h = models.BigIntegerField(default=0)
    records_last_hour = models.BigIntegerField(default=0)
    
    # Processing statistics
    successful_packets = models.BigIntegerField(default=0)
    failed_packets = models.BigIntegerField(default=0)
    processing_errors = models.BigIntegerField(default=0)
    
    class Meta:
        db_table = 'system_stats'
        indexes = [
            models.Index(fields=['-timestamp']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Stats - {self.timestamp}"
