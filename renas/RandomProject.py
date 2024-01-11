import random
import math

MAX = 187
#selectedProject = math.ceil(MAX / 10)
selectedProject = 4

#for i in range(selectedProject):
#    print(math.floor(random.random()*MAX)+1)

for _ in range(10):
    value = (random.random()*18)+1
    if value <= 10:
        print(value/10)
    else:
        print(value-9)