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
detail_info = [['triggerCommit', 'file', 'line', 'triggeroldname', 'triggernewname', 'op',
                'commitPool', 'researchCommit', 'file', 'line', 'oldname' ,'truename', 'recommendname']]

result_info = []

gitRe = re.compile(r'(?:^commit)\s+(.+)\n(?:Merge:.+\n)?Author:\s+(.+)\nDate:\s+(.+)\n', re.MULTILINE)
numberToCommit = {}
dateToCommit = {}
commitToNumber = {}
commitToDate = {}
recommendName = {}
renameInfo = {}

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
        key = dateInfo.strftime('%Y%m%d')
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
    
    for commit in renames.keys():
        renameInfo[commit] = renames[commit]["goldset"]
        for i in range(len(renames[commit]["goldset"])):
            recs = renames[commit][str(i)]
            trigger = renames[commit]["goldset"][i]
            triggerKey = getKey(trigger)
            recommendName[triggerKey] = recs

    return True


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

#Todo Dataframeで実装し直すべき
def recommendCommit(commit, tableData, operations):
    #調査体操となる複数コミットを取得
    researchCommits = getCommitsInfo(commit)
    opGroup = {}
    detail_info.append(["start"])

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
    
    allRenames = 0
    allRecommend = 0
    allTrueRec = 0

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

        if len(renames) < 1:
            print(triggerOp)
            print("one rename is conducted")
            continue

        if len(triggerRec) == 0:
            print("No recommend")
            trueRecommendIndex = []
            precision = 0
            recall = 0
            exacts = 0
            fscore = 0
        else:
            #rename情報とrecommend情報を基に評価
            print(len(renames), len(triggerRec))
            trueRecommendIndex = evaluate(renames, triggerRec)
            trueRecommendCount = len(trueRecommendIndex)
            exactMatch = getExactMatch(renames, triggerRec, trueRecommendIndex)
            exactMatchCount = len(exactMatch)
            recommendationCount = len(triggerRec)
            renameCount = len(renames)

            precision = trueRecommendCount / recommendationCount 
            recall = trueRecommendCount / renameCount
            exacts = exactMatchCount / trueRecommendCount if trueRecommendCount != 0 else 0
            fscore = calcFScore(precision, recall)

        allRenames += len(renames)
        allRecommend += len(triggerRec)
        allTrueRec += len(trueRecommendIndex)
        setDetail(commit, trigger, triggerOp, triggerRec, renames)
        print(f"operation chunk = {triggerOp}")
        print(f"precision = {precision},  recall = {recall},\
               exact = {exacts}, fscore = {fscore} ")
    
    detail_info.append(["allRenames", allRenames, "allRecommend", allRecommend,
                        "allTrueRecommend", allTrueRec, "precision", allTrueRec/allRecommend,
                         "recall", allTrueRec/allRenames ])
    result_info.append(["allRenames", allRenames, "allRecommend", allRecommend,
                        "allTrueRecommend", allTrueRec, "precision", allTrueRec/allRecommend,
                         "recall", allTrueRec/allRenames ])


def setDetail(commit, trigger, triggerOp, triggerRec, renames):
    commitPool = []
    for r in renames:
        if r["commit"] not in commitPool:
            commitPool.append(r["commit"])

    rIdentifier = []
    recIdentifier = []
    for r in renames:
        rIdentifier.append(str([r["line"], r["typeOfIdentifier"], r["oldname"], r["files"]]))

    for r in triggerRec:
        recIdentifier.append(str([r["line"], r["typeOfIdentifier"], r["name"], r["files"]]))
    
    trueRecommend = list(set(rIdentifier) & set(recIdentifier))
    trueRecommendIndex = [(rIdentifier.index(t), recIdentifier.index(t)) for t in trueRecommend]
    falseNegativeRecommend = list(set(rIdentifier) - set(recIdentifier))
    falseNegativeIndex = [rIdentifier.index(t) for t in falseNegativeRecommend]
    trueNegativeRecommend = list(set(recIdentifier) - set(rIdentifier))
    trueNegativeIndex = [recIdentifier.index(t) for t in trueNegativeRecommend]

    for t in trueRecommendIndex:
        detail = [commit, trigger["files"], trigger["line"], trigger["oldname"], trigger["newname"],
                    str(triggerOp), commitPool, renames[t[0]]["commit"], renames[t[0]]["files"], str(renames[t[0]]["line"]), 
                    renames[t[0]]["oldname"], renames[t[0]]["newname"], triggerRec[t[1]]["join"]]
        detail_info.append(detail)

    for t in falseNegativeIndex:
        detail = [commit, trigger["files"], trigger["line"], trigger["oldname"], trigger["newname"],
            str(triggerOp), commitPool, renames[t]["commit"], renames[t]["files"], str(renames[t]["line"]), 
            renames[t]["oldname"], renames[t]["newname"], "NaN"]
        detail_info.append(detail)

    for t in trueNegativeIndex:
        detail = [commit, trigger["files"], trigger["line"], trigger["oldname"], trigger["newname"],
            str(triggerOp), commitPool, commit, triggerRec[t]["files"], str(triggerRec[t]["line"]), 
            triggerRec[t]["name"], "NaN", triggerRec[t]["join"]]
        detail_info.append(detail)


def calcFScore(precision, recall):
    if precision == 0 or recall == 0:
        return 0
    else:
        return 2 * precision * recall / (precision + recall)

def getExactMatch(renames, recommendation, indexes):
    result = []
    for idx in indexes:
        trueNewName = renames[idx[0]]['newname']
        recommendNewName = recommendation[idx[1]]['join']
        _logger.debug(f'true name [{trueNewName}], recommended name [{recommendNewName}]')
        #print(f'true name [{trueNewName}], recommended name [{recommendNewName}]')
        if trueNewName == recommendNewName:
            result.append(idx)
    _logger.debug(f'exact matches: {result}')
    return result

def canRecommendation(rename, recommendation):
    renameData = tableData.selectDataByRow(rename)
    if renameData is None:
        return []
    typeOfIdentifier = rename["typeOfIdentifier"]
    oldName = rename["oldname"]
    enclosingClass = renameData["enclosingCLass"]
    fileName = rename["files"]
    if typeOfIdentifier == "ClassName":
        methods = renameData["methods"].split(" - ")
        for i in range(len(recommendation)):
            rec = recommendation[i]
            if oldName != rec["name"]:
                continue
            if fileName != rec["files"]:
                continue
            recMethods = rec["methods"].split(" - ")
            for method in methods:
                if method == "":
                    continue
                if method in recMethods:
                    return i
        return None

    elif typeOfIdentifier == "MethodName":
        siblings = renameData["siblings"].split(" - ")
        for i in range(len(recommendation)):
            rec = recommendation[i]
            if oldName != rec["name"]:
                continue
            if enclosingClass != rec["enclosingCLass"]:
                continue
            return i
        for i in range(len(recommendation)):
            rec = recommendation[i]
            if oldName != rec["name"]:
                continue
            recMethods = rec["siblings"].split(" - ")
            for method in siblings:
                if method == "":
                    continue
                if method in recMethods:
                    return i
        return None
    
    elif typeOfIdentifier == "FieldName":
        siblings = renameData["siblings"].split(" - ")
        for i in range(len(recommendation)):
            rec = recommendation[i]
            if oldName != rec["name"]:
                continue
            if enclosingClass != rec["enclosingCLass"]:
                continue
            return i
        for i in range(len(recommendation)):
            rec = recommendation[i]
            if oldName != rec["name"]:
                continue
            recFields = rec["siblings"]
            if recFields == None:
                continue
            recFields = rec["siblings"]
            for field in siblings:
                if field == "":
                    continue
                if field in recFields:
                    return i
        return None

    elif typeOfIdentifier == "ParameterName":
        enclosingMethods = renameData["enclosingMethod"]
        for i in range(len(recommendation)):
            rec = recommendation[i]
            if oldName != rec["name"]:
                continue
            if enclosingClass != rec["enclosingCLass"]:
                continue
            if enclosingMethods != rec["enclosingMethod"]:
                continue
            return i
        return None
    
    elif typeOfIdentifier == "VariableName":
        enclosingMethods = renameData["enclosingMethod"]
        for i in range(len(recommendation)):
            rec = recommendation[i]
            if oldName != rec["name"]:
                continue
            if enclosingClass != rec["enclosingCLass"]:
                continue
            if enclosingMethods != rec["enclosingMethod"]:
                continue
            return i
        return None
    
    else:
        _logger.error("unknown typeOfIdentifier")

def evaluate(renames, recommendation):
    #print(len(renames), len(recommendation))
    if len(recommendation) == 0:
        return []
    
    trueRecommendIndex = []
    for i in range(len(renames)):
        r = renames[i]
        key = str([r["line"], r["typeOfIdentifier"], r["oldname"], r["files"]])
        flag = False
        for k in range(len(recommendation)):
            rec = recommendation[k]
            recKey = str([rec["line"], rec["typeOfIdentifier"], rec["name"], rec["files"]])
            if key == recKey:
                trueRecommendIndex.append([i, k])
                flag = True
                break
        if flag:
            continue
        ri = canRecommendation(r, recommendation)
        if ri == None:
            continue
        trueRecommendIndex.append([i, ri])
        print(i, ri)
                
    '''
    rIdentifier = []
    recIdentifier = []
    for r in renames:
        rIdentifier.append(str([r["line"], r["typeOfIdentifier"], r["oldname"], r["files"]]))

    for r in recommendation:
        recIdentifier.append(str([r["line"], r["typeOfIdentifier"], r["name"], r["files"]]))
    
    trueRecommend = list(set(rIdentifier) & set(recIdentifier))
    trueRecommendIndex = [(rIdentifier.index(t), recIdentifier.index(t)) for t in trueRecommend]
    '''
    print(trueRecommendIndex)
    #print(f"recall = {len(trueRecommend)/len(renames)}, precision = {len(trueRecommend)/len(recommendation)}")
    return trueRecommendIndex


if __name__ ==  "__main__":
    args = setArgument()
    setLogger(INFO)
    setGitlog(args.source)
    detailCSV = os.path.join(args.source,'integrateDetail.csv')  ##
    resultCSV = os.path.join(args.source,'integrateResult.csv') 

    #すべてのjson Fileを読み込む(recommend_relation_normalize.json)
    for fileName, op in researchFileNames.items():
        operations = setOperations(args.source, op)
        if not setRename(args.source, fileName):
            _logger.debug(f"{fileName} is not found")
            continue

        _logger.debug(f"start researching {fileName}")
        for commit in renameInfo.keys():
            tablePath = os.path.join(args.source, "archives", commit, "exTable.csv.gz")
            tableData = ExTable(tablePath)
            recommendCommit(commit, tableData, operations)

    with open(detailCSV, 'w') as dCSV:
        w = csv.writer(dCSV)
        w.writerows(detail_info)
    
    with open(resultCSV, 'w') as dCSV:
        w = csv.writer(dCSV)
        w.writerows(result_info)

