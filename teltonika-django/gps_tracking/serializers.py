from rest_framework import serializers
from .models import Device, GPSRecord, DeviceEvent, DeviceStatus, IOParameter


class DeviceSerializer(serializers.ModelSerializer):
    """Serializer for Device model"""
    
    class Meta:
        model = Device
        fields = ['id', 'imei', 'device_name', 'vehicle_plate', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class GPSRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating GPS records - optimized for bulk inserts"""
    device_imei = serializers.CharField(write_only=True)
    
    class Meta:
        model = GPSRecord
        fields = [
            'device_imei', 'timestamp', 'latitude', 'longitude', 'altitude', 'speed', 'satellites',
            'gnss_status', 'gnss_pdop', 'gnss_hdop', 'ignition', 'movement', 'gsm_signal',
            'active_gsm_operator', 'digital_input_1', 'digital_output_1', 'digital_output_2',
            'digital_output_3', 'external_voltage', 'battery_voltage', 'battery_level',
            'battery_current', 'total_odometer', 'iccid1', 'iccid2', 'program_number',
            'door_status', 'additional_parameters', 'priority', 'event_io_id'
        ]
    
    def create(self, validated_data):
        device_imei = validated_data.pop('device_imei')
        device, created = Device.objects.get_or_create(
            imei=device_imei,
            defaults={'device_name': f'Device {device_imei}'}
        )
        validated_data['device'] = device
        return super().create(validated_data)


class GPSRecordSerializer(serializers.ModelSerializer):
    """Serializer for reading GPS records"""
    device = DeviceSerializer(read_only=True)
    
    class Meta:
        model = GPSRecord
        fields = [
            'id', 'device', 'timestamp', 'received_at', 'latitude', 'longitude', 'altitude',
            'speed', 'satellites', 'gnss_status', 'gnss_pdop', 'gnss_hdop', 'ignition',
            'movement', 'gsm_signal', 'active_gsm_operator', 'digital_input_1',
            'digital_output_1', 'digital_output_2', 'digital_output_3', 'external_voltage',
            'battery_voltage', 'battery_level', 'battery_current', 'total_odometer',
            'iccid1', 'iccid2', 'program_number', 'door_status', 'additional_parameters',
            'priority', 'event_io_id'
        ]


class DeviceEventSerializer(serializers.ModelSerializer):
    """Serializer for Device Events"""
    device = DeviceSerializer(read_only=True)
    device_imei = serializers.CharField(write_only=True)
    
    class Meta:
        model = DeviceEvent
        fields = [
            'id', 'device', 'device_imei', 'timestamp', 'event_type', 'description',
            'latitude', 'longitude', 'acknowledged', 'acknowledged_at', 'acknowledged_by',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def create(self, validated_data):
        device_imei = validated_data.pop('device_imei')
        try:
            device = Device.objects.get(imei=device_imei)
        except Device.DoesNotExist:
            device = Device.objects.create(
                imei=device_imei,
                device_name=f'Device {device_imei}'
            )
        validated_data['device'] = device
        return super().create(validated_data)


class DeviceStatusSerializer(serializers.ModelSerializer):
    """Serializer for Device Status"""
    device = DeviceSerializer(read_only=True)
    
    class Meta:
        model = DeviceStatus
        fields = [
            'device', 'last_seen', 'is_online', 'last_latitude', 'last_longitude',
            'last_speed', 'last_ignition', 'last_movement', 'last_battery_level',
            'last_gsm_signal', 'total_distance', 'updated_at'
        ]


class IOParameterSerializer(serializers.ModelSerializer):
    """Serializer for IO Parameter definitions"""
    
    class Meta:
        model = IOParameter
        fields = [
            'io_id', 'name', 'description', 'unit', 'data_type',
            'min_value', 'max_value', 'created_at'
        ]


class DeviceStatisticsSerializer(serializers.Serializer):
    """Serializer for device statistics"""
    device_count = serializers.IntegerField()
    active_devices = serializers.IntegerField()
    online_devices = serializers.IntegerField()
    total_records = serializers.IntegerField()
    records_today = serializers.IntegerField()


class BulkGPSRecordSerializer(serializers.Serializer):
    """Serializer for bulk GPS record creation"""
    records = GPSRecordCreateSerializer(many=True)
    
    def create(self, validated_data):
        records_data = validated_data['records']
        created_records = []
        
        for record_data in records_data:
            device_imei = record_data.pop('device_imei')
            device, created = Device.objects.get_or_create(
                imei=device_imei,
                defaults={'device_name': f'Device {device_imei}'}
            )
            record_data['device'] = device
            created_records.append(GPSRecord(**record_data))
        
        # Bulk create for better performance
        return GPSRecord.objects.bulk_create(created_records, batch_size=1000)


class DeviceLocationHistorySerializer(serializers.Serializer):
    """Serializer for device location history"""
    timestamp = serializers.DateTimeField()
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    speed = serializers.IntegerField()
    ignition = serializers.BooleanField()
    movement = serializers.BooleanField()


class DeviceStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating device status from GPS data"""
    imei = serializers.CharField()
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False)
    speed = serializers.IntegerField(required=False)
    ignition = serializers.BooleanField(required=False)
    movement = serializers.BooleanField(required=False)
    battery_level = serializers.IntegerField(required=False)
    gsm_signal = serializers.IntegerField(required=False) 