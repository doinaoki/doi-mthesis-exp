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

from .util.ExTable import ExTable
from datetime import datetime, date, timedelta
import pandas as pd
from .util.Name import KgExpanderSplitter
from .util.Rename import Rename
import statistics

_logger = getLogger(__name__)

researchFileNames = {
                    "recommend_none.json": "None",
                    "recommend_relation_normalize.json": "Normalize",
                    "recommend_relation.json": "Relation",
                    "recommend_all_normalize.json": "All"}

operations = ["insert", "delete", "replace", "order", "format"]
typeOfIdentifiers = ["ParameterName", "VariableName", "MethodName", "FieldName", "ClassName"]
UPPER_HOP = 100

def setArgument():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', help='set directory containing repositories to be analyzed')
    parser.add_argument('-D', help='dry run (only check how many archives will be created)', action='store_true', default=False)
    args = parser.parse_args()
    return args

AllRecommend = np.array([0.554985522,0.717062248,0.22431039707914202,0.5121484299818748,0.6504328645254336])
NormalizeRecommend = np.array([0.348337388378699, 0.563983442322067, 0.16727088162887785, 0.3311912853054191, 0.389316068065239])
args = setArgument()
fig, ax = plt.subplots()
bar_width = 0.25
alpha = 0.8
index = np.array([i+1 for i in range(5)])
plt.bar(index, AllRecommend, bar_width,
alpha=alpha,color='green')

plt.bar(index + bar_width, NormalizeRecommend, bar_width,
alpha=alpha,color='pink')

plt.ylabel('ratio')
plt.xticks(index + bar_width/2, ["MAP", "MRR", "top1", "top5", "top10"])
plt.legend()
plt.savefig(os.path.join(args.source, "figure", "showRQ.png"), pad_inches = 0)
