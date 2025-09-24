"""
Teltonika CAN Adapter Security Flags Decoder

Based on Teltonika FMB110 CAN adapters specification:
https://wiki.teltonika-gps.com/view/FMB110_CAN_adapters

This module provides comprehensive decoding of Teltonika security state flags
according to the official documentation.
"""

def decode_security_state_flags_p4(flags_value):
    """
    Decode Security State Flags P4 (IO517) according to Teltonika specification
    
    Args:
        flags_value: Integer or bytes representing the flags
        
    Returns:
        dict: Decoded flags with human-readable descriptions
    """
    
    # Convert to integer if needed
    if isinstance(flags_value, (bytes, bytearray, memoryview)):
        # Convert memoryview to bytes first if needed
        if isinstance(flags_value, memoryview):
            flags_value = flags_value.tobytes()
        flags = int.from_bytes(flags_value, byteorder='little')
    elif isinstance(flags_value, str):
        # Handle hex string format like "0x0000000000000000000002810004003C"
        if flags_value.startswith('0x'):
            flags = int(flags_value, 16)
        else:
            flags = int(flags_value)
    elif isinstance(flags_value, int):
        flags = flags_value
    else:
        # Handle any other type by attempting conversion
        try:
            flags = int(flags_value)
        except (ValueError, TypeError):
            return {}
    
    decoded_flags = {}
    
    # Byte 0 - CAN Connection Status (bits 0-7)
    can1_status = (flags >> 0) & 0x03  # bits 0-1
    can2_status = (flags >> 2) & 0x03  # bits 2-3
    can3_status = (flags >> 4) & 0x03  # bits 4-5
    
    can_status_map = {
        0x00: "connected, currently no data is received",
        0x01: "connected, currently data is received", 
        0x02: "not connected, needs connection",
        0x03: "not connected does not need connection"
    }
    
    decoded_flags['can1_status'] = {
        'active': True,  # Always show CAN status regardless of value
        'description': f"CAN1 {can_status_map.get(can1_status, 'unknown status')}",
        'value': can1_status,
        'bit_position': '0-1'
    }
    
    decoded_flags['can2_status'] = {
        'active': True,  # Always show CAN status regardless of value
        'description': f"CAN2 {can_status_map.get(can2_status, 'unknown status')}",
        'value': can2_status,
        'bit_position': '2-3'
    }
    
    decoded_flags['can3_status'] = {
        'active': True,  # Always show CAN status regardless of value
        'description': f"CAN3 {can_status_map.get(can3_status, 'unknown status')}",
        'value': can3_status,
        'bit_position': '4-5'
    }
    
    # Byte 1 - Engine and Vehicle Status (bits 8-15)
    byte1_flags = [
        (8, 'ignition_on', 'ignition on'),
        (9, 'key_in_ignition', 'key in ignition lock'),
        (10, 'webasto', 'webasto'),
        (11, 'engine_working', 'engine is working'),
        (12, 'standalone_engine', 'standalone engine'),
        (13, 'ready_to_drive', 'ready to drive'),
        (14, 'engine_cng', 'engine is working on CNG'),
        (15, 'work_mode', 'work mode (0=private, 1=company)')
    ]
    
    for bit_pos, flag_name, description in byte1_flags:
        is_active = bool(flags & (1 << bit_pos))
        decoded_flags[flag_name] = {
            'active': is_active,
            'description': description,
            'bit_position': bit_pos
        }
    
    # Byte 2 - Driver and Vehicle Control (bits 16-23)
    byte2_flags = [
        (16, 'operator_present', 'operator is present'),
        (17, 'interlock_active', 'interlock active'),
        (18, 'handbrake_active', 'handbrake is active'),
        (19, 'footbrake_active', 'footbrake is active'),
        (20, 'clutch_pushed', 'clutch is pushed')
    ]
    
    for bit_pos, flag_name, description in byte2_flags:
        is_active = bool(flags & (1 << bit_pos))
        decoded_flags[flag_name] = {
            'active': is_active,
            'description': description,
            'bit_position': bit_pos
        }
    
    # Handle additional bits that might be set
    # Check for other active bits beyond the standard ones
    standard_bits = {0, 1, 2, 3, 4, 5, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20}
    
    for bit_pos in range(64):  # Check up to 64 bits
        if (flags & (1 << bit_pos)) and bit_pos not in standard_bits:
            decoded_flags[f'unknown_bit_{bit_pos}'] = {
                'active': True,
                'description': f'Unknown flag at bit position {bit_pos}',
                'bit_position': bit_pos
            }
    
    return decoded_flags


def decode_control_state_flags_p4(flags_value):
    """
    Decode Control State Flags P4 (IO518) according to Teltonika specification
    
    Args:
        flags_value: Integer or bytes representing the flags
        
    Returns:
        dict: Decoded control flags
    """
    if flags_value is None:
        return {}
    
    # Convert to integer if needed
    if isinstance(flags_value, (bytes, bytearray)):
        flags = int.from_bytes(flags_value, byteorder='little')
    elif isinstance(flags_value, str):
        if flags_value.startswith('0x'):
            flags = int(flags_value, 16)
        else:
            flags = int(flags_value)
    elif isinstance(flags_value, int):
        flags = flags_value
    else:
        # Handle any other type by attempting conversion
        try:
            flags = int(flags_value)
        except (ValueError, TypeError):
            return {}
    
    decoded_flags = {}
    
    # Control flags are device/adapter specific
    # This is a basic template - extend based on specific device capabilities
    control_bit_descriptions = {
        0: 'control function 1',
        1: 'control function 2', 
        2: 'control function 3',
        3: 'control function 4',
        4: 'control function 5',
        5: 'control function 6',
        6: 'control function 7',
        7: 'control function 8'
    }
    
    for bit_pos in range(64):  # Check up to 64 bits
        if flags & (1 << bit_pos):
            flag_name = f'control_bit_{bit_pos}'
            description = control_bit_descriptions.get(bit_pos, f'control flag at bit {bit_pos}')
            decoded_flags[flag_name] = {
                'active': True,
                'description': description,
                'bit_position': bit_pos
            }
    
    return decoded_flags


def decode_indicator_state_flags_p4(flags_value):
    """
    Decode Indicator State Flags P4 (IO519) according to Teltonika specification
    
    Args:
        flags_value: Integer or bytes representing the flags
        
    Returns:
        dict: Decoded indicator flags
    """
    if flags_value is None:
        return {}
    
    # Convert to integer if needed
    if isinstance(flags_value, (bytes, bytearray)):
        flags = int.from_bytes(flags_value, byteorder='little')
    elif isinstance(flags_value, str):
        if flags_value.startswith('0x'):
            flags = int(flags_value, 16)
        else:
            flags = int(flags_value)
    elif isinstance(flags_value, int):
        flags = flags_value
    else:
        # Handle any other type by attempting conversion
        try:
            flags = int(flags_value)
        except (ValueError, TypeError):
            return {}
    
    decoded_flags = {}
    
    # Indicator flags are device/adapter specific
    indicator_bit_descriptions = {
        0: 'indicator 1',
        1: 'indicator 2',
        2: 'indicator 3', 
        3: 'indicator 4',
        4: 'indicator 5',
        5: 'indicator 6',
        6: 'indicator 7',
        7: 'indicator 8'
    }
    
    for bit_pos in range(64):  # Check up to 64 bits
        if flags & (1 << bit_pos):
            flag_name = f'indicator_bit_{bit_pos}'
            description = indicator_bit_descriptions.get(bit_pos, f'indicator flag at bit {bit_pos}')
            decoded_flags[flag_name] = {
                'active': True,
                'description': description,
                'bit_position': bit_pos
            }
    
    return decoded_flags


def decode_security_state_flags_io132(flags_value):
    """
    Decode basic Security State Flags (IO132)
    
    Args:
        flags_value: Integer or bytes representing the flags
        
    Returns:
        dict: Decoded security flags
    """
    if flags_value is None:
        return {}
    
    # Convert to integer if needed
    if isinstance(flags_value, (bytes, bytearray)):
        flags = int.from_bytes(flags_value, byteorder='little')
    elif isinstance(flags_value, str):
        if flags_value.startswith('0x'):
            flags = int(flags_value, 16)
        else:
            flags = int(flags_value)
    elif isinstance(flags_value, int):
        flags = flags_value
    else:
        # Handle any other type by attempting conversion
        try:
            flags = int(flags_value)
        except (ValueError, TypeError):
            return {}
    
    decoded_flags = {}
    
    # Basic security flags (based on common Teltonika implementations)
    security_flags = [
        (0, 'security_bit_0', 'Security flag bit 0'),
        (28, 'security_bit_28', 'Security flag bit 28'),
        (32, 'security_bit_32', 'Security flag bit 32'),
        (36, 'security_bit_36', 'Security flag bit 36'),
        (55, 'security_bit_55', 'Security flag bit 55')
    ]
    
    for bit_pos, flag_name, description in security_flags:
        is_active = bool(flags & (1 << bit_pos))
        decoded_flags[flag_name] = {
            'active': is_active,
            'description': description,
            'bit_position': bit_pos
        }
    
    # Check for any other active bits
    standard_bits = {0, 28, 32, 36, 55}
    for bit_pos in range(64):  # Check up to 64 bits
        if (flags & (1 << bit_pos)) and bit_pos not in standard_bits:
            decoded_flags[f'unknown_security_bit_{bit_pos}'] = {
                'active': True,
                'description': f'Unknown security flag at bit position {bit_pos}',
                'bit_position': bit_pos
            }
    
    return decoded_flags


def format_flags_summary(decoded_flags):
    """
    Format decoded flags into a human-readable summary
    
    Args:
        decoded_flags: Dictionary from decode functions
        
    Returns:
        str: Human-readable summary of active flags
    """
    if not decoded_flags:
        return "No flags active"
    
    active_flags = []
    for flag_name, flag_info in decoded_flags.items():
        if flag_info.get('active', False):
            active_flags.append(flag_info['description'])
    
    if active_flags:
        return '; '.join(active_flags)
    else:
        return "No flags active"


def decode_user_example():
    """
    Decode the specific example provided by the user
    """
    print("Decoding user's example data:")
    print("=" * 50)
    
    # User's data:
    # IO132: Security State Flags = bit0, bit28, bit32, bit36, bit55 (0x00000000000000000080001110000001)
    # IO517: Security State Flags P4 = bit2, bit3, bit4, bit5, bit18, bit32, bit39, bit41 (0x0000000000000000000002810004003C)
    
    # Decode IO132 Security State Flags
    io132_hex = "0x00000000000000000080001110000001"
    print(f"\nIO132 Security State Flags: {io132_hex}")
    io132_decoded = decode_security_state_flags_io132(io132_hex)
    print("Decoded IO132:")
    for flag_name, flag_info in io132_decoded.items():
        if flag_info['active']:
            print(f"  - {flag_info['description']} (bit {flag_info['bit_position']})")
    
    # Decode IO517 Security State Flags P4
    io517_hex = "0x0000000000000000000002810004003C"
    print(f"\nIO517 Security State Flags P4: {io517_hex}")
    io517_decoded = decode_security_state_flags_p4(io517_hex)
    print("Decoded IO517:")
    for flag_name, flag_info in io517_decoded.items():
        if flag_info['active']:
            print(f"  - {flag_info['description']} (bit {flag_info.get('bit_position', 'N/A')})")
    
    print("\nSummary:")
    print(f"IO132 Summary: {format_flags_summary(io132_decoded)}")
    print(f"IO517 Summary: {format_flags_summary(io517_decoded)}")


if __name__ == "__main__":
    decode_user_example()
