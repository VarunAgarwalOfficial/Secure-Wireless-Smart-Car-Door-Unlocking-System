import json
import random
from math import ceil
import hashlib

unlock_queue = []
lock_queue = []

def load_seed():
    with open("seed.json", "r") as f:
        data =  json.load(f)
    return data["seed"] , data["iter"]


def new_seed():
    with open("seed.json", "w") as f:
        data = {"seed": ceil(random.random() * 1000000000), "iter": 0}
        json.dump(data, f)

def save_iter():
    with open("seed.json", "r") as f:
        data =  json.load(f)
    data["iter"] = iter
    with open("seed.json", "w") as f:
        json.dump(data, f)



seed, iter = load_seed()


action = int(input("1 for LOCK , 2 for UNLOCK: "))
if action == 1:
    action = b"LOCK"
else:
    action = b"UNLOCK"

random.seed(seed)
for i in range(0, iter):
    random.random()

hashed_mac = hashlib.md5(repr(ceil(random.random() * 1000000000)).encode()).digest()
to_send = hashlib.md5((action + hashed_mac)).digest()





import socket
PORT = 5050
FORMAT = 'utf-8'

SERVER = "192.168.112.3"
ADDR = (SERVER, PORT)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(ADDR)

client.send(to_send)


iter += 1
save_iter()


