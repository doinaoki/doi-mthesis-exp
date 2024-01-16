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
researchFileNames = {
                    "recommend_none.json": "None",
                    "recommend_relation_normalize.json": "Normalize",
                    "recommend_relation.json": "Relation",
                    "recommend_all_normalize.json": "All"}

MERGE_COST = {k: [[0, 0, 0] for i in range(thresholdNumber + 1)] for k in researchFileNames.values()}
MERGE_TOPN = [[0, 0, 0] for i in range(TOPN)]

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


def registerValue(repo):
    colRange = range(105)
    repo = pathlib.Path(repo)
    dataPath = repo.joinpath(repo, "figure", "figData.csv")
    if not os.path.isfile(dataPath):
        _logger.info("file does not exist")
        exit(1)
    df = pd.read_csv(dataPath, names=colRange, header=None).fillna(0).to_dict("index")
    for i in range(0, 5*len(researchFileNames), 5):
        nameIndex = i
        operationIndex = i+1
        hopIndex = i+2
        costIndex = i+3
        typeIndex = i+4

        updateMergeCost(df[costIndex], df[nameIndex][0])


def showCostFigure(path, fileLength):
    colors = ["red", "green", "gold"]
    columns = ["Precision", "Recall", "Fscore"]
    leftValue = np.array([i / thresholdNumber for i in range(thresholdNumber + 1)])
    for fl in MERGE_COST.keys():
        costData = np.array(MERGE_COST[fl])
        for i in range(len(columns)):
            col = columns[i]
            if fl != "All":
                data = np.array([costData[0][i] / fileLength for _ in range(thresholdNumber + 1)])
            else:
                data = costData[:, i] / fileLength
            fig, ax = plt.subplots()
            plt.plot(leftValue, data, color=colors[i])
            plt.xlim(0,1)
            plt.xlabel('優先度閾値')
            plt.ylabel('Fscore')
            fig.savefig(os.path.join(path, 'mergeCost{}{}.pdf'.format(fl, col)))
            plt.close(fig)        


if __name__ == '__main__':
    mainArgs = setArgument()
    rootLogger = setLogger(DEBUG if mainArgs.d else INFO)

    for repo in mainArgs.source:
        registerValue(repo)

    resultPath =  pathlib.Path(mainArgs.source[0]).parent.joinpath("Merge")
    if not os.path.isdir(resultPath):
        os.makedirs(resultPath, exist_ok=True)
    fileLength = len(mainArgs.source)
    showCostFigure(resultPath, fileLength)
