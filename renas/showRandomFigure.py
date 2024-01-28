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

devideNumber = 20
thresholdNumber = 100
ratio = [i/devideNumber for i in range(0, devideNumber+1)]
researchFileNames = {f"recommend_all_normalize{i}.json": f"All{i}" for i in ratio}

operations = ["insert", "delete", "replace", "order", "format"]
typeOfIdentifiers = ["ParameterName", "VariableName", "MethodName", "FieldName", "ClassName"]
UPPER_HOP = 100

class showRandomFigure:

    def __init__(self, topN):
        self.topN = topN
        self.topNData = {v: [[0, 0, 0] for _ in range(topN)] for v in researchFileNames.values()}
        #[count, precision, recall, fscore]
        self.operationData = {v: {op: [0, 0, 0, 0] for op in operations} for v in researchFileNames.values()}
        self.hopData = {v: [[0, 0, 0] for _ in range(UPPER_HOP)] for v in researchFileNames.values()}
        self.costData = {v: [[0, 0, 0] for _ in range(thresholdNumber+1)] for v in researchFileNames.values()}
        #識別子の種類, 成功数, 失敗数
        self.typeData = {v: {toi: [0, 0, 0] for toi in typeOfIdentifiers} for v in researchFileNames.values()}
        self.countRename = {v: 0 for v in researchFileNames.values()}
        self.MAPData = {v: [] for v in researchFileNames.values()}
        self.MRRData = {v: [] for v in researchFileNames.values()}
        self.maxCost = thresholdNumber
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
        hopAllCount = [0 for _ in range(UPPER_HOP)]
        costAllCount = [0 for _ in range(self.maxCost+1)]
        typeAllCount = {t: 0 for t in typeOfIdentifiers}
        for recommendInfo in recommends:
            cost = math.floor(recommendInfo["rank"])
            hop = recommendInfo["hop"] - 1
            typeOfId = recommendInfo["typeOfIdentifier"]
            hopAllCount[hop] += 1
            if cost <= self.maxCost:
                costAllCount[cost] += 1
            typeAllCount[typeOfId] += 1

        topNCount = [0 for _ in range(self.topN)]
        hopCount = [0 for _ in range(UPPER_HOP)]
        costCount = [0 for _ in range(self.maxCost+1)]
        typeCount = {t: 0 for t in typeOfIdentifiers}
        #rankingEvaluation = [0 for _ in range(self.topN)]
        for trIdx in trueRecommendIndex:
            renameInfo = renames[trIdx[0]]
            recommendInfo = recommends[trIdx[1]]
            cost = math.floor(recommendInfo["rank"])
            hop = recommendInfo["hop"] - 1
            ranking = trIdx[1]
            typeOfId = recommendInfo["typeOfIdentifier"]
            if ranking < self.topN:
                topNCount[ranking] += 1
            hopCount[hop] += 1
            if cost <= self.maxCost:
                costCount[cost] += 1
            #if cost == 100.0:
            #    print(recommendInfo['similarity'], recommendInfo['relationship'],recommendInfo['rank'] , option)
            typeCount[typeOfId] += 1
        precision = len(trueRecommendIndex) / recommendsLength if recommendsLength != 0 else 0
        recall = len(trueRecommendIndex) / renamesLength
        fscore = self.calcFscore(precision, recall)

        self.updateTopNData(topNCount, renamesLength, recommendsLength, option)
        #self.updateOperationData(triggerRename, precision, recall, fscore, option)
        self.updateHopData(hopAllCount, hopCount, renamesLength, recommendsLength, option)
        self.updateCostData(costAllCount, costCount, renamesLength, recommendsLength, option)
        self.updateTypeData(typeAllCount, typeCount, triggerRename, recommendsLength, option)
        self.updateMAP(topNCount, renamesLength, recommendsLength, option)
        self.updateMRR(topNCount, renamesLength, recommendsLength, option)

        self.countRename[option] += 1

    def updateMAP(self, topNCount, renamesLength, recommendsLength, option):
        searchLength = self.topN
        countCorrect = 0
        MAP = 0
        for sl in range(searchLength):
            if topNCount[sl] == 1:
                countCorrect += 1
                MAP += (countCorrect / (sl + 1))
            elif topNCount[sl] > 1:
                print("something wrong")
                exit(1)
                return
        MAP = MAP / renamesLength if renamesLength != 0 else 0
        self.MAPData[option].append(MAP)

    def updateMRR(self, rankingEvaluation, renamesLength, recommendsLength, option):
        searchLength = self.topN
        MRR = 0  
        for sl in range(searchLength):
            if rankingEvaluation[sl] == 1:
                MRR += (1 / (sl + 1))
                break
        self.MRRData[option].append(MRR)
              
    
    # Top ?のときの精度
    def updateTopNData(self, topNCount, renamesLength, recommendsLength, option):
        nCount = 0
        for tncIdx in range(self.topN):
            nCount += topNCount[tncIdx]
            naCount = (tncIdx + 1) if tncIdx + 1 <= recommendsLength else recommendsLength
            precision = nCount / naCount if naCount != 0 else 0
            recall = nCount / renamesLength
            fscore = self.calcFscore(precision, recall)
            self.topNData[option][tncIdx][0] += precision
            self.topNData[option][tncIdx][1] += recall
            self.topNData[option][tncIdx][2] += fscore

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
        for hc in range(UPPER_HOP):
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
        for c in range(self.maxCost + 1):
            cc = self.maxCost - c
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
        allN = self.countRename["All1.0"]
        print(self.countRename)
        for op, v in self.costData.items():
            for l in range(len(v)):
                self.costData[op][l][0] = self.costData[op][l][0] / allN
                self.costData[op][l][1] = self.costData[op][l][1] / allN
                self.costData[op][l][2] = self.costData[op][l][2] / allN
        for op in self.topNData.keys():
            for l in range(len(self.topNData[op])):
                self.topNData[op][l][0] = self.topNData[op][l][0] / allN
                self.topNData[op][l][1] = self.topNData[op][l][1] / allN
                self.topNData[op][l][2] = self.topNData[op][l][2] / allN
        for op, v in self.hopData.items():
            for l in range(len(v)):
                self.hopData[op][l][0] = self.hopData[op][l][0] / allN
                self.hopData[op][l][1] = self.hopData[op][l][1] / allN
                self.hopData[op][l][2] = self.hopData[op][l][2] / allN
        for op, v in self.operationData.items():
            for l in v:
                n = self.operationData[op][l][0]
                if n == 0:
                    continue
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
                w.writerow(self.topNData[i])
                if self.MAPData[i] != [] and self.MRRData[i] != []:
                    w.writerow([statistics.mean(self.MAPData[i]), statistics.mean(self.MRRData[i])])
                else:
                    w.writerow([0, 0])
                     
        plt.rcParams['font.family'] = 'Hiragino Maru Gothic Pro'
        plt.rcParams["savefig.dpi"] = 300
        #self.showTopNFigure(figPath)
        self.showCostFigure(figPath)
        #self.showHopFigure(figPath)
        #self.showTypeTable(figPath)
        plt.rcParams['font.family'] = 'Times New Roman'
        #self.showOperationTable(figPath)
        
    def showTopNFigure(self, path):
        columns = ["Precision", "Recall", "Fscore"]
        colors = ["red", "green", "gold"]
        leftValue = np.array([i+1 for i in range(self.topN)])
        for o in self.topNData.keys():
            for i in range(len(columns)):
                col = columns[i]
                data = np.array(self.topNData[o])[:, i]
                fig, ax = plt.subplots()
                p1 = ax.bar(leftValue, data, color=colors[i])
                fig.savefig(os.path.join(path, 'topN{}{}.png'.format(col, o)))
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
        useCost = self.costData["All1.0"]
        colors = ["red", "green", "gold"]
        columns = ["Precision", "Recall", "Fscore"]
        costData = np.array(useCost)
        leftValue = np.array([i / self.maxCost for i in range(self.maxCost + 1)])

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
        leftValue = np.array([i+1 for i in range(UPPER_HOP)])
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
