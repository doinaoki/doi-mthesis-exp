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

similarityRecommend = np.array([0.484487986,0.625223649,0.17763514134615685,0.45577113202362024,0.620759483641038])
relationRecommend = np.array([0.519168647, 0.692355771, 0.20848483890952374, 0.48251721643393886, 0.6101030927341484])
allRecommend = np.array([0.536724229, 0.714280916, 0.21908170720380346, 0.4985627557210174, 0.6319131091941322])
args = setArgument()
fig, ax = plt.subplots()
bar_width = 0.25
alpha = 0.8
index = np.array([i+1 for i in range(5)])

gpoint = np.arange(0, 0.8, 0.1)
plt.hlines(gpoint, 0.8, 6, linewidth=0.1, colors='gray')

plt.bar(index, similarityRecommend, bar_width,
alpha=alpha,color='green')

plt.bar(index + bar_width, relationRecommend, bar_width,
alpha=alpha,color='pink')

plt.bar(index + bar_width*2, allRecommend, bar_width,
alpha=alpha,color='gold')

plt.ylabel('ratio')
plt.xticks(index + bar_width, ["MAP", "MRR", "top1", "top5", "top10"])

plt.savefig(os.path.join(args.source, "figure", "showRQ.png"), pad_inches = 0)

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


