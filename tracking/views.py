from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg, Max, Min
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from .models import Device, TelemetryData, DeviceEvent, SystemStats
from .serializers import (
    DeviceSerializer, TelemetryDataSerializer, DeviceEventSerializer,
    TelemetryDataDetailSerializer, DeviceStatsSerializer
)
from .database_manager import db_manager

logger = logging.getLogger('tracking')


class FastPagination(PageNumberPagination):
    """Custom pagination for fast data retrieval"""
    page_size = 1000
    page_size_query_param = 'page_size'
    max_page_size = 5000


class DeviceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for device management and data retrieval
    """
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    pagination_class = FastPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'imei']
    
    def get_queryset(self):
        """Optimize queryset with prefetch for performance"""
        return Device.objects.prefetch_related('telemetry_data', 'events').all()
    
    @action(detail=True, methods=['get'])
    def telemetry(self, request, pk=None):
        """
        Get telemetry data for specific device
        URL: /api/devices/{id}/telemetry/
        Query params:
        - start_date: YYYY-MM-DD format
        - end_date: YYYY-MM-DD format
        - limit: max records (default 1000)
        - ignition: filter by ignition status (true/false)
        - movement: filter by movement status (true/false)
        """
        device = self.get_object()
        
        # Parse query parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        limit = int(request.query_params.get('limit', 1000))
        ignition = request.query_params.get('ignition')
        movement = request.query_params.get('movement')
        
        # Build queryset
        queryset = TelemetryData.objects.filter(device=device)
        
        # Date filtering
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                queryset = queryset.filter(device_timestamp__gte=start_dt)
            except ValueError:
                return Response({'error': 'Invalid start_date format. Use YYYY-MM-DD'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                # Add 1 day to include the entire end date
                end_dt = end_dt + timedelta(days=1)
                queryset = queryset.filter(device_timestamp__lt=end_dt)
            except ValueError:
                return Response({'error': 'Invalid end_date format. Use YYYY-MM-DD'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        
        # Status filtering
        if ignition is not None:
            ignition_bool = ignition.lower() == 'true'
            queryset = queryset.filter(ignition=ignition_bool)
            
        if movement is not None:
            movement_bool = movement.lower() == 'true'
            queryset = queryset.filter(movement=movement_bool)
        
        # Order and limit
        queryset = queryset.order_by('-device_timestamp')[:limit]
        
        # Serialize data
        serializer = TelemetryDataSerializer(queryset, many=True)
        
        return Response({
            'device': device.imei,
            'count': len(serializer.data),
            'data': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def latest_position(self, request, pk=None):
        """
        Get latest GPS position for device
        URL: /api/devices/{id}/latest_position/
        """
        device = self.get_object()
        
        latest = TelemetryData.objects.filter(
            device=device,
            latitude__isnull=False,
            longitude__isnull=False
        ).order_by('-device_timestamp').first()
        
        if latest:
            serializer = TelemetryDataDetailSerializer(latest)
            return Response(serializer.data)
        else:
            return Response({'message': 'No GPS data available'}, 
                          status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def events(self, request, pk=None):
        """
        Get events for specific device
        URL: /api/devices/{id}/events/
        Query params:
        - event_type: filter by event type
        - days: number of days back (default 7)
        """
        device = self.get_object()
        
        # Parse parameters
        event_type = request.query_params.get('event_type')
        days = int(request.query_params.get('days', 7))
        
        # Build queryset
        since_date = timezone.now() - timedelta(days=days)
        queryset = DeviceEvent.objects.filter(
            device=device,
            event_time__gte=since_date
        )
        
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        queryset = queryset.order_by('-event_time')[:500]  # Limit to 500 events
        
        serializer = DeviceEventSerializer(queryset, many=True)
        return Response({
            'device': device.imei,
            'count': len(serializer.data),
            'events': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        Get statistics for specific device
        URL: /api/devices/{id}/stats/
        Query params:
        - days: number of days back (default 30)
        """
        device = self.get_object()
        days = int(request.query_params.get('days', 30))
        since_date = timezone.now() - timedelta(days=days)
        
        # Calculate statistics
        telemetry_stats = TelemetryData.objects.filter(
            device=device,
            device_timestamp__gte=since_date
        ).aggregate(
            total_records=Count('id'),
            avg_speed=Avg('speed'),
            max_speed=Max('speed'),
            total_distance=Max('total_odometer') - Min('total_odometer') if Min('total_odometer') else 0,
            ignition_time=Count('id', filter=Q(ignition=True)),
            movement_time=Count('id', filter=Q(movement=True))
        )
        
        # Get event counts
        event_counts = DeviceEvent.objects.filter(
            device=device,
            event_time__gte=since_date
        ).values('event_type').annotate(count=Count('id'))
        
        return Response({
            'device': device.imei,
            'period_days': days,
            'telemetry_stats': telemetry_stats,
            'event_counts': {item['event_type']: item['count'] for item in event_counts}
        })


class TelemetryDataViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for telemetry data with advanced filtering
    """
    queryset = TelemetryData.objects.all()
    serializer_class = TelemetryDataSerializer
    pagination_class = FastPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['device__imei', 'ignition', 'movement', 'gnss_status']
    
    def get_queryset(self):
        """Optimize queryset with select_related for performance"""
        return TelemetryData.objects.select_related('device').all()
    
    @action(detail=False, methods=['get'])
    def by_imei(self, request):
        """
        Get telemetry data by IMEI (fast endpoint)
        URL: /api/telemetry/by_imei/?imei=864636069432371
        Query params:
        - imei: device IMEI (required)
        - start_date: YYYY-MM-DD format
        - end_date: YYYY-MM-DD format  
        - limit: max records (default 1000, max 5000)
        - ignition: filter by ignition status
        - movement: filter by movement status
        - format: response format (simple/detailed, default simple)
        """
        imei = request.query_params.get('imei')
        if not imei:
            return Response({'error': 'imei parameter is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            device = Device.objects.get(imei=imei)
        except Device.DoesNotExist:
            return Response({'error': f'Device with IMEI {imei} not found'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        # Use database manager for optimized retrieval
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        limit = min(int(request.query_params.get('limit', 1000)), 5000)
        format_type = request.query_params.get('format', 'simple')
        
        # Parse dates
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except ValueError:
                return Response({'error': 'Invalid start_date format. Use YYYY-MM-DD'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                end_dt = end_dt + timedelta(days=1)  # Include entire end date
            except ValueError:
                return Response({'error': 'Invalid end_date format. Use YYYY-MM-DD'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        
        # Get data using database manager
        data = db_manager.get_device_data(imei, start_dt, end_dt, limit)
        
        if format_type == 'simple':
            # Return simplified format for better performance
            simplified_data = []
            for record in data:
                simplified_data.append({
                    'timestamp': record['device_timestamp'],
                    'lat': record['gps']['latitude'],
                    'lng': record['gps']['longitude'],
                    'speed': record['gps']['speed'],
                    'ignition': record['ignition'],
                    'movement': record['movement'],
                })
            
            return Response({
                'imei': imei,
                'count': len(simplified_data),
                'data': simplified_data
            })
        else:
            # Return detailed format
            return Response({
                'imei': imei,
                'count': len(data),
                'data': data
            })
    
    @action(detail=False, methods=['get'])
    def live_tracking(self, request):
        """
        Get latest positions for all active devices
        URL: /api/telemetry/live_tracking/
        Query params:
        - max_age: maximum age in minutes (default 30)
        """
        max_age = int(request.query_params.get('max_age', 30))
        since_time = timezone.now() - timedelta(minutes=max_age)
        
        # Get latest position for each active device
        latest_positions = []
        active_devices = Device.objects.filter(is_active=True, last_seen__gte=since_time)
        
        for device in active_devices:
            latest = TelemetryData.objects.filter(
                device=device,
                latitude__isnull=False,
                longitude__isnull=False,
                device_timestamp__gte=since_time
            ).order_by('-device_timestamp').first()
            
            if latest:
                latest_positions.append({
                    'imei': device.imei,
                    'name': device.name,
                    'timestamp': latest.device_timestamp.isoformat(),
                    'latitude': float(latest.latitude),
                    'longitude': float(latest.longitude),
                    'speed': latest.speed,
                    'angle': latest.angle,
                    'ignition': latest.ignition,
                    'movement': latest.movement,
                    'gsm_signal': latest.gsm_signal,
                })
        
        return Response({
            'count': len(latest_positions),
            'max_age_minutes': max_age,
            'positions': latest_positions
        })


class DeviceEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for device events
    """
    queryset = DeviceEvent.objects.all()
    serializer_class = DeviceEventSerializer
    pagination_class = FastPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['device__imei', 'event_type']
    
    def get_queryset(self):
        return DeviceEvent.objects.select_related('device').all()


class SystemStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for system statistics
    """
    queryset = SystemStats.objects.all()
    serializer_class = DeviceStatsSerializer
    pagination_class = FastPagination
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """
        Get current system statistics
        URL: /api/stats/current/
        """
        # Calculate current stats
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_hour = now - timedelta(hours=1)
        
        stats = {
            'timestamp': now.isoformat(),
            'devices': {
                'total': Device.objects.count(),
                'active': Device.objects.filter(is_active=True).count(),
                'active_last_24h': Device.objects.filter(last_seen__gte=last_24h).count(),
                'active_last_hour': Device.objects.filter(last_seen__gte=last_hour).count(),
            },
            'telemetry': {
                'total_records': TelemetryData.objects.count(),
                'records_last_24h': TelemetryData.objects.filter(server_timestamp__gte=last_24h).count(),
                'records_last_hour': TelemetryData.objects.filter(server_timestamp__gte=last_hour).count(),
            },
            'events': {
                'total_events': DeviceEvent.objects.count(),
                'events_last_24h': DeviceEvent.objects.filter(event_time__gte=last_24h).count(),
                'events_last_hour': DeviceEvent.objects.filter(event_time__gte=last_hour).count(),
            }
        }
        
        return Response(stats)
