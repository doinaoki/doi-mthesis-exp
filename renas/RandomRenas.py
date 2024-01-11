import pathlib
import simplejson
import os
import argparse
import time
from datetime import timedelta
import heapq

import pandas as pd
from .util.Rename import Rename, setAbbrDic
from .util.ExTable import ExTable
from .util.common import printDict, convertRenameType
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG, log, basicConfig
from copy import deepcopy

_logger = getLogger(__name__)
_logger.setLevel(DEBUG)
operationDic = {"all": {}, "Normalize": {}, "None": {}}
_RELATION_LIST = [
    "subclass","subsubclass","parents","ancestor","methods","fields","siblings","comemnt","type","enclosingCLass","assignment","methodInvocated","parameterArgument","parameter","enclosingMethod","argument", "parameterOverload"
]
_IDENTIFIER_LIST = ["id","name","line","files","typeOfIdentifier","split","case","pattern","delimiter"]
_RELATION_COST = {
    "subclass": 3.0,
    "subsubclass": 4.0,
    "parents": 3.0,
    "ancestor": 4.0,
    "methods": 4.0,
    "fields": 4.0,
    "siblings": 1.0,
    "comemnt": 2.0,
    "type": 3.0,
    "enclosingCLass": 4.0,
    "assignment": 1.0,
    "methodInvocated": 2.5,
    "parameterArgument": 2.0,
    "parameter": 3.0,
    "enclosingMethod": 3.0,
    "argument": 2.0, 
    "parameterOverload": 1.0
}
ratio = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
RANK = 50
RANK_DISTANSE_PENALTY = 1
RANK_WORD_PENALTY = 4
RANK_FILE_PENALTY = 1
UPPER = 10000
UPPER_RANKING = 20
RELATION_TIMES = 1
SIMILARITY_TIMES = 1

IS_ALL_RECOMMEND = True
IS_RELATION_RECOMMEND = False
IS_SIMILARITY_RECOMMEND = False

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


def polishJsonData(jsonData):
    jsonData['line'] = jsonData['leftSideLocations'].map(
        lambda x: x[0]['startLine']
    )
    jsonData['files'] = jsonData['location'].map(
        lambda x: x['old']
    )
    jsonData['oldname'] = jsonData['oldname'].map(
        lambda x: x.split(' ')[-1]
    )
    jsonData['newname'] = jsonData['newname'].map(
        lambda x: x.split(' ')[-1]
    )
    jsonData['typeOfIdentifier'] = jsonData['renameType'].map(
        lambda x: convertRenameType(x)
    )
    return

def getRelatedIds(relationSeries):
    relatedIds = set()
    for ids in relationSeries:
        relatedIds.update(id.rsplit(':', 1)[0] for id in ids.split(' - '))
    return relatedIds

def getRelatedIdsAndCost(relationSeries):
    relatedIds = set()
    idToCost = {}
    for i, ids in relationSeries.items():
        idList = {id.rsplit(':', 1)[0] for id in ids.split(' - ')}
        relatedIds.update(idList)
        idToCost.update([(id, _RELATION_COST[i]) for id in idList])
    return relatedIds, idToCost

def recordOperation(commit, op,normalize, all, exception={}):
    opType = ""
    if all:
        opType = "all"
    elif normalize:
        opType = "Normalize"
    else:
        opType = "None"
    if len(exception) != 0:
        key = exception["commit"]+exception["files"]+str(exception["line"])+exception["oldname"]+exception["typeOfIdentifier"]
        if commit not in operationDic[opType]:
            operationDic[opType][commit] = {}
        operationDic[opType][commit][key] = []
        return
    if commit not in operationDic[opType]:
        operationDic[opType][commit] = {}
    operationDic[opType][commit][commit+op[0]] = op[1]

# トリガーとなるRenameを設定.(operational chunkの抽出)
def doCoRename(commit, tableData, trigger, relation, similarity, all):
    _logger.info(f'do co-rename relation = {relation}, similarity = {similarity}')
    triggerData = tableData.selectDataByRow(trigger)
    if triggerData is None:
        recordOperation(commit, [], similarity, all, exception=trigger)
        return []
    triggerDataDictCopy = deepcopy(triggerData.to_dict())
    triggerRename = Rename(triggerDataDictCopy, normalize=True, all=all)
    triggerRename.setNewName(trigger['newname'])
    recordOperation(commit, triggerRename.getOp(), similarity, all)
    return coRenameRelation(tableData, triggerData, triggerRename, relation, similarity)


def coRenameNone(tableData, triggerRename):
    tableDict = tableData.selectDataByColumns(_IDENTIFIER_LIST).to_dict(orient='records')
    recommends = [triggerRename.coRename(deepcopy(d)) for d in tableDict]
    result = [r for r in recommends if r is not None]
    return result


def coRenameRelation(tableData, triggerData, triggerRename, isRelation, isSimilarity):
    triedIds = set()
    triggerScore = 0
    startHop = 0
    nextIds = []
    heapq.heappush(nextIds, [triggerScore, startHop, triggerData["id"]])  
    result = []
    trueRecommend = 0
    trueRecommendScore = RANK
    isNotAll = True
    if isRelation and isSimilarity:
        isNotAll = False
    # 4:30
    while len(nextIds) > 0:
        #調べるidを取得する 0.34  190779
        score, hop, searchId = heapq.heappop(nextIds)
        #print(score, searchId)
        #0.0002   change  0.006   10894
        if searchId in triedIds:
            continue
        triedIds.add(searchId)


        #この処理がだいぶ重い0.003  18.85  10894
        searchData = tableData.selectDataById(searchId)
        #推薦実施
        #0.00005  0.623  10894
        nextScore = score
        searchDataCopy = deepcopy(searchData)

        #print(searchDataCopy["name"])  0.711  10894
        #0.00006
        if searchDataCopy['id'] != triggerData['id']:
            recommended = triggerRename.coRename(searchDataCopy)
            if recommended is not None:
                if isSimilarity:
                    nextScore = nextScore + (recommended["similarity"] * SIMILARITY_TIMES)
                if nextScore <= trueRecommendScore or trueRecommend < UPPER_RANKING:
                    recommended['rank'] = nextScore
                    recommended['hop'] = hop
                    result.append(recommended)
                    trueRecommend += 1
                if isSimilarity:
                    nextScore = nextScore - (recommended["similarity"] * SIMILARITY_TIMES)
#            else:
#                nextScore += RANK_WORD_PENALTY

        #次に調べるべきidを格納 0.0007  change  14.90  6040
        #candidateIds, idCost = getRelatedIdsAndCost(searchData[_RELATION_LIST].dropna())
        candidateIds, idCost = getRelatedIdsAndCostTemp(searchData)
        candidateIds = candidateIds - triedIds
        #0.003  change
        candidateData = tableData.selectDataByIds(candidateIds)
        candidateLen = len(candidateData)
        #0.04  0.147   上0:25,  下 0:01
        for ci in range(candidateLen):
            #0.0001  change  6040
            candidate = candidateData[ci]
            distanceCost = idCost[candidate['id']] * RELATION_TIMES if isRelation else 0
            #if candidate['files'] != searchDataCopy["files"]:
            #    if nextScore + RANK_FILE_PENALTY + distanceCost <= trueRecommendScore or trueRecommend < UPPER_RANKING:
            #        heapq.heappush(nextIds, [nextScore + RANK_FILE_PENALTY + distanceCost, hop+1, candidate['id']])
            #else:
            if nextScore + distanceCost <= trueRecommendScore or trueRecommend < UPPER_RANKING:
                heapq.heappush(nextIds, [nextScore + distanceCost, hop+1, candidate['id']])


    print(f'triedID = {len(triedIds)}')
    print(f'debug: nextIDs = {len(nextIds)}')
    print(f'debug: countRecommend = {trueRecommend}')
    return result


def getRelatedIdsAndCostTemp(relationSeries):
    relatedIds = set()
    idToCost = {}
    for i, ids in relationSeries.items():
        if ids == "" or i not in _RELATION_LIST:
            continue
        idList = {id.rsplit(':', 1)[0] for id in ids.split(' - ')}
        relatedIds.update(idList)
        idToCost.update([(id, _RELATION_COST[i]) for id in idList])
    return relatedIds, idToCost


def recommend(repo, force):
    startTime = time.time()
    root = pathlib.Path(repo)
    jsonPath = os.path.join(root, 'goldset.json')
    try:
        jsonData = pd.read_json(jsonPath, orient='records')
        polishJsonData(jsonData)
    except ValueError:
        _logger.error(f'{jsonPath} does not exists')
        return
    except KeyError:
        _logger.error(f'{jsonPath} is empty')
        return

    archiveRoot = root.joinpath('archives')
    resultNone = {}
    resultSimilarity = {}
    resultRelation = {}
    resultAllNormalize = {}
    outputSimilarity = root.joinpath('recommend_similarity_ranking_random.json')
    outputRelation = root.joinpath('recommend_relation_ranking_random.json')
    outputAllNormalize = root.joinpath(f'recommend_all_normalize_random.json')
    outputOperation = root.joinpath('operations.json')

    #既に作られている場合終了
    if not force and \
        (os.path.exists(outputSimilarity) \
        or os.path.exists(outputRelation)):
        _logger.info(f'{root} already recommended')
        return

    for commit in jsonData['commit'].unique():
        repoRoot = archiveRoot.joinpath(commit)
        tablePath = os.path.join(repoRoot, 'exTable.csv.gz')
        abbrPath = repoRoot.joinpath('record.json')
        # hash = directory.name
        #exTable, record.jsonがない場合次へ
        if not os.path.isfile(tablePath) or not os.path.isfile(abbrPath):
            continue


        tableData = ExTable(tablePath)
        setAbbrDic(abbrPath)
        goldSet = jsonData[jsonData['commit'] == commit]

        # none result
        #resultNone[commit] = {}
        #resultNone[commit]['goldset'] = goldSet.to_dict(orient='records')
        # relation result
        resultSimilarity[commit] = {}
        resultSimilarity[commit]['goldset'] = goldSet.to_dict(orient='records')
        # relation 
        resultRelation[commit] = {}
        resultRelation[commit]['goldset'] = goldSet.to_dict(orient='records')

        resultAllNormalize[commit] = {}
        resultAllNormalize[commit]['goldset'] = goldSet.to_dict(orient='records')

        size = goldSet.shape[0]
        for gIdx in range(size):
            trigger = goldSet.iloc[gIdx]
            tData = tableData.selectDataByRow(trigger)
            resultAllNormalize[commit]['goldset'][gIdx]["normalized"] = (tData.to_dict())["normalized"] if tData is not None else []
            _logger.debug(f'trigger: {printDict(trigger.to_dict(), "description")}')
            commitStartTime = time.time()
            # all
            _logger.info(f'start recommend: {commit} | {gIdx}')
            #/ resultNone[commit][gIdx] = doCoRename(commit, tableData, trigger)
            # relation
            if IS_RELATION_RECOMMEND:
                resultSimilarity[commit][gIdx] = doCoRename(commit, tableData, trigger, relation=False, similarity=True, all=True)
            # relation normalize
            if IS_SIMILARITY_RECOMMEND:
                resultRelation[commit][gIdx] = doCoRename(commit, tableData, trigger, relation=True, similarity=False, all=True)
            # all normalize
            if IS_ALL_RECOMMEND:
                resultAllNormalize[commit][gIdx] = doCoRename(commit, tableData, trigger, relation=True, similarity=True, all=True)
            commitEndTime = time.time()
            _logger.info(f'end recommend: {commit} | {gIdx}')
            _logger.info(f'commit elapsed time: {timedelta(seconds=(commitEndTime - commitStartTime))}')
    # output
    _logger.info('export result')
    #with open(outputNone, 'w') as ON, \
    if IS_RELATION_RECOMMEND:
        with open(outputSimilarity, 'w') as OR:
            simplejson.dump(resultSimilarity, OR, indent=4, ignore_nan=True)
    if IS_SIMILARITY_RECOMMEND:
        with open(outputRelation, 'w') as ORN:
            simplejson.dump(resultRelation, ORN, indent=4, ignore_nan=True)
    if IS_ALL_RECOMMEND:
        with open(outputAllNormalize, 'w') as OAN:
            simplejson.dump(resultAllNormalize, OAN, indent=4, ignore_nan=True)

    with open(outputOperation, 'w') as oo:
        simplejson.dump(operationDic, oo, indent=4, ignore_nan=True)
    endTime = time.time()
    _logger.info(f'elapsed time: {timedelta(seconds=(endTime - startTime))}')


if __name__ == '__main__':
    mainArgs = setArgument()
    rootLogger = setLogger(DEBUG if mainArgs.d else INFO)

    for repo in mainArgs.source:
        recommend(repo, mainArgs.force)