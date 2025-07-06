#!/usr/bin/env python3
"""
Teltonika Service - Production ready server for Ubuntu
Logs all data to files and runs as a system service
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

# Configuration
CONFIG = {
    'host': '0.0.0.0',
    'port': 5000,
    'log_dir': '/var/log/teltonika',
    'data_dir': '/var/lib/teltonika',
    'max_log_size': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5
}

class TeltonikaService:
    def __init__(self, config):
        self.config = config
        self.running = True
        self.server_socket = None
        self.setup_logging()
        self.setup_directories()
        
    def setup_directories(self):
        """Create necessary directories"""
        os.makedirs(self.config['log_dir'], exist_ok=True)
        os.makedirs(self.config['data_dir'], exist_ok=True)
        
    def setup_logging(self):
        """Setup simplified logging configuration"""
        from logging.handlers import RotatingFileHandler
        
        # Main application logger - only show essential information
        self.logger = logging.getLogger('teltonika_service')
        self.logger.setLevel(logging.INFO)
        
        # Console handler - clean output
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        # Set timezone for logging
        logging.Formatter.converter = lambda *args: datetime.now(timezone(timedelta(hours=3))).timetuple()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler - clean output
        log_file = os.path.join(self.config['log_dir'], 'teltonika_service.log')
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=self.config['max_log_size'],
            backupCount=self.config['backup_count']
        )
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # GPS data logger (separate file for GPS data)
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
        """Handle IMEI authentication"""
        try:
            imei_length = struct.unpack('!H', data[:2])[0]
            
            if len(data) < 2 + imei_length:
                return False
                
            imei = data[2:2+imei_length].decode('ascii')
            
            # Accept the device (send 0x01)
            client_socket.send(b'\x01')
            
            # Log IMEI acceptance
            self.log_device_event(imei, "IMEI_ACCEPTED", client_address)
            
            return imei
            
        except:
            client_socket.send(b'\x00')
            return False
    
    def parse_gps_element(self, data, offset):
        """Parse GPS element from AVL data"""
        try:
            # Check how much data we actually have from the offset
            available_bytes = len(data) - offset
            
            if available_bytes < 15:
                # For incomplete GPS data, try to parse what we have
                if available_bytes >= 13:
                    # Try parsing with reduced format (missing last 2 bytes for speed)
                    gps_bytes = data[offset:offset+13]
                    # Parse without speed field: Longitude(4) + Latitude(4) + Altitude(2) + Angle(2) + Satellites(1)
                    longitude, latitude, altitude, angle, satellites = struct.unpack('!IIHHB', gps_bytes)
                    speed = 0  # Default speed when not available
                elif available_bytes >= 8:
                    # Minimal GPS data - just coordinates
                    gps_bytes = data[offset:offset+8]
                    longitude, latitude = struct.unpack('!II', gps_bytes)
                    altitude = 0
                    angle = 0
                    satellites = 0
                    speed = 0
                else:
                    return None
            else:
                # Normal parsing with full 15 bytes
                gps_bytes = data[offset:offset+15]
                longitude, latitude, altitude, angle, satellites, speed = struct.unpack('!IIHHBH', gps_bytes)
            
            # Convert coordinates to decimal degrees
            longitude_deg = longitude / 10000000.0 if longitude != 0 else 0
            latitude_deg = latitude / 10000000.0 if latitude != 0 else 0
            
            # Check if coordinates are negative (two's complement)
            if longitude > 0x80000000:
                longitude_deg = -(0x100000000 - longitude) / 10000000.0
            if latitude > 0x80000000:
                latitude_deg = -(0x100000000 - latitude) / 10000000.0
            
            gps_result = {
                'longitude': longitude_deg,
                'latitude': latitude_deg,
                'altitude': altitude,
                'angle': angle,
                'satellites': satellites,
                'speed': speed
            }
            
            self.logger.debug(f"GPS parsed successfully: {gps_result}")
            return gps_result
            
        except:
            return None
    
    def parse_io_element_codec8(self, data, offset):
        """Parse IO element for Codec8"""
        try:
            event_io_id = data[offset]
            n_total_io = data[offset + 1]
            
            current_offset = offset + 2
            io_data = {}
            
            # Parse 1-byte IO elements
            n1 = data[current_offset]
            current_offset += 1
            
            for _ in range(n1):
                io_id = data[current_offset]
                io_value = data[current_offset + 1]
                io_data[io_id] = io_value
                current_offset += 2
            
            # Parse 2-byte IO elements
            n2 = data[current_offset]
            current_offset += 1
            
            for _ in range(n2):
                io_id = data[current_offset]
                io_value = struct.unpack('!H', data[current_offset + 1:current_offset + 3])[0]
                io_data[io_id] = io_value
                current_offset += 3
            
            # Parse 4-byte IO elements
            n4 = data[current_offset]
            current_offset += 1
            
            for _ in range(n4):
                io_id = data[current_offset]
                io_value = struct.unpack('!I', data[current_offset + 1:current_offset + 5])[0]
                io_data[io_id] = io_value
                current_offset += 5
            
            # Parse 8-byte IO elements
            n8 = data[current_offset]
            current_offset += 1
            
            for _ in range(n8):
                io_id = data[current_offset]
                io_value = struct.unpack('!Q', data[current_offset + 1:current_offset + 9])[0]
                io_data[io_id] = io_value
                current_offset += 9
            
            return {
                'event_io_id': event_io_id,
                'n_total_io': n_total_io,
                'io_data': io_data
            }, current_offset
            
        except:
            return None, offset
    
    def parse_codec8(self, data, imei):
        """Parse Codec8 protocol data"""
        try:
            preamble = data[:4]
            data_field_length = struct.unpack('!I', data[4:8])[0]
            codec_id = data[8]
            num_data_1 = data[9]
            

            
            offset = 10
            records = []
            
            for i in range(num_data_1):
                # Parse timestamp (8 bytes)
                timestamp = struct.unpack('!Q', data[offset:offset+8])[0]
                # Convert to Egypt timezone (UTC+3)
                egypt_tz = timezone(timedelta(hours=3))
                dt = datetime.fromtimestamp(timestamp / 1000.0, tz=egypt_tz)
                
                # Parse priority (1 byte)
                priority = data[offset + 8]
                
                # Parse GPS element (15 bytes)
                gps_data = self.parse_gps_element(data, offset + 9)
                
                # Parse IO element
                io_data, new_offset = self.parse_io_element_codec8(data, offset + 24)
                
                record = {
                    'imei': imei,
                    'timestamp': dt.isoformat(),
                    'priority': priority,
                    'gps': gps_data,
                    'io': io_data
                }
                records.append(record)
                
                # Log GPS data
                self.log_gps_data(imei, dt, gps_data, io_data)
                
                offset = new_offset
            
            return records, num_data_1
            
        except:
            return None, 0
    
    def parse_io_element_codec8_extended(self, data, offset):
        """Parse IO element for Codec8 Extended"""
        try:
            event_io_id = struct.unpack('!H', data[offset:offset+2])[0]
            n_total_io = struct.unpack('!H', data[offset+2:offset+4])[0]
            
            current_offset = offset + 4
            io_data = {}
            
            # Parse 1-byte IO elements
            n1 = struct.unpack('!H', data[current_offset:current_offset+2])[0]
            current_offset += 2
            
            for _ in range(n1):
                io_id = struct.unpack('!H', data[current_offset:current_offset+2])[0]
                io_value = data[current_offset + 2]
                io_data[io_id] = io_value
                current_offset += 3
            
            # Parse 2-byte IO elements
            n2 = struct.unpack('!H', data[current_offset:current_offset+2])[0]
            current_offset += 2
            
            for _ in range(n2):
                io_id = struct.unpack('!H', data[current_offset:current_offset+2])[0]
                io_value = struct.unpack('!H', data[current_offset + 2:current_offset + 4])[0]
                io_data[io_id] = io_value
                current_offset += 4
            
            # Parse 4-byte IO elements
            n4 = struct.unpack('!H', data[current_offset:current_offset+2])[0]
            current_offset += 2
            
            for _ in range(n4):
                io_id = struct.unpack('!H', data[current_offset:current_offset+2])[0]
                io_value = struct.unpack('!I', data[current_offset + 2:current_offset + 6])[0]
                io_data[io_id] = io_value
                current_offset += 6
            
            # Parse 8-byte IO elements
            n8 = struct.unpack('!H', data[current_offset:current_offset+2])[0]
            current_offset += 2
            
            for _ in range(n8):
                io_id = struct.unpack('!H', data[current_offset:current_offset+2])[0]
                io_value = struct.unpack('!Q', data[current_offset + 2:current_offset + 10])[0]
                io_data[io_id] = io_value
                current_offset += 10
            
            # Parse variable length IO elements (NX)
            nx = struct.unpack('!H', data[current_offset:current_offset+2])[0]
            current_offset += 2
            
            for _ in range(nx):
                io_id = struct.unpack('!H', data[current_offset:current_offset+2])[0]
                io_length = struct.unpack('!H', data[current_offset+2:current_offset+4])[0]
                io_value = data[current_offset+4:current_offset+4+io_length]
                io_data[io_id] = io_value.hex()
                current_offset += 4 + io_length
            
            return {
                'event_io_id': event_io_id,
                'n_total_io': n_total_io,
                'io_data': io_data
            }, current_offset
            
        except:
            return None, offset
    
    def parse_codec8_extended(self, data, imei):
        """Parse Codec8 Extended protocol data"""
        try:
            preamble = data[:4]
            data_field_length = struct.unpack('!I', data[4:8])[0]
            codec_id = data[8]
            num_data_1 = data[9]
            

            
            offset = 10
            records = []
            
            for i in range(num_data_1):
                # Parse timestamp (8 bytes)
                if offset + 8 > len(data):
                    break
                    
                timestamp = struct.unpack('!Q', data[offset:offset+8])[0]
                # Convert to Egypt timezone (UTC+3)
                egypt_tz = timezone(timedelta(hours=3))
                dt = datetime.fromtimestamp(timestamp / 1000.0, tz=egypt_tz)
                
                # Parse priority (1 byte)
                if offset + 9 > len(data):
                    break
                priority = data[offset + 8]
                
                # Parse GPS element
                gps_offset = offset + 9
                available_gps_bytes = len(data) - gps_offset
                
                if available_gps_bytes >= 15:
                    gps_data = self.parse_gps_element(data, gps_offset)
                    # If normal parsing fails, try extraction method
                    if gps_data is None:
                        gps_data = self.extract_gps_coordinates(data, gps_offset)
                    io_offset = gps_offset + 15
                else:
                    # Try to parse what we have
                    gps_data = self.parse_gps_element(data, gps_offset)
                    # If that fails, try extraction
                    if gps_data is None:
                        gps_data = self.extract_gps_coordinates(data, gps_offset)
                    # Estimate IO offset based on available data
                    io_offset = gps_offset + min(15, available_gps_bytes)
                
                # Parse IO element - Codec8 Extended format
                if io_offset < len(data):
                    io_data, new_offset = self.parse_io_element_codec8_extended(data, io_offset)
                    


                else:
                    io_data = None
                    new_offset = io_offset
                
                record = {
                    'imei': imei,
                    'timestamp': dt.isoformat(),
                    'priority': priority,
                    'gps': gps_data,
                    'io': io_data
                }
                records.append(record)
                
                # Log GPS data
                self.log_gps_data(imei, dt, gps_data, io_data)
                
                offset = new_offset
                
                # Safety check to prevent infinite loop
                if new_offset <= io_offset:
                    break
            
            return records, num_data_1
            
        except:
            return None, 0
    
    def parse_codec12(self, data, imei):
        """Parse Codec12 protocol data (GPRS commands)"""
        try:
            preamble = data[:4]
            data_size = struct.unpack('!I', data[4:8])[0]
            codec_id = data[8]
            quantity_1 = data[9]
            message_type = data[10]
            
            if message_type == 0x05:  # Command
                command_size = struct.unpack('!I', data[11:15])[0]
                command = data[15:15+command_size]
                self.logger.info(f"Codec12 Command from {imei}: {command.decode('ascii', errors='ignore')}")
                
                # Send response
                response = "Command received"
                return self.create_codec12_response(response)
                
            elif message_type == 0x06:  # Response
                response_size = struct.unpack('!I', data[11:15])[0]
                response = data[15:15+response_size]
                self.logger.info(f"Codec12 Response from {imei}: {response.decode('ascii', errors='ignore')}")
                
        except:
            pass

        return None
    
    def create_codec12_response(self, response_text):
        """Create Codec12 response packet"""
        try:
            response_bytes = response_text.encode('ascii')
            response_size = len(response_bytes)
            
            # Build response packet
            packet = bytearray()
            packet.extend(b'\x00\x00\x00\x00')  # Preamble
            
            data_size = 1 + 1 + 1 + 4 + response_size + 1  # codec_id + quantity + type + size + response + quantity
            packet.extend(struct.pack('!I', data_size))  # Data size
            packet.extend(b'\x0C')  # Codec ID
            packet.extend(b'\x01')  # Quantity 1
            packet.extend(b'\x06')  # Response type
            packet.extend(struct.pack('!I', response_size))  # Response size
            packet.extend(response_bytes)  # Response
            packet.extend(b'\x01')  # Quantity 2
            
            # Calculate and append CRC
            crc = self.calculate_crc16(packet[8:])  # CRC from codec ID
            packet.extend(struct.pack('!I', crc))
            
            return bytes(packet)
            
        except:
            return None
    
    def log_gps_data(self, imei, timestamp, gps_data, io_data):
        """Log GPS data to file and console in clean format"""
        if gps_data:
            # Create GPS log entry for file
            gps_entry = {
                'imei': imei,
                'timestamp': timestamp.isoformat(),
                'latitude': gps_data['latitude'],
                'longitude': gps_data['longitude'],
                'altitude': gps_data['altitude'],
                'angle': gps_data['angle'],
                'satellites': gps_data['satellites'],
                'speed': gps_data['speed'],
                'io_data': io_data['io_data'] if io_data else {}
            }
            
            # Log to GPS file
            self.gps_logger.info(json.dumps(gps_entry))
            
            # Log clean summary to console
            self.logger.info(f"Device IMEI: {imei}")
            self.logger.info(f"GPS Coordinates: Lat {gps_data['latitude']:.6f}, Lon {gps_data['longitude']:.6f}")
            self.logger.info(f"Speed: {gps_data['speed']} km/h, Altitude: {gps_data['altitude']} m, Satellites: {gps_data['satellites']}")
            
            # Show detailed parameters if available
            if io_data and io_data['io_data']:
                decoded_params, _ = self.decode_io_parameters(io_data['io_data'])
                if decoded_params:
                    self.logger.info("Vehicle Parameters:")
                    for param in decoded_params:
                        self.logger.info(f"  {param}")
            
            self.logger.info("---")
    
    def log_device_event(self, imei, event, data):
        """Log device events to file"""
        # Use Egypt timezone (UTC+3)
        egypt_tz = timezone(timedelta(hours=3))
        event_entry = {
            'imei': imei,
            'timestamp': datetime.now(tz=egypt_tz).isoformat(),
            'event': event,
            'data': str(data)
        }
        
        event_file = os.path.join(self.config['log_dir'], 'device_events.log')
        with open(event_file, 'a') as f:
            f.write(f"{json.dumps(event_entry)}\n")
    
    def handle_avl_data(self, client_socket, data, imei):
        """Handle AVL data packet"""
        try:
            if len(data) < 10:
                return
            
            # Check preamble
            preamble = data[:4]
            if preamble != b'\x00\x00\x00\x00':
                return
            
            # Get codec ID
            codec_id = data[8]
            
            records = None
            num_records = 0
            
            if codec_id == 0x08:  # Codec8
                records, num_records = self.parse_codec8(data, imei)
                
            elif codec_id == 0x8E:  # Codec8 Extended
                records, num_records = self.parse_codec8_extended(data, imei)
                
            elif codec_id == 0x10:  # Codec16
                records, num_records = self.parse_codec8(data, imei)  # Similar to Codec8
                
            elif codec_id == 0x0C:  # Codec12
                response = self.parse_codec12(data, imei)
                if response:
                    client_socket.send(response)
                return
                
            else:
                return
            
            # Send acknowledgment for AVL data
            if num_records > 0:
                ack = struct.pack('!I', num_records)
                client_socket.send(ack)
            
        except:
            pass
    
    def handle_client(self, client_socket, client_address):
        """Handle individual client connection"""
        imei = None
        
        try:
            # First, expect IMEI
            imei_data = client_socket.recv(1024)
            if imei_data:
                imei = self.handle_imei(client_socket, imei_data, client_address)
                if not imei:
                    return
            
            # Then handle AVL data packets
            while self.running:
                data = client_socket.recv(2048)
                if not data:
                    break
                
                self.handle_avl_data(client_socket, data, imei)
                
        except:
            pass
        finally:
            client_socket.close()
            if imei:
                self.log_device_event(imei, "DISCONNECTED", client_address)
    
    def start_server(self):
        """Start the TCP server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.config['host'], self.config['port']))
            self.server_socket.listen(10)
            
            self.logger.info(f"Teltonika Service started on {self.config['host']}:{self.config['port']}")
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    
                    # Handle each client in a separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.error:
                    pass
                
        except:
            pass
        finally:
            self.stop_server()
    
    def stop_server(self):
        """Stop the server gracefully"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
    
    def signal_handler(self, signum, frame):
        """Handle system signals"""
        self.stop_server()
        sys.exit(0)

    def decode_io_parameters(self, io_data):
        """Decode and explain IO parameters from Teltonika devices"""
        io_meanings = {
            # Permanent I/O Elements - Core Status
            239: "Ignition",
            240: "Movement", 
            80: "Data Mode",
            21: "GSM Signal",
            200: "Sleep Mode",
            69: "GNSS Status",
            181: "GNSS PDOP",
            182: "GNSS HDOP",
            66: "External Voltage",
            24: "Speed",
            205: "GSM Cell ID",
            206: "GSM Area Code",
            67: "Battery Voltage",
            68: "Battery Current",
            241: "Active GSM Operator",
            199: "Trip Odometer",
            16: "Total Odometer",
            
            # Digital/Analog Inputs
            1: "Digital Input 1",
            2: "Digital Input 2", 
            3: "Digital Input 3",
            9: "Analog Input 1",
            6: "Analog Input 2",
            179: "Digital Output 1",
            180: "Digital Output 2",
            380: "Digital output 3",
            381: "Ground Sense",
            
            # Fuel and GPS Data
            12: "Fuel Used GPS",
            13: "Fuel Rate GPS",
            
            # Accelerometer
            17: "Axis X",
            18: "Axis Y", 
            19: "Axis Z",
            
            # Device Info
            11: "ICCID1",
            14: "ICCID2",
            10: "SD Status",
            113: "Battery Level",
            238: "User ID",
            237: "Network Type",
            
            # Pulse Counters
            4: "Pulse Counter Din1",
            5: "Pulse Counter Din2",
            
            # Bluetooth
            263: "BT Status",
            264: "Barcode ID",
            
            # Movement Detection
            303: "Instant Movement",
            
            # Temperature Sensors (Dallas)
            72: "Dallas Temperature 1",
            73: "Dallas Temperature 2", 
            74: "Dallas Temperature 3",
            75: "Dallas Temperature 4",
            76: "Dallas Temperature ID 1",
            77: "Dallas Temperature ID 2",
            79: "Dallas Temperature ID 3", 
            71: "Dallas Temperature ID 4",
            78: "iButton",
            207: "RFID",
            
            # Liquid Level Sensors
            201: "LLS 1 Fuel Level",
            202: "LLS 1 Temperature",
            203: "LLS 2 Fuel Level", 
            204: "LLS 2 Temperature",
            210: "LLS 3 Fuel Level",
            211: "LLS 3 Temperature",
            212: "LLS 4 Fuel Level",
            213: "LLS 4 Temperature", 
            214: "LLS 5 Fuel Level",
            215: "LLS 5 Temperature",
            
            # Performance
            15: "Eco Score",
            
            # Sensor Data
            327: "UL202-02 Sensor Fuel level",
            483: "UL202-02 Sensor Status",
            
            # Position Data
            387: "ISO6709 Coordinates",
            636: "UMTS/LTE Cell ID",
            
            # Driver Data  
            403: "Driver Name",
            404: "Driver card license type",
            405: "Driver Gender",
            406: "Driver Card ID",
            407: "Driver card expiration date", 
            408: "Driver Card place of issue",
            409: "Driver Status Event",
            
            # Speed Sensor
            329: "AIN Speed",
            
            # MSP500 Data
            500: "MSP500 vendor name",
            501: "MSP500 vehicle number",
            502: "MSP500 speed sensor",
            
            # Wake Reason
            637: "Wake Reason",
            
            # EYE Sensor Data (Temperature, Humidity, etc.)
            10800: "EYE Temperature 1", 10801: "EYE Temperature 2", 10802: "EYE Temperature 3", 10803: "EYE Temperature 4",
            10804: "EYE Humidity 1", 10805: "EYE Humidity 2", 10806: "EYE Humidity 3", 10807: "EYE Humidity 4", 
            10808: "EYE Magnet 1", 10809: "EYE Magnet 2", 10810: "EYE Magnet 3", 10811: "EYE Magnet 4",
            10812: "EYE Movement 1", 10813: "EYE Movement 2", 10814: "EYE Movement 3", 10815: "EYE Movement 4",
            10816: "EYE Pitch 1", 10817: "EYE Pitch 2", 10818: "EYE Pitch 3", 10819: "EYE Pitch 4",
            10820: "EYE Low Battery 1", 10821: "EYE Low Battery 2", 10822: "EYE Low Battery 3", 10823: "EYE Low Battery 4",
            10824: "EYE Battery Voltage 1", 10825: "EYE Battery Voltage 2", 10826: "EYE Battery Voltage 3", 10827: "EYE Battery Voltage 4",
            10832: "EYE Roll 1", 10833: "EYE Roll 2", 10834: "EYE Roll 3", 10835: "EYE Roll 4",
            10836: "EYE Movement count 1", 10837: "EYE Movement count 2", 10838: "EYE Movement count 3", 10839: "EYE Movement count 4",
            10840: "EYE Magnet count 1", 10841: "EYE Magnet count 2", 10842: "EYE Magnet count 3", 10843: "EYE Magnet count 4",
            
            # Calibration
            383: "AXL Calibration Status",
            
            # BLE RFID and Buttons
            451: "BLE RFID #1", 452: "BLE RFID #2", 453: "BLE RFID #3", 454: "BLE RFID #4",
            455: "BLE Button 1 state #1", 456: "BLE Button 1 state #2", 457: "BLE Button 1 state #3", 458: "BLE Button 1 state #4",
            459: "BLE Button 2 state #1", 460: "BLE Button 2 state #2", 461: "BLE Button 2 state #3", 462: "BLE Button 2 state #4",
            
            # Frequency
            622: "Frequency DIN1", 623: "Frequency DIN2",
            
            # Connectivity
            1148: "Connectivity quality",
            
            # OBD Elements
            256: "VIN", 30: "Number of DTC", 31: "Engine Load", 32: "Coolant Temperature", 33: "Short Fuel Trim",
            34: "Fuel pressure", 35: "Intake MAP", 36: "Engine RPM", 37: "Vehicle Speed", 38: "Timing Advance",
            39: "Intake Air Temperature", 40: "MAF", 41: "Throttle Position", 42: "Runtime since engine start",
            43: "Distance Traveled MIL On", 44: "Relative Fuel Rail Pressure", 45: "Direct Fuel Rail Pressure",
            46: "Commanded EGR", 47: "EGR Error", 48: "Fuel Level", 49: "Distance Since Codes Clear",
            50: "Barometic Pressure", 51: "Control Module Voltage", 52: "Absolute Load Value", 759: "Fuel Type",
            53: "Ambient Air Temperature", 54: "Time Run With MIL On", 55: "Time Since Codes Cleared",
            56: "Absolute Fuel Rail Pressure", 57: "Hybrid battery pack life", 58: "Engine Oil Temperature",
            59: "Fuel injection timing", 540: "Throttle position group", 541: "Commanded Equivalence R",
            542: "Intake MAP 2 bytes", 543: "Hybrid System Voltage", 544: "Hybrid System Current",
            281: "Fault Codes", 60: "Fuel Rate",
            
            # BLE Sensors
            25: "BLE Temperature #1", 26: "BLE Temperature #2", 27: "BLE Temperature #3", 28: "BLE Temperature #4",
            29: "BLE Battery #1", 20: "BLE Battery #2", 22: "BLE Battery #3", 23: "BLE Battery #4",
            86: "BLE Humidity #1", 104: "BLE Humidity #2", 106: "BLE Humidity #3", 108: "BLE Humidity #4",
            270: "BLE Fuel Level #1", 273: "BLE Fuel Level #2", 276: "BLE Fuel Level #3", 279: "BLE Fuel Level #4",
            385: "Beacon",
            
            # CAN Bus Data (LVCAN200, ALLCAN300, CANCONTROL)
            81: "Vehicle Speed (CAN)", 82: "Accelerator Pedal Position", 83: "Fuel Consumed (CAN)", 
            84: "Fuel Level (CAN)", 85: "Engine RPM (CAN)", 87: "Total Mileage (CAN)", 89: "Fuel level (CAN %)",
            90: "Door Status (CAN)", 100: "Program Number", 101: "Module ID 8B", 388: "Module ID 17B",
            102: "Engine Worktime", 103: "Engine Worktime (counted)", 105: "Total Mileage (counted)",
            107: "Fuel Consumed (counted)", 110: "Fuel Rate (CAN)", 111: "AdBlue Level (%)",
            112: "AdBlue Level (L)", 114: "Engine Load (CAN)", 115: "Engine Temperature",
        }
        
        decoded_params = []
        unknown_params = []
        
        for io_id, value in io_data.items():
            if io_id in io_meanings:
                param_name = io_meanings[io_id]
                
                # Format values based on parameter type and CSV specifications
                if io_id in [66, 67]:  # External/Battery Voltage (2 bytes, V)
                    formatted_value = f"{value/1000:.2f}V"
                elif io_id == 68:  # Battery Current (2 bytes, A) - but typically in mA
                    formatted_value = f"{value}mA" 
                elif io_id in [9, 6]:  # Analog Input 1&2 (2 bytes, V)
                    formatted_value = f"{value/1000:.2f}V"
                elif io_id == 113:  # Battery Level (1 byte, %)
                    formatted_value = f"{value}%"
                elif io_id == 21:  # GSM Signal (1 byte, 0-5 scale)
                    formatted_value = f"{value}/5"
                elif io_id in [24, 37, 81]:  # Speed (2 bytes, km/h)
                    formatted_value = f"{value} km/h"
                elif io_id in [36, 85]:  # Engine RPM (2 bytes, rpm)
                    formatted_value = f"{value} RPM"
                elif io_id in [31, 48, 89, 111, 114]:  # Engine Load, Fuel Level percentages (1 byte, %)
                    formatted_value = f"{value}%"
                elif io_id in [72, 73, 74, 75]:  # Dallas Temperature (4 bytes, °C) - signed, -55.0 to 115.0
                    formatted_value = f"{value/10:.1f}°C"
                elif io_id == 32:  # Coolant Temperature (1 byte, °C, signed -128 to 127)
                    formatted_value = f"{value}°C"
                elif io_id in [60, 110, 186]:  # Fuel Rate (2 bytes, L/h)
                    formatted_value = f"{value} L/h"
                elif io_id == 16:  # Total Odometer (4 bytes, no unit specified, but typically meters)
                    formatted_value = f"{value/1000:.1f} km"
                elif io_id == 199:  # Trip Odometer (4 bytes, m)
                    formatted_value = f"{value} m"
                elif io_id in [87, 105]:  # Total Mileage CAN (4 bytes, m)
                    formatted_value = f"{value/1000:.1f} km"
                elif io_id == 69:  # GNSS Status (1 byte, 0-3)
                    gnss_status = {0: "Off", 1: "No Fix", 2: "2D Fix", 3: "3D Fix"}
                    formatted_value = gnss_status.get(value, f"Unknown({value})")
                elif io_id == 80:  # Data Mode (1 byte, 0-5)
                    data_modes = {0: "Home On Stop", 1: "Home On Moving", 2: "Universal", 3: "Ping", 4: "Manual", 5: "Unknown"}
                    formatted_value = data_modes.get(value, f"Mode {value}")
                elif io_id == 200:  # Sleep Mode (1 byte, 0-4)
                    sleep_modes = {0: "No Sleep", 1: "GPS Sleep", 2: "Deep Sleep", 3: "Ultra Deep Sleep", 4: "Online Deep Sleep"}
                    formatted_value = sleep_modes.get(value, f"Sleep Mode {value}")
                elif io_id == 239:  # Ignition (1 byte, 0-1)
                    formatted_value = "ON" if value else "OFF"
                elif io_id == 240:  # Movement (1 byte, 0-1)
                    formatted_value = "Moving" if value else "Stopped"
                elif io_id in [1, 2, 3, 179, 180, 380]:  # Digital inputs/outputs (1 byte, 0-1)
                    formatted_value = "HIGH" if value else "LOW"
                elif io_id in [181, 182]:  # GNSS PDOP/HDOP (2 bytes, 0-500)
                    formatted_value = f"{value/100:.2f}"
                elif io_id in [205, 206]:  # GSM Cell ID/Area Code (2 bytes)
                    formatted_value = f"{value}"
                elif io_id == 241:  # Active GSM Operator (4 bytes)
                    formatted_value = f"{value}"
                elif io_id in [12, 83, 107]:  # Fuel consumed (4 bytes, L)
                    formatted_value = f"{value} L"
                elif io_id in [13]:  # Fuel Rate GPS (2 bytes, L/100km)
                    formatted_value = f"{value} L/100km"
                elif io_id in [17, 18, 19]:  # Accelerometer Axis (2 bytes, mG, signed -8000 to 8000)
                    formatted_value = f"{value} mG"
                elif io_id in [4, 5]:  # Pulse Counter (4 bytes)
                    formatted_value = f"{value} pulses"
                elif io_id == 15:  # Eco Score (2 bytes)
                    formatted_value = f"{value}"
                elif io_id in [201, 203, 210, 212, 214]:  # LLS Fuel Level (2 bytes, kvants or ltr, signed)
                    formatted_value = f"{value} L"
                elif io_id in [202, 204, 211, 213, 215]:  # LLS Temperature (1 byte, °C, signed -128 to 127)
                    formatted_value = f"{value}°C"
                elif io_id == 327:  # UL202-02 Sensor Fuel level (2 bytes, mm, signed)
                    formatted_value = f"{value} mm"
                elif io_id in [25, 26, 27, 28]:  # BLE Temperature (2 bytes, °C, signed -40.00 to 125.00)
                    formatted_value = f"{value/100:.2f}°C"
                elif io_id in [29, 20, 22, 23]:  # BLE Battery (1 byte, %)
                    formatted_value = f"{value}%"
                elif io_id in [86, 104, 106, 108]:  # BLE Humidity (2 bytes, %RH)
                    formatted_value = f"{value/10:.1f}%RH"
                elif io_id == 90:  # Door Status (CAN) - bit field
                    door_statuses = []
                    if value & 0x01: door_statuses.append("Driver Door Open")
                    if value & 0x02: door_statuses.append("Passenger Door Open")
                    if value & 0x04: door_statuses.append("Rear Left Door Open")
                    if value & 0x08: door_statuses.append("Rear Right Door Open")
                    if value & 0x10: door_statuses.append("Trunk Open")
                    if value & 0x20: door_statuses.append("Hood Open")
                    formatted_value = ", ".join(door_statuses) if door_statuses else "All Doors Closed"
                elif io_id == 100:  # Program Number
                    formatted_value = f"Program #{value}"
                elif io_id in [11, 14]:  # ICCID1/ICCID2 (8 bytes, SIM card ID) - convert from hex
                    # Convert to full ICCID format
                    formatted_value = f"{value:016X}"
                elif io_id == 237:  # Network Type (1 byte, 0-1)
                    network_types = {0: "GSM", 1: "LTE"}
                    formatted_value = network_types.get(value, f"Network Type {value}")
                elif io_id == 263:  # BT Status (1 byte, 0-4)
                    bt_statuses = {0: "Off", 1: "Enabled", 2: "Connected", 3: "Disconnected", 4: "Error"}
                    formatted_value = bt_statuses.get(value, f"BT Status {value}")
                elif io_id == 303:  # Instant Movement (1 byte, 0-1)
                    formatted_value = "Moving" if value else "Stationary"
                elif io_id == 381:  # Ground Sense (1 byte, 0-1)
                    formatted_value = "Grounded" if value else "Not Grounded"
                elif io_id == 383:  # AXL Calibration Status (1 byte, 0-3)
                    cal_statuses = {0: "Not Calibrated", 1: "Calibration In Progress", 2: "Calibrated", 3: "Calibration Error"}
                    formatted_value = cal_statuses.get(value, f"Calibration Status {value}")
                elif io_id == 637:  # Wake Reason (1 byte, 0-1)
                    wake_reasons = {0: "Normal", 1: "Movement"}
                    formatted_value = wake_reasons.get(value, f"Wake Reason {value}")
                elif io_id in [451, 452, 453, 454]:  # BLE RFID (8 bytes, HEX)
                    formatted_value = f"0x{value:016X}"
                elif io_id in [455, 456, 457, 458, 459, 460, 461, 462]:  # BLE Button states
                    formatted_value = "Pressed" if value else "Released"
                elif io_id in [622, 623]:  # Frequency DIN (2 bytes, Hz)
                    formatted_value = f"{value} Hz"
                elif io_id == 10:  # SD Status (1 byte, 0-1)
                    formatted_value = "SD Card Present" if value else "No SD Card"
                elif io_id == 78:  # iButton (8 bytes, HEX)
                    formatted_value = f"0x{value:016X}"
                elif io_id == 207:  # RFID (8 bytes, HEX)
                    formatted_value = f"0x{value:016X}"
                elif io_id == 238:  # User ID (8 bytes)
                    formatted_value = f"User ID: {value}"
                elif io_id == 387:  # ISO6709 Coordinates (34 bytes, HEX)
                    formatted_value = f"ISO6709: 0x{value}"
                elif io_id == 636:  # UMTS/LTE Cell ID (4 bytes)
                    formatted_value = f"Cell ID: {value}"
                elif io_id == 1148:  # Connectivity quality (4 bytes)
                    formatted_value = f"Quality: {value}"
                elif io_id == 256:  # VIN (variable length, ASCII)
                    formatted_value = f"VIN: {value}"
                elif io_id == 264:  # Barcode ID (variable length, ASCII)
                    formatted_value = f"Barcode: {value}"
                elif io_id in [82]:  # Accelerator Pedal Position (1 byte, %)
                    formatted_value = f"{value}%"
                elif io_id in [84, 112]:  # Fuel Level CAN (2 bytes, L)
                    formatted_value = f"{value} L"
                elif io_id == 115:  # Engine Temperature (2 bytes, °C, signed -60.0 to 127.0)
                    formatted_value = f"{value/10:.1f}°C"
                elif io_id in [34, 35, 50]:  # Pressures (fuel, intake MAP, barometric) in kPa
                    formatted_value = f"{value} kPa"
                elif io_id in [39, 53]:  # Air temperatures (1 byte, °C, signed)
                    formatted_value = f"{value}°C"
                elif io_id == 40:  # MAF (2 bytes, g/sec)
                    formatted_value = f"{value} g/sec"
                elif io_id in [41, 540]:  # Throttle Position (1 byte, %)
                    formatted_value = f"{value}%"
                elif io_id in [42, 54, 55]:  # Runtime/Time values (2 bytes, s or min)
                    if io_id == 42:
                        formatted_value = f"{value} sec"
                    else:
                        formatted_value = f"{value} min"
                elif io_id in [43, 49]:  
                    formatted_value = f"{value} km"
                elif io_id in [44, 45, 56]: 
                    formatted_value = f"{value} kPa"
                elif io_id in [46, 47]: 
                    formatted_value = f"{value}%"
                elif io_id == 51: 
                    formatted_value = f"{value/1000:.2f}V"
                elif io_id == 52:  
                    formatted_value = f"{value/100:.1f}%"
                elif io_id == 57: 
                    formatted_value = f"{value}%"
                elif io_id == 58:  
                    formatted_value = f"{value}°C"
                elif io_id == 59:  
                    formatted_value = f"{value/100:.2f}°"
                else:
                    formatted_value = str(value)
                    
                decoded_params.append(f"IO{io_id:03d}: {param_name} = {formatted_value}")
            else:
                unknown_params.append(f"IO{io_id:03d}: Unknown parameter = {value}")
        
        return decoded_params, unknown_params



    def extract_gps_coordinates(self, data, offset):
        """Extract GPS coordinates using the same method as GPS analysis"""
        try:
            available_bytes = len(data) - offset
            if available_bytes >= 15:
                gps_bytes = data[offset:offset+15]
                
                # Use the same method that worked in GPS analysis
                longitude_raw = struct.unpack('!I', gps_bytes[0:4])[0]
                latitude_raw = struct.unpack('!I', gps_bytes[4:8])[0]
                altitude_raw = struct.unpack('!H', gps_bytes[8:10])[0]
                angle_raw = struct.unpack('!H', gps_bytes[10:12])[0]
                satellites_raw = gps_bytes[12]
                speed_raw = struct.unpack('!H', gps_bytes[13:15])[0]
                
                longitude_deg = longitude_raw / 10000000.0
                latitude_deg = latitude_raw / 10000000.0
                
                # Handle negative coordinates
                if longitude_raw > 0x80000000:
                    longitude_deg = -(0x100000000 - longitude_raw) / 10000000.0
                if latitude_raw > 0x80000000:
                    latitude_deg = -(0x100000000 - latitude_raw) / 10000000.0
                
                return {
                    'longitude': longitude_deg,
                    'latitude': latitude_deg,
                    'altitude': altitude_raw,
                    'angle': angle_raw,
                    'satellites': satellites_raw,
                    'speed': speed_raw
                }
            return None
        except:
            return None

def main():
    """Main service function"""
    # Setup signal handlers
    service = TeltonikaService(CONFIG)
    signal.signal(signal.SIGTERM, service.signal_handler)
    signal.signal(signal.SIGINT, service.signal_handler)
    
    try:
        service.start_server()
    except KeyboardInterrupt:
        service.stop_server()

if __name__ == "__main__":
    main() 