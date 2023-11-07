import pathlib
import os
import simplejson
import numpy as np
import argparse
from multiprocessing import Pool

import pandas as pd
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG, log, basicConfig
from .evaluate import RESULT_COLUMNS, calcFScore
from matplotlib import pyplot as plt
from matplotlib import patches as mpatches
import japanize_matplotlib

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


def filterZero(merged):
    return merged.query('none_fscore > 0 or relation_fscore > 0 or relation_normalize_fscore > 0')


def calcTotal(merged, name):
    totalNone = np.nanmean(merged[f'none_{name}'])
    totalRelation = np.nanmean(merged[f'relation_{name}'])
    totalRelationNormalize = np.nanmean(merged[f'relation_normalize_{name}'])
    _logger.info(f'{name}:\n none {totalNone}, relation {totalRelation}, relation normalize {totalRelationNormalize}')
    return totalNone, totalRelation, totalRelationNormalize


def countNan(merged, name):
    fscores = merged[f'{name}_fscore']
    _logger.debug(merged)
    totalNan = sum(np.isnan(fscores))
    _logger.debug(f'{np.isnan(fscores)}')
    _logger.info(f'{name}: {totalNan} nans')
    return totalNan


def plotResult(merged, output):
    none = merged[['none_precision', 'none_recall', 'none_fscore', 'none_exact']]
    rel = merged[['relation_precision', 'relation_recall', 'relation_fscore', 'relation_exact']]
    nor = merged[['relation_normalize_precision', 'relation_normalize_recall', 'relation_normalize_fscore', 'relation_normalize_exact']]
    # position
    rel_x = np.array([1, 2.5, 4, 5.5])
    none_x = rel_x - 0.3
    nor_x = rel_x + 0.3
    # plot
    fig = plt.figure(figsize=[8, 4.5])
    ax = fig.add_subplot(1, 1, 1)
    vp1, color1 = violinplot(ax, [none[col].dropna() for col in none], none_x)
    vp2, color2 = violinplot(ax, [rel[col].dropna() for col in rel], rel_x)
    vp3, color3 = violinplot(ax, [nor[col].dropna() for col in nor], nor_x)
    # bp = ax.boxplot(none, showmeans=True, patch_artist=True, widths=0.3)
    ax.set_xticks(rel_x)
    ax.set_xticklabels(['適合率', '再現率', 'F値', '一致率'])
    ax.set_xlabel('評価指標', fontsize=16)
    # ax.set_ylabel('割合', fontsize=16)
    ax.tick_params('x', labelsize=14)
    ax.tick_params('y', labelsize=14)
    # plot = merged.boxplot()
    labels = [
        (mpatches.Patch(color=color1), 'None'),
        (mpatches.Patch(color=color2), 'Relation'),
        (mpatches.Patch(color=color3), 'RENAS'),
        ]
    fig.legend(*zip(*labels), fontsize=16, bbox_to_anchor=(1.12, 0.88), borderaxespad=0)
    plt.savefig(output, bbox_inches='tight')
    plt.close('all')

def violinplot(ax, datas, position):
    vp = ax.violinplot(datas, position, showmedians=True, showextrema=True, widths=0.3,
    quantiles=[[0.75, 0.25] for _ in range(4)]
    )
    vp['cmaxes'].set_linewidth(0)
    vp['cmins'].set_linewidth(0)
    # line length
    factor = np.array([2, 1])
    lines = vp['cmedians'].get_segments()
    vp['cmedians'].set_segments([(l-l.mean(axis=0))*factor+l.mean(axis=0) for l in lines])
    # vp['cmins'].set_linelength(0.5)
    return vp, vp['bodies'][0].get_facecolor().flatten()

if __name__ == '__main__':
    mainArgs = setArgument()
    setLogger(DEBUG if mainArgs.d else INFO)
    _logger.debug(mainArgs.source)

    merged = pd.DataFrame()
    for root in mainArgs.source:
        rootPath = pathlib.Path(root)
        csvPath = rootPath.joinpath('result.csv')
        try:
            result = pd.read_csv(csvPath)
            result['repository'] = rootPath.name
            if result.empty:
                _logger.warning(f'empty result {rootPath.name}')
                continue
            countNan(result, 'relation')
            countNan(result, 'relation_normalize')
            _logger.debug(f'result\n {result}')
        except FileNotFoundError:
            _logger.info(f'{csvPath} does not exist')
            continue
        merged = merged.append(result)
    merged.to_csv('result_all.csv', index=False)
    _logger.info(f'filter-before {merged.shape[0]}')
    filter_merged = filterZero(merged)
    _logger.info(f'filter-after\n {filter_merged.shape[0]}')
    _logger.info(f'merged\n {merged}')

    nPre, rPre, rnPre = calcTotal(filter_merged, 'precision')
    nRec, rRec, rnRec = calcTotal(filter_merged, 'recall')
    calcTotal(filter_merged, 'fscore')
    calcTotal(filter_merged, 'exact')
    countNan(filter_merged, 'none')
    countNan(filter_merged, 'relation')
    countNan(filter_merged, 'relation_normalize')
    # figure
    figOut = pathlib.Path('fig')
    os.makedirs('fig', exist_ok=True)
    plotResult(filter_merged, figOut.joinpath('result_all.pdf'))
    
    # _logger.info(f'none F1-score: {calcFScore(nPre, nRec)}')
    # _logger.info(f'rel F1-score: {calcFScore(rPre, rRec)}')
    # _logger.info(f'nor F1-score: {calcFScore(rnPre, rnRec)}')

    _logger.info(filter_merged.median())
