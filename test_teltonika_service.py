#!/usr/bin/env python3
"""
Test script for Teltonika Service on port 5000
Simulates real Teltonika device communication with GPS data
"""

import socket
import struct
import time
import threading
import random
from datetime import datetime, timezone, timedelta


class TeltonikaDeviceSimulator:
    def __init__(self, imei, server_host='127.0.0.1', server_port=5000):
        self.imei = imei
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.connected = False
        
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
    
    def connect(self):
        """Connect to Teltonika service and send IMEI"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            
            # Send IMEI packet
            imei_bytes = self.imei.encode('ascii')
            imei_packet = struct.pack('!H', len(imei_bytes)) + imei_bytes
            self.socket.send(imei_packet)
            
            # Wait for acceptance (should receive 0x01)
            response = self.socket.recv(1)
            if response == b'\x01':
                print(f"✅ Device {self.imei} connected and IMEI accepted")
                self.connected = True
                return True
            else:
                print(f"❌ Device {self.imei} IMEI rejected")
                return False
                
        except Exception as e:
            print(f"❌ Connection failed for {self.imei}: {e}")
            return False
    
    def create_gps_record(self, lat, lon, timestamp=None, speed=0, angle=0, altitude=100, satellites=8):
        """Create a GPS record with realistic data"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        # Convert to Teltonika timestamp (milliseconds since epoch)
        teltonika_timestamp = int(timestamp.timestamp() * 1000)
        
        # Convert coordinates to Teltonika format (degrees * 10^7)
        lat_raw = int(lat * 10000000)
        lon_raw = int(lon * 10000000)
        
        # Handle negative coordinates using two's complement
        if lat_raw < 0:
            lat_raw = 0x100000000 + lat_raw
        if lon_raw < 0:
            lon_raw = 0x100000000 + lon_raw
        
        return {
            'timestamp': teltonika_timestamp,
            'priority': random.choice([0, 1, 2]),
            'longitude': lon_raw,
            'latitude': lat_raw,
            'altitude': altitude,
            'angle': angle,
            'satellites': satellites,
            'speed': speed
        }
    
    def create_io_data(self, ignition=True, movement=True, gsm_signal=4):
        """Create realistic IO data"""
        io_data = {
            # Core status
            239: 1 if ignition else 0,  # Ignition
            240: 1 if movement else 0,  # Movement
            21: gsm_signal,  # GSM Signal (0-5)
            69: 3,  # GNSS Status (3D Fix)
            
            # Power and battery
            66: random.randint(11000, 14500),  # External voltage (mV)
            67: random.randint(3600, 4200),    # Battery voltage (mV)
            113: random.randint(80, 100),      # Battery level (%)
            68: random.randint(-100, 500),     # Battery current (mA)
            
            # Vehicle data
            16: random.randint(100000, 999999),  # Total odometer
            100: 1,  # Program number
            
            # Digital I/O
            1: random.choice([0, 1]),   # Digital Input 1
            179: 0,                     # Digital Output 1
            180: 1 if ignition else 0,  # Digital Output 2 (linked to ignition)
            
            # GNSS quality
            181: random.randint(10, 30),  # GNSS PDOP
            182: random.randint(5, 15),   # GNSS HDOP
            
            # GSM/Cellular
            241: 62001,  # Active GSM operator
            
            # Door status (bit field)
            90: random.randint(0, 15),  # Door status
        }
        
        return io_data
    
    def create_codec8_packet(self, gps_records):
        """Create Codec8 AVL data packet"""
        try:
            packet = bytearray()
            
            # Preamble (4 bytes)
            packet.extend(b'\x00\x00\x00\x00')
            
            # Data field length placeholder (will be calculated later)
            data_start = len(packet) + 4
            packet.extend(b'\x00\x00\x00\x00')
            
            # Codec ID (1 byte)
            packet.append(0x08)  # Codec8
            
            # Number of data records (1 byte)
            num_records = len(gps_records)
            packet.append(num_records)
            
            # Data records
            for record in gps_records:
                # Timestamp (8 bytes)
                packet.extend(struct.pack('!Q', record['timestamp']))
                
                # Priority (1 byte)
                packet.append(record['priority'])
                
                # GPS element (15 bytes)
                packet.extend(struct.pack('!I', record['longitude']))
                packet.extend(struct.pack('!I', record['latitude']))
                packet.extend(struct.pack('!H', record['altitude']))
                packet.extend(struct.pack('!H', record['angle']))
                packet.append(record['satellites'])
                packet.extend(struct.pack('!H', record['speed']))
                
                # IO element
                io_data = record.get('io_data', {})
                
                # Event IO ID (1 byte)
                packet.append(record.get('event_io_id', 0))
                
                # Separate IO data by value size, filter only valid IDs for Codec8
                io_1byte = {}
                io_2byte = {}
                io_4byte = {}
                
                for io_id, value in io_data.items():
                    # Only use IO IDs that fit in Codec8 format (0-255)
                    if not isinstance(io_id, int) or io_id > 255 or not isinstance(value, int):
                        continue
                        
                    if 0 <= value <= 255:
                        io_1byte[io_id] = value
                    elif 256 <= value <= 65535:
                        io_2byte[io_id] = value
                    elif value > 65535:
                        io_4byte[io_id] = value
                
                # Total IO count (1 byte)
                total_io_count = len(io_1byte) + len(io_2byte) + len(io_4byte)
                packet.append(total_io_count)
                
                # 1-byte IO elements
                packet.append(len(io_1byte))
                for io_id, value in io_1byte.items():
                    packet.append(io_id)
                    packet.append(value)
                
                # 2-byte IO elements
                packet.append(len(io_2byte))
                for io_id, value in io_2byte.items():
                    packet.append(io_id)
                    packet.extend(struct.pack('!H', value))
                
                # 4-byte IO elements
                packet.append(len(io_4byte))
                for io_id, value in io_4byte.items():
                    packet.append(io_id)
                    packet.extend(struct.pack('!I', value))
                
                # 8-byte IO elements
                packet.append(0)  # No 8-byte elements
            
            # Number of data records (again, 1 byte)
            packet.append(num_records)
            
            # Calculate and set data field length
            data_length = len(packet) - data_start
            struct.pack_into('!I', packet, 4, data_length)
            
            # Calculate and append CRC
            crc = self.calculate_crc16(packet[8:])  # CRC from codec ID
            packet.extend(struct.pack('!I', crc))
            
            return bytes(packet)
            
        except Exception as e:
            print(f"Error creating Codec8 packet: {e}")
            return None
    
    def send_gps_data(self, coordinates_list, batch_size=5):
        """Send GPS data in batches"""
        if not self.connected:
            print(f"❌ Device {self.imei} not connected")
            return False
        
        total_sent = 0
        
        try:
            for i in range(0, len(coordinates_list), batch_size):
                batch_coords = coordinates_list[i:i + batch_size]
                
                # Create GPS records for this batch
                gps_records = []
                base_time = datetime.now(timezone.utc) - timedelta(minutes=len(batch_coords))
                
                for j, (lat, lon) in enumerate(batch_coords):
                    timestamp = base_time + timedelta(minutes=j)
                    speed = random.randint(0, 80) if j % 5 != 0 else 0  # Stopped every 5th point
                    
                    gps_record = self.create_gps_record(
                        lat=lat, 
                        lon=lon, 
                        timestamp=timestamp,
                        speed=speed,
                        angle=random.randint(0, 359),
                        altitude=random.randint(50, 200),
                        satellites=random.randint(6, 12)
                    )
                    
                    # Add IO data
                    gps_record['io_data'] = self.create_io_data(
                        ignition=(speed > 0),
                        movement=(speed > 0),
                        gsm_signal=random.randint(3, 5)
                    )
                    
                    gps_records.append(gps_record)
                
                # Create and send packet
                packet = self.create_codec8_packet(gps_records)
                if packet:
                    self.socket.send(packet)
                    
                    # Wait for acknowledgment
                    ack = self.socket.recv(4)
                    ack_count = struct.unpack('!I', ack)[0]
                    
                    if ack_count == len(gps_records):
                        total_sent += len(gps_records)
                        print(f"✅ Batch {i//batch_size + 1}: {len(gps_records)} records sent, ACK received")
                    else:
                        print(f"❌ Batch {i//batch_size + 1}: ACK mismatch (sent: {len(gps_records)}, ack: {ack_count})")
                
                # Small delay between batches
                time.sleep(0.1)
            
            print(f"📊 Device {self.imei}: {total_sent}/{len(coordinates_list)} records sent successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error sending GPS data for {self.imei}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from service"""
        if self.socket:
            self.socket.close()
            self.connected = False
            print(f"🔌 Device {self.imei} disconnected")


def generate_cairo_route(num_points=100):
    """Generate a route around Cairo, Egypt"""
    # Cairo city center
    start_lat = 30.0444196
    start_lon = 31.2357116
    
    coordinates = []
    current_lat = start_lat
    current_lon = start_lon
    
    for i in range(num_points):
        # Simulate movement around Cairo with realistic GPS variations
        lat_change = random.uniform(-0.002, 0.002)  # ~200m variation
        lon_change = random.uniform(-0.002, 0.002)
        
        # Add progressive movement (simulating a journey around Cairo)
        if i > 0:
            progress_lat = (i / num_points) * 0.02  # Move 2km over the journey
            progress_lon = (i / num_points) * 0.02
            direction_change = random.uniform(-0.001, 0.001)  # Random direction changes
            
            current_lat = start_lat + progress_lat + lat_change + direction_change
            current_lon = start_lon + progress_lon + lon_change + direction_change
        else:
            current_lat = start_lat + lat_change
            current_lon = start_lon + lon_change
        
        coordinates.append((round(current_lat, 7), round(current_lon, 7)))
    
    return coordinates


def test_single_device(device_count=1, points_per_device=50):
    """Test with a single device"""
    print(f"🚗 Testing single device with {points_per_device} GPS points")
    
    imei = f"86732400100{device_count:04d}"
    device = TeltonikaDeviceSimulator(imei)
    
    if not device.connect():
        return False
    
    # Generate route
    coordinates = generate_cairo_route(points_per_device)
    
    # Send GPS data
    success = device.send_gps_data(coordinates, batch_size=10)
    
    # Keep connection alive for a moment
    time.sleep(1)
    
    device.disconnect()
    return success


def test_multiple_devices(device_count=3, points_per_device=20):
    """Test with multiple devices simultaneously"""
    print(f"🚛 Testing {device_count} devices with {points_per_device} points each")
    
    devices = []
    threads = []
    
    def device_test_worker(device_id):
        imei = f"86732400100{device_id:04d}"
        device = TeltonikaDeviceSimulator(imei)
        devices.append(device)
        
        if device.connect():
            coordinates = generate_cairo_route(points_per_device)
            device.send_gps_data(coordinates, batch_size=5)
            time.sleep(2)  # Keep alive
            device.disconnect()
    
    # Start all devices
    for i in range(device_count):
        thread = threading.Thread(target=device_test_worker, args=(i+1,))
        threads.append(thread)
        thread.start()
        time.sleep(0.5)  # Stagger connections
    
    # Wait for all devices to complete
    for thread in threads:
        thread.join()
    
    print(f"✅ All {device_count} devices completed testing")


def test_service_availability():
    """Test if Teltonika service is running"""
    print("🔍 Testing Teltonika service availability...")
    
    try:
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(5)
        result = test_socket.connect_ex(('127.0.0.1', 5000))
        test_socket.close()
        
        if result == 0:
            print("✅ Teltonika service is running on port 5000")
            return True
        else:
            print("❌ Teltonika service is not running on port 5000")
            return False
            
    except Exception as e:
        print(f"❌ Error testing service: {e}")
        return False


def main():
    """Main testing function"""
    print("🚀 Teltonika Service Testing")
    print("=" * 50)
    
    # Test service availability
    if not test_service_availability():
        print("\n💡 To start the service, run:")
        print("   python teltonika_service.py")
        return
    
    print("\n📊 Starting GPS device simulation tests...")
    
    # Test 1: Single device with moderate data
    print("\n" + "─" * 50)
    print("TEST 1: Single Device (50 GPS points)")
    test_single_device(device_count=1, points_per_device=50)
    
    # Wait a moment
    time.sleep(2)
    
    # Test 2: Multiple devices
    print("\n" + "─" * 50)
    print("TEST 2: Multiple Devices (3 devices, 20 points each)")
    test_multiple_devices(device_count=3, points_per_device=20)
    
    # Wait a moment
    time.sleep(2)
    
    # Test 3: High volume single device
    print("\n" + "─" * 50)
    print("TEST 3: High Volume Single Device (200 GPS points)")
    test_single_device(device_count=1, points_per_device=200)
    
    print("\n🎉 All Teltonika service tests completed!")
    print("\n📋 Check the service logs to see the received data:")
    print("   - Service console output")
    print("   - Log files in /var/log/teltonika/ (if running as service)")
    print("   - Django admin: http://localhost:8000/admin/gps_data/gpsrecord/")


if __name__ == "__main__":
    main() 