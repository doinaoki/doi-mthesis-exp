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


def getCommitsInfo(commit):
    #複数コミットの取り方
    #dateが+2のコミットを含むようにする(仮)根拠なし
    researchCommits = []
    num = 2
    fromCommitDate = commitToDate[commit]
    toCommitDate = commitToDate[commit] + timedelta(days=num)
    for date, info in dateToCommit.items():
        if fromCommitDate <= date < toCommitDate:
            researchCommits.append(dateToCommit[date])
    return researchCommits

def getKey(dic):
    return dic["commit"] + dic["files"] + str(dic["line"]) + dic["oldname"]

def getOperationGroup(commit, renameInfo, operations):
    researchCommits = getCommitsInfo(commit)
    opGroup = {}

    #operationごとにdicを作成する
    for c in researchCommits:
        if c not in renameInfo:
            continue
        print(commit)
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

#Todo Dataframeで実装し直すべき
def recommendCommit(commit, tableData, operations, recommendName, renameInfo):
    #調査体操となる複数コミットを取得
    researchCommits = getCommitsInfo(commit)
    opGroup = {}

    #operationごとにdicを作成する
    for c in researchCommits:
        if c not in renameInfo:
            continue
        print(commit)
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
    
    #調査するcommitからtriggerを選ぶ
    for trigger in renameInfo[commit]:
        # triggerを元にoperaion dicからrename情報を得る
        triggerKey = getKey(trigger)
        if triggerKey not in operations[commit]:
            print(f"something wrong {triggerKey}")
            continue
        triggerOp = operations[commit][triggerKey]
        triggerRec = recommendName[triggerKey]
        renames = []
        for op in triggerOp:
            if str(op) not in opGroup:
                continue
            for rDic in opGroup[str(op)]:
                if getKey(rDic) == triggerKey:
                    continue
                renames.append(rDic)

    return 

def outputCommitPool(opGroup):
    pass


if __name__ ==  "__main__":
    args = setArgument()
    setLogger(INFO)
    setGitlog(args.source)
    detailCSV = os.path.join(args.source,'integrateDetail.csv')  ##
    resultCSV = os.path.join(args.source,'integrateResult.csv') 

    #すべてのjson Fileを読み込む(recommend_relation_normalize.json)
    for fileName, op in researchFileNames.items():
        operations = setOperations(args.source, op)
        recommendName, renameInfo = setRename(args.source, fileName)
        for commit in commitToDate:
            opGroup = getOperationGroup(commit, renameInfo, operations)
            if fileName == "recommend_all_normalize.json":
                outputCommitPool(opGroup)
'''
        for commit in renameInfo.keys():
            if commit not in commitToDate:
                continue
            print(commit)
            tablePath = os.path.join(args.source, "archives", commit, "exTable.csv.gz")
            tableData = ExTable(tablePath)
            recommendCommit(commit, tableData, operations, recommendName, renameInfo)
'''
