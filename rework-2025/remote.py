#!/usr/bin/env python3
"""
Remote Car Control Client
Generates rolling codes and sends commands to car door control server.
"""

import json
import random
import hashlib
import socket
import sys
import time


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
        print("[ERROR] seed.json not found!")
        print("Make sure the seed file exists and is accessible.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to load seed: {e}")
        sys.exit(1)


def save_iteration(seed, iteration):
    """
    Save updated iteration counter back to seed file.
    Args:
        seed: The random seed value
        iteration: New iteration counter value
    """
    try:
        # Load existing data to preserve other fields
        with open("seed.json", "r") as f:
            data = json.load(f)
        
        # Update iteration counter
        data["iter"] = iteration
        
        # Save back to file
        with open("seed.json", "w") as f:
            json.dump(data, f, indent=2)
            
    except Exception as e:
        print(f"[ERROR] Failed to save iteration: {e}")


def generate_hash(seed, iteration, command):
    """
    Generate hash digest for specified command using rolling code.
    Uses double SHA-256 hashing with MAC-then-encrypt pattern.
    
    Args:
        seed: Random seed for pseudorandom number generation
        iteration: Current iteration counter
        command: "LOCK" or "UNLOCK"
    
    Returns:
        bytes: Hash digest to send to car
    """
    # Initialize random generator with seed
    random.seed(seed)
    
    # Skip to current iteration to get next code
    for i in range(iteration):
        random.random()
    
    # Generate next pseudorandom number
    pseudorandom_num = int(random.random() * 1000000000)
    
    # First hash: Create MAC from pseudorandom number
    base_hash = hashlib.sha256(str(pseudorandom_num).encode()).digest()
    
    # Second hash: Encrypt MAC + command (MAC-then-encrypt pattern)
    command_data = command.encode() + base_hash
    final_hash = hashlib.sha256(command_data).digest()
    
    return final_hash


def send_command(host, port, command):
    """
    Send command to car door control server.
    Args:
        host: Server hostname/IP
        port: Server port number
        command: "LOCK" or "UNLOCK"
    Returns:
        bool: True if command sent successfully
    """
    try:
        # Load current seed and iteration
        seed, iteration = load_seed()
        
        # Generate hash for this command
        hash_digest = generate_hash(seed, iteration, command)
        
        print(f"[REMOTE] Sending {command} command to {host}:{port}")
        print(f"[INFO] Using iteration: {iteration}")
        
        # Create socket connection
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(10)  # 10 second timeout
        
        # Connect to car server
        print(f"[CONNECTING] Connecting to car system...")
        client_socket.connect((host, port))
        print(f"[CONNECTED] Connected to car system!")
        
        # Send hash digest
        client_socket.send(hash_digest)
        print(f"[SENT] Command hash sent to car")
        
        # Close connection
        client_socket.close()
        
        # Update iteration counter (increment for next use)
        save_iteration(seed, iteration + 1)
        
        print(f"[SUCCESS]  {command} command sent successfully!")
        print(f"[INFO] Listen for laptop speaker beep and check Arduino LEDs")
        return True
        
    except socket.timeout:
        print(f"[ERROR]  Connection timeout - car system may be unreachable")
        print(f"[HINT] Make sure car.py is running on {host}")
        return False
    except ConnectionRefused:
        print(f"[ERROR]  Connection refused - car system may be down")
        print(f"[HINT] Check if car.py server is running on {host}:{port}")
        return False
    except OSError as e:
        print(f"[ERROR]  Network error: {e}")
        print(f"[HINT] Check if {host} is reachable on your network")
        return False
    except Exception as e:
        print(f"[ERROR]  Failed to send command: {e}")
        return False


def get_car_ip():
    """
    Get car system IP address from user.
    Returns: IP address string
    """
    print("\n=== Car System Network Configuration ===")
    print("Enter the IP address of the laptop running car.py")
    print("Examples:")
    print("  192.168.1.100  (if car laptop IP is 192.168.1.100)")
    print("  127.0.0.1      (if testing on same machine)")
    print()
    
    while True:
        ip = input("Car system IP address: ").strip()
        
        if not ip:
            print("Please enter an IP address")
            continue
            
        # Basic IP validation
        parts = ip.split('.')
        if len(parts) == 4:
            try:
                for part in parts:
                    num = int(part)
                    if not (0 <= num <= 255):
                        raise ValueError()
                return ip
            except ValueError:
                pass
        
        print("Invalid IP address format. Please try again.")


def interactive_mode():
    """
    Interactive mode for sending commands.
    """
    print("=== Smart Car Remote Control ===")
    print("This remote will connect to car.py running on another laptop")
    print()
    
    # Get car system IP address
    HOST = get_car_ip()
    PORT = 5050
    
    print(f"\n Target configured: {HOST}:{PORT}")
    print()
    print("Commands: 1=LOCK, 2=UNLOCK, 3=CHANGE IP, q=QUIT")
    print("When you send a command:")
    print("  • Car laptop speaker will beep")
    print("  • Arduino LEDs will blink")
    print()
    
    while True:
        try:
            choice = input("Enter command (1/2/3/q): ").strip()
            
            if choice.lower() == 'q':
                print("Remote control shutting down. Goodbye!")
                break
                
            elif choice == '1':
                print("\n" + "="*40)
                send_command(HOST, PORT, "LOCK")
                print("="*40)
                
            elif choice == '2':
                print("\n" + "="*40)
                send_command(HOST, PORT, "UNLOCK")  
                print("="*40)
                
            elif choice == '3':
                print()
                HOST = get_car_ip()
                print(f" Target updated: {HOST}:{PORT}")
                
            else:
                print("Invalid choice. Use:")
                print("  1 = LOCK car")
                print("  2 = UNLOCK car") 
                print("  3 = Change car IP")
                print("  q = Quit")
            
            print()  # Empty line for readability
            
        except KeyboardInterrupt:
            print("\nRemote control shutting down. Goodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    """
    Main function - handles command line arguments or starts interactive mode.
    """
    # Check for command line arguments
    if len(sys.argv) >= 2:
        command_arg = sys.argv[1].upper()
        
        if command_arg in ["LOCK", "UNLOCK"]:
            # Command line mode - need IP address
            if len(sys.argv) >= 3:
                # IP provided as argument
                HOST = sys.argv[2]
            else:
                # Ask for IP
                HOST = get_car_ip()
            
            PORT = 5050
            
            print(f"\n=== Remote Command: {command_arg} ===")
            success = send_command(HOST, PORT, command_arg)
            sys.exit(0 if success else 1)
            
        else:
            print("Usage:")
            print("  python remote.py                       # Interactive mode")
            print("  python remote.py LOCK                  # Single command (will ask for IP)")
            print("  python remote.py UNLOCK 192.168.1.100  # Single command with IP")
            sys.exit(1)
    
    elif len(sys.argv) == 1:
        # Interactive mode
        interactive_mode()
    
    else:
        print("Usage:")
        print("  python remote.py                        # Interactive mode") 
        print("  python remote.py LOCK                   # Single command (will ask for IP)")
        print("  python remote.py UNLOCK 192.168.1.100   # Single command with IP")
        sys.exit(1)


if __name__ == "__main__":
    main()