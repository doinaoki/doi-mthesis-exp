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
result = jsonData.to_dict(orient='records')
output = root.joinpath('check.csv')
setGitlog(root)

csvData = []
csvData.append(["チェックボックス", "概念？", "名前変更前", "名前変更後", "変更操作", "同時変更", "コミット日", "コミット名", "識別子の種類", "ファイル名", "行", "備考", "土居メモ"])
csvData.append(["checkBox", "conceptRename?", "oldName", "newName", "Operation", "coRename", "commitdate", "commit", "type", "file", "line", "remark", "memo"])
for data in result:
    check = ""
    concept = ""
    oldName = data["oldname"]
    newName = data["newname"]
    operation = ""
    coRename = ""
    commit = data["commit"]
    if commit in commitToDate:
        commitDate = commitToDate[commit]
    else:
        continue
    dataType = data["renameType"]
    dataFile = data["location"]["old"]
    line = data["leftSideLocations"][0]["startLine"]
    csvData.append([check, concept, oldName, newName, operation, coRename, commitDate, commit, dataType, dataFile, line])

    with open(output, 'w') as dCSV:
        w = csv.writer(dCSV)
        w.writerows(csvData)