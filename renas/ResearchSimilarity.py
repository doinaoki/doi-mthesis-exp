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
from .showRandomFigure import showRandomFigure

_logger = getLogger(__name__)
ratio = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
TOPN = 20
COST = 50
rankTrueRecommend = [[0, 0] for _ in range(COST)]

gitRe = re.compile(r'(?:^commit)\s+(.+)\nAuthor:\s+(.+)\nDate:\s+(.+)\n', re.MULTILINE)
numberToCommit = {}
dateToCommit = {}
commitToNumber = {}
commitToDate = {}
SIMILARITIES = []


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
    researchCommits.append(commit)
    return researchCommits

def getKey(dic):
    return dic["commit"] + dic["files"] + str(dic["line"]) + dic["oldname"]  + dic["typeOfIdentifier"]

def checkMeaningful(operations):
    meaningful = ["insert", "delete", "replace"]
    for op in operations:
        if op[0] in meaningful:
            return False
        if op[0] == "format":
            if op[1][0] == "Plural":
                return False
    print(operations)
    return True

def researchSimilarity(commit, operations, renameInfo):
    #調査体操となる複数コミットを取得
    researchCommits = getCommitsInfo(commit)
    opGroup = {}

    #operationごとにdicを作成する
    for c in researchCommits:
        if c not in renameInfo:
            continue
        #print(commit)
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
    
    for renameDicts in opGroup.values():
        getSimilarity(renameDicts)

    return 

def getSimilarity(renameDicts):
    for i in range(len(renameDicts)):
        for k in range(i+1, len(renameDicts)):
            aNameNormalize = renameDicts[i]["normalized"]
            bNameNormalize = renameDicts[k]["normalized"]
            print(f"{aNameNormalize} : {bNameNormalize} = {wordSimilarity(aNameNormalize, bNameNormalize)}")
            SIMILARITIES.append(wordSimilarity(aNameNormalize, bNameNormalize))

def wordSimilarity(aNormalize, bNormalize):
    similarity = len(set(aNormalize) & set(bNormalize)) * 2 / (len(aNormalize) + len(bNormalize))
    
    return similarity

def getRelationData(renameData, relation):
    if not isinstance(renameData[relation], str):
        return []
    return renameData[relation].split(" - ")

if __name__ ==  "__main__":
    args = setArgument()
    setLogger(INFO)
    setGitlog(args.source)
    evalSimilarityPath = os.path.join(args.source, 'similarity')
    if not os.path.isdir(evalSimilarityPath):
        os.mkdir(evalSimilarityPath)

    operations = setOperations(args.source, "all")
    recommendName, renameInfo = setRename(args.source, "recommend_all_normalize_random.json")

    for commit in renameInfo.keys():
        if commit not in commitToDate:
            continue
        researchSimilarity(commit, operations, renameInfo)
    #print(SIMILARITIES)
    similarityPath = os.path.join(evalSimilarityPath, 'similarity.csv')

    with open(similarityPath, 'w') as sCSV:
        w = csv.writer(sCSV)
        w.writerow(SIMILARITIES)
