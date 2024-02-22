import pathlib
import os
import sys
import glob
import time
import json
import re
import traceback
import csv
import subprocess
import argparse
from multiprocessing import Pool
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG, log
import operator
import math
import matplotlib.pyplot as plt
import numpy as np
import shutil

from .util.ExTable import ExTable
from datetime import datetime, date, timedelta
import pandas as pd
from .util.Name import KgExpanderSplitter
from .util.Rename import Rename
import statistics
'''
_logger = getLogger(__name__)

def setArgument():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', help='set directory containing repositories to be analyzed')
    parser.add_argument('-D', help='dry run (only check how many archives will be created)', action='store_true', default=False)
    args = parser.parse_args()
    return args

allRecommend = np.array([0.381, 0.594, 0.357])
NoneRecommend = np.array([0.190, 0.914, 0.241])
RelationRecommend = np.array([0.240, 0.412, 0.217])
RenasRecommend = np.array([0.27, 0.428, 0.210])
args = setArgument()
fig, ax = plt.subplots()
bar_width = 0.40
alpha = 0.8
index = np.array([i*2+1 for i in range(3)])

gpoint = np.arange(0, 0.9, 0.1)
#plt.hlines(gpoint, 0.8, 6, linewidth=0.02, colors='gray')

plt.bar(index, NoneRecommend, bar_width,
alpha=alpha,color='green')

plt.bar(index + bar_width, RelationRecommend, bar_width,
alpha=alpha,color='pink')

plt.bar(index + bar_width*2, RenasRecommend, bar_width,
alpha=alpha,color='gold')

plt.bar(index + bar_width*3, allRecommend, bar_width,
alpha=alpha,color='blue')

plt.ylabel('ratio')
plt.xticks(index + bar_width*1.5, ["Precision", "Recall", "Fscore"])

plt.savefig(os.path.join(args.source, "showRQ.svg"), pad_inches = 0)

'''


def setArgument():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', help='set directory containing repositories to be analyzed')
    parser.add_argument('-D', help='dry run (only check how many archives will be created)', action='store_true', default=False)
    args = parser.parse_args()
    return args

args = setArgument()
filePath = args.source
archivePath = os.path.join(filePath, "archives")

dirs = os.listdir(archivePath)
dirsLength = len(dirs)
c = 1
for dir in dirs:
    if dir[0] == '.':
        continue
    repoPath = os.path.join(archivePath, dir, "repo")
    if not os.path.isdir(repoPath):
        continue
    print(f"{c} / {dirsLength}")
    print(f"{repoPath} is deleted")
    shutil.rmtree(repoPath)
    c += 1


