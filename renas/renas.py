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
    "subclass","subsubclass","parents","ancestor","methods","fields","siblings","comemnt","type","enclosingCLass","assignment","methodInvocated","parameterArgument","parameter","enclosingMethod","argument"
]
_IDENTIFIER_LIST = ["id","name","line","files","typeOfIdentifier","split","case","pattern","delimiter"]

RANK = 14
RANK_DISTANSE_PENALTY = 1
RANK_WORD_PENALTY = 5
RANK_FILE_PENALTY = 1
UPPER = 20
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
        relatedIds.update(id.split(':')[0] for id in ids.split(' - '))
    return relatedIds

def recordOperation(commit, op,normalize, all, exception={}):
    opType = ""
    if all:
        opType = "all"
    elif normalize:
        opType = "Normalize"
    else:
        opType = "None"
    if len(exception) != 0:
        key = exception["commit"]+exception["files"]+str(exception["line"])+exception["oldname"]
        if commit not in operationDic[opType]:
            operationDic[opType][commit] = {}
        operationDic[opType][commit][key] = []
        return
    if commit not in operationDic[opType]:
        operationDic[opType][commit] = {}
    operationDic[opType][commit][commit+op[0]] = op[1]

# トリガーとなるRenameを設定.(operational chunkの抽出)
def doCoRename(commit, tableData, trigger, relation=False, normalize=False, all=False):
    _logger.info(f'do co-rename relation = {relation}, normalize = {normalize}')
    triggerData = tableData.selectDataByRow(trigger)
    if triggerData is None:
        recordOperation(commit, [], normalize, all, exception=trigger)
        return []
    if relation:
        triggerDataDictCopy = deepcopy(triggerData.to_dict())
        triggerRename = Rename(triggerDataDictCopy, normalize=normalize, all=all)
        triggerRename.setNewName(trigger['newname'])
        recordOperation(commit, triggerRename.getOp(), normalize, all)
        return coRenameRelation(tableData, triggerData, triggerRename)
    else:
        triggerDataDictCopy = deepcopy(triggerData[_IDENTIFIER_LIST].to_dict())
        triggerRename = Rename(triggerDataDictCopy, normalize=normalize)
        triggerRename.setNewName(trigger['newname'])
        return coRenameNone(tableData, triggerRename)


def coRenameNone(tableData, triggerRename):
    tableDict = tableData.selectDataByColumns(_IDENTIFIER_LIST).to_dict(orient='records')
    recommends = [triggerRename.coRename(deepcopy(d)) for d in tableDict]
    result = [r for r in recommends if r is not None]
    return result

'''
# 他のRenameも推薦できるか見る
def coRenameRelation(tableData, triggerData, triggerRename):
    triedIds = {triggerData['id']}
    nextIds = getRelatedIds(triggerData[_RELATION_LIST].dropna())
    result = []
    hops = 0
    _logger.debug(f'next ids: {nextIds}')
    while len(nextIds) > 0:
        triedIds.update(nextIds)
        hops += 1
        _logger.debug(f'{hops} hop distance')
        relatedData = tableData.selectDataByIds(nextIds)
        _logger.debug(f'candidate Ids: {relatedData["id"].to_list()}')
        relatedDataLen = len(relatedData)
        for rIdx in range(relatedDataLen):
            candidate = relatedData.iloc[rIdx]
            candidateCopy = deepcopy(candidate.to_dict())
            recommended = triggerRename.coRename(candidateCopy)
            if recommended is not None:
                _logger.debug(f'{candidate["name"]} should be renamed to {recommended["join"]}')
                recommended['hop'] = hops
                result.append(recommended)
                nextIds.update(getRelatedIds(candidate[_RELATION_LIST].dropna()))
        nextIds = nextIds - triedIds
        _logger.debug(f'next ids: {nextIds}')
    return result
'''

'''
def coRenameRelation(tableData, triggerData, triggerRename):
    triedIds = {triggerData['id']}
    nextIds = getRelatedIds(triggerData[_RELATION_LIST].dropna())
    idsToRank = {id : [0, triggerData["files"]] for id in nextIds}
    result = []
    hops = 0
    _logger.debug(f'next ids: {nextIds}')
    while len(nextIds) > 0:
        triedIds.update(nextIds)
        hops += 1
        _logger.debug(f'{hops} hop distance')
        relatedData = tableData.selectDataByIds(nextIds)
        _logger.debug(f'candidate Ids: {relatedData["id"].to_list()}')
        relatedDataLen = len(relatedData)
        for rIdx in range(relatedDataLen):
            candidate = relatedData.iloc[rIdx]
            candidateCopy = deepcopy(candidate.to_dict())
            candidateRank = idsToRank[candidate["id"]][0]
            previewFile = idsToRank[candidate["id"]][1]
            recommended = triggerRename.coRename(candidateCopy)
            if recommended is not None:
                _logger.debug(f'{candidate["name"]} should be renamed to {recommended["join"]}')
                newRank = candidateRank + RANK_DISTANSE_PENALTY
                if previewFile != candidate["files"]:
                    newRank += RANK_FILE_PENALTY
                if newRank > RANK:
                    continue
                recommended['hop'] = hops
                recommended['rank'] = newRank
                newIds = getRelatedIds(candidate[_RELATION_LIST].dropna())
                result.append(recommended)
                idsToRank.update({id: [newRank, candidate["files"]] for id in newIds})
                nextIds.update(newIds)
            else:
                newIds = getRelatedIds(candidate[_RELATION_LIST].dropna())
                newRank = candidateRank + RANK_DISTANSE_PENALTY + RANK_WORD_PENALTY
                if previewFile != candidate["files"]:
                    newRank += RANK_FILE_PENALTY
                if newRank > RANK:
                    continue
                idsToRank.update({id: [newRank, candidate["files"]] for id in newIds})
                nextIds.update(newIds)

        nextIds = nextIds - triedIds
        _logger.debug(f'next ids: {nextIds}')
    return result
'''

def coRenameRelation(tableData, triggerData, triggerRename):
    triedIds = {triggerData.to_dict()['id']}
    triggerScore = 0
    nextIds = []
    heapq.heappush(nextIds, [triggerScore, triggerData["id"]])  
    result = []
    _logger.debug(f'next ids: {nextIds}')
    trueRecommend = 0
    while len(nextIds) > 0 and UPPER > trueRecommend:
        #調べるidを取得する
        score ,searchId = heapq.heappop(nextIds)
        searchData = tableData.selectDataById(searchId)
        #print(score, searchId)
        triedIds.add(searchId)

        #推薦実施
        searchDataCopy = deepcopy(searchData.to_dict())
        #print(searchDataCopy["name"])
        nextScore = score + RANK_DISTANSE_PENALTY
        if searchDataCopy['id'] != triggerData['id']:
            recommended = triggerRename.coRename(searchDataCopy)
            if recommended is not None:
                recommended['rank'] = score
                result.append(recommended)
                trueRecommend += 1
            else:
                nextScore += RANK_WORD_PENALTY

        #次に調べるべきidを格納
        candidateIds = getRelatedIds(searchData[_RELATION_LIST].dropna())
        candidateData = tableData.selectDataByIds(candidateIds)
        candidateLen = len(candidateData)
        for ci in range(candidateLen):
            candidate = candidateData.iloc[ci].to_dict()
            if candidate["id"] in triedIds:
                continue
            if candidate["files"] != searchDataCopy["files"]:
                if nextScore + RANK_FILE_PENALTY < RANK:
                    heapq.heappush(nextIds, [nextScore + RANK_FILE_PENALTY, candidate["id"]])
            else:
                if nextScore < RANK:
                    heapq.heappush(nextIds, [nextScore, candidate["id"]])
        _logger.debug(f'next ids: {nextIds}')
    return result


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
    resultRelation = {}
    resultRelationNormalize = {}
    resultAllNormalize = {}
    outputNone = root.joinpath('recommend_none.json')
    outputRelation = root.joinpath('recommend_relation.json')
    outputRelationNormalize = root.joinpath('recommend_relation_normalize.json')
    outputAllNormalize = root.joinpath('recommend_all_normalize.json')
    outputOperation = root.joinpath('operations.json')

    #既に作られている場合終了
    if not force and \
        (os.path.exists(outputNone) \
        or os.path.exists(outputRelation) \
        or os.path.exists(outputRelationNormalize)):
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
        resultNone[commit] = {}
        resultNone[commit]['goldset'] = goldSet.to_dict(orient='records')
        # relation result
        resultRelation[commit] = {}
        resultRelation[commit]['goldset'] = goldSet.to_dict(orient='records')
        # relation 
        resultRelationNormalize[commit] = {}
        resultRelationNormalize[commit]['goldset'] = goldSet.to_dict(orient='records')

        resultAllNormalize[commit] = {}
        resultAllNormalize[commit]['goldset'] = goldSet.to_dict(orient='record')

        size = goldSet.shape[0]
        for gIdx in range(size):
            trigger = goldSet.iloc[gIdx]
            _logger.debug(f'trigger: {printDict(trigger.to_dict(), "description")}')
            commitStartTime = time.time()
            # all
            _logger.info(f'start recommend: {commit} | {gIdx}')
            #resultNone[commit][gIdx] = doCoRename(commit, tableData, trigger)
            # relation
            resultRelation[commit][gIdx] = doCoRename(commit, tableData, trigger, relation=True)
            # relation normalize
            resultRelationNormalize[commit][gIdx] = doCoRename(commit, tableData, trigger, relation=True, normalize=True)
            # all normalize
            resultAllNormalize[commit][gIdx] = doCoRename(commit, tableData, trigger, relation=True, normalize=True, all=True)
            commitEndTime = time.time()
            _logger.info(f'end recommend: {commit} | {gIdx}')
            _logger.info(f'commit elapsed time: {timedelta(seconds=(commitEndTime - commitStartTime))}')
    # output
    _logger.info('export result')
    #with open(outputNone, 'w') as ON, \
    with open(outputRelation, 'w') as OR, \
            open(outputRelationNormalize, 'w') as ORN, \
            open(outputAllNormalize, 'w') as OAN:
        #simplejson.dump(resultNone, ON, indent=4, ignore_nan=True)
        simplejson.dump(resultRelation, OR, indent=4, ignore_nan=True)
        simplejson.dump(resultRelationNormalize, ORN, indent=4, ignore_nan=True)
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
