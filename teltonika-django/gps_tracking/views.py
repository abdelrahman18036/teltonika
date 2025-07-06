from django.shortcuts import render
from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.db.models import Q, Count, Avg
from django.db import transaction
from datetime import timedelta, datetime
import logging

from .models import Device, GPSRecord, DeviceEvent, DeviceStatus, IOParameter
from .serializers import (
    DeviceSerializer, GPSRecordSerializer, GPSRecordCreateSerializer,
    DeviceEventSerializer, DeviceStatusSerializer, IOParameterSerializer,
    DeviceStatisticsSerializer, BulkGPSRecordSerializer,
    DeviceLocationHistorySerializer, DeviceStatusUpdateSerializer
)

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """Custom pagination class"""
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class DeviceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing devices"""
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    lookup_field = 'imei'
    
    def get_queryset(self):
        queryset = Device.objects.all()
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['get'])
    def status(self, request, imei=None):
        """Get current status of a device"""
        try:
            device = self.get_object()
            status_obj, created = DeviceStatus.objects.get_or_create(device=device)
            serializer = DeviceStatusSerializer(status_obj)
            return Response(serializer.data)
        except Device.DoesNotExist:
            return Response({'error': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def recent_records(self, request, imei=None):
        """Get recent GPS records for a device"""
        try:
            device = self.get_object()
            hours = int(request.query_params.get('hours', 24))
            since = timezone.now() - timedelta(hours=hours)
            
            records = GPSRecord.objects.filter(
                device=device,
                timestamp__gte=since
            ).order_by('-timestamp')[:100]
            
            serializer = GPSRecordSerializer(records, many=True)
            return Response(serializer.data)
        except Device.DoesNotExist:
            return Response({'error': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)


class GPSRecordViewSet(viewsets.ModelViewSet):
    """ViewSet for managing GPS records"""
    queryset = GPSRecord.objects.all()
    serializer_class = GPSRecordSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        queryset = GPSRecord.objects.select_related('device').all()
        
        # Filter by device IMEI
        imei = self.request.query_params.get('imei')
        if imei:
            queryset = queryset.filter(device__imei=imei)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                queryset = queryset.filter(timestamp__gte=start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                queryset = queryset.filter(timestamp__lte=end_dt)
            except ValueError:
                pass
        
        # Filter by ignition status
        ignition = self.request.query_params.get('ignition')
        if ignition is not None:
            queryset = queryset.filter(ignition=ignition.lower() == 'true')
        
        # Filter by movement
        movement = self.request.query_params.get('movement')
        if movement is not None:
            queryset = queryset.filter(movement=movement.lower() == 'true')
        
        return queryset.order_by('-timestamp')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return GPSRecordCreateSerializer
        return GPSRecordSerializer


@api_view(['POST'])
@permission_classes([AllowAny])  # Allow unauthenticated access for Teltonika service
def create_gps_record(request):
    """
    Endpoint for creating single GPS record from Teltonika service
    Optimized for high-frequency inserts
    """
    try:
        serializer = GPSRecordCreateSerializer(data=request.data)
        if serializer.is_valid():
            record = serializer.save()
            
            # Update device status
            update_device_status(record)
            
            logger.info(f"GPS record created for device {record.device.imei}")
            return Response({
                'id': str(record.id),
                'message': 'GPS record created successfully'
            }, status=status.HTTP_201_CREATED)
        else:
            logger.error(f"Invalid GPS record data: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Error creating GPS record: {str(e)}")
        return Response({
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def bulk_create_gps_records(request):
    """
    Endpoint for creating multiple GPS records in bulk
    Optimized for high-performance batch inserts
    """
    try:
        serializer = BulkGPSRecordSerializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                records = serializer.save()
                
                # Update device statuses for all records
                for record in records:
                    update_device_status(record)
                
                logger.info(f"Bulk created {len(records)} GPS records")
                return Response({
                    'created_count': len(records),
                    'message': 'GPS records created successfully'
                }, status=status.HTTP_201_CREATED)
        else:
            logger.error(f"Invalid bulk GPS record data: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Error bulk creating GPS records: {str(e)}")
        return Response({
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def update_device_status(gps_record):
    """Helper function to update device status from GPS record"""
    try:
        status_obj, created = DeviceStatus.objects.get_or_create(
            device=gps_record.device,
            defaults={
                'last_seen': gps_record.timestamp,
                'is_online': True,
            }
        )
        
        # Update status fields
        status_obj.last_seen = gps_record.timestamp
        status_obj.is_online = True
        
        if gps_record.latitude is not None:
            status_obj.last_latitude = gps_record.latitude
        if gps_record.longitude is not None:
            status_obj.last_longitude = gps_record.longitude
        if gps_record.speed is not None:
            status_obj.last_speed = gps_record.speed
        if gps_record.ignition is not None:
            status_obj.last_ignition = gps_record.ignition
        if gps_record.movement is not None:
            status_obj.last_movement = gps_record.movement
        if gps_record.battery_level is not None:
            status_obj.last_battery_level = gps_record.battery_level
        if gps_record.gsm_signal is not None:
            status_obj.last_gsm_signal = gps_record.gsm_signal
        
        status_obj.save()
        
    except Exception as e:
        logger.error(f"Error updating device status for {gps_record.device.imei}: {str(e)}")


class DeviceEventViewSet(viewsets.ModelViewSet):
    """ViewSet for managing device events"""
    queryset = DeviceEvent.objects.all()
    serializer_class = DeviceEventSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        queryset = DeviceEvent.objects.select_related('device').all()
        
        # Filter by device IMEI
        imei = self.request.query_params.get('imei')
        if imei:
            queryset = queryset.filter(device__imei=imei)
        
        # Filter by event type
        event_type = self.request.query_params.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        # Filter by acknowledged status
        acknowledged = self.request.query_params.get('acknowledged')
        if acknowledged is not None:
            queryset = queryset.filter(acknowledged=acknowledged.lower() == 'true')
        
        return queryset.order_by('-timestamp')
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge an event"""
        event = self.get_object()
        event.acknowledged = True
        event.acknowledged_at = timezone.now()
        event.acknowledged_by = request.user.username if request.user.is_authenticated else 'system'
        event.save()
        
        return Response({'message': 'Event acknowledged'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def device_statistics(request):
    """Get overall device statistics"""
    try:
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        stats = {
            'device_count': Device.objects.count(),
            'active_devices': Device.objects.filter(is_active=True).count(),
            'online_devices': DeviceStatus.objects.filter(
                is_online=True,
                last_seen__gte=now - timedelta(minutes=30)
            ).count(),
            'total_records': GPSRecord.objects.count(),
            'records_today': GPSRecord.objects.filter(
                received_at__gte=today_start
            ).count(),
        }
        
        serializer = DeviceStatisticsSerializer(stats)
        return Response(serializer.data)
    
    except Exception as e:
        logger.error(f"Error getting device statistics: {str(e)}")
        return Response({
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def device_location_history(request, imei):
    """Get location history for a specific device"""
    try:
        hours = int(request.query_params.get('hours', 24))
        since = timezone.now() - timedelta(hours=hours)
        
        records = GPSRecord.objects.filter(
            device__imei=imei,
            timestamp__gte=since,
            latitude__isnull=False,
            longitude__isnull=False
        ).values(
            'timestamp', 'latitude', 'longitude', 'speed', 'ignition', 'movement'
        ).order_by('timestamp')
        
        serializer = DeviceLocationHistorySerializer(records, many=True)
        return Response(serializer.data)
    
    except Exception as e:
        logger.error(f"Error getting location history for {imei}: {str(e)}")
        return Response({
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def device_live_status(request):
    """Get live status of all devices"""
    try:
        statuses = DeviceStatus.objects.select_related('device').filter(
            device__is_active=True
        ).order_by('-last_seen')
        
        serializer = DeviceStatusSerializer(statuses, many=True)
        return Response(serializer.data)
    
    except Exception as e:
        logger.error(f"Error getting live device status: {str(e)}")
        return Response({
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IOParameterViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for reading IO parameter definitions"""
    queryset = IOParameter.objects.all()
    serializer_class = IOParameterSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
