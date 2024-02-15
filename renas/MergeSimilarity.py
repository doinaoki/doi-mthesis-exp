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
ratio = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 20, 25]
MERGE_COST = {f"All{i}" :[[0, 0, 0] for i in range(50)] for i in ratio}

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


def registerValue(repo, similarityData):
    colRange = range(100)
    repo = pathlib.Path(repo)
    dataPath = repo.joinpath(repo, "similarity", "similarity.csv")
    if not os.path.isfile(dataPath):
        _logger.info("file does not exist")
        exit(1)
    with open(dataPath, 'r') as dp:
        sData = [float(v) for v in dp.readline().split(",")]
    similarityData += sData
    


def showSimilarityFigure(path, similarityData):
    width = 0.1
    sData = pd.Series(similarityData)
    bins = np.arange(0, 1.2, width)
    counts, bin = np.histogram(sData, bins=bins, density=True)
    #plt.stairs(counts * width, bin,linewidth=5, linestyle='--', fill=True)

    plt.hist(bin[:-1], bin, weights=counts*width)
    plt.xlabel('類似度')
    plt.ylabel('相対度数')
    plt.savefig(os.path.join(path, "similarity.svg"))

    '''
    freq = sData.value_counts(bins=bins, sort=False)
    print(freq)
    class_value = np.array([0.1, 0.3, 0.5, 0.7, 0.9]) # 階級値
    rel_freq = freq / sData.count()  # 相対度数
    cum_freq = freq.cumsum()  # 累積度数
    rel_cum_freq = rel_freq.cumsum()  # 相対累積度数
    fig, ax1 = plt.subplots()
    dist = pd.DataFrame(
    {
        "class": class_value,
        "frequency": freq,
        "relative frequency": rel_freq,
        "累積度数": cum_freq,
        "相対累積度数": rel_cum_freq,
    },
    index=freq.index
    )
    dist.plot.bar(x="class", y="relative frequency", tick_label=class_value,ax=ax1, width=1, ec="k")
    plt.savefig(os.path.join(path, "similarity.png"))
    '''

if __name__ == '__main__':
    mainArgs = setArgument()
    rootLogger = setLogger(DEBUG if mainArgs.d else INFO)
    similarityData = []
    for repo in mainArgs.source:
        registerValue(repo, similarityData)

    resultPath =  pathlib.Path(mainArgs.source[0]).parent.joinpath("randomMerge")
    if not os.path.isdir(resultPath):
        os.makedirs(resultPath, exist_ok=True)
    fileLength = len(mainArgs.source)
    showSimilarityFigure(resultPath, similarityData)
