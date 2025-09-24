#!/usr/bin/env python
"""
Server debugging script for Security State Flags P4
Run this on your server: python debug_server.py
"""

import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teltonika_gps.settings')
django.setup()

from gps_data.models import GPSRecord
from gps_data.teltonika_decoder import decode_security_state_flags_p4

print("=== DEBUGGING SECURITY STATE FLAGS P4 ON SERVER ===")

# Get the latest record with P4 flags
try:
    latest_record = GPSRecord.objects.filter(
        security_state_flags_p4__isnull=False
    ).exclude(
        security_state_flags_p4=b''
    ).order_by('-created_at').first()
    
    if not latest_record:
        print("❌ No records found with security_state_flags_p4 data")
        exit(1)
    
    print(f"✅ Found record ID: {latest_record.id}")
    print(f"✅ Device: {latest_record.device.imei}")
    print(f"✅ Timestamp: {latest_record.timestamp}")
    
    # Check the raw binary data
    raw_data = latest_record.security_state_flags_p4
    print(f"✅ Raw data type: {type(raw_data)}")
    print(f"✅ Raw data length: {len(raw_data) if raw_data else 0}")
    
    if raw_data:
        print(f"✅ Raw data (hex): {raw_data.hex()}")
        
        # Convert to integer to see active bits
        flags_int = int.from_bytes(raw_data, byteorder='little')
        print(f"✅ As integer: {flags_int}")
        print(f"✅ As hex: {hex(flags_int)}")
        
        # Find active bits
        active_bits = [i for i in range(64) if flags_int & (1 << i)]
        print(f"✅ Active bits: {active_bits}")
        
        # Test decoder
        print("\n=== TESTING DECODER ===")
        print(f"✅ Data type being passed to decoder: {type(raw_data)}")
        
        # Test if memoryview conversion works
        if isinstance(raw_data, memoryview):
            print("✅ Converting memoryview to bytes...")
            bytes_data = raw_data.tobytes()
            print(f"✅ Converted to: {type(bytes_data)}")
        
        try:
            decoded = decode_security_state_flags_p4(raw_data)
            print(f"✅ Decoder returned: {len(decoded)} flags")
            
            if decoded:
                print("\n=== DECODED FLAGS ===")
                active_count = 0
                for flag_name, flag_info in decoded.items():
                    is_active = flag_name.endswith('_status') or flag_info.get('active', False)
                    if is_active:
                        active_count += 1
                        print(f"  ✅ {flag_name}: {flag_info.get('description', 'No description')}")
                        print(f"      Active: {flag_info.get('active', False)}")
                        print(f"      Bit pos: {flag_info.get('bit_position', 'N/A')}")
                        print(f"      Value: {flag_info.get('value', 'N/A')}")
                        print()
                
                print(f"✅ Total active flags found: {active_count}")
                
                if active_count == 0:
                    print("❌ PROBLEM: No flags marked as active!")
                    print("❌ This explains why admin shows 'No flags decoded'")
                else:
                    print("✅ Flags should display in admin")
            else:
                print("❌ Decoder returned empty result")
                
        except Exception as e:
            print(f"❌ Decoder error: {e}")
            import traceback
            traceback.print_exc()
    
except Exception as e:
    print(f"❌ Database error: {e}")
    import traceback
    traceback.print_exc()
