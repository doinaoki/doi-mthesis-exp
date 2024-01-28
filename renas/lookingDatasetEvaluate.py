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
import statistics
import json
import pandas as pd
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG, log, basicConfig
from copy import deepcopy
from .util.Rename import Rename
import operator
from .showRQFigure import showRQFigure
from .showRandomFigure import showRandomFigure

researchFileNames = {
                    "recommend_none.json": "None",
                    "recommend_relation_normalize.json": "Normalize",
                    "recommend_relation.json": "Relation",
                    "recommend_all_normalize.json": "All"}

allPrecision = {op: [] for op in researchFileNames.values()}
allRecall = {op: [] for op in researchFileNames.values()}
allFscore = {op: [] for op in researchFileNames.values()}
detail_info = [['triggerCommit', 'file', 'line', 'type', 'triggeroldname', 'triggernewname',
                'file', 'line', 'type', 'oldname' ,'truename', 'recommendname']]

devideNumber = 20
thresholdNumber = 100.0
ratio = [i/devideNumber for i in range(0, devideNumber+1)]
result_info = []
topN = 20
maxCost = 25
_showRQFigure = showRQFigure(topN, maxCost)
_showRandomFigure = showRandomFigure(topN)

def setArgument():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', help='set directory containing repositories to be analyzed', nargs='+')
    parser.add_argument('-d', help='set debug mode', action='store_true', default=False)
    parser.add_argument('-f', '--force', help='set force mode', action='store_true', default=False)
    args = parser.parse_args()
    return args


def setOperations(path):
    filePath = os.path.join(path, "operations.json")
    with open(filePath, 'r') as f:
        operations = json.load(f)["all"]
    return operations

def getKey(dic):
    return dic["commit"] + dic["files"] + str(dic["line"]) + dic["oldname"]


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

def detail(triggerRename, renames, recommend, op):
    if op != "All":
        return

    triggerKey = getKey(triggerRename)
    correctIndex = []
    correct = 0
    for rr in range(len(renames)):
        rename = renames[rr]
        key = getKey(rename)
        if triggerKey == key:
            continue
        sameKey = str(rename["line"]) + rename["typeOfIdentifier"] + rename["oldname"] + rename["files"]
        for r in range(len(recommend)):
            rec = recommend[r]
            recKey = str(rec["line"]) + rec["typeOfIdentifier"] + rec["name"] + rec["files"]
            if sameKey == recKey:
                correct += 1
                correctIndex.append([rr, r])
                break
    precision = correct / len(recommend) if len(recommend) != 0 else 0
    recall = correct / (len(renames) - 1)
    fscore = 2 * precision * recall / (precision + recall) if correct != 0 else 0
    result_info.append([triggerRename["commit"], triggerRename["oldname"], triggerRename["newName"], triggerRename["typeOfIdentifier"], precision, recall, fscore])
    
    for ci in correctIndex:
        reI = ci[0]
        recI = ci[1]
        detail_info.append([triggerRename["commit"], triggerRename["files"], triggerRename["line"], triggerRename["typeOfIdentifier"], triggerRename["oldname"], triggerRename["newName"], 
                            renames[reI]["files"], renames[reI]["line"], renames[reI]["typeOfIdentifier"], renames[reI]["oldname"], renames[reI]["newName"], recommend[recI]["join"], recommend[recI]["rank"]])
    for r in range(len(renames)):
        rename = renames[r]
        flag = True
        key = getKey(rename)
        if triggerKey == key:
            continue
        for v in correctIndex:
            if r == v[0]:
                flag = False
        if flag:
            detail_info.append([triggerRename["commit"], triggerRename["files"], triggerRename["line"], triggerRename["typeOfIdentifier"], triggerRename["oldname"], triggerRename["newName"], 
                                renames[r]["files"], renames[r]["line"], renames[r]["typeOfIdentifier"], renames[r]["oldname"], renames[r]["newName"], "NAN", "Nan"])

    for r in range(len(recommend)):
        flag = True
        for v in correctIndex:
            if r == v[0]:
                flag = False
        if flag:
            detail_info.append([triggerRename["commit"], triggerRename["files"], triggerRename["line"], triggerRename["typeOfIdentifier"], triggerRename["oldname"], triggerRename["newName"], 
                                recommend[r]["files"], recommend[r]["line"], recommend[r]["typeOfIdentifier"], recommend[r]["name"], "NAN", recommend[r]["join"], recommend[r]["rank"]])

def evaluate(triggerRename, ren, recommend, op):
    renames = []
    triedkey = set()
    triggerKey = getKey(triggerRename)
    for r in ren:
        key = getKey(r)
        if triggerKey == key:
            continue
        if key in triedkey:
            continue
        renames.append(r)
        triedkey.add(key)
    
    if len(renames) == 0:
        return

    correct = 0
    result = []

    for re in range(len(renames)):
        rename = renames[re]

        key = getKey(rename)
        sameKey = str(rename["line"]) + rename["typeOfIdentifier"] + rename["oldname"] + rename["files"]
        for r in range(len(recommend)):
            rec = recommend[r]
            recKey = str(rec["line"]) + rec["typeOfIdentifier"] + rec["name"] + rec["files"]
            if sameKey == recKey:
                correct += 1
                result.append([re, r])
                break
    precision = correct / len(recommend) if len(recommend) != 0 else 0
    recall = correct / len(renames)
    fscore = 2 * precision * recall / (precision + recall) if correct != 0 else 0
    allPrecision[op].append(precision)
    allRecall[op].append(recall)
    allFscore[op].append(fscore)
    print(triggerRename["commit"], result)
    _showRQFigure.update(triggerRename, recommend, renames, result, op)


def randomEvaluate(triggerRename, ren, rawRecommend, op):
    renames = []
    triedkey = set()
    triggerKey = getKey(triggerRename)
    for r in ren:
        key = getKey(r)
        if triggerKey == key:
            continue
        if key in triedkey:
            continue
        renames.append(r)
        triedkey.add(key)
    
    if len(renames) == 0:
        return

    for ra in ratio:
        rec = deepcopy(rawRecommend)
        for tr in rec:
            relationshipCost = (1.0 / tr["relationship"])
            similarityCost = 1.0 - tr["similarity"]
            tr["rank"] = (ra * similarityCost + (1.0 - ra) * relationshipCost) * thresholdNumber
        recommend = sorted(rec, key=operator.itemgetter('rank', 'id'), reverse=True)
        correct = 0
        result = []
        triedkey = set()
        for re in range(len(renames)):
            rename = renames[re]
            sameKey = str(rename["line"]) + rename["typeOfIdentifier"] + rename["oldname"] + rename["files"]
            for r in range(len(recommend)):
                rec = recommend[r]
                recKey = str(rec["line"]) + rec["typeOfIdentifier"] + rec["name"] + rec["files"]
                if sameKey == recKey:
                    correct += 1
                    result.append([re, r])
                    break
        precision = correct / len(recommend) if len(recommend) != 0 else 0
        recall = correct / len(renames)
        fscore = 2 * precision * recall / (precision + recall) if correct != 0 else 0
        allPrecision[op].append(precision)
        allRecall[op].append(recall)
        allFscore[op].append(fscore)
        #print(triggerRename["commit"], result)
        _showRandomFigure.update(triggerRename, recommend, renames, result, f"All{ra}")


def changeTypeName(typeOfIdentifier):
    if typeOfIdentifier == "Parameter":
        return "ParameterName"
    elif typeOfIdentifier == "Variable":
        return "VariableName"
    elif typeOfIdentifier == "Method":
        return "MethodName"
    elif typeOfIdentifier == "Attribute":
        return "FieldName"
    elif typeOfIdentifier == "Class":
        return "ClassName"
    else:
        return None

mainArgs = setArgument()
root = pathlib.Path(mainArgs.source[0])
opPath = os.path.join(root, 'lookingDataset.csv')
datalooking = pd.read_csv(opPath, skiprows=1)

resultRepo = os.path.join(root, 'dataLooking')
allCSV = os.path.join(resultRepo, 'all.csv')
detailCSV = os.path.join(resultRepo,'integrateDetailAll.csv')  ##
resultCSV = os.path.join(resultRepo,'integrateResultAll.csv') 
_showRQFigure.setOperations(setOperations(root))

coRenameGroup = {}

for i, row in datalooking.iterrows():
    conceptRename = row["conceptRename?"]
    oldName = row["oldName"]
    newName = row["newName"]
    operation = row["Operation"]
    coRename = row["coRename"]
    commitDate = row["commitdate"]
    commit = row["commit"]
    typeOfIdentifier = changeTypeName(row["type"])
    file = row["file"]
    line = row["line"]
    
    if coRename == -1 or conceptRename != "TRUE":
        continue

    if commit not in coRenameGroup:
        coRenameGroup[commit] = {}

    if coRename not in coRenameGroup[commit]:
        coRenameGroup[commit][coRename] = []
    
    data = {"oldname": oldName, "newName": newName, "Operation": operation, "coRename": coRename, "commitdate": commitDate,
             "commit": commit, "typeOfIdentifier": typeOfIdentifier, "files": file, "line": line}
    coRenameGroup[commit][coRename].append(data)
'''
c = 0
d = 0
for i in coRenameGroup:
    for k in coRenameGroup[i]:
        if len(coRenameGroup[i][k]) >= 2:
            c += len(coRenameGroup[i][k])
            d += 1
print(c, d)
exit(0)
'''
for fileName, op in researchFileNames.items():
    recommendName, renameInfo = setRename(mainArgs.source[0], fileName)
    print(fileName)

    for commit, coRenames in coRenameGroup.items():
        for num, renames in coRenames.items():
            for triggerRename in renames:
                key = getKey(triggerRename)
                if key not in recommendName:
                    print(key)
                    continue
                if op == "All":
                    recommend = deepcopy(recommendName[key])
                    for tr in recommend:
                        relationshipCost = (1.0 / tr["relationship"])
                        similarityCost = 1.0 - tr["similarity"]
                        tr["rank"] = (0.5 * similarityCost + (1.0 - 0.5) * relationshipCost) * thresholdNumber
                    recommend = sorted(recommend, key=operator.itemgetter('rank', 'id'), reverse=True)
                elif op == "Normalize":
                    recommend = sorted(recommendName[key], key=operator.itemgetter('rank', 'id'))
                else:
                    recommend = recommendName[key]
                if len(renames) <= 1:
                    print(renames)
                    continue
                evaluate(triggerRename, renames, recommend, op)
                detail(triggerRename, renames, recommend, op)
                if op == "All":
                    randomEvaluate(triggerRename, renames, recommend, op)

if not os.path.isdir(resultRepo):
    os.mkdir(resultRepo)

with open(detailCSV, 'w') as dCSV:
    w = csv.writer(dCSV)
    w.writerows(detail_info)

with open(resultCSV, 'w') as dCSV:
    w = csv.writer(dCSV)
    w.writerows(result_info)


with open(allCSV, 'w') as dCSV:
    w = csv.writer(dCSV)
    for i, k in allPrecision.items():
        if k != []:
            w.writerow([i])
            w.writerow([statistics.mean(k)])
        else:
            w.writerow([i])
            w.writerow([0])
    for i, k in allRecall.items():
        if k != []:
            w.writerow([i])
            w.writerow([statistics.mean(k)])
        else:
            w.writerow([i])
            w.writerow([0])
    for i, k in allFscore.items():
        if k != []:
            w.writerow([i])
            w.writerow([statistics.mean(k)])
        else:
            w.writerow([i])
            w.writerow([0])
_showRQFigure.calculateData()
_showRandomFigure.calculateData()
#_showRQFigure.showConsole()
_showRQFigure.showFigure(resultRepo)
_showRandomFigure.showFigure(resultRepo)