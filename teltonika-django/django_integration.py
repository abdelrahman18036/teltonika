"""
Django Integration Module for Teltonika GPS Service

This module provides functions to integrate the existing Teltonika GPS service
with the Django PostgreSQL database.
"""

import requests
import json
import logging
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


class TeltonikaDBIntegration:
    """Integration class for storing Teltonika data in Django PostgreSQL database"""
    
    def __init__(self, django_api_url='http://localhost:8000', api_token=None):
        self.django_api_url = django_api_url.rstrip('/')
        self.api_token = api_token
        self.session = requests.Session()
        
        # Set up authentication if token is provided
        if api_token:
            self.session.headers.update({'Authorization': f'Token {api_token}'})
    
    def store_gps_record(self, imei, timestamp, gps_data, io_data, priority=None, event_io_id=None):
        """
        Store a single GPS record in the Django database
        
        Args:
            imei (str): Device IMEI
            timestamp (datetime): GPS timestamp
            gps_data (dict): GPS coordinates and related data
            io_data (dict): IO parameters data
            priority (int): Message priority
            event_io_id (int): Event IO ID
        """
        try:
            # Convert timestamp to ISO format
            if isinstance(timestamp, datetime):
                timestamp_str = timestamp.isoformat()
            else:
                timestamp_str = timestamp
            
            # Prepare GPS record data
            record_data = {
                'device_imei': imei,
                'timestamp': timestamp_str,
                'priority': priority,
                'event_io_id': event_io_id,
            }
            
            # Add GPS data
            if gps_data:
                record_data.update({
                    'latitude': self._safe_decimal(gps_data.get('latitude')),
                    'longitude': self._safe_decimal(gps_data.get('longitude')),
                    'altitude': gps_data.get('altitude'),
                    'speed': gps_data.get('speed'),
                    'satellites': gps_data.get('satellites'),
                })
            
            # Add IO data mapped to database fields
            if io_data:
                # Map IO parameters to database fields
                io_mapping = {
                    239: ('ignition', self._convert_boolean),
                    240: ('movement', self._convert_boolean),
                    21: ('gsm_signal', int),
                    69: ('gnss_status', self._convert_gnss_status),
                    181: ('gnss_pdop', self._convert_pdop_hdop),
                    182: ('gnss_hdop', self._convert_pdop_hdop),
                    1: ('digital_input_1', self._convert_boolean),
                    179: ('digital_output_1', self._convert_boolean),
                    180: ('digital_output_2', self._convert_boolean),
                    380: ('digital_output_3', self._convert_boolean),
                    66: ('external_voltage', self._convert_voltage),
                    67: ('battery_voltage', self._convert_voltage),
                    113: ('battery_level', int),
                    68: ('battery_current', int),
                    16: ('total_odometer', self._convert_odometer),
                    241: ('active_gsm_operator', int),
                    11: ('iccid1', self._convert_iccid),
                    14: ('iccid2', self._convert_iccid),
                    100: ('program_number', int),
                    90: ('door_status', self._convert_door_status),
                }
                
                # Extract and convert known parameters
                additional_params = {}
                for io_id, value in io_data.items():
                    if io_id in io_mapping:
                        field_name, converter = io_mapping[io_id]
                        try:
                            record_data[field_name] = converter(value) if converter else value
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Failed to convert IO{io_id} value {value}: {e}")
                            additional_params[f"IO{io_id}"] = value
                    else:
                        # Store unknown parameters in additional_parameters JSON field
                        additional_params[f"IO{io_id}"] = value
                
                if additional_params:
                    record_data['additional_parameters'] = additional_params
            
            # Send to Django API
            response = self.session.post(
                f"{self.django_api_url}/api/gps/create/",
                json=record_data,
                timeout=10
            )
            
            if response.status_code == 201:
                logger.debug(f"Successfully stored GPS record for {imei}")
                return True
            else:
                logger.error(f"Failed to store GPS record for {imei}: HTTP {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error storing GPS record for {imei}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error storing GPS record for {imei}: {e}")
            return False
    
    def store_bulk_gps_records(self, records_data):
        """
        Store multiple GPS records in bulk
        
        Args:
            records_data (list): List of GPS record dictionaries
        """
        try:
            if not records_data:
                return True
            
            payload = {'records': records_data}
            
            response = self.session.post(
                f"{self.django_api_url}/api/gps/bulk-create/",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 201:
                logger.info(f"Successfully stored {len(records_data)} GPS records in bulk")
                return True
            else:
                logger.error(f"Failed to store bulk GPS records: HTTP {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error storing bulk GPS records: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error storing bulk GPS records: {e}")
            return False
    
    def create_device_event(self, imei, event_type, timestamp, description="", latitude=None, longitude=None):
        """
        Create a device event
        
        Args:
            imei (str): Device IMEI
            event_type (str): Type of event
            timestamp (datetime): Event timestamp
            description (str): Event description
            latitude (float): Event latitude
            longitude (float): Event longitude
        """
        try:
            event_data = {
                'device_imei': imei,
                'event_type': event_type,
                'timestamp': timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp,
                'description': description,
            }
            
            if latitude is not None:
                event_data['latitude'] = self._safe_decimal(latitude)
            if longitude is not None:
                event_data['longitude'] = self._safe_decimal(longitude)
            
            response = self.session.post(
                f"{self.django_api_url}/api/events/",
                json=event_data,
                timeout=10
            )
            
            if response.status_code == 201:
                logger.debug(f"Successfully created event {event_type} for {imei}")
                return True
            else:
                logger.error(f"Failed to create event for {imei}: HTTP {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating event for {imei}: {e}")
            return False
    
    # Helper conversion methods
    def _safe_decimal(self, value):
        """Safely convert value to decimal"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _convert_boolean(self, value):
        """Convert value to boolean"""
        return bool(value) if value is not None else None
    
    def _convert_voltage(self, value):
        """Convert voltage from mV to V"""
        if value is None:
            return None
        try:
            return round(float(value) / 1000, 2)
        except (ValueError, TypeError):
            return None
    
    def _convert_odometer(self, value):
        """Convert odometer from meters to kilometers"""
        if value is None:
            return None
        try:
            return round(float(value) / 1000, 1)
        except (ValueError, TypeError):
            return None
    
    def _convert_pdop_hdop(self, value):
        """Convert PDOP/HDOP values"""
        if value is None:
            return None
        try:
            return round(float(value) / 100, 2)
        except (ValueError, TypeError):
            return None
    
    def _convert_gnss_status(self, value):
        """Convert GNSS status to string"""
        if value is None:
            return None
        
        status_map = {0: "Off", 1: "No Fix", 2: "2D Fix", 3: "3D Fix"}
        return status_map.get(value, f"Unknown({value})")
    
    def _convert_iccid(self, value):
        """Convert ICCID to string format"""
        if value is None:
            return None
        try:
            return f"{value:016X}"
        except (ValueError, TypeError):
            return str(value)
    
    def _convert_door_status(self, value):
        """Convert door status bit field to string"""
        if value is None:
            return None
        
        try:
            door_statuses = []
            if value & 0x01:
                door_statuses.append("Driver Door Open")
            if value & 0x02:
                door_statuses.append("Passenger Door Open")
            if value & 0x04:
                door_statuses.append("Rear Left Door Open")
            if value & 0x08:
                door_statuses.append("Rear Right Door Open")
            if value & 0x10:
                door_statuses.append("Trunk Open")
            if value & 0x20:
                door_statuses.append("Hood Open")
            
            return ", ".join(door_statuses) if door_statuses else "All Doors Closed"
        except (ValueError, TypeError):
            return str(value)


# Convenience function to create integration instance
def create_db_integration(django_url='http://localhost:8000', api_token=None):
    """Create and return a TeltonikaDBIntegration instance"""
    return TeltonikaDBIntegration(django_url, api_token) 