#!/usr/bin/env python3
"""
Django Integration Module for Teltonika Service
Provides API client for storing GPS data in Django backend
"""

import requests
import json
import threading
import queue
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

logger = logging.getLogger('django_integration')


class DBIntegration:
    """Database integration client for Teltonika GPS data"""
    
    def __init__(self, api_base_url: str = 'http://localhost:8000'):
        self.api_base_url = api_base_url.rstrip('/')
        self.session = requests.Session()
        
        # Queue for batch processing
        self.data_queue = queue.Queue(maxsize=1000)
        self.batch_size = 50
        self.batch_timeout = 5  # seconds
        
        # Threading
        self.worker_thread = None
        self.running = False
        
        # Statistics
        self.total_sent = 0
        self.total_failed = 0
        self.last_success = None
        self.last_error = None
        
        logger.info(f"Django integration initialized with API base URL: {self.api_base_url}")
    
    def start_worker(self):
        """Start background worker thread for batch processing"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            logger.info("Django integration worker thread started")
    
    def stop_worker(self):
        """Stop background worker thread"""
        self.running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=10)
            logger.info("Django integration worker thread stopped")
    
    def _worker_loop(self):
        """Background worker loop for batch processing"""
        batch = []
        last_batch_time = time.time()
        
        while self.running:
            try:
                # Try to get data with timeout
                try:
                    data = self.data_queue.get(timeout=1)
                    batch.append(data)
                    self.data_queue.task_done()
                except queue.Empty:
                    pass
                
                current_time = time.time()
                
                # Send batch if it's full or timeout reached
                if (len(batch) >= self.batch_size or 
                    (batch and current_time - last_batch_time >= self.batch_timeout)):
                    
                    if batch:
                        self._send_batch(batch)
                        batch = []
                        last_batch_time = current_time
                
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                time.sleep(1)
        
        # Send remaining batch on shutdown
        if batch:
            self._send_batch(batch)
    
    def _send_batch(self, batch: List[Dict[str, Any]]):
        """Send a batch of GPS records to Django API"""
        try:
            url = f"{self.api_base_url}/api/gps/"
            
            response = self.session.post(
                url,
                json=batch,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                self.total_sent += len(batch)
                self.last_success = datetime.now(timezone.utc)
                logger.debug(f"Successfully sent batch of {len(batch)} records")
            else:
                self.total_failed += len(batch)
                self.last_error = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Failed to send batch: {self.last_error}")
                
        except Exception as e:
            self.total_failed += len(batch)
            self.last_error = str(e)
            logger.error(f"Error sending batch to Django API: {e}")
    
    def store_gps_record(self, imei: str, timestamp: datetime, gps_data: Dict[str, Any], 
                        io_data: Dict[str, Any], priority: int = 0, 
                        event_io_id: Optional[int] = None) -> bool:
        """
        Store a single GPS record
        
        Args:
            imei: Device IMEI
            timestamp: Record timestamp
            gps_data: GPS coordinates and related data
            io_data: IO parameters data
            priority: Record priority
            event_io_id: Event IO ID
            
        Returns:
            bool: True if queued successfully, False otherwise
        """
        try:
            # Start worker if not running
            if not self.running:
                self.start_worker()
            
            # Prepare record data
            record_data = {
                'imei': imei,
                'timestamp': timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp,
                'priority': priority,
                'gps_data': gps_data,
                'io_data': io_data,
                'event_io_id': event_io_id
            }
            
            # Add to queue (non-blocking)
            try:
                self.data_queue.put_nowait(record_data)
                logger.debug(f"GPS record queued for device {imei}")
                return True
            except queue.Full:
                logger.warning(f"Queue full, dropping GPS record for device {imei}")
                self.total_failed += 1
                return False
                
        except Exception as e:
            logger.error(f"Error queuing GPS record: {e}")
            self.total_failed += 1
            return False
    
    def store_gps_record_immediate(self, imei: str, timestamp: datetime, 
                                  gps_data: Dict[str, Any], io_data: Dict[str, Any], 
                                  priority: int = 0, event_io_id: Optional[int] = None) -> bool:
        """
        Store GPS record immediately (synchronous)
        
        Args:
            imei: Device IMEI
            timestamp: Record timestamp
            gps_data: GPS coordinates and related data
            io_data: IO parameters data
            priority: Record priority
            event_io_id: Event IO ID
            
        Returns:
            bool: True if stored successfully, False otherwise
        """
        try:
            url = f"{self.api_base_url}/api/store/"
            
            record_data = {
                'imei': imei,
                'timestamp': timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp,
                'priority': priority,
                'gps_data': gps_data,
                'io_data': io_data,
                'event_io_id': event_io_id
            }
            
            response = self.session.post(
                url,
                json=record_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                self.total_sent += 1
                self.last_success = datetime.now(timezone.utc)
                logger.debug(f"GPS record stored immediately for device {imei}")
                return True
            else:
                self.total_failed += 1
                self.last_error = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Failed to store GPS record: {self.last_error}")
                return False
                
        except Exception as e:
            self.total_failed += 1
            self.last_error = str(e)
            logger.error(f"Error storing GPS record immediately: {e}")
            return False
    
    def update_device_status(self, imei: str, is_connected: bool, ip_address: Optional[str] = None) -> bool:
        """
        Update device connection status
        
        Args:
            imei: Device IMEI
            is_connected: Connection status
            ip_address: Device IP address
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            url = f"{self.api_base_url}/api/devices/{imei}/status/"
            
            data = {
                'is_connected': is_connected,
                'ip_address': ip_address
            }
            
            response = self.session.post(
                url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            
            if response.status_code == 200:
                logger.debug(f"Device status updated for {imei}: {'connected' if is_connected else 'disconnected'}")
                return True
            else:
                logger.error(f"Failed to update device status: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating device status: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get integration statistics"""
        return {
            'total_sent': self.total_sent,
            'total_failed': self.total_failed,
            'queue_size': self.data_queue.qsize(),
            'last_success': self.last_success.isoformat() if self.last_success else None,
            'last_error': self.last_error,
            'worker_running': self.running,
            'api_base_url': self.api_base_url
        }
    
    def health_check(self) -> bool:
        """Check if Django API is healthy"""
        try:
            url = f"{self.api_base_url}/api/health/"
            response = self.session.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False


def create_db_integration(api_base_url: str = 'http://localhost:8000') -> DBIntegration:
    """
    Create and return a DB integration instance
    
    Args:
        api_base_url: Base URL for Django API
        
    Returns:
        DBIntegration: Configured integration instance
    """
    integration = DBIntegration(api_base_url)
    
    # Test connection
    if integration.health_check():
        logger.info("Django API connection test successful")
    else:
        logger.warning("Django API connection test failed - service may not be available")
    
    return integration


# Global integration instance (optional)
_global_integration = None


def get_global_integration() -> Optional[DBIntegration]:
    """Get global integration instance"""
    global _global_integration
    return _global_integration


def set_global_integration(integration: DBIntegration):
    """Set global integration instance"""
    global _global_integration
    _global_integration = integration 