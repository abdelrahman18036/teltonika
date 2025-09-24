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
        (20, 'clutch_pushed', 'clutch is pushed'),
        (22, 'front_left_door_opened', 'front left door opened'),
        (23, 'front_right_door_opened', 'front right door opened')
    ]
    
    for bit_pos, flag_name, description in byte2_flags:
        is_active = bool(flags & (1 << bit_pos))
        decoded_flags[flag_name] = {
            'active': is_active,
            'description': description,
            'bit_position': bit_pos
        }
    
    # Byte 3 - Additional Vehicle Status (bits 24-31)
    byte3_flags = [
        (24, 'rear_left_door_opened', 'rear left door opened'),
        (25, 'rear_right_door_opened', 'rear right door opened'),
        (30, 'electric_engine_working', 'electric engine is working'),
        (31, 'car_closed_factory_remote', 'car is closed with factory remote control')
    ]
    
    for bit_pos, flag_name, description in byte3_flags:
        is_active = bool(flags & (1 << bit_pos))
        decoded_flags[flag_name] = {
            'active': is_active,
            'description': description,
            'bit_position': bit_pos
        }
    
    # Byte 4 - Security and System Status (bits 32-39)
    byte4_flags = [
        (32, 'car_closed', 'car is closed'),
        (39, 'can_module_sleep', 'CAN module is in SLEEP mode')
    ]
    
    for bit_pos, flag_name, description in byte4_flags:
        is_active = bool(flags & (1 << bit_pos))
        decoded_flags[flag_name] = {
            'active': is_active,
            'description': description,
            'bit_position': bit_pos
        }
    
    # Byte 5 - Drive and Engine Control (bits 40-47)
    byte5_flags = [
        (41, 'parking_active', 'parking is active'),
        (44, 'drive_active', 'drive is active'),
        (45, 'engine_lock_active', 'engine lock active')
    ]
    
    for bit_pos, flag_name, description in byte5_flags:
        is_active = bool(flags & (1 << bit_pos))
        decoded_flags[flag_name] = {
            'active': is_active,
            'description': description,
            'bit_position': bit_pos
        }
    
    # Handle additional bits that might be set
    # Check for other active bits beyond the standard ones
    standard_bits = {0, 1, 2, 3, 4, 5, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 30, 31, 32, 39, 41, 44, 45}
    
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
    if isinstance(flags_value, (bytes, bytearray, memoryview)):
        # Convert memoryview to bytes first if needed
        if isinstance(flags_value, memoryview):
            flags_value = flags_value.tobytes()
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
    
    # Byte 0 - Lighting Controls (bits 0-7)
    byte0_flags = [
        (0, 'parking_lights_on', 'parking lights turned on'),
        (1, 'dipped_headlights_on', 'dipped headlights turned on'),
        (2, 'full_beam_headlights_on', 'full beam headlights turned on'),
        (3, 'rear_fog_lights_on', 'rear fog lights turned on'),
        (4, 'front_fog_lights_on', 'front fog lights turned on'),
        (5, 'additional_front_lights_on', 'additional front lights turned on'),
        (6, 'additional_rear_lights_on', 'additional rear lights turned on'),
        (7, 'light_signal_on', 'light signal turned on')
    ]
    
    for bit_pos, flag_name, description in byte0_flags:
        is_active = bool(flags & (1 << bit_pos))
        decoded_flags[flag_name] = {
            'active': is_active,
            'description': description,
            'bit_position': bit_pos
        }
    
    # Byte 1 - Vehicle Systems and Safety (bits 8-15)
    byte1_flags = [
        (8, 'air_conditioning_on', 'air conditioning turned on'),
        (9, 'cruise_control_on', 'cruise control turned on'),
        (10, 'automatic_retarder_on', 'automatic retarder turned on'),
        (11, 'manual_retarder_on', 'manual retarder turned on'),
        (12, 'driver_seatbelt_fastened', 'driver\'s seatbelt fastened'),
        (13, 'front_passenger_seatbelt_fastened', 'front passenger\'s seatbelt fastened'),
        (14, 'rear_left_seatbelt_fastened', 'rear left passenger\'s seatbelt fastened'),
        (15, 'rear_right_seatbelt_fastened', 'rear right passenger\'s seatbelt fastened')
    ]
    
    for bit_pos, flag_name, description in byte1_flags:
        is_active = bool(flags & (1 << bit_pos))
        decoded_flags[flag_name] = {
            'active': is_active,
            'description': description,
            'bit_position': bit_pos
        }
    
    # Byte 2 - Advanced Vehicle Systems (bits 16-23)
    byte2_flags = [
        (16, 'rear_centre_seatbelt_fastened', 'rear centre passenger\'s seatbelt fastened'),
        (17, 'front_passenger_present', 'front passenger is present'),
        (18, 'pto_on', 'PTO is on'),
        (19, 'front_differential_locked', 'front differential locked'),
        (20, 'rear_differential_locked', 'rear differential locked'),
        (21, 'central_differential_4hi_locked', 'central differential (4HI) locked'),
        (22, 'central_differential_4lo_locked', 'central differential with reductor (4LO) locked'),
        (23, 'trailer_axle_1_lift_active', 'trailer axle 1 lift active')
    ]
    
    for bit_pos, flag_name, description in byte2_flags:
        is_active = bool(flags & (1 << bit_pos))
        decoded_flags[flag_name] = {
            'active': is_active,
            'description': description,
            'bit_position': bit_pos
        }
    
    # Byte 3 - Trailer Systems (bits 24+)
    byte3_flags = [
        (24, 'trailer_axle_2_lift_active', 'trailer axle 2 lift active')
    ]
    
    for bit_pos, flag_name, description in byte3_flags:
        is_active = bool(flags & (1 << bit_pos))
        decoded_flags[flag_name] = {
            'active': is_active,
            'description': description,
            'bit_position': bit_pos
        }
    
    # Handle additional bits that might be set
    # Check for other active bits beyond the standard ones
    standard_control_bits = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24}
    
    for bit_pos in range(64):  # Check up to 64 bits
        if (flags & (1 << bit_pos)) and bit_pos not in standard_control_bits:
            decoded_flags[f'unknown_control_bit_{bit_pos}'] = {
                'active': True,
                'description': f'Unknown control flag at bit position {bit_pos}',
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
    Decode Security State Flags (IO132) according to Teltonika specification
    
    Supports comprehensive decoding of all IO132 security flags including:
    - CAN connection status
    - Engine and system control
    - Electric engine and charging
    - Ignition and security
    - Gearbox and brake status  
    - Door status
    - Remote control actions
    
    Args:
        flags_value: Integer, bytes, or memoryview representing the flags
        
    Returns:
        dict: Decoded security flags with descriptions and bit positions
    """
    if flags_value is None:
        return {}
    
    # Convert to integer if needed
    if isinstance(flags_value, (bytes, bytearray, memoryview)):
        # Convert memoryview to bytes first if needed
        if isinstance(flags_value, memoryview):
            flags_value = flags_value.tobytes()
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
    
    # Byte 0 - CAN Connection Status (bits 0-7)
    can1_status = (flags >> 0) & 0x03  # bits 0-1
    can2_status = (flags >> 2) & 0x03  # bits 2-3
    can3_status = (flags >> 4) & 0x03  # bits 4-5
    
    can_status_map = {
        0x00: "not connected, connection not required",
        0x01: "connected, currently no data is received",
        0x02: "not connected, needs connection",
        0x03: "connected, currently data is received"
    }
    
    decoded_flags['can1_status'] = {
        'active': True,  # Always show CAN status
        'description': f"CAN1 {can_status_map.get(can1_status, 'unknown status')}",
        'value': can1_status,
        'bit_position': '0-1'
    }
    
    decoded_flags['can2_status'] = {
        'active': True,  # Always show CAN status
        'description': f"CAN2 {can_status_map.get(can2_status, 'unknown status')}",
        'value': can2_status,
        'bit_position': '2-3'
    }
    
    decoded_flags['can3_status'] = {
        'active': True,  # Always show CAN status
        'description': f"CAN3 {can_status_map.get(can3_status, 'unknown status')}",
        'value': can3_status,
        'bit_position': '4-5'
    }
    
    # Byte 1 - Engine and System Control (bits 8-15)
    byte1_flags = [
        (8, 'engine_lock_request', 'request to lock the engine (activation after attempt to restart the engine)'),
        (9, 'hazard_warning_lights', 'status of the hazard warning lights switch active'),
        (10, 'factory_armed', 'factory armed')
    ]
    
    for bit_pos, flag_name, description in byte1_flags:
        is_active = bool(flags & (1 << bit_pos))
        decoded_flags[flag_name] = {
            'active': is_active,
            'description': description,
            'bit_position': bit_pos
        }
    
    # Byte 2 - Electric Engine and Charging (bits 16-23)
    byte2_flags = [
        (17, 'electric_engine_working', 'electric engine is working (information available only when the ignition is on)'),
        (18, 'battery_charging_on', 'battery charging is on'),
        (19, 'charging_wire_plugged', 'charging wire is plugged'),
        (20, 'vehicle_working_mode', 'vehicle working mode (1=business mode, 0=private mode)'),
        (21, 'operate_button_pressed', 'bit appears when any operate button in car was put (reset when button is released)'),
        (22, 'immobilizer_service_mode', 'bit appears when immobilizer is in service mode'),
        (23, 'immobilizer_key_sequence', 'immobilizer, bit appears during introduction of a programmed sequence of keys in the car')
    ]
    
    for bit_pos, flag_name, description in byte2_flags:
        is_active = bool(flags & (1 << bit_pos))
        decoded_flags[flag_name] = {
            'active': is_active,
            'description': description,
            'bit_position': bit_pos
        }
    
    # Byte 3 - Ignition and Security (bits 24-31)
    byte3_flags = [
        (24, 'key_in_ignition', 'the key is in ignition lock'),
        (25, 'ignition_on', 'ignition on'),
        (26, 'dynamic_ignition_on', 'dynamic ignition on'),
        (27, 'webasto', 'webasto'),
        (28, 'car_closed', 'car is closed'),
        (29, 'car_closed_factory_remote', 'car is closed by factory\'s remote control or module command'),
        (30, 'factory_alarm_panic', 'factory installed alarm system is actuated (is in panic mode)'),
        (31, 'factory_alarm_emulated', 'factory installed alarm system is emulated by module')
    ]
    
    for bit_pos, flag_name, description in byte3_flags:
        is_active = bool(flags & (1 << bit_pos))
        decoded_flags[flag_name] = {
            'active': is_active,
            'description': description,
            'bit_position': bit_pos
        }
    
    # Byte 4 - Gearbox and Brake Status (bits 32-39)
    byte4_flags = [
        (32, 'parking_activated', 'parking activated (automatic gearbox)'),
        (34, 'neutral_activated', 'neutral activated (automatic gearbox)'),
        (35, 'drive_activated', 'drive activated (automatic gearbox)'),
        (36, 'handbrake_actuated', 'handbrake is actuated (information available only with ignition on)'),
        (37, 'footbrake_actuated', 'footbrake is actuated (information available only with ignition on)'),
        (38, 'engine_working', 'Engine is working (information available only when the ignition on)'),
        (39, 'reverse_on', 'reverse is on')
    ]
    
    for bit_pos, flag_name, description in byte4_flags:
        is_active = bool(flags & (1 << bit_pos))
        decoded_flags[flag_name] = {
            'active': is_active,
            'description': description,
            'bit_position': bit_pos
        }
    
    # Byte 5 - Door Status (bits 40-47)
    byte5_flags = [
        (40, 'front_left_door_opened', 'front left door opened'),
        (41, 'front_right_door_opened', 'front right door opened'),
        (42, 'rear_left_door_opened', 'rear left door opened'),
        (43, 'rear_right_door_opened', 'rear right door opened'),
        (44, 'engine_cover_opened', 'engine cover opened'),
        (45, 'trunk_door_opened', 'trunk door opened'),
        (46, 'roof_opened', 'roof opened')
    ]
    
    for bit_pos, flag_name, description in byte5_flags:
        is_active = bool(flags & (1 << bit_pos))
        decoded_flags[flag_name] = {
            'active': is_active,
            'description': description,
            'bit_position': bit_pos
        }
    
    # Byte 6 - Remote Control and Sleep Mode (bits 48-55)
    # Low nibble (bits 48-51) - Remote control actions
    remote_action = (flags >> 48) & 0x0F
    remote_action_map = {
        0x01: "car was closed by the factory's remote control",
        0x02: "car was opened by the factory's remote control",
        0x03: "trunk cover was opened by the factory's remote control",
        0x04: "module has sent a rearming signal",
        0x05: "car was closed three times by the factory's remote control"
    }
    
    if remote_action > 0:
        decoded_flags['remote_control_action'] = {
            'active': True,
            'description': remote_action_map.get(remote_action, f'Unknown remote control action: {remote_action}'),
            'value': remote_action,
            'bit_position': '48-51'
        }
    
    # High nibble - Sleep mode (bit 52)
    can_sleep_mode = bool(flags & (1 << 52))
    decoded_flags['can_module_sleep'] = {
        'active': can_sleep_mode,
        'description': 'CAN module goes to sleep mode',
        'bit_position': 52
    }
    
    # Handle additional bits that might be set
    # Check for other active bits beyond the standard ones
    standard_io132_bits = {0, 1, 2, 3, 4, 5, 8, 9, 10, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 48, 49, 50, 51, 52}
    
    for bit_pos in range(64):  # Check up to 64 bits
        if (flags & (1 << bit_pos)) and bit_pos not in standard_io132_bits:
            decoded_flags[f'unknown_io132_bit_{bit_pos}'] = {
                'active': True,
                'description': f'Unknown IO132 security flag at bit position {bit_pos}',
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
