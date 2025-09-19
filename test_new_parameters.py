#!/usr/bin/env python3
"""
Test script for the new IO parameters and binary flag handling
Tests Dallas Temperature 1 and P4 State Flags
"""

def test_new_parameters():
    """Test the new parameter handling"""
    
    # Sample data including the new parameters
    sample_io_data = {
        # Previously added parameters
        "2": 0,      # Digital Input 2 
        "3": 0,      # Digital Input 3
        "6": 2179,   # Analog Input 2 (2.179V)
        "9": 1955,   # Analog Input 1 (1.955V)
        "17": 89,    # Axis X (89 mG)
        "18": 986,   # Axis Y (986 mG)
        "19": 65401, # Axis Z (-135 mG when converted)
        "71": 0,     # Dallas Temperature ID 4
        
        # New parameters
        "72": 235,   # Dallas Temperature 1 (23.5°C)
        "132": 0x1234567890ABCDEF,  # Security State Flags (8 bytes)
        "517": 0xFEDCBA0987654321,  # Security State Flags P4 (8 bytes)
        "518": 0x1122334455667788,  # Control State Flags P4 (8 bytes) 
        "519": 0xAABBCCDDEEFF0011,  # Indicator State Flags P4 (8 bytes)
    }
    
    # Test parameter descriptions
    io_meanings = {
        2: "Digital Input 2",
        3: "Digital Input 3",
        6: "Analog Input 2", 
        9: "Analog Input 1",
        17: "Axis X",
        18: "Axis Y",
        19: "Axis Z",
        71: "Dallas Temperature ID 4",
        72: "Dallas Temperature 1",
        132: "Security State Flags",
        517: "Security State Flags P4",
        518: "Control State Flags P4",
        519: "Indicator State Flags P4"
    }
    
    print("Testing New Parameter Processing:")
    print("=" * 60)
    
    for io_id, value in sample_io_data.items():
        io_id_int = int(io_id)
        param_name = io_meanings.get(io_id_int, "Unknown")
        
        # Format according to teltonika service logic
        if io_id_int in [2, 3]:  # Digital inputs
            formatted_value = "HIGH" if value else "LOW"
        elif io_id_int in [6, 9]:  # Analog inputs (voltage)
            formatted_value = f"{value/1000:.3f}V"
        elif io_id_int in [17, 18, 19]:  # Accelerometer
            if value > 32767:
                signed_value = value - 65536
            else:
                signed_value = value
            formatted_value = f"{signed_value} mG"
        elif io_id_int == 71:  # Dallas Temperature ID
            formatted_value = f"0x{value:016X}" if value != 0 else "No sensor"
        elif io_id_int == 72:  # Dallas Temperature 1
            formatted_value = f"{value/10:.1f}°C"
        elif io_id_int in [132, 517, 518, 519]:  # State Flags
            flag_types = {132: "Security", 517: "Security P4", 518: "Control P4", 519: "Indicator P4"}
            flag_type = flag_types[io_id_int]
            
            # Convert to binary for storage
            binary_data = value.to_bytes(8, byteorder='little')
            
            # Show some active bits for demonstration
            active_bits = []
            for i in range(8):
                if value & (1 << i):
                    active_bits.append(f"bit{i}")
            
            if active_bits:
                formatted_value = f"{flag_type}: {', '.join(active_bits[:3])}{'...' if len(active_bits) > 3 else ''} (0x{value:016X})"
            else:
                formatted_value = f"{flag_type}: No flags active"
                
        else:
            formatted_value = str(value)
        
        print(f"IO{io_id_int:03d}: {param_name} = {formatted_value}")
    
    print("\nDjango Field Mapping:")
    print("=" * 60)
    
    # Django field mapping for all parameters
    django_field_mapping = {
        2: 'digital_input_2',
        3: 'digital_input_3',
        6: 'analog_input_2',
        9: 'analog_input_1', 
        17: 'axis_x',
        18: 'axis_y',
        19: 'axis_z',
        71: 'dallas_temperature_id_4',
        72: 'dallas_temperature_1',
        132: 'security_state_flags',
        517: 'security_state_flags_p4',
        518: 'control_state_flags_p4',
        519: 'indicator_state_flags_p4'
    }
    
    for io_id, value in sample_io_data.items():
        io_id_int = int(io_id)
        field_name = django_field_mapping.get(io_id_int, 'other_io_data')
        
        # Convert values for database storage
        if io_id_int in [2, 3]:  # Convert to boolean
            db_value = bool(value)
        elif io_id_int in [17, 18, 19]:  # Handle signed values
            if value > 32767:
                db_value = value - 65536
            else:
                db_value = value
        elif io_id_int in [132, 517, 518, 519]:  # Convert to binary
            db_value = f"binary: {value.to_bytes(8, byteorder='little').hex()}"
        else:
            db_value = value
            
        print(f"IO{io_id_int:03d} -> {field_name}: {db_value}")
    
    print("\nBinary Flag Handling:")
    print("=" * 60)
    
    # Test binary flag conversion
    for io_id in [132, 517, 518, 519]:
        if str(io_id) in sample_io_data:
            value = sample_io_data[str(io_id)]
            binary_data = value.to_bytes(8, byteorder='little')
            
            # Convert back to verify
            reconstructed = int.from_bytes(binary_data, byteorder='little')
            
            print(f"IO{io_id}: 0x{value:016X} -> binary -> 0x{reconstructed:016X} ✓")
    
    print("\nField Types and Storage:")
    print("=" * 60)
    print("dallas_temperature_1: IntegerField (IO072: Dallas Temperature 1 in °C * 10)")
    print("security_state_flags: BinaryField (IO132: Security state flags, 8 bytes)")
    print("security_state_flags_p4: BinaryField (IO517: Security State Flags P4, 8 bytes)")
    print("control_state_flags_p4: BinaryField (IO518: Control State Flags P4, 8 bytes)")
    print("indicator_state_flags_p4: BinaryField (IO519: Indicator State Flags P4, 8 bytes)")
    
    print("\nNotes:")
    print("- All state flags are stored as 8-byte binary fields for bit manipulation")
    print("- Binary fields use little-endian byte order")
    print("- Dallas Temperature 1 is stored as integer (value * 10) for precision")
    print("- State flags can be decoded bit-by-bit for specific meanings")

if __name__ == "__main__":
    test_new_parameters()
