from rest_framework import serializers
from .models import Device, TelemetryData, DeviceEvent, SystemStats


class DeviceSerializer(serializers.ModelSerializer):
    """Serializer for Device model"""
    
    class Meta:
        model = Device
        fields = [
            'id', 'imei', 'name', 'description', 'created_at', 
            'updated_at', 'is_active', 'last_seen'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_seen']


class TelemetryDataSerializer(serializers.ModelSerializer):
    """Basic serializer for TelemetryData model"""
    device_imei = serializers.CharField(source='device.imei', read_only=True)
    
    class Meta:
        model = TelemetryData
        fields = [
            'id', 'device_imei', 'device_timestamp', 'server_timestamp',
            'latitude', 'longitude', 'altitude', 'angle', 'speed', 'satellites',
            'ignition', 'movement', 'gsm_signal', 'gnss_status',
            'external_voltage', 'battery_voltage', 'battery_current', 
            'battery_level', 'total_odometer'
        ]
        read_only_fields = ['id', 'server_timestamp', 'processed_at']


class TelemetryDataDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for TelemetryData model including IO data"""
    device_imei = serializers.CharField(source='device.imei', read_only=True)
    device_name = serializers.CharField(source='device.name', read_only=True)
    
    class Meta:
        model = TelemetryData
        fields = [
            'id', 'device_imei', 'device_name', 'device_timestamp', 'server_timestamp',
            'latitude', 'longitude', 'altitude', 'angle', 'speed', 'satellites',
            'ignition', 'movement', 'gsm_signal', 'gnss_status',
            'external_voltage', 'battery_voltage', 'battery_current', 
            'battery_level', 'total_odometer', 'io_data', 'processed_at'
        ]
        read_only_fields = ['id', 'server_timestamp', 'processed_at']


class DeviceEventSerializer(serializers.ModelSerializer):
    """Serializer for DeviceEvent model"""
    device_imei = serializers.CharField(source='device.imei', read_only=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    
    class Meta:
        model = DeviceEvent
        fields = [
            'id', 'device_imei', 'event_type', 'event_type_display',
            'event_time', 'description', 'additional_data', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DeviceStatsSerializer(serializers.ModelSerializer):
    """Serializer for SystemStats model"""
    
    class Meta:
        model = SystemStats
        fields = [
            'id', 'timestamp', 'total_devices', 'active_devices', 'devices_last_24h',
            'total_records', 'records_last_24h', 'records_last_hour',
            'successful_packets', 'failed_packets', 'processing_errors'
        ]
        read_only_fields = ['id', 'timestamp'] 