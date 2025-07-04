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
        """Setup logging configuration"""
        from logging.handlers import RotatingFileHandler
        
        # Main application logger
        self.logger = logging.getLogger('teltonika_service')
        self.logger.setLevel(logging.DEBUG)  # Enable debug temporarily for packet analysis
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)  # Enable debug temporarily for packet analysis
        # Set timezone for logging
        logging.Formatter.converter = lambda *args: datetime.now(timezone(timedelta(hours=3))).timetuple()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
        file_handler.setLevel(logging.DEBUG)  # Enable debug temporarily for packet analysis
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
        
        # Create detailed packet logger
        self.packet_logger = logging.getLogger('packet_details')
        self.packet_logger.setLevel(logging.DEBUG)
        
        packet_log_file = os.path.join(self.config['log_dir'], 'packet_details.log')
        packet_handler = RotatingFileHandler(
            packet_log_file,
            maxBytes=self.config['max_log_size'],
            backupCount=self.config['backup_count']
        )
        packet_formatter = logging.Formatter('%(asctime)s - %(message)s')
        packet_handler.setFormatter(packet_formatter)
        self.packet_logger.addHandler(packet_handler)
        
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
    
    def analyze_packet_details(self, data, packet_type, source):
        """Analyze and log detailed packet information"""
        self.packet_logger.info(f"=== PACKET ANALYSIS - {packet_type} from {source} ===")
        self.packet_logger.info(f"Total packet size: {len(data)} bytes")
        self.packet_logger.info(f"Raw packet (hex): {data.hex()}")
        
        # Analyze packet structure based on type
        if packet_type == "IMEI":
            if len(data) >= 2:
                imei_length = struct.unpack('!H', data[:2])[0]
                self.packet_logger.info(f"IMEI length field: {imei_length}")
                if len(data) >= 2 + imei_length:
                    imei = data[2:2+imei_length].decode('ascii', errors='ignore')
                    self.packet_logger.info(f"IMEI: {imei}")
                else:
                    self.packet_logger.warning(f"IMEI packet too short. Expected {2 + imei_length}, got {len(data)}")
            else:
                self.packet_logger.warning("IMEI packet too short for length field")
        
        elif packet_type == "AVL_DATA":
            if len(data) >= 10:
                # Analyze AVL packet structure
                preamble = data[:4]
                data_length = struct.unpack('!I', data[4:8])[0] if len(data) >= 8 else 0
                codec_id = data[8] if len(data) > 8 else 0
                num_records = data[9] if len(data) > 9 else 0
                
                self.packet_logger.info(f"Preamble: {preamble.hex()} (should be 00000000)")
                self.packet_logger.info(f"Data length: {data_length}")
                self.packet_logger.info(f"Codec ID: 0x{codec_id:02X}")
                self.packet_logger.info(f"Number of records: {num_records}")
                
                # Show detailed breakdown of packet structure
                if len(data) > 10:
                    self.packet_logger.info("Packet breakdown:")
                    self.packet_logger.info(f"  Bytes 0-3 (Preamble): {data[0:4].hex()}")
                    self.packet_logger.info(f"  Bytes 4-7 (Data Length): {data[4:8].hex()}")
                    self.packet_logger.info(f"  Byte 8 (Codec ID): {data[8:9].hex()}")
                    self.packet_logger.info(f"  Byte 9 (Num Records): {data[9:10].hex()}")
                    
                    if len(data) > 10:
                        remaining = data[10:]
                        self.packet_logger.info(f"  Remaining data ({len(remaining)} bytes): {remaining.hex()}")
                        
                        # Try to parse first record structure if available
                        if len(remaining) >= 25:  # Minimum for timestamp + priority + GPS start
                            timestamp_bytes = remaining[0:8]
                            priority_byte = remaining[8:9]
                            gps_start = remaining[9:24] if len(remaining) >= 24 else remaining[9:]
                            
                            timestamp = struct.unpack('!Q', timestamp_bytes)[0]
                            priority = priority_byte[0]
                            
                            self.packet_logger.info(f"  First Record Analysis:")
                            self.packet_logger.info(f"    Timestamp bytes: {timestamp_bytes.hex()} = {timestamp}")
                            self.packet_logger.info(f"    Priority: {priority}")
                            self.packet_logger.info(f"    GPS data start: {gps_start.hex()}")
                            
                            # Convert timestamp to readable format
                            try:
                                egypt_tz = timezone(timedelta(hours=3))
                                dt = datetime.fromtimestamp(timestamp / 1000.0, tz=egypt_tz)
                                self.packet_logger.info(f"    Timestamp: {dt.isoformat()}")
                            except:
                                self.packet_logger.info(f"    Invalid timestamp: {timestamp}")
                                
                            # Try to decode IO data for Codec8 Extended
                            if codec_id == 0x8E and len(remaining) >= 30:
                                self.packet_logger.info(f"  IO Data Analysis (Codec8 Extended):")
                                io_start = 24  # After timestamp(8) + priority(1) + GPS(15)
                                if len(remaining) > io_start + 4:
                                    try:
                                        event_io_id = struct.unpack('!H', remaining[io_start:io_start+2])[0]
                                        n_total_io = struct.unpack('!H', remaining[io_start+2:io_start+4])[0]
                                        self.packet_logger.info(f"    Event IO ID: {event_io_id}")
                                        self.packet_logger.info(f"    Total IO elements: {n_total_io}")
                                        
                                        # Try to parse some IO elements
                                        io_offset = io_start + 4
                                        if len(remaining) > io_offset + 2:
                                            n1 = struct.unpack('!H', remaining[io_offset:io_offset+2])[0]
                                            self.packet_logger.info(f"    1-byte IO elements: {n1}")
                                            io_offset += 2
                                            
                                            # Parse some 1-byte elements
                                            for i in range(min(n1, 10)):  # Show first 10 elements
                                                if len(remaining) >= io_offset + 3:
                                                    io_id = struct.unpack('!H', remaining[io_offset:io_offset+2])[0]
                                                    io_value = remaining[io_offset + 2]
                                                    self.packet_logger.info(f"      IO{io_id}: {io_value}")
                                                    io_offset += 3
                                                else:
                                                    break
                                    except:
                                        self.packet_logger.info(f"    Could not parse IO data")
            else:
                self.packet_logger.warning("AVL packet too short for basic analysis")
        
        # Show byte-by-byte analysis for small packets
        if len(data) <= 50:
            byte_analysis = []
            for i, byte in enumerate(data):
                byte_analysis.append(f"[{i:2d}] 0x{byte:02X} ({byte:3d}) '{chr(byte) if 32 <= byte <= 126 else '.'}'")
            self.packet_logger.info("Byte-by-byte analysis:")
            for line in byte_analysis:
                self.packet_logger.info(f"  {line}")
        
        self.packet_logger.info("=== END PACKET ANALYSIS ===\n")
    
    def handle_imei(self, client_socket, data, client_address):
        """Handle IMEI authentication"""
        try:
            # Analyze IMEI packet in detail
            self.analyze_packet_details(data, "IMEI", client_address)
            
            imei_length = struct.unpack('!H', data[:2])[0]
            
            if len(data) < 2 + imei_length:
                self.logger.warning(f"Invalid IMEI packet from {client_address}")
                return False
                
            imei = data[2:2+imei_length].decode('ascii')
            self.logger.info(f"Device IMEI: {imei} from {client_address}")
            
            # Accept the device (send 0x01)
            client_socket.send(b'\x01')
            self.logger.info(f"IMEI {imei} accepted")
            
            # Log IMEI acceptance
            self.log_device_event(imei, "IMEI_ACCEPTED", client_address)
            
            return imei
            
        except Exception as e:
            self.logger.error(f"Error handling IMEI from {client_address}: {e}")
            client_socket.send(b'\x00')
            return False
    
    def parse_gps_element(self, data, offset):
        """Parse GPS element from AVL data"""
        try:
            # Check how much data we actually have from the offset
            available_bytes = len(data) - offset
            
            self.logger.debug(f"GPS parsing: offset={offset}, available_bytes={available_bytes}, total_data_len={len(data)}")
            
            if available_bytes < 15:
                self.logger.warning(f"GPS data incomplete. Need 15 bytes, have {available_bytes} bytes.")
                
                # For incomplete GPS data, try to parse what we have
                if available_bytes >= 13:
                    # Try parsing with reduced format (missing last 2 bytes for speed)
                    gps_bytes = data[offset:offset+13]
                    self.logger.debug(f"Parsing {len(gps_bytes)} GPS bytes: {gps_bytes.hex()}")
                    
                    # Parse without speed field: Longitude(4) + Latitude(4) + Altitude(2) + Angle(2) + Satellites(1)
                    longitude, latitude, altitude, angle, satellites = struct.unpack('!IIHHB', gps_bytes)
                    speed = 0  # Default speed when not available
                elif available_bytes >= 8:
                    # Minimal GPS data - just coordinates
                    gps_bytes = data[offset:offset+8]
                    self.logger.debug(f"Parsing minimal {len(gps_bytes)} GPS bytes: {gps_bytes.hex()}")
                    longitude, latitude = struct.unpack('!II', gps_bytes)
                    altitude = 0
                    angle = 0
                    satellites = 0
                    speed = 0
                else:
                    self.logger.error(f"GPS data too short: only {available_bytes} bytes available")
                    return None
            else:
                # Normal parsing with full 15 bytes
                gps_bytes = data[offset:offset+15]
                self.logger.debug(f"Parsing full {len(gps_bytes)} GPS bytes: {gps_bytes.hex()}")
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
            
        except struct.error as e:
            self.logger.error(f"GPS struct unpack error: {e}")
            self.logger.error(f"Data length: {len(data)}, Offset: {offset}, Available: {len(data) - offset}")
            if offset < len(data):
                remaining_data = data[offset:offset+20] if len(data) >= offset+20 else data[offset:]
                self.logger.error(f"Remaining data: {remaining_data.hex()}")
            return None
        except Exception as e:
            self.logger.error(f"GPS parsing error: {e}")
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
            
        except Exception as e:
            self.logger.error(f"Error parsing IO element: {e}")
            return None, offset
    
    def parse_codec8(self, data, imei):
        """Parse Codec8 protocol data"""
        try:
            preamble = data[:4]
            data_field_length = struct.unpack('!I', data[4:8])[0]
            codec_id = data[8]
            num_data_1 = data[9]
            
            self.logger.info(f"Codec8 - IMEI: {imei}, Records: {num_data_1}, Data Length: {data_field_length}")
            
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
            
        except Exception as e:
            self.logger.error(f"Error parsing Codec8 data: {e}")
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
            
        except Exception as e:
            self.logger.error(f"Error parsing IO element: {e}")
            return None, offset
    
    def parse_codec8_extended(self, data, imei):
        """Parse Codec8 Extended protocol data"""
        try:
            preamble = data[:4]
            data_field_length = struct.unpack('!I', data[4:8])[0]
            codec_id = data[8]
            num_data_1 = data[9]
            
            self.logger.info(f"Codec8 Extended - IMEI: {imei}, Records: {num_data_1}, Data Length: {data_field_length}")
            
            offset = 10
            records = []
            
            for i in range(num_data_1):
                self.logger.debug(f"Processing record {i+1} at offset {offset}")
                
                # Parse timestamp (8 bytes)
                if offset + 8 > len(data):
                    self.logger.error(f"Not enough data for timestamp at offset {offset}")
                    break
                    
                timestamp = struct.unpack('!Q', data[offset:offset+8])[0]
                # Convert to Egypt timezone (UTC+3)
                egypt_tz = timezone(timedelta(hours=3))
                dt = datetime.fromtimestamp(timestamp / 1000.0, tz=egypt_tz)
                
                # Parse priority (1 byte)
                if offset + 9 > len(data):
                    self.logger.error(f"Not enough data for priority at offset {offset+8}")
                    break
                priority = data[offset + 8]
                
                self.logger.debug(f"Timestamp: {dt}, Priority: {priority}")
                
                # Parse GPS element (15 bytes) - but check available data first
                gps_offset = offset + 9
                available_gps_bytes = len(data) - gps_offset
                self.logger.debug(f"GPS offset: {gps_offset}, available bytes: {available_gps_bytes}")
                
                # Add detailed GPS analysis
                self.analyze_gps_structure(data, gps_offset)
                
                if available_gps_bytes >= 15:
                    gps_data = self.parse_gps_element(data, gps_offset)
                    # If normal parsing fails, try extraction method
                    if gps_data is None:
                        gps_data = self.extract_gps_coordinates(data, gps_offset)
                        if gps_data:
                            self.logger.info(f"✅ GPS coordinates extracted successfully using fallback method")
                    io_offset = gps_offset + 15
                else:
                    self.logger.warning(f"Insufficient GPS data: need 15 bytes, have {available_gps_bytes}")
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
                    
                    # Decode and log all parameters
                    if io_data and 'io_data' in io_data:
                        decoded_params, unknown_params = self.decode_io_parameters(io_data['io_data'])
                        
                        self.logger.info(f"🚗 CAR PARAMETERS for {imei}:")
                        for param in decoded_params:
                            self.logger.info(f"   ✅ {param}")
                        
                        if unknown_params:
                            self.logger.info(f"   🔍 UNKNOWN PARAMETERS:")
                            for param in unknown_params:
                                self.logger.info(f"   ❓ {param}")
                        
                        # Log to packet details for analysis
                        self.packet_logger.info(f"DECODED PARAMETERS for {imei}:")
                        for param in decoded_params + unknown_params:
                            self.packet_logger.info(f"  {param}")
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
                    self.logger.warning("Parser offset not advancing, breaking loop")
                    break
            
            return records, num_data_1
            
        except Exception as e:
            self.logger.error(f"Error parsing Codec8 Extended data: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
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
                
        except Exception as e:
            self.logger.error(f"Error parsing Codec12 data: {e}")

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
            
        except Exception as e:
            self.logger.error(f"Error creating Codec12 response: {e}")
            return None
    
    def log_gps_data(self, imei, timestamp, gps_data, io_data):
        """Log GPS data to file and console"""
        if gps_data:
            # Create GPS log entry
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
            
            # Log to console
            self.logger.info(f"🚗 {imei} - {timestamp.strftime('%H:%M:%S')} - GPS: {gps_data['latitude']:.6f}, {gps_data['longitude']:.6f}")
            
            # Log IO data if available
            if io_data and io_data['io_data']:
                io_info = []
                for io_id, value in io_data['io_data'].items():
                    if io_id == 1:
                        io_info.append(f"DIN1: {value}")
                    elif io_id == 21:
                        io_info.append(f"Signal: {value}")
                    elif io_id == 66:
                        io_info.append(f"Voltage: {value/1000:.1f}V")
                    elif io_id == 239:
                        io_info.append(f"Ignition: {'ON' if value else 'OFF'}")
                    else:
                        io_info.append(f"IO{io_id}: {value}")
                
                if io_info:
                    self.logger.info(f"   📊 {', '.join(io_info)}")
        else:
            self.logger.warning(f"No valid GPS data for {imei}")
    
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
                self.logger.warning("Data packet too short")
                # Analyze short packets too
                self.analyze_packet_details(data, "AVL_DATA_SHORT", imei)
                return
            
            # Analyze AVL packet in detail
            self.analyze_packet_details(data, "AVL_DATA", imei)
            
            # Check preamble
            preamble = data[:4]
            if preamble != b'\x00\x00\x00\x00':
                self.logger.warning("Invalid preamble")
                return
            
            # Get codec ID
            codec_id = data[8]
            
            records = None
            num_records = 0
            
            if codec_id == 0x08:  # Codec8
                self.logger.info("Processing Codec8 data...")
                records, num_records = self.parse_codec8(data, imei)
                
            elif codec_id == 0x8E:  # Codec8 Extended
                self.logger.info("Processing Codec8 Extended data...")
                records, num_records = self.parse_codec8_extended(data, imei)
                
            elif codec_id == 0x10:  # Codec16
                self.logger.info("Processing Codec16 data...")
                records, num_records = self.parse_codec8(data, imei)  # Similar to Codec8
                
            elif codec_id == 0x0C:  # Codec12
                self.logger.info("Processing Codec12 data...")
                response = self.parse_codec12(data, imei)
                if response:
                    client_socket.send(response)
                return
                
            else:
                self.logger.warning(f"Unsupported codec ID: 0x{codec_id:02X}")
                return
            
            # Send acknowledgment for AVL data
            if num_records > 0:
                ack = struct.pack('!I', num_records)
                client_socket.send(ack)
                self.logger.info(f"Sent acknowledgment for {num_records} records to {imei}")
            
        except Exception as e:
            self.logger.error(f"Error handling AVL data: {e}")
            # Analyze problematic packets
            self.analyze_packet_details(data, "AVL_DATA_ERROR", imei)
    
    def handle_client(self, client_socket, client_address):
        """Handle individual client connection"""
        self.logger.info(f"New connection from {client_address}")
        imei = None
        
        try:
            # First, expect IMEI
            imei_data = client_socket.recv(1024)
            if imei_data:
                self.logger.debug(f"Received IMEI data ({len(imei_data)} bytes): {imei_data.hex()}")
                imei = self.handle_imei(client_socket, imei_data, client_address)
                if not imei:
                    return
            
            # Then handle AVL data packets
            while self.running:
                data = client_socket.recv(2048)
                if not data:
                    break
                
                self.logger.debug(f"Received {len(data)} bytes from {imei}: {data.hex()}")
                self.handle_avl_data(client_socket, data, imei)
                
        except Exception as e:
            self.logger.error(f"Error handling client {client_address}: {e}")
        finally:
            client_socket.close()
            if imei:
                self.logger.info(f"Connection closed: {imei} ({client_address})")
                self.log_device_event(imei, "DISCONNECTED", client_address)
    
    def start_server(self):
        """Start the TCP server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.config['host'], self.config['port']))
            self.server_socket.listen(10)
            
            self.logger.info(f"🚀 Teltonika Service started on {self.config['host']}:{self.config['port']}")
            self.logger.info(f"📁 Logs: {self.config['log_dir']}")
            self.logger.info(f"💾 Data: {self.config['data_dir']}")
            
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
                    
                except socket.error as e:
                    if self.running:
                        self.logger.error(f"Socket error: {e}")
                
        except Exception as e:
            self.logger.error(f"Server error: {e}")
        finally:
            self.stop_server()
    
    def stop_server(self):
        """Stop the server gracefully"""
        self.logger.info("Stopping Teltonika Service...")
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        self.logger.info("Teltonika Service stopped")
    
    def signal_handler(self, signum, frame):
        """Handle system signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop_server()
        sys.exit(0)

    def decode_io_parameters(self, io_data):
        """Decode and explain IO parameters from Teltonika devices"""
        
        # Known IO parameter meanings for Teltonika devices
        io_meanings = {
            # Digital Inputs (common for physical inputs)
            1: "Digital Input 1",
            2: "Digital Input 2",
            3: "Digital Input 3",
            4: "Digital Input 4",

            # Analog Inputs (measure voltage)
            9: "Analog Input 1 (mV)",
            10: "Analog Input 2 (mV)",
            11: "Analog Input 3 (mV)",
            12: "Analog Input 4 (mV)",

            # Vehicle/Device Status Data
            21: "GSM Signal Strength", # Typically 0-5
            24: "Speed (km/h)", # GNSS-derived speed
            66: "External Voltage (mV)", # Main power supply
            67: "Internal Battery Voltage (mV)", # Device's internal backup battery
            69: "GNSS Status", # E.g., 0=Off, 3=Working (has fix)
            72: "Dallas Temperature 1 (°C)", # Multiplied by 10 (e.g., 250 for 25°C)
            73: "Dallas Temperature 2 (°C)",
            74: "Dallas Temperature 3 (°C)",
            75: "Dallas Temperature 4 (°C)",
            78: "iButton ID",
            80: "Data Mode", # E.g., 0=Home On Stop, 1=Home On Moving
            113: "Internal Battery Level (%)", # Percentage of internal battery charge

            # Engine/OBD Data (requires OBD-II dongle/integration)
            179: "Engine RPM (OBD)",
            180: "Vehicle Speed (OBD)", # From OBD-II, potentially more accurate than GNSS speed at low speeds
            181: "Fuel Level (OBD) (%)",
            182: "Engine Coolant Temperature (OBD)",
            183: "Engine Load (OBD) (%)",
            184: "Manifold Absolute Pressure (OBD)",
            185: "Throttle Position (OBD) (%)",
            186: "Fuel Rate (OBD) (L/h)",
            187: "Total Mileage (OBD) (km)",
            188: "Fuel Consumption (OBD) (L/100km)",

            # Core Status Parameters
            239: "Ignition Status", # 0=Off, 1=On
            240: "Movement Status", # 0=Not Moving, 1=Moving (based on accelerometer)
            241: "Active GSM Operator",

            # Digital Outputs (for controlling external devices)
            216: "Digital Output 1",
            217: "Digital Output 2",

            # CAN Bus Data (requires specific CAN adapter and vehicle support)
            385: "CAN Speed (km/h)",
            386: "CAN RPM",
            387: "CAN Fuel Level (%)",

            # Extended Parameters (Green Driving, Security, Trip)
            389: "Harsh Acceleration",
            390: "Harsh Braking",
            391: "Harsh Cornering",
            392: "Crash Detection",
            393: "Jamming Detection",
            394: "Trip Distance (m)", # Often distance of current trip segment
            395: "Overspeeding",

            # Vehicle specific / Advanced CAN data (highly dependent on model, CAN adapter, and vehicle)
            400: "Door Status",
            401: "Window Status",
            402: "Lights Status",
            403: "Air Conditioning Status",
            404: "Seat Belt Status",
            405: "Emergency Button", # Often a specific Digital Input used for this function
            
            # Additional common parameters
            68: "Battery Current (mA)",
            14: "OBD Diagnostic Trouble Codes",
            16: "Total Distance (m)",
            380: "BLE Sensor Data",
        }
        
        decoded_params = []
        unknown_params = []
        
        for io_id, value in io_data.items():
            if io_id in io_meanings:
                param_name = io_meanings[io_id]
                
                # Format values based on parameter type
                if io_id in [66, 67]:  # Voltage in mV
                    formatted_value = f"{value/1000:.2f}V"
                elif io_id in [9, 10, 11, 12]:  # Analog inputs in mV
                    formatted_value = f"{value}mV"
                elif io_id == 113:  # Battery percentage
                    formatted_value = f"{value}%"
                elif io_id == 21:  # Signal strength (0-5 scale)
                    formatted_value = f"{value}/5"
                elif io_id in [24, 180, 385]:  # Speed in km/h
                    formatted_value = f"{value} km/h"
                elif io_id in [179, 386]:  # RPM
                    formatted_value = f"{value} RPM"
                elif io_id in [181, 183, 185, 387]:  # Percentages (fuel, engine load, throttle, CAN fuel)
                    formatted_value = f"{value}%"
                elif io_id in [72, 73, 74, 75]:  # Dallas temperature (multiplied by 10)
                    formatted_value = f"{value/10:.1f}°C"
                elif io_id == 182:  # OBD Coolant temperature (offset by 40)
                    formatted_value = f"{value-40}°C"
                elif io_id == 186:  # Fuel rate L/h
                    formatted_value = f"{value} L/h"
                elif io_id in [187, 394]:  # Distance/mileage
                    if io_id == 187:  # Total mileage in km
                        formatted_value = f"{value} km"
                    else:  # Trip distance in meters
                        formatted_value = f"{value} m"
                elif io_id == 16:  # Total distance in meters
                    formatted_value = f"{value/1000:.1f} km"
                elif io_id == 68:  # Battery current in mA
                    formatted_value = f"{value}mA"
                elif io_id == 188:  # Fuel consumption
                    formatted_value = f"{value} L/100km"
                elif io_id == 69:  # GNSS Status
                    gnss_status = {0: "Off", 1: "No Fix", 2: "2D Fix", 3: "3D Fix"}
                    formatted_value = gnss_status.get(value, f"Unknown({value})")
                elif io_id == 80:  # Data Mode
                    data_mode = {0: "Home On Stop", 1: "Home On Moving"}
                    formatted_value = data_mode.get(value, f"Mode {value}")
                elif io_id == 239:  # Ignition
                    formatted_value = "ON" if value else "OFF"
                elif io_id == 240:  # Movement
                    formatted_value = "Moving" if value else "Stopped"
                elif io_id in [1, 2, 3, 4, 216, 217]:  # Digital inputs/outputs
                    formatted_value = "HIGH" if value else "LOW"
                elif io_id in [389, 390, 391, 392, 393, 395]:  # Event flags
                    formatted_value = "DETECTED" if value else "Normal"
                elif io_id in [400, 401, 402, 403, 404, 405]:  # Vehicle status
                    formatted_value = "ACTIVE" if value else "Inactive"
                else:
                    formatted_value = str(value)
                    
                decoded_params.append(f"IO{io_id:03d}: {param_name} = {formatted_value}")
            else:
                unknown_params.append(f"IO{io_id:03d}: Unknown parameter = {value}")
        
        return decoded_params, unknown_params

    def analyze_gps_structure(self, data, offset):
        """Analyze GPS data structure from actual packet"""
        try:
            available_bytes = len(data) - offset
            self.packet_logger.info(f"GPS Structure Analysis at offset {offset}:")
            self.packet_logger.info(f"Available bytes: {available_bytes}")
            
            if available_bytes >= 15:
                gps_bytes = data[offset:offset+15]
                self.packet_logger.info(f"Full GPS data (15 bytes): {gps_bytes.hex()}")
                
                # Byte-by-byte breakdown
                self.packet_logger.info("GPS byte breakdown:")
                for i, byte in enumerate(gps_bytes):
                    self.packet_logger.info(f"  GPS[{i:2d}]: 0x{byte:02X} ({byte:3d})")
                
                # Try different interpretations
                self.packet_logger.info("Interpretation attempts:")
                
                # Standard Teltonika GPS format
                try:
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
                    
                    self.packet_logger.info(f"  Standard format:")
                    self.packet_logger.info(f"    Longitude: {longitude_raw} -> {longitude_deg}°")
                    self.packet_logger.info(f"    Latitude: {latitude_raw} -> {latitude_deg}°")
                    self.packet_logger.info(f"    Altitude: {altitude_raw} m")
                    self.packet_logger.info(f"    Angle: {angle_raw}°")
                    self.packet_logger.info(f"    Satellites: {satellites_raw}")
                    self.packet_logger.info(f"    Speed: {speed_raw} km/h")
                    
                except Exception as e:
                    self.packet_logger.info(f"  Standard format failed: {e}")
                
            else:
                gps_bytes = data[offset:offset+available_bytes]
                self.packet_logger.info(f"Partial GPS data ({available_bytes} bytes): {gps_bytes.hex()}")
                
        except Exception as e:
            self.packet_logger.error(f"GPS structure analysis failed: {e}")
            
        return None

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
        except Exception as e:
            self.logger.debug(f"GPS extraction failed: {e}")
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
        service.logger.info("Service interrupted by user")
        service.stop_server()

if __name__ == "__main__":
    main() 