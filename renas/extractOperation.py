import pathlib
import simplejson
import os
import argparse
import time
from datetime import datetime, date, timedelta
import heapq
import csv
import subprocess
import re
import pandas as pd
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG, log, basicConfig
from copy import deepcopy
from .util.Rename import Rename

gitRe = re.compile(r'(?:^commit)\s+(.+)\nAuthor:\s+(.+)\nDate:\s+(.+)\n', re.MULTILINE)
commitToDate = {}

def setGitlog(path):
    repoPath = os.path.join(path, "repo")
    cp = subprocess.run(f"cd {repoPath}; git log",shell=True, stdout=subprocess.PIPE)
    gitLog = cp.stdout.decode('utf-8','ignore')
    gitInfo = gitRe.findall(gitLog)
    for info in gitInfo:
        commit = info[0]
        author = info[1]
        dateInfo = datetime.strptime(info[2], '%a %b %d %H:%M:%S %Y %z')
        commitToDate[commit] = dateInfo
    

def setArgument():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', help='set directory containing repositories to be analyzed', nargs='+')
    parser.add_argument('-d', help='set debug mode', action='store_true', default=False)
    parser.add_argument('-f', '--force', help='set force mode', action='store_true', default=False)
    args = parser.parse_args()
    return args


mainArgs = setArgument()
root = pathlib.Path(mainArgs.source[0])
jsonPath = os.path.join(root, 'goldset.json')
jsonData = pd.read_json(jsonPath, orient='records')

opPath = os.path.join(root, 'operations.json')
operation = pd.read_json(opPath)
opD = operation.to_dict(orient='dict')
print(len(opD))
operationData = opD["all"]

result = jsonData.to_dict(orient='records')
output = root.joinpath('checkOperation.csv')
setGitlog(root)

csvData = []
csvData.append(["operation"])
csvData.append(["operation"])

for data in result:
    commit = data["commit"]
    if commit in commitToDate:
        commitDate = commitToDate[commit]
    else:
        continue
    if commit in operationData:
        key = data["commit"] + data["location"]["old"] + str(data["leftSideLocations"][0]["startLine"]) + data["oldname"]
        if key in operationData[commit]:
            csvData.append([data["oldname"], data["newname"], operationData[commit][key]])
        else:
            csvData.append([data["oldname"], data["newname"], []])

with open(output, 'w') as dCSV:
    w = csv.writer(dCSV)
    w.writerows(csvData)
