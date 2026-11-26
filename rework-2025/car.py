#!/usr/bin/env python3
"""
Car Door Control Server
Secure wireless smart car door unlocking system using rolling codes and SHA-256 hashing.
"""

import hashlib
import json
import random
import socket
import threading
import time
from collections import defaultdict

# Arduino hardware control (optional)
try:
    import winsound  # For Windows sound alerts

    from pyfirmata import Arduino

    HARDWARE_AVAILABLE = True
    print("[HARDWARE] PyFirmata available - hardware control enabled")
except ImportError:
    HARDWARE_AVAILABLE = False
    print("[HARDWARE] PyFirmata not available - simulation mode only")

# Global variables for rolling code system
unlock_queue = []
lock_queue = []
used_hashes = set()  # Track used hashes to prevent replay attacks

# Security tracking
failed_attempts = defaultdict(int)  # Track failed attempts per IP
request_times = defaultdict(list)  # Track request timestamps per IP
blocked_ips = {}  # Track temporarily blocked IPs

# Hardware control
board = None  # Arduino board object

# Arduino port configuration - UPDATE THIS FOR YOUR SYSTEM
ARDUINO_PORT = "COM5"  # Windows (check Device Manager)
# ARDUINO_PORT = "COM3"            # Windows alternative
# ARDUINO_PORT = "/dev/ttyUSB0"     # Linux
# ARDUINO_PORT = "/dev/ttyACM0"     # Linux alternative
# ARDUINO_PORT = "/dev/tty.usbmodem*" # macOS

# To find your Arduino port:
# Windows: Device Manager → Ports → Arduino Uno (COM#)
# Linux: ls /dev/tty* | grep -i usb
# macOS: ls /dev/tty.usb*

# System configuration
QUEUE_SIZE = 128
RATE_LIMIT_WINDOW = 60  # seconds
MAX_REQUESTS_PER_WINDOW = 5
BLOCK_DURATION = 300  # 5 minutes
MAX_FAILED_ATTEMPTS = 3

# Hardware pin configuration
LOCK_LED_PIN = 13  # LED indicator for lock status
UNLOCK_LED_PIN = 12  # LED indicator for unlock status
SERVO_PIN = 9  # Servo motor for door mechanism
BUZZER_PIN = 8  # Buzzer for audio feedback


def init_hardware():
    """
    Initialize Arduino board and hardware components.
    Returns: bool - True if hardware initialization successful
    """
    global board

    if not HARDWARE_AVAILABLE:
        print("[HARDWARE] PyFirmata not available - running in simulation mode")
        return False

    try:
        # Try to connect to Arduino
        print(f"[HARDWARE] Connecting to Arduino on {ARDUINO_PORT}...")
        board = Arduino(ARDUINO_PORT)

        # Configure pins
        board.digital[LOCK_LED_PIN].mode = 1  # OUTPUT
        board.digital[UNLOCK_LED_PIN].mode = 1  # OUTPUT
        board.digital[SERVO_PIN].mode = 1  # OUTPUT
        board.digital[BUZZER_PIN].mode = 1  # OUTPUT

        # Initialize all pins to LOW
        board.digital[LOCK_LED_PIN].write(0)
        board.digital[UNLOCK_LED_PIN].write(0)
        board.digital[SERVO_PIN].write(0)
        board.digital[BUZZER_PIN].write(0)

        print("[HARDWARE] ✓ Arduino connected successfully")

        # Test sequence - blink LEDs to show system is ready
        print("[HARDWARE] Running hardware test sequence...")
        for _ in range(3):
            board.digital[LOCK_LED_PIN].write(1)
            time.sleep(0.2)
            board.digital[LOCK_LED_PIN].write(0)
            board.digital[UNLOCK_LED_PIN].write(1)
            time.sleep(0.2)
            board.digital[UNLOCK_LED_PIN].write(0)

        return True

    except Exception as e:
        print(f"[HARDWARE] ✗ Failed to initialize Arduino: {e}")
        print("[HARDWARE] Continuing in simulation mode...")
        board = None
        return False


def load_seed():
    """
    Load seed and iteration counter from JSON file.
    Returns: tuple (seed, iteration_counter)
    """
    try:
        with open("seed.json", "r") as f:
            data = json.load(f)
        return data["seed"], data["iter"]
    except FileNotFoundError:
        print("[ERROR] seed.json not found! Run generate_seed() first.")
        raise
    except Exception as e:
        print(f"[ERROR] Failed to load seed: {e}")
        raise


def save_iteration(seed, iteration):
    """
    Save current iteration counter back to seed file.
    Args:
        seed: The random seed value
        iteration: Current iteration counter
    """
    try:
        data = {"seed": seed, "iter": iteration}
        with open("seed.json", "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save iteration: {e}")


def generate_queue(seed, iteration):
    """
    Generate rolling code queues for lock and unlock commands.
    Uses double SHA-256 hashing with MAC-then-encrypt pattern.

    Args:
        seed: Random seed for pseudorandom number generation
        iteration: Current iteration to sync with remote
    """
    global unlock_queue, lock_queue

    unlock_queue.clear()
    lock_queue.clear()

    # Initialize random generator with seed
    random.seed(seed)

    # Skip to current iteration to stay in sync with remote
    for i in range(iteration):
        random.random()

    # Generate queue of pseudorandom numbers
    temp_queue = []
    for i in range(QUEUE_SIZE):
        # Generate large pseudorandom number
        pseudorandom_num = int(random.random() * 1000000000)
        temp_queue.append(pseudorandom_num)

    # Create hashes for each command type using MAC-then-encrypt pattern
    for num in temp_queue:
        # First hash: Create MAC from pseudorandom number
        base_hash = hashlib.sha256(str(num).encode()).digest()

        # Second hash: Encrypt MAC + command (MAC-then-encrypt)
        unlock_data = b"UNLOCK" + base_hash
        lock_data = b"LOCK" + base_hash

        # Final hash digests for each command
        unlock_hash = hashlib.sha256(unlock_data).digest()
        lock_hash = hashlib.sha256(lock_data).digest()

        unlock_queue.append(unlock_hash)
        lock_queue.append(lock_hash)

    print(
        f"[INFO] Generated {len(unlock_queue)} unlock codes and {len(lock_queue)} lock codes"
    )


def check_rate_limit(client_ip):
    """
    Check if client IP is within rate limits.
    Args:
        client_ip: IP address of the client
    Returns:
        bool: True if within limits, False if rate limited
    """
    current_time = time.time()

    # Clean old requests outside the time window
    cutoff_time = current_time - RATE_LIMIT_WINDOW
    request_times[client_ip] = [t for t in request_times[client_ip] if t > cutoff_time]

    # Check if too many requests in time window
    if len(request_times[client_ip]) >= MAX_REQUESTS_PER_WINDOW:
        print(f"[SECURITY] Rate limit exceeded for {client_ip}")
        return False

    # Add current request timestamp
    request_times[client_ip].append(current_time)
    return True


def is_ip_blocked(client_ip):
    """
    Check if IP address is currently blocked.
    Args:
        client_ip: IP address to check
    Returns:
        bool: True if IP is blocked
    """
    if client_ip in blocked_ips:
        if time.time() < blocked_ips[client_ip]:
            return True
        else:
            # Unblock expired IP
            del blocked_ips[client_ip]
            print(f"[INFO] Unblocked {client_ip}")
    return False


def block_ip(client_ip, duration=BLOCK_DURATION):
    """
    Temporarily block an IP address.
    Args:
        client_ip: IP address to block
        duration: Block duration in seconds
    """
    blocked_ips[client_ip] = time.time() + duration
    print(f"[SECURITY] Blocked {client_ip} for {duration} seconds")


def simulate_car_action(action):
    """
    Control physical car door hardware (Arduino) AND laptop speaker.
    Args:
        action: "LOCK" or "UNLOCK"
    """
    global board

    if action == "LOCK":
        print("[CAR] Door locking mechanism activated")

        # LAPTOP SPEAKER - Always try to beep (two short beeps for lock)
        try:
            if HARDWARE_AVAILABLE:
                winsound.Beep(800, 200)  # High pitch beep
                time.sleep(0.1)
                winsound.Beep(800, 200)  # Second beep
                print("[SPEAKER] Lock sound played on laptop")
        except Exception as e:
            print(f"[SPEAKER] Could not play sound: {e}")

        # ARDUINO HARDWARE - Control LEDs and buzzer if connected
        if board is not None:
            try:
                print("[ARDUINO] Activating lock mechanism...")

                # Turn on lock LED, turn off unlock LED
                board.digital[LOCK_LED_PIN].write(1)
                board.digital[UNLOCK_LED_PIN].write(0)

                # Blink lock LED pattern (3 quick blinks)
                for _ in range(3):
                    board.digital[LOCK_LED_PIN].write(0)
                    time.sleep(0.1)
                    board.digital[LOCK_LED_PIN].write(1)
                    time.sleep(0.1)

                # Activate servo motor for lock mechanism
                board.digital[SERVO_PIN].write(1)
                time.sleep(0.5)  # Servo movement time
                board.digital[SERVO_PIN].write(0)

                # Arduino buzzer feedback - two short beeps
                for _ in range(2):
                    board.digital[BUZZER_PIN].write(1)
                    time.sleep(0.1)
                    board.digital[BUZZER_PIN].write(0)
                    time.sleep(0.1)

                print("[ARDUINO] Lock mechanism engaged - LED blinking, servo moved")

            except Exception as e:
                print(f"[ARDUINO] Error controlling lock mechanism: {e}")
        else:
            print("[ARDUINO] No Arduino connected - laptop speaker only")

    elif action == "UNLOCK":
        print("[CAR] Door unlocking mechanism activated")

        # LAPTOP SPEAKER - Always try to beep (one long beep for unlock)
        try:
            if HARDWARE_AVAILABLE:
                winsound.Beep(600, 500)  # Lower pitch, longer beep
                print("[SPEAKER] Unlock sound played on laptop")
        except Exception as e:
            print(f"[SPEAKER] Could not play sound: {e}")

        # ARDUINO HARDWARE - Control LEDs and buzzer if connected
        if board is not None:
            try:
                print("[ARDUINO] Activating unlock mechanism...")

                # Turn on unlock LED, turn off lock LED
                board.digital[UNLOCK_LED_PIN].write(1)
                board.digital[LOCK_LED_PIN].write(0)

                # Blink unlock LED pattern (steady on for 1 second)
                time.sleep(1.0)

                # Activate servo motor for unlock mechanism
                board.digital[SERVO_PIN].write(1)
                time.sleep(0.5)  # Servo movement time
                board.digital[SERVO_PIN].write(0)

                # Arduino buzzer feedback - one long beep
                board.digital[BUZZER_PIN].write(1)
                time.sleep(0.5)
                board.digital[BUZZER_PIN].write(0)

                print("[ARDUINO] Unlock mechanism engaged - LED on, servo moved")

            except Exception as e:
                print(f"[ARDUINO] Error controlling unlock mechanism: {e}")
        else:
            print("[ARDUINO] No Arduino connected - laptop speaker only")


def handle_client(conn, addr):
    """
    Handle incoming client connection and validate hash digest.
    Args:
        conn: Socket connection object
        addr: Client address tuple (ip, port)
    """
    global seed, iteration

    client_ip = addr[0]
    print(f"[CONNECTION] {client_ip} connected")

    try:
        # Security check: Is IP blocked?
        if is_ip_blocked(client_ip):
            print(f"[SECURITY] Blocked IP {client_ip} attempted connection")
            conn.close()
            return

        # Security check: Rate limiting
        if not check_rate_limit(client_ip):
            print(f"[SECURITY] Rate limiting {client_ip}")
            block_ip(client_ip, 60)  # Short block for rate limiting
            conn.close()
            return

        # Receive hash digest from client
        received_hash = conn.recv(128)

        if not received_hash:
            print(f"[ERROR] No data received from {client_ip}")
            conn.close()
            return

        print(f"[RECEIVED] {len(received_hash)} bytes from {client_ip}")

        # Check for replay attack
        if received_hash in used_hashes:
            print(f"[SECURITY] Replay attack detected from {client_ip}")
            failed_attempts[client_ip] += 1

            if failed_attempts[client_ip] >= MAX_FAILED_ATTEMPTS:
                block_ip(client_ip)

            conn.close()
            return

        # Search for matching hash in queues
        command_found = False
        codes_checked = 0

        # Check unlock queue
        for i, unlock_hash in enumerate(unlock_queue):
            codes_checked += 1
            if received_hash == unlock_hash:
                print(f"[UNLOCK] Valid unlock command from {client_ip}")

                # Execute unlock action
                simulate_car_action("UNLOCK")

                # Mark hash as used (prevent replay)
                used_hashes.add(received_hash)

                # Update iteration counter (consume codes up to this point)
                iteration += i + 1
                save_iteration(seed, iteration)

                # Regenerate queue from new position
                generate_queue(seed, iteration)

                # Reset failed attempts on success
                failed_attempts[client_ip] = 0

                command_found = True
                break

        # Check lock queue if unlock not found
        if not command_found:
            for i, lock_hash in enumerate(lock_queue):
                codes_checked += 1
                if received_hash == lock_hash:
                    print(f"[LOCK] Valid lock command from {client_ip}")

                    # Execute lock action
                    simulate_car_action("LOCK")

                    # Mark hash as used
                    used_hashes.add(received_hash)

                    # Update iteration counter
                    iteration += i + 1
                    save_iteration(seed, iteration)

                    # Regenerate queue
                    generate_queue(seed, iteration)

                    # Reset failed attempts
                    failed_attempts[client_ip] = 0

                    command_found = True
                    break

        # Handle invalid hash
        if not command_found:
            print(
                f"[SECURITY] Invalid hash from {client_ip} (checked {codes_checked} codes)"
            )
            failed_attempts[client_ip] += 1

            # Progressive blocking based on failed attempts
            if failed_attempts[client_ip] >= MAX_FAILED_ATTEMPTS:
                block_ip(client_ip)
            elif failed_attempts[client_ip] >= 2:
                print(
                    f"[WARNING] {client_ip} has {failed_attempts[client_ip]} failed attempts"
                )

    except Exception as e:
        print(f"[ERROR] Error handling client {client_ip}: {e}")

    finally:
        conn.close()


def cleanup_old_data():
    """
    Periodic cleanup of old security data to prevent memory leaks.
    Runs in background thread.
    """
    while True:
        try:
            current_time = time.time()

            # Clean old request times (keep only last hour)
            cutoff_time = current_time - 3600
            for ip in list(request_times.keys()):
                request_times[ip] = [t for t in request_times[ip] if t > cutoff_time]
                if not request_times[ip]:
                    del request_times[ip]

            # Clean expired IP blocks
            expired_ips = [
                ip
                for ip, unblock_time in blocked_ips.items()
                if current_time >= unblock_time
            ]
            for ip in expired_ips:
                del blocked_ips[ip]
                print(f"[INFO] Auto-unblocked {ip}")

            # Limit used_hashes size (keep last 1000)
            if len(used_hashes) > 1000:
                # Convert to list, keep last 1000, convert back to set
                hash_list = list(used_hashes)
                used_hashes.clear()
                used_hashes.update(hash_list[-1000:])

            print(
                f"[CLEANUP] Active connections tracked: {len(request_times)}, "
                f"Blocked IPs: {len(blocked_ips)}, Used hashes: {len(used_hashes)}"
            )

        except Exception as e:
            print(f"[ERROR] Cleanup error: {e}")

        time.sleep(300)  # Run every 5 minutes


def get_local_ip():
    """
    Get the local IP address of this machine.
    Returns: IP address string
    """
    try:
        # Connect to a remote address to determine local IP
        # This doesn't actually send data
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"


def main():
    """
    Main server function - sets up socket and handles connections.
    """
    global seed, iteration

    print("=== Smart Car Door Control Server ===")

    # Initialize hardware first
    hardware_ready = init_hardware()

    # Load seed and iteration from file
    seed, iteration = load_seed()
    print(f"[INIT] Loaded seed: {seed}, iteration: {iteration}")

    # Generate initial rolling code queues
    generate_queue(seed, iteration)

    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_old_data, daemon=True)
    cleanup_thread.start()

    # Network configuration
    HOST = "0.0.0.0"  # Listen on all interfaces
    PORT = 5050

    # Create and configure server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)

        # Get local IP for remote connection info
        local_ip = get_local_ip()

        print("[STARTING] Car door control server")
        print(f"[LISTENING] Server listening on {HOST}:{PORT}")
        print(
            f"[STATUS] Queue size: {QUEUE_SIZE}, Rate limit: {MAX_REQUESTS_PER_WINDOW}/{RATE_LIMIT_WINDOW}s"
        )
        print(
            f"[HARDWARE] Hardware control: {'ENABLED' if hardware_ready else 'SIMULATION'}"
        )
        print()
        print("=" * 50)
        print("CAR SYSTEM READY")
        print("=" * 50)
        print(f"Car system IP address: {local_ip}")
        print(f"Arduino status: {'CONNECTED' if board else 'NOT CONNECTED'}")
        print(f"Laptop speaker: {'READY' if HARDWARE_AVAILABLE else 'NOT AVAILABLE'}")
        print()
        print("To connect from remote laptop:")
        print("  python remote.py")
        print(f"  Then enter IP: {local_ip}")
        print()
        print("Waiting for remote commands...")
        print("=" * 50)
        print()

        while True:
            try:
                # Accept new connection
                conn, addr = server_socket.accept()

                # Handle client in separate thread for concurrency
                client_thread = threading.Thread(
                    target=handle_client, args=(conn, addr), daemon=True
                )
                client_thread.start()

            except KeyboardInterrupt:
                print("\n[SHUTDOWN] Server shutting down...")
                break
            except Exception as e:
                print(f"[ERROR] Server error: {e}")

    except Exception as e:
        print(f"[FATAL] Failed to start server: {e}")

    finally:
        # Cleanup hardware on shutdown
        if board is not None:
            try:
                print("[SHUTDOWN] Turning off all hardware...")
                board.digital[LOCK_LED_PIN].write(0)
                board.digital[UNLOCK_LED_PIN].write(0)
                board.digital[SERVO_PIN].write(0)
                board.digital[BUZZER_PIN].write(0)
                board.exit()
            except:
                pass

        server_socket.close()
        print("[SHUTDOWN] Server stopped")


if __name__ == "__main__":
    main()
