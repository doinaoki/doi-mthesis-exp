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
_RELATION_LIST = [
    "subclass","subsubclass","parents","ancestor","methods","fields","siblings","comemnt","type","enclosingCLass","assignment","methodInvocated","parameterArgument","parameter","enclosingMethod","argument"
]
_IDENTIFIER_LIST = ["id","name","line","files","typeOfIdentifier","split","case","pattern","delimiter"]

IS_NORMALIZE_RECOMMEND = True
IS_RELATION_RECOMMEND = True
IS_NONE_RECOMMEND = True

def setArgument():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', help='set directory containing repositories to be analyzed', nargs='+')
    parser.add_argument('-d', help='set debug mode', action='store_true', default=False)
    parser.add_argument('-f', '--force', help='set force mode', action='store_true', default=False)
    args = parser.parse_args()
    return args


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


def doCoRename(tableData, trigger, relation=False, normalize=False):
    _logger.info(f'do co-rename relation = {relation}, normalize = {normalize}')
    triggerData = tableData.selectDataByRow(trigger)
    if triggerData is None:
        return []
    if relation:
        triggerDataDictCopy = deepcopy(triggerData.to_dict())
        triggerRename = Rename(triggerDataDictCopy, normalize=normalize)
        triggerRename.setNewName(trigger['newname'])
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


def coRenameRelation(tableData, triggerData, triggerRename):
    triedIds = {triggerData['id']}
    nextIds = getRelatedIds(triggerData[_RELATION_LIST].dropna())
    result = []
    hops = 0
    #_logger.debug(f'next ids: {nextIds}')
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
        #_logger.debug(f'next ids: {nextIds}')
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
            if IS_NONE_RECOMMEND:
                resultNone[commit][gIdx] = doCoRename(tableData, trigger)
            # relation
            if IS_RELATION_RECOMMEND:
                resultRelation[commit][gIdx] = doCoRename(tableData, trigger, relation=True)
            # relation normalize
            if IS_NORMALIZE_RECOMMEND:
                resultRelationNormalize[commit][gIdx] = doCoRename(tableData, trigger, relation=True, normalize=True)
            # 
            commitEndTime = time.time()
            _logger.info(f'end recommend: {commit} | {gIdx}')
            _logger.info(f'commit elapsed time: {timedelta(seconds=(commitEndTime - commitStartTime))}')
    # output
    _logger.info('export result')
    if IS_NONE_RECOMMEND:
        with open(outputNone, 'w') as ON:
            simplejson.dump(resultNone, ON, indent=4, ignore_nan=True)
    if IS_RELATION_RECOMMEND:
        with open(outputRelation, 'w') as OR:
            simplejson.dump(resultRelation, OR, indent=4, ignore_nan=True)
    if IS_NORMALIZE_RECOMMEND:
        with open(outputRelationNormalize, 'w') as ORN:
            simplejson.dump(resultRelationNormalize, ORN, indent=4, ignore_nan=True)

    endTime = time.time()
    _logger.info(f'elapsed time: {timedelta(seconds=(endTime - startTime))}')


if __name__ == '__main__':
    mainArgs = setArgument()
    rootLogger = setLogger(DEBUG if mainArgs.d else INFO)
    for repo in mainArgs.source:
        recommend(repo, mainArgs.force)
