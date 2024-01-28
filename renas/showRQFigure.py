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
import pytrec_eval

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
UPPER_HOP = 100
thresholdNumber = 100

class showRQFigure:

    def __init__(self, topN, maxCost):
        self.topN = topN
        self.topNData = {"Normalize": [[0, 0, 0] for _ in range(topN)], "All": [[0, 0, 0] for _ in range(topN)]}
        #[count, precision, recall, fscore]
        self.operationData = {v: {op: [0, 0, 0, 0] for op in operations} for v in researchFileNames.values()}
        self.hopData = {v: [[0, 0, 0] for _ in range(UPPER_HOP)] for v in researchFileNames.values()}
        self.costData = {v: [[0, 0, 0] for _ in range(thresholdNumber + 1)] for v in researchFileNames.values()}
        #識別子の種類, 成功数, 失敗数
        self.typeData = {v: {toi: [0, 0, 0, 0] for toi in typeOfIdentifiers} for v in researchFileNames.values()}
        self.countRename = {v: 0 for v in researchFileNames.values()}
        self.MAPData = {"Normalize": [], "All": []}
        self.MRRData = {"Normalize": [], "All": []}
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
        costAllCount = [0 for _ in range(self.maxCost + 1)]
        typeAllCount = {t: 0 for t in typeOfIdentifiers}
        for recommendInfo in recommends:
            cost = math.floor(recommendInfo["rank"])
            hop = recommendInfo["hop"] - 1
            typeOfId = recommendInfo["typeOfIdentifier"]
            hopAllCount[hop] += 1
            if cost <= self.maxCost:
                costAllCount[cost] += 1
            #typeAllCount[typeOfId] += 1

        for ren in renames:
            typeOfId = ren["typeOfIdentifier"]
            typeAllCount[typeOfId] += 1

        topNCount = [0 for _ in range(max(recommendsLength, self.topN))]
        hopCount = [0 for _ in range(UPPER_HOP)]
        costCount = [0 for _ in range(self.maxCost + 1)]
        typeCount = {t: 0 for t in typeOfIdentifiers}
        #rankingEvaluation = [0 for _ in range(self.topN)]
        for trIdx in trueRecommendIndex:
            renameInfo = renames[trIdx[0]]
            recommendInfo = recommends[trIdx[1]]
            cost = math.floor(recommendInfo["rank"])
            hop = recommendInfo["hop"] - 1
            ranking = trIdx[1]
            typeOfId = recommendInfo["typeOfIdentifier"]
            if option == "All" or option == "Normalize":
                if ranking < recommendsLength:
                    topNCount[ranking] += 1
            hopCount[hop] += 1
            if cost <= self.maxCost:
                costCount[cost] += 1
            if cost <= self.maxCost:
                typeCount[typeOfId] += 1

        #self.updateHopData(hopAllCount, hopCount, renamesLength, recommendsLength, option)
        #self.updateOperationData(triggerRename, precision, recall, fscore, option)
        #self.updateTypeData(triggerRename, precision, recall, fscore, option)

        precision = 0
        recall = 0
        fscore = 0
        if option != "All":
            precision = len(trueRecommendIndex) / recommendsLength if recommendsLength != 0 else 0
            recall = len(trueRecommendIndex) / renamesLength
            fscore = self.calcFscore(precision, recall)
            self.costData[option][0][0] += precision
            self.costData[option][0][1] += recall
            self.costData[option][0][2] += fscore
        #else:  
        #    precision = self.calculatePrecision(55, costCount, costAllCount)
        #    recall = self.calculateRecall(55, costCount, renamesLength)
        #    fscore = self.calcFscore(precision, recall)

        if option == "All":
            self.updateCostData(costAllCount, costCount, renamesLength, recommendsLength, option)
        if option == "All" or option == "Normalize":
            v = self.usePytrec(renames, recommends, triggerRename)
            pp, pr = self.updateTopNData(topNCount, renamesLength, recommendsLength, option)
            Map = self.updateMAP(topNCount, renamesLength, trueRecommendIndex, option)
            Mrr = self.updateMRR(topNCount, renamesLength, recommendsLength, option)
            if v['recall_10'] != pr or v['P_10'] != pp:
                print(f"{v['recall_10']}, {pr}, {v['P_10']}, {pp}")
                print(trueRecommendIndex)
                print(topNCount)
                print("precision 10 error")
                exit(1)

            if abs(v["map"] - Map) >= 10**(-4)  or abs(v["recip_rank"] - Mrr) >= 10**(-4):
                print(f"{v}, {Map}, {Mrr}")
                print(trueRecommendIndex)
                print(topNCount)
                print("map or mrr error")
                exit(1)

        self.countRename[option] += 1

    def usePytrec(self, renames, recommends, triggerRename):
        triggerKey = self.getKey(triggerRename)
        qrel = {triggerKey: {}}
        run = {triggerKey: {}}
        for re in renames:
            qrel[triggerKey][self.getKey(re)+re["typeOfIdentifier"]] = 1
        for r in range(len(recommends)):
            rec = recommends[r]
            key = triggerRename['commit'] + rec['files'] + str(rec['line']) + rec['name']+rec['typeOfIdentifier']
            run[triggerKey][key] = len(recommends) - r
        evaluator = pytrec_eval.RelevanceEvaluator(
            qrel, {'map', 'recip_rank', 'recall', 'P'})
        value = evaluator.evaluate(run)
        #print(qrel)
        #print(run)
        return value[triggerKey]

    def calculatePrecision(self, cost, costCount, costAllCount):
        sumCost = 0
        sumTrueCost = 0
        for i in range(cost + 1):
            ii = self.maxCost - i
            sumCost += costAllCount[ii]
            sumTrueCost += costCount[ii]
        return sumTrueCost / sumCost if sumCost != 0 else 0

    def calculateRecall(self, cost, costCount, renamesLength):
        sumTrueCost = 0
        for i in range(cost + 1):
            ii = self.maxCost - i
            sumTrueCost += costCount[ii]
        return sumTrueCost / renamesLength if renamesLength != 0 else 0

    def updateMAP(self, topNCount, renamesLength, trueRecommendIndex, option):
        if option != "Normalize" and option != "All":
            return

        searchLength = len(topNCount)
        countCorrect = 0
        MAP = 0
        for sl in range(searchLength):
            if topNCount[sl] == 1:
                countCorrect += 1
                MAP += (countCorrect / (sl + 1))
            elif topNCount[sl] > 1:
                print(topNCount)
                print("something wrong")
                exit(1)
        MAP = MAP / renamesLength if renamesLength != 0 else 0
        self.MAPData[option].append(MAP)
        return MAP

    def updateMRR(self, topNCount, renamesLength, recommendsLength, option):
        if option != "Normalize" and option != "All":
            return
        searchLength = len(topNCount)
        MRR = 0  
        for sl in range(searchLength):
            if topNCount[sl] == 1:
                MRR += (1 / (sl + 1))
                break
        self.MRRData[option].append(MRR)
        return MRR
              
    
    # Top ?のときの精度
    def updateTopNData(self, topNCount, renamesLength, recommendsLength, option):
        if option != "Normalize" and option != "All":
            return
        nCount = 0
        pr = 0
        pp = 0
        for tncIdx in range(self.topN):
            nCount += topNCount[tncIdx]
            naCount = (tncIdx + 1)
            precision = nCount / naCount if naCount != 0 else 0
            recall = nCount / renamesLength
            fscore = self.calcFscore(precision, recall)
            self.topNData[option][tncIdx][0] += precision
            self.topNData[option][tncIdx][1] += recall
            self.topNData[option][tncIdx][2] += fscore
            if naCount == 10:
                pp = precision
                pr = recall
        return pp, pr
    '''
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
    '''
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
    def updateTypeData(self, triggerRename, precision, recall, fscore, option):
        self.typeData[option][triggerRename["typeOfIdentifier"]][0] += 1
        self.typeData[option][triggerRename["typeOfIdentifier"]][1] += precision
        self.typeData[option][triggerRename["typeOfIdentifier"]][2] += recall
        self.typeData[option][triggerRename["typeOfIdentifier"]][3] += fscore


    def calcFscore(self, precision, recall):
        if precision == 0 or recall == 0:
            return 0
        else:
            return 2 * precision * recall / (precision + recall)

    def getKey(self, dic):
        return dic["commit"] + dic["files"] + str(dic["line"]) + dic["oldname"] 
    
    def showConsole(self):
        #print(self.costData)
        print(self.topNData)
        #print(self.operationData)
        #print(self.typeData)
        #print(self.hopData)
        #print(self.countRename)
        print(self.MAPData)
        print(self.MRRData)

    def calculateData(self):
        allN = self.countRename["All"]
        for op, v in self.costData.items():
            for l in range(len(v)):
                self.costData[op][l][0] = self.costData[op][l][0] / allN
                self.costData[op][l][1] = self.costData[op][l][1] / allN
                self.costData[op][l][2] = self.costData[op][l][2] / allN
        for op in ["Normalize", "All"]:
            for l in range(len(self.topNData[op])):
                self.topNData[op][l][0] = self.topNData[op][l][0] / allN
                self.topNData[op][l][1] = self.topNData[op][l][1] / allN
                self.topNData[op][l][2] = self.topNData[op][l][2] / allN
        '''
        for op, v in self.typeData.items():
            for l in v:
                allTypeCount = self.typeData[op][l][0]
                if allTypeCount == 0:
                    continue
                self.typeData[op][l][1] = round(self.typeData[op][l][1] / allTypeCount, 2)
                self.typeData[op][l][2] = round(self.typeData[op][l][2] / allTypeCount, 2)
                self.typeData[op][l][3] = round(self.typeData[op][l][3] / allTypeCount, 2)
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
        '''

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
            w.writerow(self.topNData["Normalize"])
            w.writerow(self.topNData["All"])
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
        print(self.MRRData)
            

            
        plt.rcParams['font.family'] = 'Hiragino Maru Gothic Pro'
        plt.rcParams["savefig.dpi"] = 300
        self.showTopNFigure(figPath)
        self.showCostFigure(figPath)
        #self.showHopFigure(figPath)
        #self.showTypeTable(figPath)
        #plt.rcParams['font.family'] = 'Times New Roman'
        #self.showOperationTable(figPath)
        
    def showTopNFigure(self, path):
        columns = ["Precision", "Recall", "Fscore"]
        colors = ["red", "green", "gold"]
        for k, data in self.topNData.items():
            topNData = np.array(data)
            leftValue = np.array([i+1 for i in range(self.topN)])
            for i in range(len(columns)):
                col = columns[i]
                data = topNData[:, i]
                fig, ax = plt.subplots()
                p1 = ax.plot(leftValue, data, color=colors[i])
                fig.savefig(os.path.join(path, 'topN{}{}.pdf'.format(col, k)))
                plt.close(fig)
    '''
    def showTypeTable(self, path):
        for i, v in self.typeData.items():
            fig, ax = plt.subplots(figsize=(12,2))
            ax.table(cellText=list(v.values()),
                colLabels=['総数','precision', 'recall', 'fscore'],
                rowLabels=list(v.keys()),
                rowColours=["gray"] * len(v),
                colColours=["gray"] * 4,
                cellLoc='center',
                loc='center')
            ax.axis('off')
            ax.axis('tight')
            fig.savefig(os.path.join(path, 'typeTable{}.png'.format(i)))
            plt.close(fig)
    '''
            
    def showCostFigure(self, path):
        useCost = self.costData["All"]
        colors = ["red", "green", "gold"]
        columns = ["Precision", "Recall", "Fscore"]
        costData = np.array(useCost)
        leftValue = np.array([i/thresholdNumber for i in range(self.maxCost + 1)])

        for i in range(len(columns)):
            col = columns[i]
            data = costData[:, i]
            fig, ax = plt.subplots()
            #p1 = ax.bar(leftValue, data, color=colors[i], tick_label=leftValue)
            plt.plot(leftValue, data, color=colors[i])
            fig.savefig(os.path.join(path, 'cost{}.pdf'.format(col)))
            plt.close(fig)

    '''
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
    '''