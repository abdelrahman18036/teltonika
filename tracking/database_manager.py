import logging
import threading
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from django.db import transaction, connection
from django.utils import timezone as django_timezone
from django.core.exceptions import ValidationError
from .models import Device, TelemetryData, DeviceEvent, DataProcessingStatus, SystemStats
import json
import time

logger = logging.getLogger('tracking')


class DatabaseManager:
    """
    Database manager for handling Teltonika data with fault tolerance and bulk operations
    """
    
    def __init__(self):
        self.bulk_buffer = []
        self.bulk_size = 100  # Process in batches of 100 records
        self.retry_attempts = 3
        self.lock = threading.Lock()
        
    def get_or_create_device(self, imei: str) -> Device:
        """
        Get existing device or create new one
        
        Args:
            imei: Device IMEI
            
        Returns:
            Device instance
        """
        try:
            device, created = Device.objects.get_or_create(
                imei=imei,
                defaults={
                    'name': f'Device {imei}',
                    'is_active': True,
                    'last_seen': django_timezone.now()
                }
            )
            
            if not created:
                # Update last seen timestamp
                Device.objects.filter(id=device.id).update(
                    last_seen=django_timezone.now(),
                    is_active=True
                )
                
            logger.debug(f"Device {'created' if created else 'updated'}: {imei}")
            return device
            
        except Exception as e:
            logger.error(f"Error getting/creating device {imei}: {e}")
            raise
    
    def store_telemetry_data(self, imei: str, data: Dict[str, Any]) -> bool:
        """
        Store single telemetry record with fault tolerance
        
        Args:
            imei: Device IMEI
            data: Telemetry data dictionary
            
        Returns:
            Success status
        """
        attempt = 0
        while attempt < self.retry_attempts:
            try:
                with transaction.atomic():
                    device = self.get_or_create_device(imei)
                    
                    # Parse GPS data
                    gps_data = data.get('gps', {})
                    
                    # Parse IO data
                    io_data = data.get('io_data', {})
                    
                    # Create telemetry record
                    telemetry = TelemetryData(
                        device=device,
                        device_timestamp=data.get('timestamp', django_timezone.now()),
                        server_timestamp=django_timezone.now(),
                        
                        # GPS fields
                        latitude=self._safe_decimal(gps_data.get('latitude')),
                        longitude=self._safe_decimal(gps_data.get('longitude')),
                        altitude=gps_data.get('altitude'),
                        angle=gps_data.get('angle'),
                        speed=gps_data.get('speed'),
                        satellites=gps_data.get('satellites'),
                        
                        # Core IO parameters
                        ignition=self._safe_bool(io_data.get(239)),  # IO239
                        movement=self._safe_bool(io_data.get(240)),  # IO240
                        gsm_signal=io_data.get(21),                  # IO21
                        gnss_status=io_data.get(69),                 # IO69
                        external_voltage=self._safe_voltage(io_data.get(66)),  # IO66
                        battery_voltage=self._safe_voltage(io_data.get(67)),   # IO67
                        battery_current=io_data.get(68),             # IO68
                        battery_level=io_data.get(113),              # IO113
                        total_odometer=io_data.get(16),              # IO16
                        
                        # Store all IO data as JSON
                        io_data=io_data,
                        raw_packet=data.get('raw_packet', '')
                    )
                    
                    telemetry.save()
                    
                    # Check for significant events
                    self._check_and_create_events(device, telemetry, io_data)
                    
                    logger.debug(f"Stored telemetry data for {imei}")
                    return True
                    
            except Exception as e:
                attempt += 1
                logger.warning(f"Attempt {attempt} failed to store data for {imei}: {e}")
                
                if attempt >= self.retry_attempts:
                    # Store failed packet for later processing
                    self._store_failed_packet(imei, data, str(e))
                    return False
                    
                # Wait before retry
                time.sleep(0.1 * attempt)
                
        return False
    
    def bulk_store_telemetry_data(self, records: List[Tuple[str, Dict[str, Any]]]) -> Dict[str, int]:
        """
        Store multiple telemetry records efficiently using bulk operations
        
        Args:
            records: List of (imei, data) tuples
            
        Returns:
            Dictionary with success/failure counts
        """
        results = {'success': 0, 'failed': 0, 'errors': []}
        
        if not records:
            return results
        
        # Group records by IMEI for device lookup optimization
        device_cache = {}
        telemetry_objects = []
        
        try:
            with transaction.atomic():
                for imei, data in records:
                    try:
                        # Get or create device (with caching)
                        if imei not in device_cache:
                            device_cache[imei] = self.get_or_create_device(imei)
                        device = device_cache[imei]
                        
                        # Parse data
                        gps_data = data.get('gps', {})
                        io_data = data.get('io_data', {})
                        
                        # Create telemetry object
                        telemetry = TelemetryData(
                            device=device,
                            device_timestamp=data.get('timestamp', django_timezone.now()),
                            server_timestamp=django_timezone.now(),
                            
                            # GPS fields
                            latitude=self._safe_decimal(gps_data.get('latitude')),
                            longitude=self._safe_decimal(gps_data.get('longitude')),
                            altitude=gps_data.get('altitude'),
                            angle=gps_data.get('angle'),
                            speed=gps_data.get('speed'),
                            satellites=gps_data.get('satellites'),
                            
                            # Core IO parameters
                            ignition=self._safe_bool(io_data.get(239)),
                            movement=self._safe_bool(io_data.get(240)),
                            gsm_signal=io_data.get(21),
                            gnss_status=io_data.get(69),
                            external_voltage=self._safe_voltage(io_data.get(66)),
                            battery_voltage=self._safe_voltage(io_data.get(67)),
                            battery_current=io_data.get(68),
                            battery_level=io_data.get(113),
                            total_odometer=io_data.get(16),
                            
                            io_data=io_data,
                            raw_packet=data.get('raw_packet', '')
                        )
                        
                        telemetry_objects.append(telemetry)
                        
                    except Exception as e:
                        logger.error(f"Error preparing telemetry record for {imei}: {e}")
                        results['errors'].append(f"{imei}: {str(e)}")
                        results['failed'] += 1
                
                # Bulk create telemetry records
                if telemetry_objects:
                    created_objects = TelemetryData.objects.bulk_create(
                        telemetry_objects,
                        batch_size=self.bulk_size,
                        ignore_conflicts=False
                    )
                    results['success'] = len(created_objects)
                    
                    # Process events for created records
                    for telemetry in created_objects:
                        try:
                            self._check_and_create_events(telemetry.device, telemetry, telemetry.io_data)
                        except Exception as e:
                            logger.warning(f"Error creating events for {telemetry.device.imei}: {e}")
                
                logger.info(f"Bulk stored {results['success']} records, {results['failed']} failed")
                
        except Exception as e:
            logger.error(f"Bulk storage transaction failed: {e}")
            results['failed'] = len(records)
            results['success'] = 0
            results['errors'].append(f"Transaction failed: {str(e)}")
        
        return results
    
    def get_device_data(self, imei: str, start_date: Optional[datetime] = None, 
                       end_date: Optional[datetime] = None, limit: int = 1000) -> List[Dict]:
        """
        Retrieve telemetry data for specific device with filtering
        
        Args:
            imei: Device IMEI
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of records
            
        Returns:
            List of telemetry data dictionaries
        """
        try:
            device = Device.objects.get(imei=imei)
            
            # Build query
            queryset = TelemetryData.objects.filter(device=device)
            
            if start_date:
                queryset = queryset.filter(device_timestamp__gte=start_date)
            if end_date:
                queryset = queryset.filter(device_timestamp__lte=end_date)
            
            # Order by timestamp and limit
            queryset = queryset.order_by('-device_timestamp')[:limit]
            
            # Convert to list of dictionaries
            results = []
            for record in queryset:
                results.append({
                    'id': str(record.id),
                    'device_timestamp': record.device_timestamp.isoformat(),
                    'server_timestamp': record.server_timestamp.isoformat(),
                    'gps': {
                        'latitude': float(record.latitude) if record.latitude else None,
                        'longitude': float(record.longitude) if record.longitude else None,
                        'altitude': record.altitude,
                        'angle': record.angle,
                        'speed': record.speed,
                        'satellites': record.satellites,
                    },
                    'ignition': record.ignition,
                    'movement': record.movement,
                    'gsm_signal': record.gsm_signal,
                    'gnss_status': record.gnss_status,
                    'external_voltage': float(record.external_voltage) if record.external_voltage else None,
                    'battery_voltage': float(record.battery_voltage) if record.battery_voltage else None,
                    'battery_current': record.battery_current,
                    'battery_level': record.battery_level,
                    'total_odometer': record.total_odometer,
                    'io_data': record.io_data,
                })
            
            return results
            
        except Device.DoesNotExist:
            logger.warning(f"Device not found: {imei}")
            return []
        except Exception as e:
            logger.error(f"Error retrieving data for {imei}: {e}")
            return []
    
    def get_latest_position(self, imei: str) -> Optional[Dict]:
        """
        Get latest GPS position for device
        
        Args:
            imei: Device IMEI
            
        Returns:
            Latest position data or None
        """
        try:
            device = Device.objects.get(imei=imei)
            
            latest = TelemetryData.objects.filter(
                device=device,
                latitude__isnull=False,
                longitude__isnull=False
            ).order_by('-device_timestamp').first()
            
            if latest:
                return {
                    'latitude': float(latest.latitude),
                    'longitude': float(latest.longitude),
                    'timestamp': latest.device_timestamp.isoformat(),
                    'speed': latest.speed,
                    'angle': latest.angle,
                    'ignition': latest.ignition,
                    'movement': latest.movement,
                }
            
            return None
            
        except Device.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting latest position for {imei}: {e}")
            return None
    
    def retry_failed_packets(self, max_attempts: int = 5) -> Dict[str, int]:
        """
        Retry processing failed packets
        
        Args:
            max_attempts: Maximum retry attempts
            
        Returns:
            Processing results
        """
        results = {'processed': 0, 'failed': 0}
        
        # Get failed packets that haven't exceeded max attempts
        failed_packets = DataProcessingStatus.objects.filter(
            processed=False,
            processing_attempts__lt=max_attempts
        ).order_by('created_at')[:100]  # Process in batches
        
        for packet_status in failed_packets:
            try:
                # Increment attempt counter
                packet_status.processing_attempts += 1
                packet_status.save()
                
                # Try to parse and store the packet
                packet_data = json.loads(packet_status.packet_data)
                success = self.store_telemetry_data(packet_status.device_imei, packet_data)
                
                if success:
                    packet_status.processed = True
                    packet_status.error_message = ""
                    packet_status.save()
                    results['processed'] += 1
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                packet_status.error_message = str(e)
                packet_status.save()
                results['failed'] += 1
                logger.error(f"Retry failed for packet {packet_status.id}: {e}")
        
        logger.info(f"Retry results: {results['processed']} processed, {results['failed']} failed")
        return results
    
    def _safe_decimal(self, value) -> Optional[Decimal]:
        """Convert value to Decimal safely"""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except:
            return None
    
    def _safe_bool(self, value) -> Optional[bool]:
        """Convert value to bool safely"""
        if value is None:
            return None
        return bool(value)
    
    def _safe_voltage(self, value) -> Optional[Decimal]:
        """Convert voltage from mV to V safely"""
        if value is None:
            return None
        try:
            return Decimal(str(value)) / 1000
        except:
            return None
    
    def _store_failed_packet(self, imei: str, data: Dict[str, Any], error: str):
        """Store failed packet for later retry"""
        try:
            DataProcessingStatus.objects.create(
                device_imei=imei,
                packet_data=json.dumps(data, default=str),
                processing_attempts=1,
                error_message=error,
                processed=False
            )
            logger.info(f"Stored failed packet for {imei}")
        except Exception as e:
            logger.error(f"Failed to store failed packet for {imei}: {e}")
    
    def _check_and_create_events(self, device: Device, telemetry: TelemetryData, io_data: Dict):
        """Check for significant events and create event records"""
        events_to_create = []
        
        try:
            # Get previous record for comparison
            previous = TelemetryData.objects.filter(
                device=device,
                device_timestamp__lt=telemetry.device_timestamp
            ).order_by('-device_timestamp').first()
            
            if previous:
                # Check for ignition changes
                if previous.ignition != telemetry.ignition and telemetry.ignition is not None:
                    event_type = 'ignition_on' if telemetry.ignition else 'ignition_off'
                    events_to_create.append(DeviceEvent(
                        device=device,
                        telemetry=telemetry,
                        event_type=event_type,
                        event_time=telemetry.device_timestamp,
                        description=f"Ignition {'turned on' if telemetry.ignition else 'turned off'}"
                    ))
                
                # Check for movement changes
                if previous.movement != telemetry.movement and telemetry.movement is not None:
                    event_type = 'movement_start' if telemetry.movement else 'movement_stop'
                    events_to_create.append(DeviceEvent(
                        device=device,
                        telemetry=telemetry,
                        event_type=event_type,
                        event_time=telemetry.device_timestamp,
                        description=f"Movement {'started' if telemetry.movement else 'stopped'}"
                    ))
            
            # Check for low battery
            if telemetry.battery_level is not None and telemetry.battery_level < 20:
                events_to_create.append(DeviceEvent(
                    device=device,
                    telemetry=telemetry,
                    event_type='low_battery',
                    event_time=telemetry.device_timestamp,
                    description=f"Low battery: {telemetry.battery_level}%"
                ))
            
            # Bulk create events
            if events_to_create:
                DeviceEvent.objects.bulk_create(events_to_create)
                logger.debug(f"Created {len(events_to_create)} events for {device.imei}")
                
        except Exception as e:
            logger.warning(f"Error creating events for {device.imei}: {e}")


# Global database manager instance
db_manager = DatabaseManager() 