#!/usr/bin/env python3
"""
Test script for Teltonika database integration
"""

import os
import sys
import django
from datetime import datetime, timezone

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teltonika_db.settings')
django.setup()

from tracking.database_manager import db_manager
from tracking.models import Device, TelemetryData


def test_database_integration():
    """Test the database integration functionality"""
    print("🧪 Testing Teltonika Database Integration")
    print("=" * 50)
    
    # Test device creation
    print("\n1. Testing device creation...")
    test_imei = "864636069432371"
    device = db_manager.get_or_create_device(test_imei)
    print(f"✅ Device created/retrieved: {device.imei}")
    
    # Test telemetry data storage
    print("\n2. Testing telemetry data storage...")
    test_data = {
        'timestamp': datetime.now(timezone.utc),
        'gps': {
            'latitude': 30.0444,
            'longitude': 31.2357,
            'altitude': 74,
            'angle': 90,
            'speed': 45,
            'satellites': 8
        },
        'io_data': {
            239: 1,  # Ignition ON
            240: 1,  # Movement
            21: 5,   # GSM Signal
            69: 3,   # GNSS Status
            66: 12860,  # External voltage (mV)
            67: 4200,   # Battery voltage (mV)
            68: 150,    # Battery current (mA)
            113: 85,    # Battery level (%)
            16: 302300  # Total odometer (m)
        },
        'raw_packet': 'test_packet_hex_data'
    }
    
    success = db_manager.store_telemetry_data(test_imei, test_data)
    if success:
        print("✅ Telemetry data stored successfully")
    else:
        print("❌ Failed to store telemetry data")
    
    # Test data retrieval
    print("\n3. Testing data retrieval...")
    retrieved_data = db_manager.get_device_data(test_imei, limit=5)
    print(f"✅ Retrieved {len(retrieved_data)} records")
    
    if retrieved_data:
        latest = retrieved_data[0]
        print(f"   Latest record: {latest['device_timestamp']}")
        print(f"   GPS: {latest['gps']['latitude']}, {latest['gps']['longitude']}")
        print(f"   Ignition: {latest['ignition']}")
    
    # Test latest position
    print("\n4. Testing latest position...")
    latest_pos = db_manager.get_latest_position(test_imei)
    if latest_pos:
        print(f"✅ Latest position: {latest_pos['latitude']}, {latest_pos['longitude']}")
        print(f"   Timestamp: {latest_pos['timestamp']}")
    else:
        print("❌ No position data found")
    
    # Test bulk storage
    print("\n5. Testing bulk storage...")
    bulk_records = []
    for i in range(3):
        record_data = test_data.copy()
        record_data['gps']['latitude'] += i * 0.001
        record_data['gps']['longitude'] += i * 0.001
        bulk_records.append((test_imei, record_data))
    
    bulk_results = db_manager.bulk_store_telemetry_data(bulk_records)
    print(f"✅ Bulk storage: {bulk_results['success']} success, {bulk_results['failed']} failed")
    
    # Display database statistics
    print("\n6. Database statistics...")
    total_devices = Device.objects.count()
    total_records = TelemetryData.objects.count()
    print(f"✅ Total devices: {total_devices}")
    print(f"✅ Total telemetry records: {total_records}")
    
    print("\n" + "=" * 50)
    print("🎉 Database integration test completed!")


if __name__ == "__main__":
    try:
        test_database_integration()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1) 