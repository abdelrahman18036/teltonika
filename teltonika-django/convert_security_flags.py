#!/usr/bin/env python3
"""
Data Migration Script for Converting Security State Flags to Binary
Run this after applying migration 0007_add_temperature_and_p4_flags.py

This script converts existing integer security_state_flags values to binary format.
"""

def convert_security_flags_to_binary():
    """
    Convert existing integer security_state_flags to binary format
    """
    # This is a template - adjust the import path based on your Django setup
    import os
    import django
    
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teltonika_gps.settings')
    django.setup()
    
    from gps_data.models import GPSRecord
    
    print("Converting security_state_flags from integer to binary format...")
    
    # Find all records with integer security_state_flags
    records_to_update = GPSRecord.objects.filter(
        security_state_flags__isnull=False
    ).exclude(
        security_state_flags=b''  # Exclude records that are already binary
    )
    
    total_records = records_to_update.count()
    print(f"Found {total_records} records to convert")
    
    updated_count = 0
    error_count = 0
    
    for record in records_to_update:
        try:
            # Check if the field is still an integer (not binary)
            if isinstance(record.security_state_flags, int):
                # Convert integer to 8-byte binary (little-endian)
                binary_value = record.security_state_flags.to_bytes(8, byteorder='little')
                record.security_state_flags = binary_value
                record.save(update_fields=['security_state_flags'])
                updated_count += 1
                
                if updated_count % 100 == 0:
                    print(f"Processed {updated_count}/{total_records} records...")
                    
        except Exception as e:
            print(f"Error converting record {record.id}: {e}")
            error_count += 1
    
    print(f"Conversion complete!")
    print(f"Successfully converted: {updated_count} records")
    print(f"Errors: {error_count} records")

if __name__ == "__main__":
    convert_security_flags_to_binary()
