# Smart Car Door Control

## Overview
This system allows you to control car door locks from one laptop (remote) to another laptop (car) over a network connection.

## Hardware Setup

### Laptop 1: Car System (Arduino Connected)
1. **Connect Arduino to laptop via USB**
2. **Install Arduino IDE and upload StandardFirmata:**
   - Open Arduino IDE
   - File → Examples → Firmata → StandardFirmata
   - Upload to Arduino
3. **Wire Arduino components:**
   ```
   Pin 13 → Lock LED (+ resistor)
   Pin 12 → Unlock LED (+ resistor)  
   Pin 9  → Servo motor signal wire
   Pin 8  → Buzzer positive
   GND    → All component grounds
   5V     → Power for servo/buzzer
   ```

### Laptop 2: Remote Control
- No hardware needed, just runs remote.py

## Software Setup

### Both Laptops:
```bash
# Install Python dependencies
pip install pyfirmata

# Copy these files to both laptops:
# - car.py
# - remote.py  
# - seed.json (MUST BE IDENTICAL ON BOTH!)
```

### Important: Seed File Synchronization
The `seed.json` file MUST be identical on both laptops:
1. Generate seed.json on one laptop
2. Copy the EXACT same file to the other laptop
3. Both laptops must start with the same iteration counter

## Network Setup

### Step 1: Connect Both Laptops to Same Network
- Both laptops on same WiFi network, OR
- Connect laptops with Ethernet cable, OR  
- Use mobile hotspot

### Step 2: Find Car Laptop IP Address
On the car laptop (Laptop 1), run:
```bash
# Windows
ipconfig

# Linux/Mac  
ifconfig
```
Note the IP address (e.g., 192.168.1.100)

### Step 3: Configure Firewall (Windows)
On car laptop, allow Python through Windows Firewall:
1. Windows Security → Firewall → Allow an app
2. Add Python.exe 
3. Enable for both Private and Public networks

## Running the System

### Step 1: Start Car System (Laptop 1)
```bash
cd /path/to/car/system
python car.py
```

You'll see output like:
```
CAR SYSTEM READY
Car system IP address: 192.168.1.100
Arduino status: CONNECTED
Laptop speaker: READY

To connect from remote laptop:
  python remote.py
  Then enter IP: 192.168.1.100
```

### Step 2: Start Remote Control (Laptop 2)
```bash
cd /path/to/car/system  
python remote.py
```

Enter the car laptop IP when prompted:
```
Car system IP address: 192.168.1.100
```

### Step 3: Send Commands!
```
Commands: 1=LOCK, 2=UNLOCK, 3=CHANGE IP, q=QUIT

Enter command (1/2/3/q): 2
```

## What Happens When You Send Commands

### UNLOCK Command:
- **Car laptop speaker**: Low pitch beep (600Hz, 500ms)
- **Arduino LED**: Pin 12 turns ON, Pin 13 turns OFF
- **Arduino servo**: Moves for 0.5 seconds
- **Arduino buzzer**: One long beep

### LOCK Command:  
- **Car laptop speaker**: Two high pitch beeps (800Hz, 200ms each)
- **Arduino LED**: Pin 13 blinks 3 times quickly
- **Arduino servo**: Moves for 0.5 seconds  
- **Arduino buzzer**: Two short beeps

## Troubleshooting

### Remote Can't Connect to Car
1. **Check IP address**: Make sure you're using the correct car laptop IP
2. **Check firewall**: Disable Windows Firewall temporarily to test
3. **Check network**: Both laptops on same network?
4. **Test ping**: From remote laptop: `ping 192.168.1.100`

### Arduino Not Working
1. **Check USB connection**: Arduino connected and recognized?
2. **Check COM port**: Update `ARDUINO_PORT` in car.py
3. **Check StandardFirmata**: Upload StandardFirmata sketch to Arduino
4. **Check wiring**: LEDs, servo, buzzer properly connected?

### No Sound from Laptop
- **Windows**: `winsound` module should work automatically
- **Linux/Mac**: Install additional sound libraries if needed

### Seed Synchronization Issues  
1. **Same seed.json**: Both laptops must have identical file
2. **Reset if needed**: Delete seed.json on both, restart car.py to generate new one
3. **Copy fresh**: Copy the new seed.json to remote laptop

## Security Notes
- This system uses rolling codes - each command uses a different hash
- Replay attacks are automatically blocked
- Rate limiting prevents brute force attacks
- Failed attempts result in temporary IP blocking

## Command Line Usage

### Car System (always interactive):
```bash
python car.py
```

### Remote Control:
```bash
# Interactive mode
python remote.py

# Single commands
python remote.py LOCK 192.168.1.100
python remote.py UNLOCK 192.168.1.100
```

## Testing
Run security tests from either laptop:
```bash
python test.py
```

This will test various attack scenarios to verify the security measures are working.