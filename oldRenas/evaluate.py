import pathlib
import numpy as np
import os
import simplejson
import argparse
from multiprocessing import Pool

import pandas as pd
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG, log, basicConfig

FSCORE_INDEX = 2
RESULT_COLUMNS = [
    'commit',
    'renames',
    'description',
    'none_precision',
    'none_recall',
    'none_fscore',
    'none_exact',
    'relation_precision',
    'relation_recall',
    'relation_fscore',
    'relation_exact',
    'relation_normalize_precision',
    'relation_normalize_recall',
    'relation_normalize_fscore',
    'relation_normalize_exact',
    ]
_logger = getLogger(__name__)
_logger.setLevel(DEBUG)

def setArgument():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', help='set directory containing repositories to be analyzed', nargs='+')
    parser.add_argument('-d', help='set debug mode', action='store_true', default=False)
    args = parser.parse_args()
    return args


def setLogger(level):
    root_logger = getLogger()
    root_logger.setLevel(level)
    handler = StreamHandler()
    handler.setLevel(level)
    formatter = Formatter('[%(asctime)s] %(name)s __ %(levelname)s : %(message)s')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    return root_logger


def loadJsons(root):
    nonePath = root.joinpath('recommend_none.json')
    relationPath = root.joinpath('recommend_relation.json')
    relationNormalizePath = root.joinpath('recommend_relation_normalize.json')
    if not os.path.exists(nonePath) \
        or not os.path.exists(relationPath) \
        or not os.path.exists(relationNormalizePath):
        _logger.error(f'{root} recommend results do not exist. Run recommendation.py first.')
        return None, None, None
    return _loadJson(nonePath), _loadJson(relationPath), _loadJson(relationNormalizePath)

def _loadJson(jsonPath):
    with open(jsonPath, 'r') as f:
        data = simplejson.load(f)
    return data

def evaluate(root):
    _logger.info(f'{root} start evaluation')
    noneJson, relationJson, relationNormalizeJson = loadJsons(root)
    if noneJson is None:
        return None
    commits = noneJson.keys()
    results = []
    for c in commits:
        goldSet = pd.DataFrame.from_records(noneJson[c]['goldset'])
        description = generateDescription(goldSet) 
        goldSetSize = goldSet.shape[0]
        noneResult = evaluateCommit(goldSet, noneJson[c])
        relationResult = evaluateCommit(goldSet, relationJson[c])
        relationNormalizeResult = evaluateCommit(goldSet, relationNormalizeJson[c])
        _logger.info(f'commit {c}, goldsetsize {goldSetSize}')
        _logger.debug(f'description:\n {description}')
        _logger.info(f'pre, rec, exa: {noneResult} (none)')
        _logger.info(f'pre, rec, exa: {relationResult} (relation)')
        _logger.info(f'pre, rec, exa: {relationNormalizeResult} (relation normalize)')
        # filter zero
        # if noneResult[FSCORE_INDEX] == 0 and \
        #     relationResult[FSCORE_INDEX] == 0 and \
        #     relationNormalizeResult[FSCORE_INDEX] == 0:
        #     _logger.info(f'none of three can recommend, skip this commit')
        #     continue
        results.append((c, goldSetSize, description, *noneResult, *relationResult, *relationNormalizeResult))
    return pd.DataFrame.from_records(results, columns=RESULT_COLUMNS)


def evaluateCommit(goldSet, commitRecommendData):
    goldSetSize = goldSet.shape[0]
    positiveCount = goldSetSize - 1
    precisions = []
    recalls = []
    fscores = []
    exacts = []
    for i in range(goldSetSize):
        recommend = pd.DataFrame.from_records(commitRecommendData[str(i)])
        recommendCount = recommend.shape[0]
        if recommend.empty:
            _logger.debug(f'no rename recommended')
            precisions.append(np.nan)
            recalls.append(0)
            fscores.append(np.nan)
            exacts.append(np.nan)
        else:
            idMatchIndexes = getIdentifierMatch(goldSet, recommend)
            idMatchCount = len(idMatchIndexes)
            exactMatch = getExactMatch(goldSet, recommend, idMatchIndexes)
            exactMatchCount = len(exactMatch)
            precision = idMatchCount / recommendCount
            recall = idMatchCount / positiveCount
            fscore = calcFScore(precision, recall)
            exact = exactMatchCount / idMatchCount if idMatchCount > 0 else np.nan
            precisions.append(precision)
            recalls.append(recall)
            fscores.append(fscore)
            exacts.append(exact)

            _logger.debug(f'precision (idMatch / recommend): {idMatchCount}/{recommendCount} = {precision}')
            _logger.debug(f'recall (idMatch / positive): {idMatchCount}/{positiveCount} = {recall}')
            _logger.debug(f'exact (exMatch / idMatch): {exactMatchCount}/{idMatchCount} = {exact}')
        avgPrecision = np.nanmean(precisions)
        avgRecall = np.nanmean(recalls)
        avgFScore = np.nanmean(fscores)
        avgExact = np.nanmean(exacts)
    return avgPrecision, avgRecall, avgFScore, avgExact


def generateDescription(goldSet):
    return ", ".join(f'{old} -> {new}' for old, new in zip(goldSet['oldname'], goldSet['newname']))


def getIdentifierMatch(goldSet, recommend):
    goldSetTuples = goldSet[["line", "typeOfIdentifier", "oldname", "files"]].to_records(index=False).tolist()
    recommendTuples = recommend[["line", "typeOfIdentifier", "name", "files"]].to_records(index=False).tolist()

    truePositiveTuples = list(set(goldSetTuples) & set(recommendTuples))
    truePositiveIndexes = [(goldSetTuples.index(t), recommendTuples.index(t)) for t in truePositiveTuples]

    _logger.debug(f'goldset: {goldSetTuples}')
    _logger.debug(f'recommend: {recommendTuples}')
    _logger.debug(f'true positive: {truePositiveTuples}')
    _logger.debug(f'indexes: {truePositiveIndexes}')
    return truePositiveIndexes


def getExactMatch(goldSet, recommend, indexes):
    result = []
    for idx in indexes:
        trueNewName = goldSet.iloc[idx[0]]['newname']
        recommendNewName = recommend.iloc[idx[1]]['join']
        _logger.debug(f'true name [{trueNewName}], recommended name [{recommendNewName}]')
        if trueNewName == recommendNewName:
            result.append(idx)
    _logger.debug(f'exact matches: {result}')
    return result


def calcFScore(precision, recall):
    if precision == 0 or recall == 0:
        return 0
    else:
        return 2 * precision * recall / (precision + recall)

if __name__ == '__main__':
    mainArgs = setArgument()
    setLogger(DEBUG if mainArgs.d else INFO)
    _logger.debug(mainArgs.source)
    for root in mainArgs.source:
        rootPath = pathlib.Path(root)
        result = evaluate(rootPath)
        _logger.debug(f'result\n {result}')
        if result is not None:
            result.to_csv(rootPath.joinpath('result.csv'), index=False)




