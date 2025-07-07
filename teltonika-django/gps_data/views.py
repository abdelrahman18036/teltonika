from django.shortcuts import render
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
import time
import json
import logging

from .models import Device, GPSRecord, DeviceStatus, APILog
from .serializers import (
    DeviceSerializer, GPSRecordSerializer, BulkGPSRecordSerializer,
    DeviceStatusSerializer, TeltonikaDataSerializer
)

logger = logging.getLogger('gps_data')


class TeltonikaGPSDataView(APIView):
    """
    Main endpoint for receiving GPS data from Teltonika service
    Accepts bulk GPS data and stores it efficiently
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        start_time = time.time()
        
        try:
            # Log the incoming request
            logger.info(f"Received GPS data: {len(request.data)} bytes")
            
            # Handle both single record and bulk data
            if isinstance(request.data, list):
                # Multiple records
                records_processed = 0
                records_created = 0
                
                with transaction.atomic():
                    for record_data in request.data:
                        if self.process_single_record(record_data):
                            records_created += 1
                        records_processed += 1
                
                response_data = {
                    'status': 'success',
                    'records_processed': records_processed,
                    'records_created': records_created,
                    'processing_time': time.time() - start_time
                }
                
            else:
                # Single record
                success = self.process_single_record(request.data)
                response_data = {
                    'status': 'success' if success else 'error',
                    'records_processed': 1,
                    'records_created': 1 if success else 0,
                    'processing_time': time.time() - start_time
                }
            
            # Log API call
            self.log_api_call(request, 200, time.time() - start_time)
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error processing GPS data: {str(e)}")
            self.log_api_call(request, 500, time.time() - start_time, str(e))
            
            return Response({
                'status': 'error',
                'message': str(e),
                'processing_time': time.time() - start_time
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def process_single_record(self, record_data):
        """Process a single GPS record"""
        try:
            serializer = BulkGPSRecordSerializer(data=record_data)
            if serializer.is_valid():
                serializer.save()
                return True
            else:
                logger.warning(f"Invalid GPS record data: {serializer.errors}")
                return False
        except Exception as e:
            logger.error(f"Error processing GPS record: {str(e)}")
            return False
    
    def log_api_call(self, request, status_code, response_time, error_message=None):
        """Log API call for monitoring"""
        try:
            device_imei = None
            request_size = 0
            
            if hasattr(request, 'data'):
                request_size = len(json.dumps(request.data))
                if isinstance(request.data, dict):
                    device_imei = request.data.get('imei')
                elif isinstance(request.data, list) and request.data:
                    device_imei = request.data[0].get('imei')
            
            APILog.objects.create(
                endpoint=request.path,
                method=request.method,
                status_code=status_code,
                device_imei=device_imei,
                request_size=request_size,
                response_time=response_time,
                error_message=error_message
            )
        except Exception:
            pass  # Don't fail the main request if logging fails


@api_view(['POST'])
@permission_classes([AllowAny])
def store_gps_record(request):
    """
    Store a single GPS record
    Compatible with the teltonika_service.py integration
    """
    try:
        # Extract data from request
        imei = request.data.get('imei')
        timestamp = request.data.get('timestamp')
        gps_data = request.data.get('gps_data')
        io_data = request.data.get('io_data')
        priority = request.data.get('priority', 0)
        event_io_id = request.data.get('event_io_id')
        
        if not imei:
            return Response({'error': 'IMEI is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Prepare data for serializer
        record_data = {
            'imei': imei,
            'timestamp': timestamp,
            'priority': priority,
            'gps_data': gps_data,
            'io_data': io_data,
            'event_io_id': event_io_id
        }
        
        serializer = BulkGPSRecordSerializer(data=record_data)
        if serializer.is_valid():
            gps_record = serializer.save()
            logger.info(f"GPS record stored for device {imei}")
            
            return Response({
                'status': 'success',
                'record_id': gps_record.id,
                'device_imei': imei
            }, status=status.HTTP_201_CREATED)
        else:
            logger.warning(f"Invalid GPS data for device {imei}: {serializer.errors}")
            return Response({
                'status': 'error',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error storing GPS record: {str(e)}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeviceListView(generics.ListCreateAPIView):
    """List all devices or create a new device"""
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [AllowAny]


class DeviceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update or delete a specific device"""
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [AllowAny]
    lookup_field = 'imei'


class DeviceGPSRecordsView(generics.ListAPIView):
    """Get GPS records for a specific device"""
    serializer_class = GPSRecordSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        imei = self.kwargs['imei']
        device = get_object_or_404(Device, imei=imei)
        return GPSRecord.objects.filter(device=device).order_by('-timestamp')


class LatestGPSRecordsView(generics.ListAPIView):
    """Get latest GPS records for all devices"""
    serializer_class = GPSRecordSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        # Get the latest record for each device
        latest_records = []
        for device in Device.objects.filter(is_active=True):
            latest_record = GPSRecord.objects.filter(device=device).order_by('-timestamp').first()
            if latest_record:
                latest_records.append(latest_record.id)
        
        return GPSRecord.objects.filter(id__in=latest_records).order_by('-timestamp')


class DeviceStatusView(generics.ListAPIView):
    """Get status of all devices"""
    queryset = DeviceStatus.objects.all()
    serializer_class = DeviceStatusSerializer
    permission_classes = [AllowAny]


@api_view(['POST'])
@permission_classes([AllowAny])
def update_device_status(request, imei):
    """Update device connection status"""
    try:
        device = get_object_or_404(Device, imei=imei)
        is_connected = request.data.get('is_connected', True)
        ip_address = request.data.get('ip_address')
        
        device_status, created = DeviceStatus.objects.get_or_create(device=device)
        device_status.update_status(is_connected=is_connected, ip_address=ip_address)
        
        return Response({
            'status': 'success',
            'device_imei': imei,
            'is_connected': is_connected
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_stats(request):
    """Get API usage statistics"""
    try:
        from django.db.models import Count, Q
        from datetime import timedelta
        
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        
        stats = {
            'total_devices': Device.objects.count(),
            'active_devices': Device.objects.filter(is_active=True).count(),
            'total_records': GPSRecord.objects.count(),
            'records_last_24h': GPSRecord.objects.filter(created_at__gte=last_24h).count(),
            'online_devices': DeviceStatus.objects.filter(is_online=True).count(),
            'api_calls_last_24h': APILog.objects.filter(timestamp__gte=last_24h).count(),
            'successful_calls_last_24h': APILog.objects.filter(
                timestamp__gte=last_24h,
                status_code__lt=400
            ).count(),
        }
        
        return Response(stats, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Health check endpoint
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint"""
    try:
        # Test database connection
        device_count = Device.objects.count()
        
        return Response({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'database': 'connected',
            'total_devices': device_count
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'timestamp': timezone.now().isoformat(),
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
