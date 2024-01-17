import socket
import numpy as np


PORT = 5050
SERVER = socket.gethostbyname(socket.gethostname())
SERVER = "192.168.112.3"
# ADDR = (, PORT)
ADDR = (SERVER, PORT)
FORMAT = 'utf-8'

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(ADDR)

for i in range(0,256):
    client.send(str(np.random.randint(2)).encode())





