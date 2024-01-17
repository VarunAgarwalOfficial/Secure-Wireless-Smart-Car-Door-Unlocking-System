import json
import random
from math import ceil
import hashlib
# from pyfirmata import Arduino
import time
import winsound


# board = Arduino("COM5")
# print("Communication Successfully started")
unlock_queue = []
lock_queue = []

def load_seed():
    with open("seed.json", "r") as f:
        data =  json.load(f)
        f.close()
    return data["seed"] , data["iter"]


def new_seed():
    with open("seed.json", "w") as f:
        data = {"seed": ceil(random.random() * 1000000000), "iter": 0}
        json.dump(data, f)
        f.close()



def generate_queue(seed, iter):
    global lock_queue
    global unlock_queue
    unlock_queue = []
    lock_queue = []
    random.seed(seed)
    for i in range(0, iter - 1):
        random.random()
    queue = []
    for i in range(0, 128):
        queue.append(ceil(random.random() * 1000000000))
    
    for i in queue:
        hashed_mac = hashlib.sha256(repr(i).encode()).digest()
        unlock_queue.append(hashlib.sha256((b"UNLOCK" + hashed_mac)).digest())
        lock_queue.append(hashlib.sha256((b"LOCK" + hashed_mac)).digest())

    
def save_iter():
    data = {"seed": seed, "iter": iter}
    with open("seed.json", "w") as f:
        json.dump(data, f)



seed, iter = load_seed()
generate_queue(seed,iter)









import socket 

PORT = 5050
SERVER = socket.gethostbyname(socket.gethostname())
SERVER = "192.168.192.3"
# ADDR = (, PORT)
ADDR = (SERVER, PORT)
FORMAT = 'utf-8'

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)

print("[STARTING] server is starting...")
print(f"[LISTENING] Server is listening on {SERVER}")
server.listen()



def handle_client(conn , addr):
    global iter
    print(f"[NEW CONNECTION] {addr} connected.")
    msg = conn.recv(128)
    print(f"[RECEIVED] {msg}")
    for i in range(len(unlock_queue)):
        if msg == unlock_queue[i]:
            print(f"[UNLOCK] {msg}")
            
            winsound.Beep(440, 500)
            for j in range(10):
                # board.digital[13].write(1)
                time.sleep(0.00000001)
                # board.digital[13].write(0)
                time.sleep(0.00000001)
            # board.digital[8].write(1)
            iter += i
            save_iter()
            break
        elif msg == lock_queue[i]:
            print(f"[LOCK] {msg}")
            for j in range(10):
                # board.digital[13].write(1)
                time.sleep(0.00000001)
                # board.digital[13].write(0)
                time.sleep(0.00000001)
            # board.digital[8].write(1)
            winsound.Beep(440, 500)
            # board.digital[8].write(1)
            time.sleep(0.1)
            # board.digital[8].write(0)
            time.sleep(0.1)
            
            winsound.Beep(440, 500)

            time.sleep(0.1)
            # board.digital[8].write(0)

            iter += i
            save_iter()
            break
    
    generate_queue(seed, iter)




while True:
    conn, addr = server.accept()
    handle_client(conn, addr)



