import pathlib
import simplejson
import os
import argparse
import time
from datetime import timedelta
import heapq
import csv

import pandas as pd
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG, log, basicConfig
from copy import deepcopy

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

csvData = []
csvData.append(["チェックボックス", "概念？", "名前変更前", "名前変更後", "変更操作", "コミット名", "識別子の種類", "ファイル名", "行", "備考"])
csvData.append(["checkBox", "conceptRename?", "oldName", "newName", "Operation", "commit", "type", "file", "line", "remark"])
for data in result:
    check = ""
    concept = ""
    oldName = data["oldname"]
    newName = data["newname"]
    operation = ""
    commit = data["commit"]
    dataType = data["renameType"]
    dataFile = data["location"]["old"]
    line = data["leftSideLocations"][0]["startLine"]
    csvData.append([check, concept, oldName, newName, operation, commit, dataType, dataFile, line])

    with open(output, 'w') as dCSV:
        w = csv.writer(dCSV)
        w.writerows(csvData)