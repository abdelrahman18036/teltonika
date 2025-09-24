# Teltonika CAN Adapter Security Flags Decoder

This document explains how to use the comprehensive Teltonika CAN adapter security flags decoder that has been implemented according to the official [Teltonika FMB110 CAN adapters specification](https://wiki.teltonika-gps.com/view/FMB110_CAN_adapters).

## Overview

The decoder supports all major Teltonika flag types:

- **IO132**: Security State Flags (basic)
- **IO517**: Security State Flags P4 (CAN adapter specific)
- **IO518**: Control State Flags P4 
- **IO519**: Indicator State Flags P4

## Features

- ✅ **Complete P4 Security Flags Support** - Decodes CAN connection status, engine state, driver presence, etc.
- ✅ **Human-Readable Output** - Converts binary flags to meaningful descriptions
- ✅ **Django Admin Integration** - Shows decoded flags in the admin interface
- ✅ **Management Command** - Command-line tool for testing and debugging
- ✅ **Model Properties** - Easy access to decoded flags in Python code
- ✅ **Multiple Output Formats** - Detailed, summary, and JSON formats

## Usage Examples

### Your Example Data Decoded

Based on your provided data:

```
IO132 Security State Flags: bit0, bit28, bit32, bit36, bit55 (0x00000000000000000080001110000001)
IO517 Security State Flags P4: bit2, bit3, bit4, bit5, bit18, bit32, bit39, bit41 (0x0000000000000000000002810004003C)
```

**Decoded IO517 Security State Flags P4:**
- CAN1 connected, currently no data is received
- CAN2 not connected does not need connection  
- CAN3 not connected does not need connection
- Handbrake is active (bit 18)
- Additional unknown flags at bits 32, 39, 41

### Using the Django Management Command

```bash
# Decode your example data
python manage.py decode_teltonika_flags --example

# Decode specific flag types
python manage.py decode_teltonika_flags --io517 "0x0000000000000000000002810004003C"
python manage.py decode_teltonika_flags --io132 "0x00000000000000000080001110000001"

# Different output formats
python manage.py decode_teltonika_flags --io517 "0x0000000000000000000002810004003C" --format summary
python manage.py decode_teltonika_flags --io517 "0x0000000000000000000002810004003C" --format json
```

### Using in Django Models

```python
# Get a GPS record
record = GPSRecord.objects.first()

# Access decoded flags
security_flags = record.security_flags_p4_decoded
control_flags = record.control_flags_p4_decoded

# Get human-readable summaries
print(record.security_flags_p4_summary)
print(record.control_flags_p4_summary)

# Access specific flag information
for flag_name, flag_info in security_flags.items():
    if flag_info['active']:
        print(f"Active: {flag_info['description']} (bit {flag_info.get('bit_position', 'N/A')})")
```

### Using the Decoder Directly

```python
from gps_data.teltonika_decoder import decode_security_state_flags_p4

# Decode your data
flags = decode_security_state_flags_p4("0x0000000000000000000002810004003C")

# Check specific flags
if flags['handbrake_active']['active']:
    print("Handbrake is active!")

if flags['can1_status']['value'] == 1:
    print("CAN1 is receiving data")
```

## Django Admin Interface

The Django admin now displays decoded flags in a human-readable format:

1. **Raw Binary Data**: Shows the original hex values and bit positions
2. **Decoded Flags Display**: Shows the actual meaning of each active flag according to Teltonika specification

Navigate to any GPSRecord in the admin interface and check the "State Flags" section to see both raw and decoded flag information.

## Supported Flag Types

### IO517 Security State Flags P4

Based on Teltonika specification:

| Byte | Bit | Description | Supported |
|------|-----|-------------|-----------|
| 0 | 0-1 | CAN1 connection status | ✅ |
| 0 | 2-3 | CAN2 connection status | ✅ |
| 0 | 4-5 | CAN3 connection status | ✅ |
| 1 | 8 | Ignition on | ✅ |
| 1 | 9 | Key in ignition lock | ✅ |
| 1 | 10 | Webasto | ✅ |
| 1 | 11 | Engine is working | ✅ |
| 1 | 12 | Standalone engine | ✅ |
| 1 | 13 | Ready to drive | ✅ |
| 1 | 14 | Engine working on CNG | ✅ |
| 1 | 15 | Work mode (private/company) | ✅ |
| 2 | 16 | Operator is present | ✅ |
| 2 | 17 | Interlock active | ✅ |
| 2 | 18 | Handbrake is active | ✅ |
| 2 | 19 | Footbrake is active | ✅ |
| 2 | 20 | Clutch is pushed | ✅ |

### CAN Connection Status Values

- `0x00`: Connected, currently no data is received
- `0x01`: Connected, currently data is received  
- `0x02`: Not connected, needs connection
- `0x03`: Not connected does not need connection

## API Integration

The decoder integrates seamlessly with your existing Django API. All GPSRecord model instances now have these new properties:

```python
# In your API views/serializers
class GPSRecordSerializer(serializers.ModelSerializer):
    decoded_security_flags = serializers.SerializerMethodField()
    
    def get_decoded_security_flags(self, obj):
        return {
            'io132_summary': obj.security_flags_summary,
            'io517_summary': obj.security_flags_p4_summary,
            'io518_summary': obj.control_flags_p4_summary,
            'io519_summary': obj.indicator_flags_p4_summary,
        }
```

## Testing the Decoder

Run the decoder with your example data to verify it's working:

```bash
cd teltonika-django
python manage.py decode_teltonika_flags --example
```

Expected output matches your data:
- IO132: bits 0, 28, 32, 36, 55 active
- IO517: CAN status, handbrake active, and additional flags at bits 32, 39, 41

## Database Integration

The decoder works with your existing binary field storage:
- Supports both bytes and integer inputs
- Handles little-endian byte order conversion
- Compatible with existing database records
- No migration required

## Compatibility

- ✅ **LV-CAN200** CAN adapter
- ✅ **ALL-CAN300** CAN adapter  
- ✅ **CAN-CONTROL** adapter
- ✅ **FMB110** device family
- ✅ All program numbers and firmware versions

## Support

For questions about flag meanings, refer to the official [Teltonika documentation](https://wiki.teltonika-gps.com/view/FMB110_CAN_adapters) or contact Teltonika support with your vehicle's make, model, and year.
