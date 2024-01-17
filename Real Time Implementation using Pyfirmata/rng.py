import math
import numpy as np
import os
import dotenv

head = 0


def change_seed():
    dotenv_file = dotenv.find_dotenv()
    dotenv.load_dotenv(dotenv_file)
    os.environ["RANDOM_SEED"] = np.random.rand()*10000
    dotenv.set_key(dotenv_file, "RANDOM_SEED", os.environ["RANDOM_SEED"])


def get_seed():
    dotenv_file = dotenv.find_dotenv()
    dotenv.load_dotenv(dotenv_file)
    return os.environ["RANDOM_SEED"]


def search_rn(x):
    for i in range(256):
        if queue[i] == x:
            return i
    return -1


def pop():
    ele = queue[0]
    queue = queue[1:]
    queue.append(np.random.rand()*10000)
    return ele


np.random.seed(int(get_seed()))
queue = [math.floor(x) for x in np.random.rand(256)*(10**9)]
print(queue)
