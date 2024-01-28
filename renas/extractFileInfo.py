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
from copy import deepcopy

from .util.ExTable import ExTable
from datetime import datetime, date, timedelta
import pandas as pd
from .util.Name import KgExpanderSplitter
from .util.Rename import Rename
import statistics
from .showRQFigure import showRQFigure

_logger = getLogger(__name__)

researchFileNames = {
                    "recommend_all_normalize.json": "All"}

gitRe = re.compile(r'(?:^commit)\s+(.+)\nAuthor:\s+(.+)\nDate:\s+(.+)\n', re.MULTILINE)

sameRenameSetLength = [0 for _ in range(10)]
researchTypeOfIdentifier = {i:0 for i in ["ParameterName", "ClassName", "MethodName", "VariableName", "FieldName"]}
renameCount = 0

def setArgument():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', help='set directory containing repositories to be analyzed', nargs='+')
    parser.add_argument('-D', help='dry run (only check how many archives will be created)', action='store_true', default=False)
    args = parser.parse_args()
    return args


def setLogger(level):
    _logger.setLevel(level)
    root_logger = getLogger()
    handler = StreamHandler()
    handler.setLevel(level)
    formatter = Formatter('[%(asctime)s] %(name)s -- %(levelname)s : %(message)s')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(INFO)
    return root_logger


def setGitlog(path):
    repoPath = os.path.join(path, "repo")
    cp = subprocess.run(f"cd {repoPath}; git log",shell=True, stdout=subprocess.PIPE)
    gitLog = cp.stdout.decode('utf-8','ignore')
    gitInfo = gitRe.findall(gitLog)
    commitData = set()
    for info in gitInfo:
        commit = info[0]
        author = info[1]
        dateInfo = datetime.strptime(info[2], '%a %b %d %H:%M:%S %Y %z')
        commitData.add(commit)
    
    return commitData


def setRename(path, fileName):
    filePath = os.path.join(path, fileName)
    if not os.path.isfile(filePath):
        return False

    with open(filePath, 'r') as f:
        renames = json.load(f)

    recommendName = {}
    renameInfo = {}
    for commit in renames.keys():
        renameInfo[commit] = renames[commit]["goldset"]
        for i in range(len(renames[commit]["goldset"])):
            recs = renames[commit][str(i)]
            trigger = renames[commit]["goldset"][i]
            triggerKey = getKey(trigger)
            recommendName[triggerKey] = recs

    return recommendName, renameInfo

def setOperations(path, op):
    filePath = os.path.join(path, "operations.json")
    operations = {}
    with open(filePath, 'r') as f:
        ops = json.load(f)[op]
    for commit, gold in ops.items():
        operations[commit] = {}
        for k, o in gold.items():
            key = re.sub(r'MethodName$|ClassName$|ParameterName$|VariableName$|FieldName$', '', k)
            operations[commit][key] = o
    return operations
'''
def setOperations(path, op):
    filePath = os.path.join(path, "operations.json")
    operations = {}
    with open(filePath, 'r') as f:
        operations = json.load(f)[op]
    return operations
'''

def getCommitsInfo(commit):
    #複数コミットの取り方
    #dateが+2のコミットを含むようにする(仮)根拠なし
    researchCommits = []
    researchCommits.append(commit)
    return researchCommits

def getKey(dic):
    return dic["commit"] + dic["files"] + str(dic["line"]) + dic["oldname"]

def checkMeaningful(operations):
    meaningful = ["insert", "delete", "replace"]
    for op in operations:
        if op[0] in meaningful:
            return False
        if op[0] == "format":
            if op[1][0] == "Plural":
                return False
    #print(operations)
    return True

def recommendCommit(commit, operations, renameInfo):
    #調査対象となる複数コミットを取得
    researchCommits = getCommitsInfo(commit)
    opGroup = {}
    deb = 0

    #operationごとにdicを作成する
    for c in researchCommits:
        if c not in renameInfo:
            continue
        goldset = renameInfo[c]
        for rDic in goldset:
            key = getKey(rDic)
            #Todo: fix extracting parameter or variable using AST
            if key not in operations[c]:
                print(f"something wrong with {key}")
                continue
            ops = operations[c][key]
            for op in ops:
                #must change
                if str(op) not in opGroup:
                    opGroup[str(op)] = []
                opGroup[str(op)].append(rDic)
    
    renameIdSet = set()
    for i in opGroup.keys():
        if checkMeaningful([eval(i)]):
            continue
        num = len(opGroup[i])-1 if len(opGroup[i]) <= 10 else 9
        sameRenameSetLength[num] += 1
        if len(opGroup[i]) == 1:
            continue
        for o in opGroup[i]:
            if getKey(o)+o["typeOfIdentifier"] not in renameIdSet:
                renameIdSet.add(getKey(o)+o["typeOfIdentifier"])
                researchTypeOfIdentifier[o["typeOfIdentifier"]] += 1
            #else:
                #print(o["oldname"], o["newname"])

    debSet = set()
    for trigger in renameInfo[commit]:
        # triggerを元にoperaion dicからrename情報を得る
        triggerKey = getKey(trigger)
        if triggerKey not in operations[commit]:
            print(f"something wrong {triggerKey}")
            continue
        triggerOp = operations[commit][triggerKey]
        if checkMeaningful(triggerOp):
            continue
        renames = []
        rKeys = []
        for op in triggerOp:
            if str(op) not in opGroup:
                print(f"something wrong {triggerKey}")
                exit(1)
            for rDic in opGroup[str(op)]:
                if getKey(rDic) == triggerKey:
                    continue
                if getKey(rDic) in rKeys:
                    continue
                rKeys.append(getKey(rDic))
                renames.append(rDic)
        if len(renames) == 0:
            continue
        deb += 1
        if triggerKey+trigger["typeOfIdentifier"] in debSet:
            continue
        debSet.add(triggerKey+trigger["typeOfIdentifier"])

    '''
    if len(renameIdSet) == 1:
        return len(renameIdSet), deb

    if len(renameIdSet) != deb:
        for i in renameInfo[commit]:
            print(i["oldname"], i["newname"], operations[commit][getKey(i)], i["typeOfIdentifier"])
        print(list(i for i in opGroup.keys() if len(opGroup[i]) >= 1))
        print(len(renameIdSet), deb, len(debSet))
        exit(1)
    '''


    
    return len(renameIdSet), deb
    
            
            



def getRelationData(renameData, relation):
    if not isinstance(renameData[relation], str):
        return []
    return renameData[relation].split(" - ")


if __name__ ==  "__main__":
    args = setArgument()
    setLogger(INFO)    
    renameCount = 0
    deb = 0
    researchTypeOfIdentifier = {i:0 for i in ["ParameterName", "ClassName", "MethodName", "VariableName", "FieldName"]}
    #すべてのjson Fileを読み込む(recommend_relation_normalize.json)
    for repo in args.source:
        commitData = setGitlog(repo)
        for fileName, op in researchFileNames.items():
            operations = setOperations(repo, "all")
            recommendName, renameInfo = setRename(repo, fileName)

            for commit in renameInfo.keys():
                if commit not in commitData:
                    continue
                r, d = recommendCommit(commit, operations, renameInfo)
                renameCount += r
                deb += d



print(renameCount, researchTypeOfIdentifier, sameRenameSetLength)
c = 0
for i in range(1, 10):
    c += sameRenameSetLength[i]
print(deb, c)
