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

researchFileNames = {
                    "recommend_relation_normalize.json": "Normalize",
                    "recommend_relation_normalize_ranking.json": "normalize_ranking",
                    "recommend_relation.json": "Relation",
                    "recommend_all_normalize.json": "all"}

allPrecision = {op: [] for op in researchFileNames.values()}
allRecall = {op: [] for op in researchFileNames.values()}
allFscore = {op: [] for op in researchFileNames.values()}
detail_info = [['triggerCommit', 'file', 'line', 'type', 'triggeroldname', 'triggernewname',
                'file', 'line', 'type', 'oldname' ,'truename', 'recommendname']]

result_info = []

def setArgument():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', help='set directory containing repositories to be analyzed', nargs='+')
    parser.add_argument('-d', help='set debug mode', action='store_true', default=False)
    parser.add_argument('-f', '--force', help='set force mode', action='store_true', default=False)
    args = parser.parse_args()
    return args


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
    if op != "all":
        return

    triggerKey = triggerRename["commit"] + triggerRename["file"] + str(triggerRename["line"]) + triggerRename["oldName"]
    correctIndex = []
    correct = 0
    for rr in range(len(renames)):
        rename = renames[rr]
        key = rename["commit"] + rename["file"] + str(rename["line"]) + rename["oldName"]
        if triggerKey == key:
            continue
        sameKey = str(rename["line"]) + rename["type"] + rename["oldName"] + rename["file"]
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
    result_info.append([triggerRename["commit"], triggerRename["oldName"], triggerRename["newName"], triggerRename["type"], precision, recall, fscore])
    
    for ci in correctIndex:
        reI = ci[0]
        recI = ci[1]
        detail_info.append([triggerRename["commit"], triggerRename["file"], triggerRename["line"], triggerRename["type"], triggerRename["oldName"], triggerRename["newName"], 
                            renames[reI]["file"], renames[reI]["line"], renames[reI]["type"], renames[reI]["oldName"], renames[reI]["newName"], recommend[recI]["join"], recommend[recI]["rank"]])
    for r in range(len(renames)):
        rename = renames[r]
        flag = True
        key = rename["commit"] + rename["file"] + str(rename["line"]) + rename["oldName"]
        if triggerKey == key:
            continue
        for v in correctIndex:
            if r == v[0]:
                flag = False
        if flag:
            detail_info.append([triggerRename["commit"], triggerRename["file"], triggerRename["line"], triggerRename["type"], triggerRename["oldName"], triggerRename["newName"], 
                                renames[r]["file"], renames[r]["line"], renames[r]["type"], renames[r]["oldName"], renames[r]["newName"], "NAN", "Nan"])

    for r in range(len(recommend)):
        flag = True
        for v in correctIndex:
            if r == v[0]:
                flag = False
        if flag:
            detail_info.append([triggerRename["commit"], triggerRename["file"], triggerRename["line"], triggerRename["type"], triggerRename["oldName"], triggerRename["newName"], 
                                recommend[r]["files"], recommend[r]["line"], recommend[r]["typeOfIdentifier"], recommend[r]["name"], "NAN", recommend[r]["join"], recommend[r]["rank"]])

def evaluate(triggerRename, renames, recommend, op):
    triggerKey = triggerRename["commit"] + triggerRename["file"] + str(triggerRename["line"]) + triggerRename["oldName"]
    correct = 0
    for rename in renames:

        key = rename["commit"] + rename["file"] + str(rename["line"]) + rename["oldName"]
        if triggerKey == key:
            continue
        sameKey = str(rename["line"]) + rename["type"] + rename["oldName"] + rename["file"]
        for rec in recommend:
            recKey = str(rec["line"]) + rec["typeOfIdentifier"] + rec["name"] + rec["files"]
            if sameKey == recKey:
                correct += 1
                break
    precision = correct / len(recommend) if len(recommend) != 0 else 0
    recall = correct / (len(renames) - 1)
    fscore = 2 * precision * recall / (precision + recall) if correct != 0 else 0
    allPrecision[op].append(precision)
    allRecall[op].append(recall)
    allFscore[op].append(fscore)

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
    
    if coRename == -1 or conceptRename == "FALSE":
        continue

    if commit not in coRenameGroup:
        coRenameGroup[commit] = {}

    if coRename not in coRenameGroup[commit]:
        coRenameGroup[commit][coRename] = []
    
    data = {"oldName": oldName, "newName": newName, "Operation": operation, "coRename": coRename, "commitdate": commitDate,
             "commit": commit, "type": typeOfIdentifier, "file": file, "line": line}
    coRenameGroup[commit][coRename].append(data)

for fileName, op in researchFileNames.items():

    recommendName, renameInfo = setRename(mainArgs.source[0], fileName)
    print(fileName)

    for commit, coRenames in coRenameGroup.items():
        for num, renames in coRenames.items():
            for triggerRename in renames:
                key = triggerRename["commit"] + triggerRename["file"] + str(triggerRename["line"]) + triggerRename["oldName"]
                if key not in recommendName:
                    print(key)
                    continue
                recommend = recommendName[key]
                if len(renames) <= 1:
                    print(renames)
                    continue
                evaluate(triggerRename, renames, recommend, op)
                detail(triggerRename, renames, recommend, op)

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