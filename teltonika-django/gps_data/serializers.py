from rest_framework import serializers
from .models import Device, GPSRecord, DeviceStatus, APILog
from django.utils import timezone
from datetime import datetime


class DeviceSerializer(serializers.ModelSerializer):
    """Serializer for Device model"""
    
    class Meta:
        model = Device
        fields = ['id', 'imei', 'device_name', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class GPSRecordSerializer(serializers.ModelSerializer):
    """Serializer for GPS Record with all Teltonika parameters"""
    
    # Allow device to be specified by IMEI
    device_imei = serializers.CharField(write_only=True, required=False)
    
    # Read-only computed fields
    security_flags_decoded = serializers.ReadOnlyField()
    security_flags_summary = serializers.ReadOnlyField()
    
    class Meta:
        model = GPSRecord
        fields = [
            'id', 'device', 'device_imei', 'timestamp', 'priority',
            'latitude', 'longitude', 'altitude', 'speed', 'angle', 'satellites',
            'gnss_status', 'gnss_pdop', 'gnss_hdop',
            'ignition', 'movement',
            'gsm_signal', 'active_gsm_operator', 'iccid1', 'iccid2',
            'digital_input_1', 'digital_output_1', 'digital_output_2', 'digital_output_3',
            'external_voltage', 'battery_voltage', 'battery_level', 'battery_current',
            'total_odometer', 'program_number', 'door_status',
            'vehicle_speed_can', 'accelerator_pedal_position', 'engine_rpm_can',
            'total_mileage_can', 'fuel_level_can', 'total_mileage_counted', 'security_state_flags',
            'other_io_data', 'event_io_id', 'created_at'
        ]
        read_only_fields = ['id', 'device', 'created_at']
    
    def validate_timestamp(self, value):
        """Validate timestamp format"""
        if isinstance(value, str):
            try:
                # Parse ISO format timestamp
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                raise serializers.ValidationError("Invalid timestamp format. Use ISO format.")
        return value
    
    def create(self, validated_data):
        """Create GPS record with device lookup by IMEI"""
        device_imei = validated_data.pop('device_imei', None)
        
        if device_imei:
            device, created = Device.objects.get_or_create(
                imei=device_imei,
                defaults={'device_name': f'Device {device_imei}'}
            )
            validated_data['device'] = device
        
        return super().create(validated_data)


class BulkGPSRecordSerializer(serializers.Serializer):
    """Serializer for bulk GPS data insertion"""
    imei = serializers.CharField(max_length=15)
    timestamp = serializers.DateTimeField()
    priority = serializers.IntegerField(default=0)
    gps_data = serializers.DictField(required=False, allow_null=True)
    io_data = serializers.DictField(required=False, allow_null=True)
    event_io_id = serializers.IntegerField(required=False, allow_null=True)
    
    def validate_gps_data(self, value):
        """Validate GPS data structure"""
        if value is None:
            return {}
        
        # Check required GPS fields
        expected_fields = ['latitude', 'longitude', 'altitude', 'angle', 'satellites', 'speed']
        validated_gps = {}
        
        for field in expected_fields:
            if field in value:
                validated_gps[field] = value[field]
        
        return validated_gps
    
    def validate_io_data(self, value):
        """Validate IO data structure"""
        if value is None:
            return {}
        
        return value
    
    def create(self, validated_data):
        """Create GPS record from bulk data"""
        imei = validated_data['imei']
        timestamp = validated_data['timestamp']
        priority = validated_data.get('priority', 0)
        gps_data = validated_data.get('gps_data', {})
        io_data = validated_data.get('io_data', {})
        event_io_id = validated_data.get('event_io_id')
        
        # Get or create device
        device, created = Device.objects.get_or_create(
            imei=imei,
            defaults={'device_name': f'Device {imei}'}
        )
        
        # Map IO data to model fields
        record_data = {
            'device': device,
            'timestamp': timestamp,
            'priority': priority,
            'event_io_id': event_io_id,
        }
        
        # Map GPS data
        if gps_data:
            record_data.update({
                'latitude': gps_data.get('latitude'),
                'longitude': gps_data.get('longitude'),
                'altitude': gps_data.get('altitude'),
                'speed': gps_data.get('speed'),
                'angle': gps_data.get('angle'),
                'satellites': gps_data.get('satellites'),
            })
        
        # Map specific IO parameters to model fields
        other_io = {}
        if io_data:
            io_params = io_data.get('io_data', {}) if 'io_data' in io_data else io_data
            
            # Map known IO parameters to specific fields
            field_mapping = {
                24: 'speed',  # Speed - already handled in GPS section but include to avoid duplicating in other_io
                69: 'gnss_status',
                181: 'gnss_pdop', 
                182: 'gnss_hdop',
                239: 'ignition',
                240: 'movement',
                21: 'gsm_signal',
                241: 'active_gsm_operator',
                11: 'iccid1',
                14: 'iccid2',
                1: 'digital_input_1',
                179: 'digital_output_1',
                180: 'digital_output_2',
                380: 'digital_output_3',
                66: 'external_voltage',
                67: 'battery_voltage',
                113: 'battery_level',
                68: 'battery_current',
                16: 'total_odometer',
                100: 'program_number',
                90: 'door_status',
                81: 'vehicle_speed_can',
                82: 'accelerator_pedal_position',
                85: 'engine_rpm_can',
                87: 'total_mileage_can',
                89: 'fuel_level_can',
                105: 'total_mileage_counted',
                132: 'security_state_flags',
            }
            
            for io_id, value in io_params.items():
                io_id_int = int(io_id) if isinstance(io_id, str) else io_id
                
                if io_id_int in field_mapping:
                    field_name = field_mapping[io_id_int]
                    if io_id_int in [87, 105]:
                        value = value // 1000  # convert meters to km for readability
                    record_data[field_name] = value
                else:
                    # Store unknown parameters in other_io_data
                    other_io[str(io_id_int)] = value
        
        if other_io:
            record_data['other_io_data'] = other_io
        
        # Create the GPS record
        gps_record = GPSRecord.objects.create(**record_data)
        
        # Update device status
        try:
            device_status = device.status
        except DeviceStatus.DoesNotExist:
            device_status = DeviceStatus.objects.create(device=device)
        
        device_status.last_gps_record = timestamp
        device_status.total_records += 1
        device_status.save()
        
        return gps_record


class DeviceStatusSerializer(serializers.ModelSerializer):
    """Serializer for Device Status"""
    device_imei = serializers.CharField(source='device.imei', read_only=True)
    
    class Meta:
        model = DeviceStatus
        fields = [
            'device_imei', 'last_seen', 'last_gps_record', 'total_records',
            'is_online', 'last_ip_address', 'connection_count',
            'last_connection_at', 'last_disconnection_at'
        ]


class APILogSerializer(serializers.ModelSerializer):
    """Serializer for API Log"""
    
    class Meta:
        model = APILog
        fields = [
            'id', 'timestamp', 'endpoint', 'method', 'status_code',
            'device_imei', 'request_size', 'response_time', 'error_message'
        ]
        read_only_fields = ['id', 'timestamp']


class TeltonikaDataSerializer(serializers.Serializer):
    """
    Main serializer for Teltonika service data
    Matches the format expected from teltonika_service.py
    """
    imei = serializers.CharField(max_length=15)
    records = serializers.ListField(
        child=BulkGPSRecordSerializer(),
        allow_empty=False
    )
    
    def create(self, validated_data):
        """Process multiple GPS records from Teltonika service"""
        imei = validated_data['imei']
        records_data = validated_data['records']
        
        created_records = []
        for record_data in records_data:
            # Ensure IMEI is consistent
            record_data['imei'] = imei
            
            serializer = BulkGPSRecordSerializer(data=record_data)
            if serializer.is_valid():
                record = serializer.save()
                created_records.append(record)
            else:
                # Log validation errors but continue processing
                print(f"Validation error for record: {serializer.errors}")
        
        return {
            'imei': imei,
            'records_created': len(created_records),
            'total_records': len(records_data)
        } 