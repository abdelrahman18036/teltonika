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
import requests
import json
from datetime import datetime, timezone, timedelta


def test_command_api():
    """Test the command API functionality"""
    print("🔧 Testing Command API functionality...")
    
    try:
        # Test API health check
        response = requests.get('http://localhost:5001/health', timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Command API is healthy: {health_data['connected_devices']} devices connected")
        else:
            print("❌ Command API health check failed")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Command API not available on port 5001")
        return False
    except Exception as e:
        print(f"❌ Error testing command API: {e}")
        return False
    
    return True


def test_device_commands(imei):
    """Test sending commands to a specific device"""
    print(f"📱 Testing commands for device {imei}...")
    
    # Commands to test (both Digital Output and CAN Control streams)
    test_commands = [
        {'type': 'digital_output', 'name': 'lock', 'text': 'setdigout 1?? 2??'},
        {'type': 'digital_output', 'name': 'unlock', 'text': 'setdigout ?1? ?2?'},
        {'type': 'digital_output', 'name': 'immobilize', 'text': 'setdigout ??0'},
        {'type': 'digital_output', 'name': 'mobilize', 'text': 'setdigout ??1'},
        {'type': 'can_control', 'name': 'lock', 'text': 'lvcanlockalldoors'},
        {'type': 'can_control', 'name': 'unlock', 'text': 'lvcanopenalldoors'},
        {'type': 'can_control', 'name': 'immobilize', 'text': 'lvcanblockengine'},
        {'type': 'can_control', 'name': 'mobilize', 'text': 'lvcanunblockengine'},
    ]
    
    success_count = 0
    
    for cmd in test_commands:
        try:
            print(f"  📤 Sending {cmd['type']} - {cmd['name']}: {cmd['text']}")
            
            # Send command via HTTP API
            response = requests.post('http://localhost:5001/send_command', json={
                'imei': imei,
                'command': cmd['text'],
                'command_id': f"test_{int(time.time())}_{cmd['name']}"
            }, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                print(f"    ✅ {result['message']}")
                success_count += 1
            else:
                print(f"    ❌ Failed: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
        
        # Small delay between commands
        time.sleep(1)
    
    print(f"📊 Command Test Results: {success_count}/{len(test_commands)} commands sent successfully")
    return success_count == len(test_commands)


def test_django_command_api():
    """Test the Django API for sending commands"""
    print("🐍 Testing Django Command API...")
    
    test_imei = "867324001001001"  # Use a test IMEI
    
    try:
        # Test sending a command via Django API
        response = requests.post(f'http://localhost:8000/api/devices/{test_imei}/commands/', json={
            'command_type': 'digital_output',
            'command_name': 'lock'
        }, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Django command API: {result['message']}")
            command_id = result.get('command_id')
            
            # Check command status
            if command_id:
                time.sleep(1)
                status_response = requests.get(f'http://localhost:8000/api/commands/{command_id}/', timeout=5)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"  📊 Command status: {status_data['command']['status']}")
                
            return True
        else:
            print(f"❌ Django command API failed: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Django API not available on port 8000")
        return False
    except Exception as e:
        print(f"❌ Error testing Django API: {e}")
        return False


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
            
            # Speed data (both GPS and CAN)
            24: random.randint(0, 80) if movement else 0,  # Speed (GPS)
            81: random.randint(0, 85) if movement else 0,  # Vehicle Speed (CAN)
            
            # Vehicle CAN/OBD data
            82: random.randint(0, 100) if movement else 0,  # Accelerator Pedal Position %
            85: random.randint(800, 3500) if ignition else 0,  # Engine RPM (CAN)
            87: random.randint(24800000, 24810000),  # Total Mileage (CAN) in meters
            89: random.randint(20, 80),  # Fuel Level (CAN) %
            105: random.randint(18070000, 18080000),  # Total Mileage Counted in meters
            
            # Security State Flags (IO132) - 64-bit value with byte 3 containing flags
            132: self.create_security_flags(ignition, movement),
            
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
    
    def create_security_flags(self, ignition=True, movement=True):
        """Create realistic security state flags (IO132)"""
        # Build byte 3 (bits 16-23) with security flags
        byte3 = 0
        
        # Key in ignition (bit 0)
        if ignition:
            byte3 |= 0x01
            
        # Ignition on (bit 1) 
        if ignition:
            byte3 |= 0x02
            
        # Dynamic ignition on (bit 2) - sometimes active when moving
        if movement and random.choice([True, False]):
            byte3 |= 0x04
            
        # Webasto heater (bit 3) - rarely on
        if random.randint(1, 10) == 1:
            byte3 |= 0x08
            
        # Car locked (bit 4) - usually when not moving
        if not movement and random.choice([True, False]):
            byte3 |= 0x10
            
        # Car locked remote (bit 5) - sometimes when locked
        if not movement and (byte3 & 0x10) and random.choice([True, False]):
            byte3 |= 0x20
            
        # Alarm active (bit 6) - rarely
        if random.randint(1, 20) == 1:
            byte3 |= 0x40
            
        # Immobilizer (bit 7) - sometimes when ignition off
        if not ignition and random.choice([True, False]):
            byte3 |= 0x80
        
        # Create full 64-bit value with flags in byte 3 (bits 16-23)
        security_flags = byte3 << 16
        
        # Add some random data in other bytes to simulate real device
        security_flags |= random.randint(0, 0xFFFF)  # Lower 16 bits
        security_flags |= (random.randint(0, 0xFFFFFFFF) << 24)  # Upper 32 bits
        
        return security_flags
    
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
                    
                    # Determine vehicle state for realistic IO data
                    is_ignition_on = speed > 0 or random.choice([True, False])  # Sometimes ignition on while stopped
                    is_moving = speed > 0
                    
                    gps_record = self.create_gps_record(
                        lat=lat, 
                        lon=lon, 
                        timestamp=timestamp,
                        speed=speed,
                        angle=random.randint(0, 359),
                        altitude=random.randint(50, 200),
                        satellites=random.randint(6, 12)
                    )
                    
                    # Add IO data with realistic vehicle states
                    gps_record['io_data'] = self.create_io_data(
                        ignition=is_ignition_on,
                        movement=is_moving,
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
    print("🚀 Teltonika Service Testing - Command Control Edition")
    print("=" * 70)
    print("📊 Features being tested:")
    print("  ✅ GPS coordinates and navigation data")  
    print("  ✅ Vehicle CAN/OBD data (speed, RPM, fuel, mileage)")
    print("  ✅ Security state flags (ignition, locks, alarm)")
    print("  ✅ Power management and battery data")
    print("  ✅ Digital I/O and sensor data")
    print("  ✅ GSM/GNSS status and quality")
    print("  🆕 Device command sending (Digital Output & CAN Control)")
    print("  🆕 Command history tracking")
    print("")
    
    # Test service availability
    if not test_service_availability():
        print("\n💡 To start the service, run:")
        print("   python teltonika_service.py")
        return
    
    # Test command API availability
    command_api_available = test_command_api()
    
    print("\n📊 Starting GPS device simulation tests...")
    
    # Test 1: Single device with moderate data
    print("\n" + "─" * 70)
    print("TEST 1: Single Device with Enhanced Data (50 GPS points)")
    print("        → Testing all new IO parameters and security flags")
    device_imei = "867324001001001"
    test_single_device(device_count=1, points_per_device=50)
    
    # Test command functionality if API is available
    if command_api_available:
        time.sleep(2)
        print("\n" + "─" * 70)
        print("TEST 4: Command Functionality Testing")
        print("        → Testing Digital Output and CAN Control commands")
        
        # Test commands via direct service API
        test_device_commands(device_imei)
        
        # Test Django command API
        time.sleep(2)
        test_django_command_api()
    
    # Wait a moment
    time.sleep(2)
    
    # Test 2: Multiple devices
    print("\n" + "─" * 70)
    print("TEST 2: Multiple Devices (3 devices, 20 points each)")
    print("        → Testing concurrent device connections")
    test_multiple_devices(device_count=3, points_per_device=20)
    
    # Wait a moment
    time.sleep(2)
    
    # Test 3: High volume single device
    print("\n" + "─" * 70)
    print("TEST 3: High Volume Single Device (200 GPS points)")
    print("        → Testing system performance with large datasets")
    test_single_device(device_count=1, points_per_device=200)
    
    print("\n🎉 All Teltonika service tests completed!")
    print("\n📋 Check the results in:")
    print("   - Service console output (security flags decoded)")
    print("   - Log files in /var/log/teltonika/ (if running as service)")
    print("   - Django admin: http://localhost:8000/admin/gps_data/gpsrecord/")
    print("   - Django admin: http://localhost:8000/admin/gps_data/devicecommand/")
    print("   - API endpoint: http://localhost:8000/api/devices/")
    print("\n💡 GPS Data you'll see:")
    print("   🚗 Vehicle Speed (CAN): IO81")
    print("   🚗 Accelerator Position: IO82") 
    print("   🚗 Engine RPM: IO85")
    print("   🚗 Total Mileage: IO87 (converted to km)")
    print("   🚗 Fuel Level: IO89")
    print("   🚗 Mileage Counter: IO105 (converted to km)")
    print("   🔒 Security Flags: IO132 (decoded as human-readable)")
    print("\n🆕 Command System Features:")
    print("   📱 Digital Output Stream Commands:")
    print("      - Lock: setdigout 1?? 2??")
    print("      - Unlock: setdigout ?1? ?2?")
    print("      - Mobilize: setdigout ??1")
    print("      - Immobilize: setdigout ??0")
    print("   🚗 CAN Control Stream Commands:")
    print("      - Lock: lvcanlockalldoors")
    print("      - Unlock: lvcanopenalldoors")
    print("      - Mobilize: lvcanunblockengine")
    print("      - Immobilize: lvcanblockengine")
    print("\n🔍 In Django Admin:")
    print("   - Check 'Device commands' for command history")
    print("   - Check 'Security' column in GPS records")
    print("   - Check 'Vehicle CAN/OBD Data' section for new fields!")
    print("\n📡 API Endpoints for Commands:")
    print("   POST /api/devices/{imei}/commands/")
    print("   GET  /api/devices/{imei}/commands/")
    print("   GET  /api/commands/{command_id}/")


if __name__ == "__main__":
    main() 