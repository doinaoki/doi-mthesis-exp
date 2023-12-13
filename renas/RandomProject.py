import random
import math

MAX = 187
selectedProject = math.ceil(MAX / 10)

for i in range(selectedProject):
    print(math.floor(random.random()*MAX))