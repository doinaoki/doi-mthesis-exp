import pathlib
import simplejson
import os
import argparse
import time
from datetime import timedelta

import pandas as pd
from .util.Rename import Rename, setAbbrDic
from .util.ExTable import ExTable
from .util.common import printDict, convertRenameType
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG, log, basicConfig
from copy import deepcopy

_logger = getLogger(__name__)
_logger.setLevel(DEBUG)
operationDic = {"Relation-Normalize": {}, "Relation": {}}
_RELATION_LIST = [
    "subclass","subsubclass","parents","ancestor","methods","fields","siblings","comemnt","type","enclosingCLass","assignment","methodInvocated","parameterArgument","parameter","enclosingMethod","argument"
]
_IDENTIFIER_LIST = ["id","name","line","files","typeOfIdentifier","split","case","pattern","delimiter"]

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

def recordOperation(commit, op):
    if op == []:
        if commit not in operationDic["Relation-Normalize"]:
            operationDic["Relation-Normalize"][commit] = {}
        return
    if commit not in operationDic[op[0]]:
        operationDic[op[0]][commit] = {}
    operationDic[op[0]][commit][commit+op[1]] = op[2]

# トリガーとなるRenameを設定.(operational chunkの抽出)
def doCoRename(commit, tableData, trigger, relation=False, normalize=False):
    _logger.info(f'do co-rename relation = {relation}, normalize = {normalize}')
    triggerData = tableData.selectDataByRow(trigger)
    if triggerData is None:
        recordOperation(commit, [])
        return []
    if relation:
        triggerDataDictCopy = deepcopy(triggerData.to_dict())
        triggerRename = Rename(triggerDataDictCopy, normalize=normalize)
        triggerRename.setNewName(trigger['newname'])
        recordOperation(commit, triggerRename.getOp())
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
    outputNone = root.joinpath('recommend_none.json')
    outputRelation = root.joinpath('recommend_relation.json')
    outputRelationNormalize = root.joinpath('recommend_relation_normalize.json')
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

        size = goldSet.shape[0]
        for gIdx in range(size):
            trigger = goldSet.iloc[gIdx]
            _logger.debug(f'trigger: {printDict(trigger.to_dict(), "description")}')
            commitStartTime = time.time()
            # all
            _logger.info(f'start recommend: {commit} | {gIdx}')
            resultNone[commit][gIdx] = doCoRename(commit, tableData, trigger)
            # relation
            resultRelation[commit][gIdx] = doCoRename(commit, tableData, trigger, relation=True)
            # relation normalize
            resultRelationNormalize[commit][gIdx] = doCoRename(commit, tableData, trigger, relation=True, normalize=True)
            # 
            commitEndTime = time.time()
            _logger.info(f'end recommend: {commit} | {gIdx}')
            _logger.info(f'commit elapsed time: {timedelta(seconds=(commitEndTime - commitStartTime))}')
    # output
    _logger.info('export result')
    with open(outputNone, 'w') as ON, \
            open(outputRelation, 'w') as OR, \
            open(outputRelationNormalize, 'w') as ORN:
        simplejson.dump(resultNone, ON, indent=4, ignore_nan=True)
        simplejson.dump(resultRelation, OR, indent=4, ignore_nan=True)
        simplejson.dump(resultRelationNormalize, ORN, indent=4, ignore_nan=True)

    with open(outputOperation, 'w') as oo:
        simplejson.dump(operationDic, oo, indent=4, ignore_nan=True)
    endTime = time.time()
    _logger.info(f'elapsed time: {timedelta(seconds=(endTime - startTime))}')


if __name__ == '__main__':
    mainArgs = setArgument()
    rootLogger = setLogger(DEBUG if mainArgs.d else INFO)
    for repo in mainArgs.source:
        recommend(repo, mainArgs.force)
