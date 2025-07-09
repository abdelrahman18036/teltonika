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
import requests
import socket

from .models import Device, GPSRecord, DeviceStatus, APILog, DeviceCommand
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


class DeviceCommandView(APIView):
    """
    Send commands to IoT devices via Teltonika service
    """
    permission_classes = [AllowAny]
    
    def post(self, request, imei):
        """Send a command to a device by IMEI"""
        try:
            # Get device
            device = get_object_or_404(Device, imei=imei)
            
            # Extract command parameters
            command_type = request.data.get('command_type')
            command_name = request.data.get('command_name')
            
            # Validate inputs
            if not command_type or not command_name:
                return Response({
                    'status': 'error',
                    'message': 'command_type and command_name are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate command type
            valid_types = ['digital_output', 'can_control']
            if command_type not in valid_types:
                return Response({
                    'status': 'error',
                    'message': f'command_type must be one of: {valid_types}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate command name
            valid_commands = ['lock', 'unlock', 'mobilize', 'immobilize']
            if command_name not in valid_commands:
                return Response({
                    'status': 'error',
                    'message': f'command_name must be one of: {valid_commands}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get the actual command text
            command_text = DeviceCommand.get_command_text(command_type, command_name)
            if not command_text:
                return Response({
                    'status': 'error',
                    'message': 'Invalid command combination'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create command record
            command = DeviceCommand.objects.create(
                device=device,
                command_type=command_type,
                command_name=command_name,
                command_text=command_text,
                status='pending'
            )
            
            # Try to send command to device via teltonika service
            try:
                success = self.send_command_to_service(imei, command_text, command.id)
                if success:
                    command.mark_sent()
                    return Response({
                        'status': 'success',
                        'message': 'Command sent successfully',
                        'command_id': command.id,
                        'command_text': command_text
                    }, status=status.HTTP_200_OK)
                else:
                    command.mark_failed('Failed to send command to teltonika service')
                    return Response({
                        'status': 'error',
                        'message': 'Failed to send command to device',
                        'command_id': command.id
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
            except Exception as e:
                command.mark_failed(str(e))
                return Response({
                    'status': 'error',
                    'message': f'Error sending command: {str(e)}',
                    'command_id': command.id
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error in DeviceCommandView: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def send_command_to_service(self, imei, command_text, command_id):
        """Send command to teltonika service via HTTP API"""
        try:
            logger.info(f"Sending command to device {imei}: {command_text} (command_id: {command_id})")
            
            # Send HTTP request to teltonika service command API
            response = requests.post('http://localhost:5001/send_command', json={
                'imei': imei,
                'command': command_text,
                'command_id': command_id
            }, timeout=10)
            
            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"Command successfully queued: {response_data.get('message')}")
                return True
            else:
                logger.error(f"Failed to send command: HTTP {response.status_code}")
                return False
            
        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to teltonika service (is it running on port 5001?)")
            return False
        except requests.exceptions.Timeout:
            logger.error("Timeout while sending command to teltonika service")
            return False
        except Exception as e:
            logger.error(f"Error sending command to service: {str(e)}")
            return False

    def get(self, request, imei):
        """Get command history for a device"""
        try:
            device = get_object_or_404(Device, imei=imei)
            commands = DeviceCommand.objects.filter(device=device).order_by('-created_at')
            
            command_data = []
            for cmd in commands:
                command_data.append({
                    'id': cmd.id,
                    'command_type': cmd.command_type,
                    'command_name': cmd.command_name,
                    'command_text': cmd.command_text,
                    'status': cmd.status,
                    'created_at': cmd.created_at,
                    'sent_at': cmd.sent_at,
                    'completed_at': cmd.completed_at,
                    'device_response': cmd.device_response,
                    'error_message': cmd.error_message,
                    'retry_count': cmd.retry_count,
                    'duration': cmd.duration
                })
            
            return Response({
                'status': 'success',
                'device_imei': imei,
                'commands': command_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def command_status(request, command_id):
    """Get status of a specific command"""
    try:
        command = get_object_or_404(DeviceCommand, id=command_id)
        
        return Response({
            'status': 'success',
            'command': {
                'id': command.id,
                'device_imei': command.device.imei,
                'command_type': command.command_type,
                'command_name': command.command_name,
                'command_text': command.command_text,
                'status': command.status,
                'created_at': command.created_at,
                'sent_at': command.sent_at,
                'completed_at': command.completed_at,
                'device_response': command.device_response,
                'error_message': command.error_message,
                'retry_count': command.retry_count,
                'duration': command.duration
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def update_command_status(request):
    """Update command status (called by teltonika service)"""
    try:
        command_id = request.data.get('command_id')
        new_status = request.data.get('status')
        response_text = request.data.get('response')
        error_message = request.data.get('error')
        
        if not command_id or not new_status:
            return Response({
                'status': 'error',
                'message': 'command_id and status are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        command = get_object_or_404(DeviceCommand, id=command_id)
        
        if new_status == 'success':
            command.mark_success(response_text)
        elif new_status == 'failed':
            command.mark_failed(error_message)
        elif new_status == 'timeout':
            command.mark_timeout()
        elif new_status == 'sent':
            command.mark_sent()
        else:
            return Response({
                'status': 'error',
                'message': 'Invalid status value'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'status': 'success',
            'message': 'Command status updated',
            'command_id': command_id,
            'new_status': new_status
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
