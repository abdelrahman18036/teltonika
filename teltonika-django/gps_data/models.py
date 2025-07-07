from django.db import models
from django.db.models import JSONField
from django.utils import timezone


class Device(models.Model):
    """Device information model"""
    imei = models.CharField(max_length=15, unique=True, db_index=True)
    device_name = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'devices'
        indexes = [
            models.Index(fields=['imei']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"Device {self.imei}"


class GPSRecord(models.Model):
    """Main GPS data record with all Teltonika parameters"""
    
    # Basic identifiers
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='gps_records')
    timestamp = models.DateTimeField(db_index=True)
    priority = models.IntegerField(default=0)
    
    # GPS Coordinates and Navigation
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    altitude = models.IntegerField(null=True, blank=True, help_text="Altitude in meters")
    speed = models.IntegerField(null=True, blank=True, help_text="Speed in km/h")
    angle = models.IntegerField(null=True, blank=True, help_text="Direction angle")
    satellites = models.IntegerField(null=True, blank=True, help_text="Number of satellites")
    
    # GNSS Status and Quality
    gnss_status = models.IntegerField(null=True, blank=True, help_text="IO069: 0=Off, 1=No Fix, 2=2D Fix, 3=3D Fix")
    gnss_pdop = models.IntegerField(null=True, blank=True, help_text="IO181: Position Dilution of Precision")
    gnss_hdop = models.IntegerField(null=True, blank=True, help_text="IO182: Horizontal Dilution of Precision")
    
    # Vehicle Status
    ignition = models.BooleanField(null=True, blank=True, help_text="IO239: Ignition status")
    movement = models.BooleanField(null=True, blank=True, help_text="IO240: Movement detection")
    
    # GSM/Cellular Information
    gsm_signal = models.IntegerField(null=True, blank=True, help_text="IO021: GSM signal strength (0-5)")
    active_gsm_operator = models.BigIntegerField(null=True, blank=True, help_text="IO241: Active GSM operator")
    iccid1 = models.CharField(max_length=32, null=True, blank=True, help_text="IO011: SIM card ICCID1")
    iccid2 = models.CharField(max_length=32, null=True, blank=True, help_text="IO014: SIM card ICCID2")
    
    # Digital I/O
    digital_input_1 = models.BooleanField(null=True, blank=True, help_text="IO001: Digital Input 1")
    digital_output_1 = models.BooleanField(null=True, blank=True, help_text="IO179: Digital Output 1")
    digital_output_2 = models.BooleanField(null=True, blank=True, help_text="IO180: Digital Output 2")
    digital_output_3 = models.BooleanField(null=True, blank=True, help_text="IO380: Digital Output 3")
    
    # Power and Battery
    external_voltage = models.IntegerField(null=True, blank=True, help_text="IO066: External voltage in mV")
    battery_voltage = models.IntegerField(null=True, blank=True, help_text="IO067: Battery voltage in mV")
    battery_level = models.IntegerField(null=True, blank=True, help_text="IO113: Battery level percentage")
    battery_current = models.IntegerField(null=True, blank=True, help_text="IO068: Battery current in mA")
    
    # Vehicle Information
    total_odometer = models.BigIntegerField(null=True, blank=True, help_text="IO016: Total odometer in meters")
    program_number = models.IntegerField(null=True, blank=True, help_text="IO100: Program number")
    door_status = models.IntegerField(null=True, blank=True, help_text="IO090: Door status CAN (bitfield)")
    
    # Additional IO parameters (for any other parameters not specifically listed)
    other_io_data = JSONField(default=dict, blank=True, null=True, help_text="All other IO parameters")
    
    # Event information
    event_io_id = models.IntegerField(null=True, blank=True, help_text="Event IO ID")
    
    # Vehicle CAN / OBD Extra Data
    vehicle_speed_can = models.IntegerField(null=True, blank=True, help_text="IO081: Vehicle speed (CAN) km/h")
    accelerator_pedal_position = models.IntegerField(null=True, blank=True, help_text="IO082: Accelerator pedal position %")
    engine_rpm_can = models.IntegerField(null=True, blank=True, help_text="IO085: Engine RPM (CAN)")
    total_mileage_can = models.BigIntegerField(null=True, blank=True, help_text="IO087: Total mileage (CAN) in meters")
    fuel_level_can = models.IntegerField(null=True, blank=True, help_text="IO089: Fuel level (CAN) % or L")
    total_mileage_counted = models.BigIntegerField(null=True, blank=True, help_text="IO105: Total mileage counted in meters")
    security_state_flags = models.BigIntegerField(null=True, blank=True, help_text="IO132: Security state flags bit-field")
    
    # Record metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'gps_records'
        indexes = [
            models.Index(fields=['device', 'timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['created_at']),
            models.Index(fields=['ignition']),
            models.Index(fields=['movement']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"GPS Record for {self.device} at {self.timestamp}"
    
    @property
    def has_valid_coordinates(self):
        """Check if record has valid GPS coordinates"""
        return (self.latitude is not None and 
                self.longitude is not None and
                self.latitude != 0 and 
                self.longitude != 0)
    
    @property
    def formatted_coordinates(self):
        """Return formatted coordinates string"""
        if self.has_valid_coordinates:
            return f"{self.latitude}, {self.longitude}"
        return "No GPS coordinates"
    
    @property
    def door_status_decoded(self):
        """Decode door status bitfield"""
        if self.door_status is None:
            return {}
        
        door_value = int(self.door_status)
        return {
            'driver_door': bool(door_value & 0x01),
            'passenger_door': bool(door_value & 0x02),
            'rear_left_door': bool(door_value & 0x04),
            'rear_right_door': bool(door_value & 0x08),
            'trunk': bool(door_value & 0x10),
            'hood': bool(door_value & 0x20),
        }


class DeviceStatus(models.Model):
    """Track device connection status and statistics"""
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='status')
    last_seen = models.DateTimeField(null=True, blank=True)
    last_gps_record = models.DateTimeField(null=True, blank=True)
    total_records = models.BigIntegerField(default=0)
    is_online = models.BooleanField(default=False)
    last_ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Connection statistics
    connection_count = models.IntegerField(default=0)
    last_connection_at = models.DateTimeField(null=True, blank=True)
    last_disconnection_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'device_status'
    
    def __str__(self):
        return f"Status for {self.device.imei}"
    
    def update_status(self, is_connected=True, ip_address=None):
        """Update device connection status"""
        now = timezone.now()
        
        if is_connected:
            self.is_online = True
            self.last_seen = now
            self.last_connection_at = now
            self.connection_count += 1
            if ip_address:
                self.last_ip_address = ip_address
        else:
            self.is_online = False
            self.last_disconnection_at = now
        
        self.save()


class APILog(models.Model):
    """Log API requests for monitoring and debugging"""
    timestamp = models.DateTimeField(auto_now_add=True)
    endpoint = models.CharField(max_length=200)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField()
    device_imei = models.CharField(max_length=15, null=True, blank=True)
    request_size = models.IntegerField(null=True, blank=True)
    response_time = models.FloatField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'api_logs'
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['device_imei']),
            models.Index(fields=['status_code']),
        ]
    
    def __str__(self):
        return f"API Log: {self.method} {self.endpoint} - {self.status_code}"
