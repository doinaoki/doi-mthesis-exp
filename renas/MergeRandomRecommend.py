import pathlib
import simplejson
import os
import argparse
import time
from datetime import timedelta
import heapq
import numpy as np
import matplotlib.pyplot as plt
import japanize_matplotlib

import pandas as pd
from .util.Rename import Rename, setAbbrDic
from .util.ExTable import ExTable
from .util.common import printDict, convertRenameType
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG, log, basicConfig
from copy import deepcopy


_logger = getLogger(__name__)
_logger.setLevel(DEBUG)
devideNumber = 20
thresholdNumber = 100
TOPN = 20
ratio = [i/devideNumber for i in range(0, devideNumber+1)]
MERGE_COST = {f"All{i}" :[[0, 0, 0] for i in range(thresholdNumber + 1)] for i in ratio}
MERGE_MAP = {f"All{i}" :0 for i in ratio}
MERGE_MRR = {f"All{i}" :0 for i in ratio}
MERGE_TOPN = {f"All{i}" :[[0, 0, 0] for i in range(TOPN)] for i in ratio}

#コマンドライン引数処理
def setArgument():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', help='set directory containing repositories to be analyzed', nargs='+')
    parser.add_argument('-d', help='set debug mode', action='store_true', default=False)
    parser.add_argument('-f', '--force', help='set force mode', action='store_true', default=False)
    args = parser.parse_args()
    return args

#ログ情報出力(後)
def setLogger(level):
    root_logger = getLogger()
    root_logger.setLevel(level)
    handler = StreamHandler()
    handler.setLevel(level)
    formatter = Formatter('[%(asctime)s] %(name)s -- %(levelname)s : %(message)s')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    return root_logger

def updateMergeCost(costs, name):
    for c in range(thresholdNumber + 1):
        values = eval(costs[c])
        precision = values[0]
        recall = values[1]
        fscore = values[2]
        MERGE_COST[name][c][0] += precision
        MERGE_COST[name][c][1] += recall
        MERGE_COST[name][c][2] += fscore

def updateMapMrr(mapMrr, name):
    mapValue = mapMrr[0]
    mrrValue = mapMrr[1]
    MERGE_MAP[name] += float(mapValue)
    MERGE_MRR[name] += float(mrrValue)

def updateTopN(topN, name):
    for c in range(TOPN):
        values = eval(topN[c])
        precision = values[0]
        recall = values[1]
        fscore = values[2]
        MERGE_TOPN[name][c][0] += precision
        MERGE_TOPN[name][c][1] += recall
        MERGE_TOPN[name][c][2] += fscore

def registerValue(repo):
    colRange = range(105)
    repo = pathlib.Path(repo)
    dataPath = repo.joinpath(repo, "randomRanking", "figure", "figData.csv")
    if not os.path.isfile(dataPath):
        _logger.info("file does not exist")
        exit(1)
    df = pd.read_csv(dataPath, names=colRange, header=None).fillna(0).to_dict("index")
    for i in range(0, 7*len(ratio), 7):
        nameIndex = i
        operationIndex = i+1
        hopIndex = i+2
        costIndex = i+3
        typeIndex = i+4
        topNIndex = i+5
        MapMrrIndex = i+6
        updateMergeCost(df[costIndex], df[nameIndex][0])
        updateMapMrr(df[MapMrrIndex], df[nameIndex][0])
        updateTopN(df[topNIndex], df[nameIndex][0])


def showCostFigure(path, fileLength):
    colors = ["black", "black", "black"]
    columns = ["Precision", "Recall", "Fscore"]
    leftValue = np.array([i / thresholdNumber for i in range(thresholdNumber + 1)])

    for fl in MERGE_COST.keys():
        costData = np.array(MERGE_COST[fl])
        for i in range(len(columns)):
            col = columns[i]
            data = costData[:, i] / fileLength
            if i == 2 and fl == "All0.5":
                print([f"{i}: {k}"for i, k in enumerate(data)])
            fig, ax = plt.subplots()
            plt.plot(leftValue, data, color=colors[i])
            plt.xlim(0,1)
            plt.xlabel('優先度閾値')
            plt.ylabel('Fscore')
            fig.savefig(os.path.join(path, 'mergeCost{}{}.pdf'.format(fl, col)))
            plt.close(fig)        

def caluculateCostValues(fileLength, path):
    maxFscoreValue = 0
    maxAllIndex = ""
    maxFscoreList = {mc: 0 for mc in MERGE_COST.keys()}
    for mc in MERGE_COST.keys():
        costData = np.array(MERGE_COST[mc])
        costFscore = costData[:, 2]  / fileLength
        maxValue = np.amax(costFscore)
        maxFscoreList[mc] = maxValue
        if maxFscoreValue < maxValue:
            maxFscoreValue = maxValue
            maxAllIndex = mc
        _logger.info(f"{mc}: maxFscore = {maxValue}")
        #_logger.info(costFscore)
    _logger.info(f"{maxAllIndex} : {maxFscoreValue}")

    left = [i for i in ratio]
    fig, ax = plt.subplots()

    p1 = plt.plot(left, list(maxFscoreList.values()), color='black')
    #p1 = ax.bar(left, list(maxFscoreList.values()), color='b')
    #ax.bar_label(p1, label_type='edge')
    plt.xlabel('α')
    plt.ylabel('Fscore')
    plt.savefig(os.path.join(path, 'costBar.svg'))  
    #plt.show()

def showMAPMRRFigure(fileLength, path):
    valueMAPList = [v / fileLength for v in MERGE_MAP.values()]
    valueMRRList = [v / fileLength for v in MERGE_MRR.values()]
    xAxisValue = ratio

    #MAP
    fig, ax = plt.subplots()
    plt.plot(xAxisValue, valueMAPList)
    plt.xlabel('α')
    plt.ylabel('MAP')
    maxIndex = np.argmax(valueMAPList)
    maxValue = valueMAPList[maxIndex]
    #print(maxIndex / len(ratio), maxValue)
    plt.plot(maxIndex / (len(ratio) - 1), maxValue, '.', markersize=7, color='r')
    #plt.text(maxIndex / (len(ratio) - 1), maxValue, round(maxValue, 3))
    #plt.ylim(0, max(valueMAPList)+0.08)
    fig.savefig(os.path.join(path, 'mergeMAP.svg'))
    plt.close(fig) 

    #MRR
    fig, ax = plt.subplots()
    plt.plot(xAxisValue, valueMRRList)
    plt.xlabel('α')
    plt.ylabel('MRR')
    maxIndex = np.argmax(valueMRRList)
    maxValue = valueMRRList[maxIndex]
    #print(maxIndex / len(ratio), maxValue)
    plt.plot(maxIndex / (len(ratio) - 1), maxValue, '.', markersize=7, color='r')
    #plt.text(maxIndex / (len(ratio) - 1), maxValue, round(maxValue, 3))
    #plt.ylim(0, max(valueMRRList)+0.08)
    fig.savefig(os.path.join(path, 'mergeMRR.svg'))
    plt.close(fig)  

def showTopNFigure(fileLength, path):
    columns = ["Precision", "Recall", "Fscore"]
    colors = ["red", "green", "gold"]
    leftValue = np.array([i+1 for i in range(TOPN)])
    top1Recall = {f"All{i}": 0 for i in ratio}
    top5Recall = {f"All{i}": 0 for i in ratio}
    top10Recall = {f"All{i}": 0 for i in ratio}
    for o in MERGE_TOPN.keys():
        for i in range(len(columns)):
            col = columns[i]
            data = np.array(MERGE_TOPN[o])[:, i] / fileLength
            fig, ax = plt.subplots()
            p1 = ax.bar(leftValue, data, color=colors[i])
            plt.ylabel('{}'.format(i))
            plt.xlabel('topN')
            fig.savefig(os.path.join(path, 'topN{}{}.png'.format(col, o)))
            plt.close(fig)

            if i == 1:
                top1Recall[o] = data[0]
                top5Recall[o] = data[4]
                top10Recall[o] = data[9]
                #print(f"{o}\n top1:{data[0]}\n top5:{data[4]}\n top10:{data[9]}")
    fig, ax = plt.subplots()
    p1 = ax.plot(ratio, list(top1Recall.values()))
    plt.ylabel('top1Recall')
    plt.xlabel('α')
    maxIndex = np.argmax(list(top1Recall.values()))
    maxValue = list(top1Recall.values())[maxIndex]
    #print(maxIndex / len(ratio), maxValue)
    plt.plot(maxIndex / (len(ratio) - 1), maxValue, '.', markersize=7, color='r')
    plt.text(maxIndex / (len(ratio) - 1), maxValue, round(maxValue, 3))
    fig.savefig(os.path.join(path, 'top1Recall.pdf'))
    plt.close(fig)

    fig, ax = plt.subplots()
    p1 = ax.plot(ratio, list(top5Recall.values()))
    plt.ylabel('top5Recall')
    plt.xlabel('α')
    maxIndex = np.argmax(list(top5Recall.values()))
    maxValue = list(top5Recall.values())[maxIndex]
    #print(maxIndex / len(ratio), maxValue)
    plt.plot(maxIndex / (len(ratio) - 1), maxValue, '.', markersize=7, color='r')
    plt.text(maxIndex / (len(ratio) - 1), maxValue, round(maxValue, 3))
    fig.savefig(os.path.join(path, 'top5Recall.pdf'))
    plt.close(fig)

    fig, ax = plt.subplots()
    p1 = ax.plot(ratio, list(top10Recall.values()))
    plt.ylabel('top10Recall')
    plt.xlabel('α')
    maxIndex = np.argmax(list(top10Recall.values()))
    maxValue = list(top10Recall.values())[maxIndex]
    #print(maxIndex / len(ratio), maxValue)
    plt.plot(maxIndex / (len(ratio) - 1), maxValue, '.', markersize=7, color='r')
    plt.text(maxIndex / (len(ratio) - 1), maxValue, round(maxValue, 3))
    fig.savefig(os.path.join(path, 'top10Recall.pdf'))
    plt.close(fig)

    print(top1Recall["All0.0"], top1Recall["All1.0"])
    print(top5Recall["All0.0"], top5Recall["All1.0"])
    print(top10Recall["All0.0"], top10Recall["All1.0"])
    print(top1Recall, top1Recall)
    print(top5Recall, top5Recall)
    print(top10Recall, top10Recall)



if __name__ == '__main__':
    mainArgs = setArgument()
    rootLogger = setLogger(DEBUG if mainArgs.d else INFO)

    for repo in mainArgs.source:
        registerValue(repo)

    resultPath =  pathlib.Path(mainArgs.source[0]).parent.joinpath("randomMerge")
    if not os.path.isdir(resultPath):
        os.makedirs(resultPath, exist_ok=True)
    fileLength = len(mainArgs.source)
    showCostFigure(resultPath, fileLength)
    caluculateCostValues(fileLength, resultPath)
    showMAPMRRFigure(fileLength, resultPath)
    showTopNFigure(fileLength, resultPath)
    print([(i, v / fileLength) for i, v in MERGE_MAP.items()])
    print([(i, v / fileLength) for i, v in MERGE_MRR.items()])