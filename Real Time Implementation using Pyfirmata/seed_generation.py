import json
import random
from math import ceil


def new_seed():
    with open("seed.json", "w") as f:
        data = {"seed": ceil(random.random() * 1000000000), "iter": 0}
        json.dump(data, f)
        f.close()


new_seed()
