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
import math
import matplotlib.pyplot as plt
import numpy as np

from .util.ExTable import ExTable
from datetime import datetime, date, timedelta
import pandas as pd
from .util.Name import KgExpanderSplitter
from .util.Rename import Rename
import statistics

_logger = getLogger(__name__)

researchFileNames = {
                    "recommend_none.json": "None",
                    "recommend_relation_normalize.json": "Normalize",
                    "recommend_relation.json": "Relation",
                    "recommend_all_normalize.json": "All"}

operations = ["insert", "delete", "replace", "order", "format"]
typeOfIdentifiers = ["ParameterName", "VariableName", "MethodName", "FieldName", "ClassName"]

class showRQFigure:

    def __init__(self, topN, maxCost):
        self.topN = topN
        self.topNData = [[0, 0, 0] for _ in range(topN)]
        #[count, precision, recall, fscore]
        self.operationData = {v: {op: [0, 0, 0, 0] for op in operations} for v in researchFileNames.values()}
        self.hopData = {v: [[0, 0, 0] for _ in range(topN)] for v in researchFileNames.values()}
        self.costData = {v: [[0, 0, 0] for _ in range(maxCost)] for v in researchFileNames.values()}
        #識別子の種類, 成功数, 失敗数
        self.typeData = {v: {toi: [0, 0, 0] for toi in typeOfIdentifiers} for v in researchFileNames.values()}
        self.countRename = {v: 0 for v in researchFileNames.values()}
        self.MAPData = {"Normalize": [], "All": []}
        self.MRRData = {"Normalize": [], "All": []}
        self.maxCost = maxCost
        self.operations = operations

    def setOperations(self, operations):
        self.operations = operations

    def setLogger(self, level):
        _logger.setLevel(level)
        root_logger = getLogger()
        handler = StreamHandler()
        handler.setLevel(level)
        formatter = Formatter('[%(asctime)s] %(name)s -- %(levelname)s : %(message)s')
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        root_logger.setLevel(INFO)
        return root_logger


    def update(self, triggerRename, recommends, renames, trueRecommendIndex, option):
        renamesLength = len(renames)
        recommendsLength = len(recommends)
        hopAllCount = [0 for _ in range(self.topN)]
        costAllCount = [0 for _ in range(self.maxCost)]
        typeAllCount = {t: 0 for t in typeOfIdentifiers}
        for recommendInfo in recommends:
            cost = math.ceil(recommendInfo["rank"]) - 1
            hop = recommendInfo["hop"] - 1
            typeOfId = recommendInfo["typeOfIdentifier"]
            hopAllCount[hop] += 1
            costAllCount[cost] += 1
            typeAllCount[typeOfId] += 1

        topNCount = [0 for _ in range(self.topN)]
        hopCount = [0 for _ in range(self.topN)]
        costCount = [0 for _ in range(self.maxCost)]
        typeCount = {t: 0 for t in typeOfIdentifiers}
        rankingEvaluation = [0 for _ in range(recommendsLength)]
        for trIdx in trueRecommendIndex:
            renameInfo = renames[trIdx[0]]
            recommendInfo = recommends[trIdx[1]]
            cost = math.ceil(recommendInfo["rank"]) - 1
            hop = recommendInfo["hop"] - 1
            ranking = trIdx[1]
            typeOfId = recommendInfo["typeOfIdentifier"]
            if option == "All":
                if ranking < self.topN:
                    topNCount[ranking] += 1
            rankingEvaluation[ranking] += 1
            hopCount[hop] += 1
            costCount[cost] += 1
            typeCount[typeOfId] += 1
        precision = len(trueRecommendIndex) / recommendsLength if recommendsLength != 0 else 0
        recall = len(trueRecommendIndex) / renamesLength
        fscore = self.calcFscore(precision, recall)

        self.updateTopNData(topNCount, renamesLength, recommendsLength, option)
        self.updateOperationData(triggerRename, precision, recall, fscore, option)
        self.updateHopData(hopAllCount, hopCount, renamesLength, recommendsLength, option)
        self.updateCostData(costAllCount, costCount, renamesLength, recommendsLength, option)
        self.updateTypeData(typeAllCount, typeCount, triggerRename, recommendsLength, option)
        self.updateMAP(rankingEvaluation, renamesLength, recommendsLength, option)
        self.updateMRR(rankingEvaluation, renamesLength, recommendsLength, option)

        self.countRename[option] += 1

    def updateMAP(self, rankingEvaluation, renamesLength, recommendsLength, option):
        if option != "Normalize" and option != "All":
            return
        searchLength = min(renamesLength, recommendsLength)
        print(renamesLength, recommendsLength)
        countCorrect = 0
        MAP = 0
        for sl in range(searchLength):
            if rankingEvaluation[sl] == 1:
                countCorrect += 1
                MAP += (countCorrect / (sl + 1))
            elif rankingEvaluation[sl] > 1:
                print("something wrong")
                exit(1)
                return
        MAP = MAP / searchLength if searchLength != 0 else 0
        self.MAPData[option].append(MAP)

    def updateMRR(self, rankingEvaluation, renamesLength, recommendsLength, option):
        if option != "Normalize" and option != "All":
            return
        searchLength = min(renamesLength, recommendsLength)
        MRR = 0  
        for sl in range(searchLength):
            if rankingEvaluation[sl] == 1:
                MRR += (1 / (sl + 1))
                break
        self.MRRData[option].append(MRR)
              
    
    # Top ?のときの精度
    def updateTopNData(self, topNCount, renamesLength, recommendsLength, option):
        if option != "All":
            return
        nCount = 0
        for tncIdx in range(self.topN):
            nCount += topNCount[tncIdx]
            naCount = (tncIdx + 1) if recommendsLength > tncIdx else recommendsLength
            precision = nCount / naCount if naCount != 0 else 0
            recall = nCount / renamesLength
            fscore = self.calcFscore(precision, recall)
            self.topNData[tncIdx][0] += precision
            self.topNData[tncIdx][1] += recall
            self.topNData[tncIdx][2] += fscore

    # TopN のときの変更操作ごとの精度
    def updateOperationData(self, triggerRename, precision, recall, fscore, option):
        key = self.getKey(triggerRename)
        renameOperations = self.operations[triggerRename["commit"]][key]
        for ro in renameOperations:
            op = ro[0]
            self.operationData[option][op][0] += 1
            self.operationData[option][op][1] += precision
            self.operationData[option][op][2] += recall
            self.operationData[option][op][3] += fscore

    # hopごとの正解率
    def updateHopData(self, hopAllCount, hopCount, renamesLength, recommendsLength, option):
        hCount = 0
        haCount = 0
        for hc in range(self.topN):
            hCount += hopCount[hc]
            haCount += hopAllCount[hc]
            precision = hCount / haCount if haCount != 0 else 0
            recall = hCount / renamesLength
            fscore = self.calcFscore(precision, recall)
            self.hopData[option][hc][0] += precision
            self.hopData[option][hc][1] += recall
            self.hopData[option][hc][2] += fscore

    # costごとの正解率
    def updateCostData(self, costAllCount, costCount, renamesLength, recommendsLength, option):
        cCount = 0
        caCount = 0
        for cc in range(self.maxCost):
            cCount += costCount[cc]
            caCount += costAllCount[cc]
            precision = cCount / caCount if caCount != 0 else 0
            recall = cCount / renamesLength
            fscore = self.calcFscore(precision, recall)
            self.costData[option][cc][0] += precision
            self.costData[option][cc][1] += recall
            self.costData[option][cc][2] += fscore
    
    # TopN のときの識別子の種類ごとの正解率
    def updateTypeData(self, typeAllCount, typeCount, triggerRename, recommendsLength, option):
        self.typeData[option][triggerRename["typeOfIdentifier"]][0] += 1
        for ti in typeOfIdentifiers:
            missCount = typeAllCount[ti] - typeCount[ti]
            self.typeData[option][ti][1] += typeCount[ti]
            self.typeData[option][ti][2] += missCount


    def calcFscore(self, precision, recall):
        if precision == 0 or recall == 0:
            return 0
        else:
            return 2 * precision * recall / (precision + recall)

    def getKey(self, dic):
        return dic["commit"] + dic["files"] + str(dic["line"]) + dic["oldname"]
    
    def showConsole(self):
        print(self.costData)
        print(self.topNData)
        print(self.operationData)
        print(self.typeData)
        print(self.hopData)
        print(self.countRename)

    def calculateData(self):
        allN = self.countRename["All"]
        for op, v in self.costData.items():
            for l in range(len(v)):
                self.costData[op][l][0] = self.costData[op][l][0] / allN
                self.costData[op][l][1] = self.costData[op][l][1] / allN
                self.costData[op][l][2] = self.costData[op][l][2] / allN
        for l in range(len(self.topNData)):
            self.topNData[l][0] = self.topNData[l][0] / allN
            self.topNData[l][1] = self.topNData[l][1] / allN
            self.topNData[l][2] = self.topNData[l][2] / allN
        for op, v in self.hopData.items():
            for l in range(len(v)):
                self.hopData[op][l][0] = self.hopData[op][l][0] / allN
                self.hopData[op][l][1] = self.hopData[op][l][1] / allN
                self.hopData[op][l][2] = self.hopData[op][l][2] / allN
        for op, v in self.operationData.items():
            for l in v:
                n = self.operationData[op][l][0]
                self.operationData[op][l][1] = round(self.operationData[op][l][1] / n, 2)
                self.operationData[op][l][2] = round(self.operationData[op][l][2] / n, 2)
                self.operationData[op][l][3] = round(self.operationData[op][l][3] / n, 2)

    def showFigure(self, path):
        figPath = os.path.join(path, 'figure')
        figDataPath = os.path.join(figPath, 'figData.csv')
        if not os.path.isdir(figPath):
            os.mkdir(figPath)
        
        with open(figDataPath, 'w') as fCSV:
            w = csv.writer(fCSV)
            for i in researchFileNames.values():
                w.writerow([i])
                w.writerow(self.operationData[i].values())
                w.writerow(self.hopData[i])
                w.writerow(self.costData[i])
                w.writerow(self.typeData[i].values())
            w.writerow(self.topNData)
            w.writerow(["MAP", "MRR"])
            if self.MAPData["Normalize"] != [] and self.MRRData["Normalize"] != 0:
                w.writerow(["Normalize"])
                w.writerow([statistics.mean(self.MAPData["Normalize"]), statistics.mean(self.MRRData["Normalize"])])
            else:
                w.writerow("Normalize")
                w.writerow([0,0])
            if self.MAPData["All"] != [] and self.MRRData["All"] != 0:
                w.writerow(["All"])
                w.writerow([statistics.mean(self.MAPData["All"]), statistics.mean(self.MRRData["All"])])
            else:
                w.writerow("All")
                w.writerow([0,0])
        print(self.MAPData)
            

            
        plt.rcParams['font.family'] = 'Hiragino Maru Gothic Pro'
        plt.rcParams["savefig.dpi"] = 300
        self.showTopNFigure(figPath)
        self.showCostFigure(figPath)
        self.showHopFigure(figPath)
        self.showTypeTable(figPath)
        plt.rcParams['font.family'] = 'Times New Roman'
        self.showOperationTable(figPath)
        
    def showTopNFigure(self, path):
        columns = ["Precision", "Recall", "Fscore"]
        colors = ["red", "green", "gold"]
        topNData = np.array(self.topNData)
        leftValue = np.array([i+1 for i in range(self.topN)])
        for i in range(len(columns)):
            col = columns[i]
            data = topNData[:, i]
            fig, ax = plt.subplots()
            p1 = ax.bar(leftValue, data, color=colors[i], tick_label=leftValue)
            fig.savefig(os.path.join(path, 'topN{}'.format(col)))
            plt.close(fig)

    def showTypeTable(self, path):
        for i, v in self.typeData.items():
            fig, ax = plt.subplots(figsize=(12,2))
            ax.table(cellText=list(v.values()),
                colLabels=['総数','推薦したできた数', '推薦できてない数'],
                rowLabels=list(v.keys()),
                rowColours=["gray"] * len(v),
                colColours=["gray"] * 3,
                cellLoc='center',
                loc='center')
            ax.axis('off')
            ax.axis('tight')
            fig.savefig(os.path.join(path, 'typeTable{}.png'.format(i)))
            plt.close(fig)

    def showCostFigure(self, path):
        useCost = self.costData["All"]
        colors = ["red", "green", "gold"]
        columns = ["Precision", "Recall", "Fscore"]
        costData = np.array(useCost)
        leftValue = np.array([i+1 for i in range(self.maxCost)])

        for i in range(len(columns)):
            col = columns[i]
            data = costData[:, i]
            fig, ax = plt.subplots()
            p1 = ax.bar(leftValue, data, color=colors[i], tick_label=leftValue)
            fig.savefig(os.path.join(path, 'cost{}.png'.format(col)))
            plt.close(fig)

    def showHopFigure(self, path):
        columns = ["Precision", "Recall", "Fscore"]
        colors = ["red", "green", "gold"]
        leftValue = np.array([i+1 for i in range(self.topN)])
        for op, v in self.hopData.items():
            costData = np.array(v)
            for i in range(len(columns)):
                col = columns[i]
                data = costData[:, i]
                fig, ax = plt.subplots()
                p1 = ax.bar(leftValue, data, color=colors[i], tick_label=leftValue)
                fig.savefig(os.path.join(path, 'hop{}{}.png'.format(op, col)))
                plt.close(fig)

    def showOperationTable(self, path):
        for i, v in self.operationData.items():
            fig, ax = plt.subplots()
            ax.table(cellText=list(v.values()),
                colLabels=['Countrename','Precision', 'Recall', 'Fscore'],
                rowLabels=list(v.keys()),
                rowColours=["gray"] * len(v),
                colColours=["gray"] * 4,
                cellLoc='center',
                loc='center')
            ax.axis('off')
            fig.savefig(os.path.join(path, 'operation{}.png'.format(i)))
            plt.close(fig)
