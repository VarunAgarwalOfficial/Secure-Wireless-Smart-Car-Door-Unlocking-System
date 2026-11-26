# Secure IoV Unlocking System: Two-Laptop Hardware Demo

A two-laptop demonstration of rolling-code car door locking. One laptop plays the car and drives an Arduino (LEDs, servo signal line and buzzer) through pyFirmata; the other plays the remote and sends one-time lock and unlock codes over the local network.

This repository is the 2025 hardware and network rework of the demonstration for the paper "Secure Wireless Smart Car Door Unlocking System" (Springer, Lecture Notes in Networks and Systems, vol. 528, [doi:10.1007/978-981-19-5845-8_8](https://doi.org/10.1007/978-981-19-5845-8_8)). The paper's own repository is [Secure-Wireless-Smart-Car-Door-Unlocking-System](https://github.com/VarunAgarwalOfficial/Secure-Wireless-Smart-Car-Door-Unlocking-System).

## Why it is interesting

- **Rolling codes from a shared seed.** Both sides read the same `seed.json` (a seed and a counter), seed Python's `random` with it and skip ahead by the counter. The next number is turned into a code as `SHA-256(command + SHA-256(number))`, so a LOCK code cannot be reused as an UNLOCK code. The remote sends the raw 32-byte digest over TCP port 5050; the car sends nothing back.
- **A look-ahead window for resynchronisation.** The remote advances its counter after every send without waiting for a reply, so it can get ahead of the car, for example when the car dropped a code while rate limiting. The car therefore precomputes the next 128 codes for each command and accepts a match anywhere in that window, then moves its own counter just past the matched code. This is the same idea key fobs use to cope with button presses out of range. Codes behind the counter no longer match, and the car also keeps a set of digests it has already accepted, so a recorded code cannot be replayed.
- **Limits on guessing.** Each IP address may make 5 requests per 60 seconds; going over that blocks it for 60 seconds, and 3 failed or replayed codes block it for 5 minutes.
- **Limitations.** This is a demonstration, not a secure product. Python's `random` is not a cryptographic generator, the seed is a single integer stored in a plain file, and there is no encryption or authentication of the channel beyond the code itself. The `seed.json` committed here is public, so generate your own (see below).

## Run it

Python 3 on both laptops. Copy `car.py`, `remote.py` and `seed.json` to both.

```bash
pip install -r requirements.txt   # pyfirmata
```

### Shared seed

`seed.json` must be identical on both laptops, including the counter. Nothing in the repository creates it; to make a fresh one, run this once and copy the file to the other laptop:

```bash
python -c "import json, secrets; json.dump({'seed': secrets.randbelow(10**9), 'iter': 0}, open('seed.json', 'w'))"
```

If the car's counter ends up ahead of the remote's, or the remote gets more than 128 codes ahead, copy the same file to both laptops again.

### Car laptop: Arduino wiring

1. Upload StandardFirmata to the Arduino (Arduino IDE: File, Examples, Firmata, StandardFirmata) and connect it by USB.
2. Set `ARDUINO_PORT` in `car.py` to the Arduino's COM port (default `COM5`; see Device Manager, Ports).
3. Wire the components:

   ```
   Pin 13 -> Lock LED (+ resistor)
   Pin 12 -> Unlock LED (+ resistor)
   Pin 9  -> Servo motor signal wire
   Pin 8  -> Buzzer positive
   GND    -> All component grounds
   5V     -> Power for servo/buzzer
   ```

All four pins are driven as plain digital outputs: pin 9 gets a 0.5-second high pulse, not a servo PWM signal. `car.py` imports `winsound` together with pyFirmata, so Arduino control and the laptop beeps only work on Windows. On other systems it runs in simulation mode and only prints what it would do; on Windows with no Arduino attached it prints and beeps.

### Network

1. Put both laptops on the same network (Wi-Fi, Ethernet cable or a phone hotspot).
2. Find the car laptop's IP address (`ipconfig` on Windows, `ip addr` or `ifconfig` on Linux and macOS). `car.py` also prints it on start-up.
3. On Windows, allow Python through the firewall (Windows Security, Firewall, Allow an app) for private and public networks.

### Start it

On the car laptop:

```bash
python car.py
```

On the remote laptop:

```bash
python remote.py                         # interactive: enter the car's IP, then 1 = lock, 2 = unlock, 3 = change IP, q = quit
python remote.py UNLOCK 192.168.1.100    # single command
python remote.py LOCK 192.168.1.100
```

What the car does:

- **Unlock:** laptop beep (600 Hz, 0.5 s); unlock LED (pin 12) on, lock LED (pin 13) off; after 1 s, pin 9 pulsed for 0.5 s; one long buzzer beep.
- **Lock:** two laptop beeps (800 Hz, 0.2 s each); lock LED on and blinking three times; pin 9 pulsed for 0.5 s; two short buzzer beeps.

### Attack tests

With `car.py` running, run this on the car laptop (it targets `127.0.0.1:5050`):

```bash
python test.py
```

It tries replay, brute force, rate-limit, flooding, malformed and wrong-length data, timing and connection-exhaustion attacks, then sends a valid lock and unlock. It reads `seed.json` to build valid codes, so afterwards copy the car's `seed.json` to the remote again. Restarting `car.py` clears any IP blocks the tests trigger.

### Troubleshooting

- **Remote cannot connect:** check the IP address, that both laptops are on the same network (`ping` the car), and the Windows firewall.
- **Arduino not responding:** check the USB connection, `ARDUINO_PORT`, that StandardFirmata is uploaded, and the wiring.
- **Valid commands rejected:** the counters are out of step; copy the same `seed.json` to both laptops.

## Tech

Python 3 (sockets, hashlib, threading) with pyFirmata and an Arduino running StandardFirmata.

## Context

2025 rework of the hardware demonstration for the book chapter "Secure Wireless Smart Car Door Unlocking System" (Springer, LNNS vol. 528). The paper and original code are in [Secure-Wireless-Smart-Car-Door-Unlocking-System](https://github.com/VarunAgarwalOfficial/Secure-Wireless-Smart-Car-Door-Unlocking-System).

## Status

Finished, as of 26 November 2026. A 2022 prototype, not maintained. See [STATUS.md](STATUS.md).

## Licence

MIT, see LICENSE.
