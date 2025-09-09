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
    digital_input_2 = models.BooleanField(null=True, blank=True, help_text="IO002: Digital Input 2")
    digital_input_3 = models.BooleanField(null=True, blank=True, help_text="IO003: Digital Input 3")
    digital_output_1 = models.BooleanField(null=True, blank=True, help_text="IO179: Digital Output 1")
    digital_output_2 = models.BooleanField(null=True, blank=True, help_text="IO180: Digital Output 2")
    digital_output_3 = models.BooleanField(null=True, blank=True, help_text="IO380: Digital Output 3")
    
    # Analog Inputs
    analog_input_1 = models.IntegerField(null=True, blank=True, help_text="IO009: Analog Input 1 (mV)")
    analog_input_2 = models.IntegerField(null=True, blank=True, help_text="IO006: Analog Input 2 (mV)")
    
    # Accelerometer Data (mG - milliG)
    axis_x = models.IntegerField(null=True, blank=True, help_text="IO017: X axis value (mG)")
    axis_y = models.IntegerField(null=True, blank=True, help_text="IO018: Y axis value (mG)")
    axis_z = models.IntegerField(null=True, blank=True, help_text="IO019: Z axis value (mG)")
    
    # Dallas Temperature Sensors
    dallas_temperature_id_4 = models.BigIntegerField(null=True, blank=True, help_text="IO071: Dallas Temperature ID 4")
    
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

    @property
    def security_flags_decoded(self):
        """Decode security state flags (IO132) bit field"""
        if self.security_state_flags is None:
            return {}
        
        # Convert to integer if needed
        flags = int(self.security_state_flags)
        
        # Extract byte 3 (bits 16-23) which contains the security flags
        byte3 = (flags >> 16) & 0xFF
        
        return {
            'key_in_ignition': bool(byte3 & 0x01),
            'ignition_on': bool(byte3 & 0x02),
            'dynamic_ign_on': bool(byte3 & 0x04),
            'webasto_on': bool(byte3 & 0x08),
            'car_locked': bool(byte3 & 0x10),
            'car_locked_remote': bool(byte3 & 0x20),
            'alarm_active': bool(byte3 & 0x40),
            'immobilizer': bool(byte3 & 0x80),
        }

    @property
    def security_flags_summary(self):
        """Get a summary of active security flags"""
        flags = self.security_flags_decoded
        if not flags:
            return "No security data"
        
        active_flags = []
        for flag_name, is_active in flags.items():
            if is_active:
                active_flags.append(flag_name.replace('_', ' ').title())
        
        if active_flags:
            return ', '.join(active_flags)
        else:
            return "No security flags active"


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


class DeviceCommand(models.Model):
    """Track commands sent to IoT devices with success/failure status"""
    
    # Command types based on the two streams mentioned
    COMMAND_TYPE_CHOICES = [
        ('digital_output', 'Digital Output Stream'),
        ('can_control', 'CAN Control Stream'),
        ('custom', 'Custom Command'),
    ]
    
    # Specific command choices for each stream type
    DIGITAL_OUTPUT_COMMANDS = [
        ('lock', 'Lock (setdigout 1?? 2??)'),
        ('unlock', 'Unlock (setdigout ?1? ?2?)'),
        ('mobilize', 'Mobilize (setdigout ??1)'),
        ('immobilize', 'Immobilize (setdigout ??0)'),
    ]
    
    CAN_CONTROL_COMMANDS = [
        ('lock', 'Lock (lvcanlockalldoors)'),
        ('unlock', 'Unlock (lvcanopenalldoors)'),
        ('mobilize', 'Mobilize (lvcanunblockengine)'),
        ('immobilize', 'Immobilize (lvcanblockengine)'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('timeout', 'Timeout'),
    ]
    
    # Basic information
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='commands')
    command_type = models.CharField(max_length=20, choices=COMMAND_TYPE_CHOICES)
    command_name = models.CharField(max_length=50, help_text="lock, unlock, mobilize, immobilize, or custom command name")
    command_text = models.CharField(max_length=200, help_text="The actual command sent to device")
    
    # Status tracking
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Response tracking
    device_response = models.TextField(null=True, blank=True, help_text="Response received from device")
    error_message = models.TextField(null=True, blank=True)
    
    # Additional metadata
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    is_custom_command = models.BooleanField(default=False, help_text="True if this is a custom command")
    
    class Meta:
        db_table = 'device_commands'
        indexes = [
            models.Index(fields=['device', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['command_type', 'command_name']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Command {self.command_name} for {self.device.imei} - {self.status}"
    
    def mark_sent(self):
        """Mark command as sent"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])
    
    def mark_success(self, response=None):
        """Mark command as successful"""
        self.status = 'success'
        self.completed_at = timezone.now()
        if response:
            self.device_response = response
        self.save(update_fields=['status', 'completed_at', 'device_response'])
    
    def mark_failed(self, error=None):
        """Mark command as failed"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        if error:
            self.error_message = error
        self.save(update_fields=['status', 'completed_at', 'error_message'])
    
    def mark_timeout(self):
        """Mark command as timed out"""
        self.status = 'timeout'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
    
    def can_retry(self):
        """Check if command can be retried"""
        return self.retry_count < self.max_retries and self.status in ['failed', 'timeout']
    
    def increment_retry(self):
        """Increment retry count"""
        self.retry_count += 1
        self.status = 'pending'
        self.save(update_fields=['retry_count', 'status'])
    
    @classmethod
    def get_command_text(cls, command_type, command_name, custom_text=None):
        """Get the actual command text to send to device"""
        if command_type == 'custom':
            return custom_text or command_name
            
        command_map = {
            'digital_output': {
                'lock': 'setdigout 1?? 2??',     # Lock doors - DOUT1=HIGH, additional parameter
                'unlock': 'setdigout ?1? ?2?',   # Unlock doors - DOUT2=HIGH, additional parameter
                'mobilize': 'setdigout ??1',     # Mobilize engine - DOUT3=HIGH
                'immobilize': 'setdigout ??0',   # Immobilize engine - DOUT3=LOW
            },
            'can_control': {
                'lock': 'lvcanlockalldoors',
                'unlock': 'lvcanopenalldoors', 
                'mobilize': 'lvcanunblockengine',
                'immobilize': 'lvcanblockengine',
            }
        }
        
        return command_map.get(command_type, {}).get(command_name, '')
    
    @property
    def is_pending(self):
        """Check if command is pending"""
        return self.status == 'pending'
    
    @property
    def is_completed(self):
        """Check if command is completed (success/failed/timeout)"""
        return self.status in ['success', 'failed', 'timeout']
    
    @property
    def duration(self):
        """Get command duration if completed"""
        if self.sent_at and self.completed_at:
            return (self.completed_at - self.sent_at).total_seconds()
        return None
