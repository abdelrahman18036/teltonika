# Teltonika Device Server

A Python server implementation for receiving and parsing real-time data from Teltonika GPS tracking devices. This server supports multiple Teltonika protocols and can handle both TCP and UDP connections.

## Supported Protocols

- **Codec8** (0x08) - Main protocol for AVL data
- **Codec8 Extended** (0x8E) - Extended version with variable-length IO elements
- **Codec16** (0x10) - Protocol with generation type support
- **Codec12** (0x0C) - GPRS command protocol

## Features

- ✅ IMEI authentication
- ✅ Real-time GPS data parsing
- ✅ IO element parsing (sensors, inputs, outputs)
- ✅ Multi-client support with threading
- ✅ TCP and UDP protocol support
- ✅ Proper acknowledgment responses
- ✅ CRC-16 validation
- ✅ Detailed logging and debugging

## Installation

1. Clone or download the files
2. Ensure you have Python 3.6+ installed
3. No additional dependencies required (uses only built-in libraries)

## Usage

### Starting the Server

```bash
python main.py
```

The server will prompt you to choose between TCP or UDP protocol:

```
Teltonika Device Server
======================
Supported protocols:
- Codec8 (0x08)
- Codec8 Extended (0x8E)
- Codec16 (0x10)
- Codec12 (0x0C)

Enter protocol (TCP/UDP) or 'quit' to exit: TCP
```

### Server Configuration

You can modify the server settings in `main.py`:

```python
HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 5000       # Server port
```

### Device Configuration

Configure your Teltonika device to send data to your server:

1. **Server IP**: Your server's IP address
2. **Server Port**: 5000 (or your configured port)
3. **Protocol**: TCP or UDP
4. **Codec**: Codec8, Codec8 Extended, or Codec16

## Testing

Use the included test client to verify your server is working:

```bash
python test_client.py
```

The test client provides several options:

1. **Test TCP with sample Codec8 data** - Uses real packet examples from Teltonika documentation
2. **Test UDP with sample data** - Tests UDP protocol with sample packets
3. **Test TCP with custom GPS coordinates** - Sends custom location data
4. **Exit** - Quit the test client

### Sample Output

When a device connects, you'll see output like this:

```
Teltonika TCP Server listening on 0.0.0.0:5000
New connection from ('192.168.1.100', 52341)
Device IMEI: 356307042441013
IMEI 356307042441013 accepted
Received 58 bytes: 000000000000003608010000016b40d8ea30010000000000000000000000000000000105021503010101425e0f01f10000601a014e0000000000000000010000c7cf
Processing Codec8 data...
Codec8 - Records: 1, Data Length: 54
Record 1: 2019-06-10 10:04:46, GPS: 0.000000, 0.000000
  IO Data: {21: 3, 1: 1, 66: 24079, 241: 24602, 78: 0}
Sent acknowledgment for 1 records
```

## Data Structure

### GPS Data

The server extracts the following GPS information:

- **Timestamp**: Date and time of the record
- **Latitude/Longitude**: GPS coordinates in decimal degrees
- **Altitude**: Height above sea level (meters)
- **Angle**: Direction from north pole (degrees)
- **Satellites**: Number of visible satellites
- **Speed**: Speed calculated from satellites (km/h)

### IO Elements

Common IO element IDs:

- **1**: Digital Input 1 (DIN1)
- **21**: GSM Signal strength
- **66**: External voltage
- **78**: iButton ID
- **239**: Ignition status
- **241**: Active GSM Operator

## Real Device Integration

### For your IoT device in the car:

1. **Configure device settings**:

   - Set server IP to your server's IP address
   - Set server port to 5000
   - Choose TCP protocol for reliable data transmission
   - Set codec to Codec8 or Codec8 Extended

2. **Data transmission**:

   - Your device will send IMEI for authentication
   - Server will accept/reject the device
   - Device will then send GPS and sensor data
   - Server will acknowledge each data packet

3. **Monitoring**:
   - Server logs all received data
   - GPS coordinates are displayed in decimal degrees
   - IO elements show sensor readings and status

## Protocol Details

### TCP Communication Flow

1. Device connects to server
2. Device sends IMEI (15 digits)
3. Server responds with 0x01 (accept) or 0x00 (reject)
4. Device sends AVL data packets
5. Server acknowledges with number of records received
6. Process repeats for each data transmission

### UDP Communication Flow

1. Device sends UDP packet with IMEI and AVL data
2. Server responds with acknowledgment packet
3. Device may retry if no acknowledgment received

## Troubleshooting

### Common Issues

1. **Connection refused**: Check if server is running and port is open
2. **IMEI rejected**: Verify IMEI format (15 digits)
3. **No data received**: Check device configuration and network connectivity
4. **Parsing errors**: Verify device is using supported codec

### Debug Mode

The server provides detailed hex dumps of received data for debugging:

```
Received 58 bytes: 000000000000003608010000016b40d8ea30...
```

## File Structure

```
├── main.py          # Main server implementation
├── test_client.py   # Test client for validation
└── README.md        # This documentation
```

## License

This project is open source and available under the MIT License.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## Support

For questions or support, please create an issue in the repository or refer to the Teltonika documentation for device-specific configuration details.
