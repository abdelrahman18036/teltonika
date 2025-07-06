#!/usr/bin/env python3
"""
Teltonika Service - Production Server for Ubuntu
Optimized for handling high volumes of GPS tracking data
Includes PostgreSQL database integration via Django
"""

import socket
import struct
import threading
import time
import logging
import json
import os
import signal
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import argparse

# Django setup for database integration
import django
from django.conf import settings

# Configure Django settings
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teltonika_db.settings')
    django.setup()

# Production Configuration
CONFIG = {
    'host': '0.0.0.0',
    'port': 5000,
    'log_dir': '/var/log/teltonika',
    'data_dir': '/var/lib/teltonika',
    'max_log_size': 50 * 1024 * 1024,  # 50MB for production
    'backup_count': 10,
    'max_connections': 100,
    'socket_timeout': 30,
    'buffer_size': 8192
}

class TeltonikaProductionService:
    """Production-ready Teltonika GPS tracking service"""
    
    def __init__(self, config):
        self.config = config
        self.running = True
        self.server_socket = None
        self.client_threads = {}
        self.connection_count = 0
        
        self.setup_directories()
        self.setup_logging()
        self.setup_signal_handlers()
        self.load_parameter_definitions()
        
        # Initialize database manager
        try:
            from tracking.database_manager import db_manager
            self.db_manager = db_manager
            self.logger.info("✅ Database manager initialized")
        except Exception as e:
            self.logger.error(f"❌ Database manager failed: {e}")
            self.db_manager = None
        
    def setup_directories(self):
        """Create necessary directories"""
        os.makedirs(self.config['log_dir'], exist_ok=True)
        os.makedirs(self.config['data_dir'], exist_ok=True)
        
    def setup_logging(self):
        """Setup optimized logging for production"""
        from logging.handlers import RotatingFileHandler
        
        # Main service logger
        self.logger = logging.getLogger('teltonika_production')
        self.logger.setLevel(logging.INFO)  # INFO level for production
        
        # Console handler (less verbose in production)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler
        log_file = os.path.join(self.config['log_dir'], 'teltonika_service.log')
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=self.config['max_log_size'],
            backupCount=self.config['backup_count']
        )
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # GPS data logger (JSON format for structured logging)
        self.gps_logger = logging.getLogger('gps_data')
        self.gps_logger.setLevel(logging.INFO)
        
        gps_log_file = os.path.join(self.config['log_dir'], 'gps_data.log')
        gps_handler = RotatingFileHandler(
            gps_log_file,
            maxBytes=self.config['max_log_size'],
            backupCount=self.config['backup_count']
        )
        gps_formatter = logging.Formatter('%(asctime)s - %(message)s')
        gps_handler.setFormatter(gps_formatter)
        self.gps_logger.addHandler(gps_handler)
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGHUP, self.reload_handler)
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"🛑 Received signal {signum}, shutting down...")
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        
    def reload_handler(self, signum, frame):
        """Handle reload signal (HUP)"""
        self.logger.info("🔄 Received HUP signal, reloading configuration...")
        self.load_parameter_definitions()
        
    def load_parameter_definitions(self):
        """Load parameter definitions from CSV file"""
        import csv
        self.io_parameters = {}
        
        csv_file = 'fmb920_parameters.csv'
        if os.path.exists(csv_file):
            try:
                with open(csv_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if 'Property ID' in row and 'Property name' in row:
                            self.io_parameters[int(row['Property ID'])] = {
                                'name': row['Property name'],
                                'description': row.get('Description', ''),
                                'units': row.get('Units', ''),
                                'type': row.get('Type', 'N/A')
                            }
                self.logger.info(f"✅ Loaded {len(self.io_parameters)} parameter definitions")
            except Exception as e:
                self.logger.error(f"❌ Failed to load parameter definitions: {e}")
                self.io_parameters = {}
        else:
            self.logger.warning(f"⚠️  Parameter file {csv_file} not found")
            self.io_parameters = {}
    
    def calculate_crc16(self, data):
        """Calculate CRC-16/IBM for data validation"""
        crc = 0x0000
        polynomial = 0xA001
        
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ polynomial
                else:
                    crc >>= 1
        return crc
    
    def handle_imei(self, client_socket, data, client_address):
        """Handle IMEI identification packet"""
        try:
            if len(data) < 2:
                self.logger.warning(f"Invalid IMEI packet from {client_address}")
                return None
                
            imei_length = struct.unpack('!H', data[:2])[0]
            
            if len(data) < 2 + imei_length:
                self.logger.warning(f"IMEI packet too short from {client_address}")
                return None
                
            imei = data[2:2+imei_length].decode('ascii', errors='ignore')
            
            # Send IMEI confirmation (1 byte: 0x01 for accept, 0x00 for reject)
            response = b'\x01'
            client_socket.send(response)
            
            self.logger.info(f"📱 IMEI authenticated: {imei} from {client_address[0]}")
            
            # Log device connection to database
            if self.db_manager:
                try:
                    self.db_manager.log_device_connection(imei, client_address[0])
                except Exception as e:
                    self.logger.error(f"Database error logging connection: {e}")
            
            return imei
            
        except Exception as e:
            self.logger.error(f"IMEI handling error from {client_address}: {e}")
            return None
    
    def parse_gps_element(self, data, offset):
        """Parse GPS element from AVL record"""
        try:
            if len(data) < offset + 15:
                return None, offset
                
            longitude = struct.unpack('!i', data[offset:offset+4])[0] / 10000000.0
            latitude = struct.unpack('!i', data[offset+4:offset+8])[0] / 10000000.0
            altitude = struct.unpack('!H', data[offset+8:offset+10])[0]
            angle = struct.unpack('!H', data[offset+10:offset+12])[0]
            satellites = data[offset+12]
            speed = struct.unpack('!H', data[offset+13:offset+15])[0]
            
            return {
                'longitude': longitude,
                'latitude': latitude,
                'altitude': altitude,
                'angle': angle,
                'satellites': satellites,
                'speed': speed
            }, offset + 15
            
        except Exception as e:
            self.logger.error(f"GPS parsing error: {e}")
            return None, offset
    
    def parse_io_element_codec8(self, data, offset):
        """Parse IO element for Codec 8"""
        try:
            if len(data) < offset + 2:
                return {}, offset
                
            event_id = data[offset]
            total_elements = data[offset + 1]
            offset += 2
            
            io_data = {'event_id': event_id}
            
            # Parse different byte size elements
            for byte_size, count_bytes in [(1, 1), (2, 1), (4, 1), (8, 1)]:
                if len(data) < offset + count_bytes:
                    break
                    
                element_count = data[offset] if count_bytes == 1 else struct.unpack('!H', data[offset:offset+2])[0]
                offset += count_bytes
                
                for _ in range(element_count):
                    if len(data) < offset + 1 + byte_size:
                        break
                        
                    param_id = data[offset]
                    offset += 1
                    
                    if byte_size == 1:
                        value = data[offset]
                    elif byte_size == 2:
                        value = struct.unpack('!H', data[offset:offset+2])[0]
                    elif byte_size == 4:
                        value = struct.unpack('!I', data[offset:offset+4])[0]
                    elif byte_size == 8:
                        value = struct.unpack('!Q', data[offset:offset+8])[0]
                    
                    offset += byte_size
                    
                    # Get parameter name from definitions
                    param_info = self.io_parameters.get(param_id, {'name': f'IO{param_id}'})
                    io_data[param_info['name']] = {
                        'id': param_id,
                        'value': value,
                        'units': param_info.get('units', ''),
                        'description': param_info.get('description', '')
                    }
            
            return io_data, offset
            
        except Exception as e:
            self.logger.error(f"IO parsing error: {e}")
            return {}, offset
    
    def parse_codec8(self, data, imei):
        """Parse Codec 8 AVL data"""
        try:
            if len(data) < 10:
                return []
                
            preamble = data[:4]
            if preamble != b'\x00\x00\x00\x00':
                self.logger.warning(f"Invalid preamble: {preamble.hex()}")
                
            data_length = struct.unpack('!I', data[4:8])[0]
            codec_id = data[8]
            num_records = data[9]
            
            if codec_id != 0x08:
                self.logger.warning(f"Expected Codec 8, got 0x{codec_id:02X}")
                return []
            
            offset = 10
            records = []
            
            for i in range(num_records):
                if len(data) < offset + 8:
                    break
                    
                # Parse timestamp
                timestamp = struct.unpack('!Q', data[offset:offset+8])[0]
                offset += 8
                
                # Skip priority
                offset += 1
                
                # Parse GPS
                gps_data, offset = self.parse_gps_element(data, offset)
                if not gps_data:
                    continue
                    
                # Parse IO
                io_data, offset = self.parse_io_element_codec8(data, offset)
                
                # Convert timestamp to datetime
                try:
                    dt = datetime.fromtimestamp(timestamp / 1000.0, tz=timezone(timedelta(hours=3)))
                except:
                    dt = datetime.now(tz=timezone(timedelta(hours=3)))
                
                record = {
                    'imei': imei,
                    'timestamp': dt.isoformat(),
                    'gps': gps_data,
                    'io': io_data
                }
                
                records.append(record)
                
                # Log to database in batches for efficiency
                if self.db_manager:
                    try:
                        self.db_manager.store_telemetry_data_bulk([{
                            'imei': imei,
                            'timestamp': dt,
                            'latitude': gps_data.get('latitude', 0),
                            'longitude': gps_data.get('longitude', 0),
                            'altitude': gps_data.get('altitude', 0),
                            'speed': gps_data.get('speed', 0),
                            'angle': gps_data.get('angle', 0),
                            'satellites': gps_data.get('satellites', 0),
                            'io_data': io_data
                        }])
                    except Exception as e:
                        self.logger.error(f"Database storage error: {e}")
            
            # Log GPS data to file
            for record in records:
                self.gps_logger.info(json.dumps(record, ensure_ascii=False))
            
            return records
            
        except Exception as e:
            self.logger.error(f"Codec 8 parsing error: {e}")
            return []
    
    def handle_avl_data(self, client_socket, data, imei):
        """Handle AVL data packet"""
        try:
            records = self.parse_codec8(data, imei)
            
            if records:
                # Send response with number of accepted records
                response = struct.pack('!I', len(records))
                client_socket.send(response)
                
                self.logger.info(f"📊 Processed {len(records)} records from {imei}")
                
                # Log significant events
                for record in records:
                    io_data = record.get('io', {})
                    if 'Ignition' in io_data:
                        ignition_state = io_data['Ignition']['value']
                        if ignition_state == 1:
                            self.logger.info(f"🔑 Ignition ON - {imei}")
                        elif ignition_state == 0:
                            self.logger.info(f"🔑 Ignition OFF - {imei}")
            else:
                # Send 0 if no records processed
                response = struct.pack('!I', 0)
                client_socket.send(response)
                
        except Exception as e:
            self.logger.error(f"AVL data handling error: {e}")
            try:
                client_socket.send(struct.pack('!I', 0))
            except:
                pass
    
    def handle_client(self, client_socket, client_address):
        """Handle individual client connection"""
        thread_id = threading.current_thread().ident
        self.client_threads[thread_id] = client_address
        imei = None
        
        try:
            client_socket.settimeout(self.config['socket_timeout'])
            self.logger.info(f"🔗 New connection from {client_address[0]}:{client_address[1]}")
            
            while self.running:
                try:
                    # Read packet length first (for TCP framing)
                    data = client_socket.recv(self.config['buffer_size'])
                    if not data:
                        break
                    
                    if imei is None:
                        # First packet should be IMEI
                        imei = self.handle_imei(client_socket, data, client_address)
                        if not imei:
                            self.logger.warning(f"Failed to authenticate IMEI from {client_address}")
                            break
                    else:
                        # Subsequent packets are AVL data
                        self.handle_avl_data(client_socket, data, imei)
                        
                except socket.timeout:
                    self.logger.debug(f"Timeout from {client_address}")
                    break
                except ConnectionResetError:
                    self.logger.info(f"Connection reset by {client_address}")
                    break
                except Exception as e:
                    self.logger.error(f"Client handling error from {client_address}: {e}")
                    break
                    
        except Exception as e:
            self.logger.error(f"Client thread error: {e}")
        finally:
            client_socket.close()
            if thread_id in self.client_threads:
                del self.client_threads[thread_id]
            if imei:
                self.logger.info(f"📱 Disconnected: {imei} from {client_address[0]}")
            self.connection_count -= 1
    
    def start_server(self):
        """Start the TCP server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.config['host'], self.config['port']))
            self.server_socket.listen(self.config['max_connections'])
            
            self.logger.info(f"🚀 Teltonika Production Service started")
            self.logger.info(f"📡 Listening on {self.config['host']}:{self.config['port']}")
            self.logger.info(f"📁 Logs: {self.config['log_dir']}")
            self.logger.info(f"🗄️  Database: {'✅ Connected' if self.db_manager else '❌ Disabled'}")
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    
                    # Check connection limit
                    if self.connection_count >= self.config['max_connections']:
                        self.logger.warning(f"Max connections reached, rejecting {client_address}")
                        client_socket.close()
                        continue
                    
                    self.connection_count += 1
                    
                    # Handle client in separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        self.logger.error(f"Server error: {e}")
                        time.sleep(1)
                        
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            sys.exit(1)
    
    def stop_server(self):
        """Stop the server gracefully"""
        self.logger.info("🛑 Stopping server...")
        self.running = False
        if self.server_socket:
            self.server_socket.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Teltonika Production Service')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--max-connections', type=int, default=100, help='Maximum concurrent connections')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Update config with command line arguments
    config = CONFIG.copy()
    config['host'] = args.host
    config['port'] = args.port
    config['max_connections'] = args.max_connections
    
    if args.debug:
        config['log_level'] = logging.DEBUG
    
    # Create and start service
    service = TeltonikaProductionService(config)
    
    try:
        service.start_server()
    except KeyboardInterrupt:
        service.logger.info("Service interrupted by user")
    finally:
        service.stop_server()


if __name__ == "__main__":
    main() 