# Summary of New Parameters and Binary Flag Implementation

## New Parameters Added

### 1. Dallas Temperature 1 (IO072)
- **Type**: Temperature sensor reading
- **Range**: Temperature in °C * 10 (e.g., 235 = 23.5°C)
- **Storage**: IntegerField in Django
- **Display**: Formatted as "23.5°C"

### 2. Security State Flags P4 (IO517)
- **Type**: 8-byte binary state flags
- **Storage**: BinaryField (8 bytes) in Django
- **Format**: Binary data for bit manipulation
- **Display**: Shows active bits and hex representation

### 3. Control State Flags P4 (IO518)
- **Type**: 8-byte binary state flags
- **Storage**: BinaryField (8 bytes) in Django
- **Format**: Binary data for bit manipulation
- **Display**: Shows active bits and hex representation

### 4. Indicator State Flags P4 (IO519)
- **Type**: 8-byte binary state flags
- **Storage**: BinaryField (8 bytes) in Django
- **Format**: Binary data for bit manipulation
- **Display**: Shows active bits and hex representation

## Updated Parameter

### Security State Flags (IO132) - CHANGED TO BINARY
- **Previous**: BigIntegerField storing as integer
- **New**: BinaryField (8 bytes) storing as binary data
- **Reason**: Better bit manipulation and consistency with P4 flags
- **Migration**: Requires data conversion from integer to binary

## Implementation Details

### Django Models (`gps_data/models.py`)

```python
# New fields added
dallas_temperature_1 = models.IntegerField(null=True, blank=True, help_text="IO072: Dallas Temperature 1 (°C * 10)")
security_state_flags_p4 = models.BinaryField(max_length=8, null=True, blank=True, help_text="IO517: Security State Flags P4 (8 bytes binary)")
control_state_flags_p4 = models.BinaryField(max_length=8, null=True, blank=True, help_text="IO518: Control State Flags P4 (8 bytes binary)")
indicator_state_flags_p4 = models.BinaryField(max_length=8, null=True, blank=True, help_text="IO519: Indicator State Flags P4 (8 bytes binary)")

# Updated field
security_state_flags = models.BinaryField(max_length=8, null=True, blank=True, help_text="IO132: Security state flags (8 bytes binary)")
```

### Binary Flag Properties
Added property methods for decoding binary flags:
- `security_flags_p4_decoded`: Decodes IO517 binary flags
- `control_flags_p4_decoded`: Decodes IO518 binary flags  
- `indicator_flags_p4_decoded`: Decodes IO519 binary flags
- Updated `security_flags_decoded`: Now handles binary data for IO132

### Teltonika Service (`teltonika_service.py`)

#### Added IO Meanings:
```python
72: "Dallas Temperature 1",
517: "Security State Flags P4",
518: "Control State Flags P4", 
519: "Indicator State Flags P4",
```

#### Added Formatting:
- Dallas Temperature 1: `f"{value/10:.1f}°C"`
- P4 State Flags: `format_binary_flags(value, io_id)` - shows active bits and hex

#### New Method:
```python
def format_binary_flags(self, flags_value, io_id):
    """Format P4 state flags for display"""
    # Converts to binary, shows active bits, displays as hex
```

### Django Serializers (`gps_data/serializers.py`)

#### Updated Field Lists:
- Added `dallas_temperature_1` to serializer fields
- Added P4 flag fields: `security_state_flags_p4`, `control_state_flags_p4`, `indicator_state_flags_p4`
- Added computed fields: `security_flags_p4_decoded`, `control_flags_p4_decoded`, `indicator_flags_p4_decoded`

#### Updated Field Mapping:
```python
72: 'dallas_temperature_1',
132: 'security_state_flags',
517: 'security_state_flags_p4',
518: 'control_state_flags_p4', 
519: 'indicator_state_flags_p4',
```

#### Binary Conversion Logic:
```python
elif io_id_int in [132, 517, 518, 519]:  # State flags - convert to binary
    if isinstance(value, int):
        value = value.to_bytes(8, byteorder='little')
    elif isinstance(value, str):
        if value.startswith('0x'):
            value = int(value, 16).to_bytes(8, byteorder='little')
        else:
            value = int(value).to_bytes(8, byteorder='little')
```

### Django Admin (`gps_data/admin.py`)

#### New Fieldsets:
- **Temperature Sensors**: Shows Dallas temperature with formatted display
- **State Flags**: Consolidated all state flags with binary flag summary

#### New Helper Methods:
- `dallas_temp_1_formatted()`: Shows temperature as "23.5°C"
- `binary_flags_summary()`: Shows P4 flags as "Sec P4: 0x1234, Ctrl P4: 0x5678"

#### Updated Display:
- Added formatted temperature display
- Added binary flag summaries
- Consolidated state flag management

## Database Migrations

### Migration 0007: `add_temperature_and_p4_flags.py`
- Adds `dallas_temperature_1` field
- Adds three P4 binary flag fields
- Converts `security_state_flags` to BinaryField

### Data Migration: `convert_security_flags.py`
- Converts existing integer `security_state_flags` to binary format
- Handles migration from old integer storage to new binary storage

## Binary Data Handling

### Storage Format:
- **Byte Order**: Little-endian
- **Size**: 8 bytes (64 bits) per flag field
- **Encoding**: Raw binary data in database

### Conversion Process:
1. **Input**: Integer or hex string (e.g., `0x1234567890ABCDEF`)
2. **Storage**: Convert to 8-byte binary using `value.to_bytes(8, byteorder='little')`
3. **Retrieval**: Convert back using `int.from_bytes(binary_data, byteorder='little')`
4. **Display**: Show as hex or decoded bit flags

### Bit Manipulation:
```python
# Check specific bits
if flags & (1 << bit_position):
    print(f"Bit {bit_position} is set")

# Extract byte 3 (for security flags)
byte3 = (flags >> 16) & 0xFF
```

## Usage Examples

### Sample Data:
```json
{
    "72": 235,                    // 23.5°C
    "132": "0x1234567890ABCDEF",  // Security flags (binary)
    "517": "0xFEDCBA0987654321",  // Security P4 flags (binary)
    "518": "0x1122334455667788",  // Control P4 flags (binary)
    "519": "0xAABBCCDDEEFF0011"   // Indicator P4 flags (binary)
}
```

### Database Storage:
- `dallas_temperature_1`: 235
- `security_state_flags`: `b'\xef\xcd\xab\x90\x78\x56\x34\x12'`
- `security_state_flags_p4`: `b'\x21\x43\x65\x87\x09\xba\xdc\xfe'`
- `control_state_flags_p4`: `b'\x88\x77\x66\x55\x44\x33\x22\x11'`
- `indicator_state_flags_p4`: `b'\x11\x00\xff\xee\xdd\xcc\xbb\xaa'`

### Admin Display:
- Dallas Temperature 1: "23.5°C"
- P4 Flags: "Sec P4: 0xFEDCBA0987654321, Ctrl P4: 0x1122334455667788"

## Benefits of Binary Storage

1. **Efficient Bit Manipulation**: Direct bit operations on binary data
2. **Consistent Storage**: All state flags use same 8-byte binary format
3. **No Data Loss**: Preserves full 64-bit precision
4. **Future-Proof**: Easy to add new bit meanings without schema changes
5. **Performance**: Binary operations are faster than string parsing

## Migration Notes

1. **Run Migration**: Apply `0007_add_temperature_and_p4_flags.py`
2. **Convert Data**: Run `convert_security_flags.py` to convert existing integer flags
3. **Test**: Verify existing security flag functionality still works
4. **Update Code**: Any custom code reading `security_state_flags` may need updates

The system now efficiently handles both temperature data and complex binary state flags while maintaining backward compatibility and providing user-friendly displays in the admin interface.
