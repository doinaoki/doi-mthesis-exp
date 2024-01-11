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
ratio = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
MERGE_COST = {f"All{i}" :[[0, 0, 0] for i in range(50)] for i in ratio}
MERGE_MAP = {f"All{i}" :0 for i in ratio}
MERGE_MRR = {f"All{i}" :0 for i in ratio}
COST = 50

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
    for c in range(COST):
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

def registerValue(repo):
    colRange = range(100)
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


def showCostFigure(path, fileLength):
    colors = ["red", "green", "gold"]
    columns = ["Precision", "Recall", "Fscore"]
    leftValue = np.array([i+1 for i in range(COST)])
    for fl in MERGE_COST.keys():
        costData = np.array(MERGE_COST[fl])
        for i in range(len(columns)):
            col = columns[i]
            data = costData[:, i] / fileLength
            fig, ax = plt.subplots()
            plt.plot(leftValue, data, color=colors[i])
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

    p1 = ax.bar(left, list(maxFscoreList.values()), color='b')
    #ax.bar_label(p1, label_type='edge')]
    plt.xlabel('α')
    plt.ylabel('Fscore')
    plt.savefig(os.path.join(path, 'costBar.pdf'))  
    plt.show()

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
    print([(i, v / fileLength) for i, v in MERGE_MAP.items()])
    print([(i, v / fileLength) for i, v in MERGE_MRR.items()])