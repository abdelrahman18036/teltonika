# Summary of Changes for Additional IO Parameters

## New Parameters Added
Based on the user's request, the following IO parameters have been added to both the Teltonika service and Django system:

### Parameters from user data: {"2": 0, "3": 0, "6": 2179, "9": 1955, "17": 89, "18": 986, "19": 65401, "71": 0}

1. **IO002 - Digital Input 2**: Logic 0/1 (Boolean)
2. **IO003 - Digital Input 3**: Logic 0/1 (Boolean)  
3. **IO006 - Analog Input 2**: 0-65535, 0.001V scale (2.179V in example)
4. **IO009 - Analog Input 1**: 0-65535, 0.001V scale (1.955V in example)
5. **IO017 - Axis X**: -8000 to 8000 mG (89 mG in example)
6. **IO018 - Axis Y**: -8000 to 8000 mG (986 mG in example) 
7. **IO019 - Axis Z**: -8000 to 8000 mG (65401 = -135 mG when converted from unsigned)
8. **IO071 - Dallas Temperature ID 4**: 8-byte sensor ID

## Files Modified

### 1. Django Models (`teltonika-django/gps_data/models.py`)
- Added new fields to GPSRecord model:
  - `digital_input_2` - BooleanField
  - `digital_input_3` - BooleanField  
  - `analog_input_1` - IntegerField (mV)
  - `analog_input_2` - IntegerField (mV)
  - `axis_x` - IntegerField (mG)
  - `axis_y` - IntegerField (mG)
  - `axis_z` - IntegerField (mG)
  - `dallas_temperature_id_4` - BigIntegerField

### 2. Django Serializers (`teltonika-django/gps_data/serializers.py`)
- Updated GPSRecordSerializer fields list to include new parameters
- Updated BulkGPSRecordSerializer field_mapping to map IO IDs to model fields:
  - IO002 → digital_input_2
  - IO003 → digital_input_3
  - IO006 → analog_input_2  
  - IO009 → analog_input_1
  - IO017 → axis_x
  - IO018 → axis_y
  - IO019 → axis_z
  - IO071 → dallas_temperature_id_4

### 3. Django Admin (`teltonika-django/gps_data/admin.py`)
- Added new fieldsets for better organization:
  - **Analog Inputs**: Shows raw mV values and converted voltage
  - **Accelerometer Data**: Shows X,Y,Z axis values in mG
  - **Temperature Sensors**: Shows Dallas sensor IDs
- Updated Digital I/O fieldset to include digital_input_2 and digital_input_3
- Added new filter options for digital inputs
- Added helper methods for user-friendly display:
  - `analog_voltage_1()` - Converts mV to V with 3 decimal places
  - `analog_voltage_2()` - Converts mV to V with 3 decimal places  
  - `accelerometer_summary()` - Shows X:Y:Z format

### 4. Database Migration (`teltonika-django/gps_data/migrations/0006_add_additional_io_parameters.py`)
- Created migration to add the new fields to the database
- All fields are nullable to support existing records

### 5. Teltonika Service (`teltonika-service/teltonika_service.py`)
- IO parameter definitions were already present in the `decode_io_parameters()` method
- Parameter formatting handles:
  - Digital inputs as HIGH/LOW
  - Analog inputs as voltage with 3 decimal places
  - Accelerometer as signed mG values
  - Dallas temperature ID as hex format

## Data Processing Flow

1. **Teltonika Device** → Sends IO data with parameters 2,3,6,9,17,18,19,71
2. **Teltonika Service** → Receives and decodes parameters using existing `io_meanings` dictionary
3. **Django API** → BulkGPSRecordSerializer maps IO IDs to specific model fields
4. **Database Storage** → New fields store the values with proper data types
5. **Django Admin** → Displays values in user-friendly format with units

## Value Conversions

- **Digital Inputs (IO002, IO003)**: 0/1 → Boolean False/True → "LOW"/"HIGH" display
- **Analog Inputs (IO006, IO009)**: Raw mV value → Stored as integer → Displayed as "X.XXXv"
- **Accelerometer (IO017-019)**: Signed mG values → Handle 16-bit signed conversion → "XXX mG" display  
- **Dallas ID (IO071)**: 64-bit ID → Stored as BigInteger → "0xXXXXXXXXXXXXXXXX" display

## Example Data Processing

Input: `{"2": 0, "3": 0, "6": 2179, "9": 1955, "17": 89, "18": 986, "19": 65401, "71": 0}`

Database Storage:
- digital_input_2: False
- digital_input_3: False  
- analog_input_2: 2179 (mV)
- analog_input_1: 1955 (mV)
- axis_x: 89 (mG)
- axis_y: 986 (mG)
- axis_z: -135 (mG, converted from 65401)
- dallas_temperature_id_4: 0

Admin Display:
- Digital Input 2: LOW
- Digital Input 3: LOW
- Analog Input 2: 2.179V  
- Analog Input 1: 1.955V
- Accelerometer: X:89 Y:986 Z:-135 mG
- Dallas Temperature ID 4: No sensor (when 0)

All changes maintain backward compatibility and follow the existing code patterns.
