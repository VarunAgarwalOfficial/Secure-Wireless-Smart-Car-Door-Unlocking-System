#!/usr/bin/env python3
"""
Security Attack Testing Suite
Tests various attack scenarios against the car door control system.
Run this with the car.py server running to test security measures.

Requirements:
- car.py server must be running
- pyfirmata (optional, for hardware testing)
"""

import socket
import threading
import time
import json
import random
import hashlib
import sys
from concurrent.futures import ThreadPoolExecutor


# Test configuration
TARGET_HOST = "127.0.0.1"
TARGET_PORT = 5050
TEST_TIMEOUT = 5


def send_raw_data(data, expect_response=False):
    """
    Send raw data to server and return success status.
    Args:
        data: bytes to send
        expect_response: whether to expect a response
    Returns:
        bool: True if connection succeeded
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TEST_TIMEOUT)
        sock.connect((TARGET_HOST, TARGET_PORT))
        sock.send(data)
        
        if expect_response:
            response = sock.recv(1024)
        
        sock.close()
        return True
    except Exception:
        return False


def load_seed():
    """Load seed from JSON file for generating valid hashes."""
    try:
        with open("seed.json", "r") as f:
            data = json.load(f)
        return data["seed"], data["iter"]
    except:
        return None, None


def generate_valid_hash(command="UNLOCK"):
    """Generate a valid hash using the current seed and iteration."""
    seed, iteration = load_seed()
    if seed is None:
        return None
    
    # Same algorithm as remote.py
    random.seed(seed)
    for i in range(iteration):
        random.random()
    
    pseudorandom_num = int(random.random() * 1000000000)
    base_hash = hashlib.sha256(str(pseudorandom_num).encode()).digest()
    command_data = command.encode() + base_hash
    final_hash = hashlib.sha256(command_data).digest()
    
    return final_hash


def test_replay_attack():
    """
    Test 1: Replay Attack
    Send the same valid hash multiple times to test replay protection.
    """
    print("\n" + "="*50)
    print("TEST 1: REPLAY ATTACK")
    print("="*50)
    
    # Generate one valid hash
    valid_hash = generate_valid_hash("UNLOCK")
    if not valid_hash:
        print("[SKIP] Could not generate valid hash - seed.json missing?")
        return
    
    print("[INFO] Generated valid hash for replay test")
    
    # First send should succeed
    print("[TEST] Sending valid hash (first time)...")
    success1 = send_raw_data(valid_hash)
    print(f"[RESULT] First send: {'SUCCESS' if success1 else 'FAILED'}")
    
    time.sleep(1)
    
    # Second send should be blocked (replay attack)
    print("[TEST] Sending same hash again (replay attack)...")
    success2 = send_raw_data(valid_hash)
    print(f"[RESULT] Replay attempt: {'BLOCKED (expected)' if not success2 else 'NOT BLOCKED (vulnerability!)'}")
    
    # Try multiple replays
    print("[TEST] Attempting 5 more replays...")
    replay_successes = 0
    for i in range(5):
        if send_raw_data(valid_hash):
            replay_successes += 1
        time.sleep(0.1)
    
    print(f"[RESULT] {replay_successes}/5 replays succeeded (should be 0)")
    
    if replay_successes == 0:
        print("[PASS]  Replay attack protection working")
    else:
        print("[FAIL]  Replay attack protection failed")


def test_brute_force_attack():
    """
    Test 2: Brute Force Attack
    Send many random hashes to test if server blocks brute force attempts.
    """
    print("\n" + "="*50)
    print("TEST 2: BRUTE FORCE ATTACK")
    print("="*50)
    
    print("[INFO] Sending 20 random invalid hashes rapidly...")
    
    successes = 0
    start_time = time.time()
    
    for i in range(20):
        # Generate random invalid hash
        random_data = random.randbytes(32)  # 32 random bytes
        
        if send_raw_data(random_data):
            successes += 1
        
        time.sleep(0.1)  # Small delay to avoid overwhelming
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"[RESULT] {successes}/20 random hashes accepted")
    print(f"[RESULT] Test duration: {duration:.2f} seconds")
    
    if successes <= 2:  # Allow some tolerance for network delays
        print("[PASS]  Brute force protection working")
    else:
        print("[FAIL]  Too many invalid hashes accepted")


def test_rate_limiting():
    """
    Test 3: Rate Limiting
    Send requests rapidly from same IP to test rate limiting.
    """
    print("\n" + "="*50)
    print("TEST 3: RATE LIMITING")
    print("="*50)
    
    print("[INFO] Sending 10 requests rapidly to trigger rate limiting...")
    
    successes = 0
    start_time = time.time()
    
    # Send requests as fast as possible
    for i in range(10):
        random_data = random.randbytes(32)
        
        if send_raw_data(random_data):
            successes += 1
        # No delay - send as fast as possible
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"[RESULT] {successes}/10 rapid requests succeeded")
    print(f"[RESULT] Test duration: {duration:.2f} seconds")
    
    # Test if IP gets blocked after rate limiting
    print("[TEST] Testing if IP is blocked after rate limiting...")
    time.sleep(1)
    
    blocked_successes = 0
    for i in range(3):
        if send_raw_data(random.randbytes(32)):
            blocked_successes += 1
        time.sleep(0.5)
    
    print(f"[RESULT] {blocked_successes}/3 requests succeeded after rate limiting")
    
    if successes < 8 and blocked_successes == 0:
        print("[PASS]  Rate limiting working")
    else:
        print("[FAIL]  Rate limiting may not be working properly")


def test_dos_attack():
    """
    Test 4: DoS Attack
    Launch multiple concurrent connections to test DoS protection.
    """
    print("\n" + "="*50)
    print("TEST 4: DOS ATTACK (CONCURRENT CONNECTIONS)")
    print("="*50)
    
    def attack_thread(thread_id):
        """Single attack thread."""
        successes = 0
        for i in range(3):
            if send_raw_data(random.randbytes(32)):
                successes += 1
            time.sleep(0.1)
        return successes
    
    print("[INFO] Launching 15 concurrent attack threads...")
    
    start_time = time.time()
    total_successes = 0
    
    # Use ThreadPoolExecutor for concurrent attacks
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(attack_thread, i) for i in range(15)]
        
        for future in futures:
            try:
                result = future.result(timeout=10)
                total_successes += result
            except Exception as e:
                print(f"[ERROR] Thread failed: {e}")
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"[RESULT] {total_successes}/45 concurrent requests succeeded")
    print(f"[RESULT] Test duration: {duration:.2f} seconds")
    
    if total_successes < 20:  # Server should block most concurrent attacks
        print("[PASS]  DoS protection working")
    else:
        print("[FAIL]  DoS protection may be insufficient")


def test_malformed_data():
    """
    Test 5: Malformed Data Attack
    Send various types of malformed data to test input validation.
    """
    print("\n" + "="*50)
    print("TEST 5: MALFORMED DATA ATTACK")
    print("="*50)
    
    malformed_payloads = [
        b"",                    # Empty data
        b"A" * 1000,            # Oversized data
        b"\x00" * 32,           # Null bytes
        b"UNLOCK",              # Plain text command
        b"invalid hash data",   # Text data
        b"\xff" * 32,           # Invalid bytes
        "unicode string 🚗".encode('utf-8'),  # Unicode data
    ]
    
    print(f"[INFO] Testing {len(malformed_payloads)} malformed payloads...")
    
    successes = 0
    for i, payload in enumerate(malformed_payloads):
        print(f"[TEST] Payload {i+1}: {len(payload)} bytes")
        
        if send_raw_data(payload):
            successes += 1
            print(f"         Accepted (vulnerability!)")
        else:
            print(f"         Rejected")
        
        time.sleep(0.2)
    
    print(f"[RESULT] {successes}/{len(malformed_payloads)} malformed payloads accepted")
    
    if successes == 0:
        print("[PASS]  Input validation working")
    else:
        print("[FAIL]  Some malformed data was accepted")


def test_hash_length_attack():
    """
    Test 6: Hash Length Attack
    Test with different hash lengths to check validation.
    """
    print("\n" + "="*50)
    print("TEST 6: HASH LENGTH ATTACK")
    print("="*50)
    
    hash_lengths = [1, 16, 31, 33, 64, 128, 256]
    
    print(f"[INFO] Testing hashes of different lengths...")
    
    successes = 0
    for length in hash_lengths:
        payload = random.randbytes(length)
        print(f"[TEST] Hash length: {length} bytes")
        
        if send_raw_data(payload):
            successes += 1
            print(f"         Accepted")
        else:
            print(f"         Rejected")
        
        time.sleep(0.1)
    
    print(f"[RESULT] {successes}/{len(hash_lengths)} different length hashes accepted")
    
    if successes <= 1:  # Only 32-byte hashes should be accepted
        print("[PASS]  Hash length validation working")
    else:
        print("[FAIL]  Multiple hash lengths accepted")


def test_timing_attack():
    """
    Test 7: Timing Attack
    Measure response times to detect timing vulnerabilities.
    """
    print("\n" + "="*50)
    print("TEST 7: TIMING ATTACK")
    print("="*50)
    
    print("[INFO] Measuring response times for timing analysis...")
    
    valid_hash = generate_valid_hash("UNLOCK")
    if not valid_hash:
        print("[SKIP] Cannot generate valid hash")
        return
    
    # Test valid hash timing
    valid_times = []
    for i in range(5):
        start = time.time()
        send_raw_data(valid_hash)
        end = time.time()
        valid_times.append(end - start)
        time.sleep(0.5)
    
    # Test invalid hash timing
    invalid_times = []
    for i in range(5):
        invalid_hash = random.randbytes(32)
        start = time.time()
        send_raw_data(invalid_hash)
        end = time.time()
        invalid_times.append(end - start)
        time.sleep(0.5)
    
    avg_valid = sum(valid_times) / len(valid_times)
    avg_invalid = sum(invalid_times) / len(invalid_times)
    time_diff = abs(avg_valid - avg_invalid)
    
    print(f"[RESULT] Average valid hash time: {avg_valid:.4f}s")
    print(f"[RESULT] Average invalid hash time: {avg_invalid:.4f}s")
    print(f"[RESULT] Time difference: {time_diff:.4f}s")
    
    if time_diff < 0.01:  # Less than 10ms difference
        print("[PASS]  No significant timing difference detected")
    else:
        print("[WARN]  Timing difference may allow timing attacks")


def test_connection_exhaustion():
    """
    Test 8: Connection Exhaustion
    Try to exhaust server's connection pool.
    """
    print("\n" + "="*50)
    print("TEST 8: CONNECTION EXHAUSTION")
    print("="*50)
    
    print("[INFO] Testing connection exhaustion with held connections...")
    
    sockets = []
    successful_connections = 0
    
    try:
        # Try to open many connections and hold them
        for i in range(50):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((TARGET_HOST, TARGET_PORT))
                sockets.append(sock)
                successful_connections += 1
                
                if i % 10 == 0:
                    print(f"[INFO] Opened {successful_connections} connections...")
                
            except Exception as e:
                print(f"[INFO] Connection {i+1} failed: {e}")
                break
        
        print(f"[RESULT] Opened {successful_connections} simultaneous connections")
        
        # Try to send data on a new connection while others are held
        print("[TEST] Attempting new connection while others are held...")
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.settimeout(5)
            test_sock.connect((TARGET_HOST, TARGET_PORT))
            test_sock.send(random.randbytes(32))
            test_sock.close()
            print("[RESULT] New connection succeeded despite held connections")
        except Exception as e:
            print(f"[RESULT] New connection failed: {e}")
    
    finally:
        # Clean up held connections
        print("[CLEANUP] Closing held connections...")
        for sock in sockets:
            try:
                sock.close()
            except:
                pass
    
    if successful_connections < 20:
        print("[PASS]  Connection limits working")
    else:
        print("[WARN]  Many connections accepted - check server limits")


def test_hardware_functionality():
    """
    Test 9: Hardware Functionality
    Test if hardware control is working (if Arduino is connected).
    """
    print("\n" + "="*50)
    print("TEST 9: HARDWARE FUNCTIONALITY")
    print("="*50)
    
    print("[INFO] Testing hardware by sending valid commands...")
    
    # Generate a few valid commands to test hardware
    valid_commands = []
    seed, iteration = load_seed()
    
    if seed is None:
        print("[SKIP] Cannot test hardware - seed.json missing")
        return
    
    print("[TEST] Sending UNLOCK command to test hardware...")
    unlock_hash = generate_valid_hash("UNLOCK")
    if unlock_hash:
        success = send_raw_data(unlock_hash)
        print(f"[RESULT] Unlock command: {'SUCCESS' if success else 'FAILED'}")
        if success:
            print("[INFO] Check Arduino LEDs and listen for buzzer sound")
        time.sleep(2)
    
    print("[TEST] Sending LOCK command to test hardware...")
    lock_hash = generate_valid_hash("LOCK")
    if lock_hash:
        success = send_raw_data(lock_hash)
        print(f"[RESULT] Lock command: {'SUCCESS' if success else 'FAILED'}")
        if success:
            print("[INFO] Check Arduino LEDs and listen for buzzer sound")
    
    print("[INFO] Hardware test complete - check server logs for hardware status")
    print("[NOTE] If no Arduino connected, commands still work in simulation mode")


def main():
    """
    Main test runner - executes all security tests.
    """
    print("Smart Car Security Testing Suite")
    print("================================")
    print(f"Target: {TARGET_HOST}:{TARGET_PORT}")
    print("Make sure car.py server is running before starting tests!")
    print()
    
    # Test server connectivity first
    print("Testing server connectivity...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((TARGET_HOST, TARGET_PORT))
        sock.close()
        print(" Server is reachable")
    except Exception as e:
        print(f" Cannot connect to server: {e}")
        print("Please start car.py server first!")
        sys.exit(1)
    
    # Run all tests
    tests = [
        test_replay_attack,
        test_brute_force_attack,
        test_rate_limiting,
        test_dos_attack,
        test_malformed_data,
        test_hash_length_attack,
        test_timing_attack,
        test_connection_exhaustion,
        test_hardware_functionality,
    ]
    
    start_time = time.time()
    
    for test_func in tests:
        try:
            test_func()
            time.sleep(2)  # Cool down between tests
        except KeyboardInterrupt:
            print("\n[INTERRUPTED] Tests stopped by user")
            break
        except Exception as e:
            print(f"\n[ERROR] Test failed with exception: {e}")
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    print("\n" + "="*50)
    print("TESTING COMPLETE")
    print("="*50)
    print(f"Total test duration: {total_duration:.2f} seconds")
    print("Check the car.py server logs for detailed security events.")
    print("\nNote: Some tests may show 'failures' if the server is properly")
    print("blocking attacks - this indicates the security is working!")


if __name__ == "__main__":
    main()