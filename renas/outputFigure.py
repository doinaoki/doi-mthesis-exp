import pathlib
import os
import sys
import glob
import time
import json
import re
import traceback
import csv
import statistics
import math
import subprocess
import argparse
from multiprocessing import Pool
import matplotlib.pyplot as plt
import numpy as np
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG, log

from .util.ExTable import ExTable
from datetime import datetime, date, timedelta
import pandas as pd
from .util.Name import KgExpanderSplitter
from .util.Rename import Rename

_logger = getLogger(__name__)

researchFileNames = {"recommend_relation_normalize.json": "Normalize",
                    "recommend_relation.json": "None",
                    "recommend_all_normalize.json": "all"}

gitRe = re.compile(r'(?:^commit)\s+(.+)\nAuthor:\s+(.+)\nDate:\s+(.+)\n', re.MULTILINE)
numberToCommit = {}
dateToCommit = {}
commitToNumber = {}
commitToDate = {}

def setArgument():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', help='set directory containing repositories to be analyzed')
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
    num = len(gitInfo)-1
    for info in gitInfo:
        commit = info[0]
        author = info[1]
        dateInfo = datetime.strptime(info[2], '%a %b %d %H:%M:%S %Y %z')
        commitToDate[commit] = dateInfo
        dateToCommit[dateInfo]= commit

        numberToCommit[num] = commit
        commitToNumber[commit] = num
        num -= 1
    
    return True


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
    with open(filePath, 'r') as f:
        operations = json.load(f)[op]
    return operations


def getCommitsInfo(commit, num):
    #複数コミットの取り方
    #dateが+2のコミットを含むようにする(仮)根拠なし
    researchCommits = []
    if commit not in commitToDate:
        return []
    fromCommitDate = commitToDate[commit]
    toCommitDate = commitToDate[commit] + timedelta(days=num)
    for date, info in dateToCommit.items():
        if fromCommitDate <= date <= toCommitDate:
            researchCommits.append(dateToCommit[date])
    return researchCommits

def getKey(dic):
    return dic["commit"] + dic["files"] + str(dic["line"]) + dic["oldname"]

def getOperationGroup(commit, renameInfo, operations, num):
    researchCommits = getCommitsInfo(commit, num)
    opGroup = {}

    #operationごとにdicを作成する
    for c in researchCommits:
        if c not in renameInfo:
            continue
        goldset = renameInfo[c]
        for rDic in goldset:
            key = getKey(rDic)
            if key not in operations[c]:
                print(f"something wrong {key}")
                continue
            ops = operations[c][key]
            for op in ops:
                #must change
                if str(op) not in opGroup:
                    opGroup[str(op)] = []
                opGroup[str(op)].append(rDic)
    return opGroup



def collectGroupRename(commit, opGroup, operations, renameInfo, collectRename):
    #調査体操となる複数コミットを取得
    #調査するcommitからtriggerを選ぶ
    for trigger in renameInfo[commit]:
        # triggerを元にoperaion dicからrename情報を得る
        triggerKey = getKey(trigger)
        if triggerKey not in operations[commit]:
            print(f"something wrong {triggerKey}")
            continue
        triggerOp = operations[commit][triggerKey]
        ops = []
        for op in triggerOp:
            if str(op) not in opGroup:
                continue
            for rDic in opGroup[str(op)]:
                key = getKey(rDic)
                ops.append(key)
        countRename = len(set(ops)) if len(set(ops)) > 0 else 1  
        collectRename[countRename-1 if countRename < 10 else 9] += 1

    return 
''''
def appendCommitPool(commit, opGroup, commitPool):
    for i in opGroup.keys():
        commits = []
        for rDic in opGroup[i]:
            if rDic["commit"] not in commits:
                commits.append(rDic["commit"])
        commitPool[len(commits)-1 if len(commits) < 10 else 9] += 1
'''

def appendCommitPool(commit, opGroup, operations, renameInfo, commitPool):
    for trigger in renameInfo[commit]:
        # triggerを元にoperaion dicからrename情報を得る
        triggerKey = getKey(trigger)
        if triggerKey not in operations[commit]:
            print(f"something wrong {triggerKey}")
            continue
        triggerOp = operations[commit][triggerKey]
        ops = []
        commits = [commit]
        for op in triggerOp:
            if str(op) not in opGroup:
                continue
            for rDic in opGroup[str(op)]:
                key = getKey(rDic)
                ops.append(key)
                commits.append(rDic["commit"])
        countPool = len(set(commits))  
        commitPool[countPool-1 if countPool < 10 else 9] += 1
    
    return

def outputCommitPool(commitPool, source):
    left = [i+1 for i in range(10)]
    print(commitPool)
    fig, ax = plt.subplots()

    p1 = ax.bar(left, commitPool, color='r')
    ax.bar_label(p1, label_type='edge')
    plt.savefig(os.path.join(source, "recCommitSize.png"))  
    plt.show()

def showStatistic(cRenames):
    sList = []
    for i in range(len(cRenames)):
        num = i+1
        amount = cRenames[i]
        sList += [num] * amount
    print(statistics.mean(sList))
    print(statistics.median(sList))


def outputCollectRename(collectRename, source):
    none = collectRename["None"]
    nor = collectRename["Normalize"]
    all = collectRename["all"]
    print("none")
    showStatistic(none)
    print("nor")
    showStatistic(nor)
    print("all")
    showStatistic(all)
    index = np.array([i+1 for i in range(10)])
    
    fig, ax = plt.subplots()
    bar_width = 0.25
    alpha = 0.8

    plt.bar(index, none, bar_width,
    alpha=alpha,color='green',label='None')
    
    plt.bar(index + bar_width, nor, bar_width,
    alpha=alpha,color='pink',label='existingApproach')

    plt.bar(index + 2*bar_width, all, bar_width,
    alpha=alpha,color='gold',label='proposedApproach')
    plt.ylabel('Counts')
    plt.xticks(index + bar_width, (i+1 for i in range(10)))
    plt.legend()
    plt.savefig(os.path.join(source, "collectRename.png"), pad_inches = 0)
    plt.show()


if __name__ ==  "__main__":
    args = setArgument()
    setLogger(INFO)
    setGitlog(args.source)
    collectRename = {"Normalize": [0 for _ in range(10)], "None":  [0 for _ in range(10)], "all": [0 for _ in range(10)]}

    #すべてのjson Fileを読み込む(recommend_relation_normalize.json)
    for fileName, op in researchFileNames.items():
        operations = setOperations(args.source, op)
        recommendName, renameInfo = setRename(args.source, fileName)
        commitPool = [0 for _ in range(10)]
        for commit in renameInfo.keys():
            if commit not in commitToDate:
                continue
            opGroup = getOperationGroup(commit, renameInfo, operations, 0)
            collectGroupRename(commit, opGroup, operations, renameInfo, collectRename[op])
            if fileName == "recommend_all_normalize.json":
                opGroup = getOperationGroup(commit, renameInfo, operations, 2)
                appendCommitPool(commit, opGroup, operations, renameInfo, commitPool)
        if fileName == "recommend_all_normalize.json":
            outputCommitPool(commitPool, args.source)
    outputCollectRename(collectRename, args.source)
    print("end")
