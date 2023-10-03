import argparse
import re
import os
import json
import matplotlib.pyplot as plt
from matplotlib import rcParams
import pandas as pd
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG, log

rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['Hiragino Maru Gothic Pro', 'Yu Gothic', 'Meirio', 'Takao', 'IPAexGothic', 'IPAGothic', 'VL Gothic', 'Noto Sans CJK JP']
rcParams['text.usetex'] = True
logger = getLogger(__name__)
logger.setLevel(DEBUG)

def createUnitFigure(file_list):
    files = []
    rate = []
    group_df = pd.DataFrame()
    unique_df = pd.DataFrame()

    # rate
    for file in file_list:
        try:
            logger.info("(Unit) reading result " + file)
            total = pd.read_csv(os.path.join(file, "count_all.csv"), index_col="Unnamed: 0")
            solo = pd.read_csv(os.path.join(file, "count_unit_solo.csv"), index_col = "Unnamed: 0")
            group = pd.read_csv(os.path.join(file, "count_unit_group.csv")).rename(columns={"Unnamed: 0": "unitsize"})
            unique = {}
            with open(os.path.join(file, 'unit.json')) as f:
                all_units = json.load(f)
                for units in all_units.values():
                    for diff, unit in units.items():
                        total_num, u = list(unit.values())
                        unique_num = sum(len(rl) for rl in unpack(u))
                        total_unique = (total_num, unique_num)
                        if total_unique not in unique:
                            unique[total_unique] = 0
                        unique[total_unique] += 1
            unique = pd.DataFrame([(*tu, v) for tu, v in unique.items()])
            unique.columns = ['total', 'unique', 'num']

            logger.debug(f'total\n {total}')
            logger.debug(f'solo\n {solo}')
            logger.debug(f'group\n {group}')
            logger.debug(f'unique\n {unique}')
            total_sum = int(total.sum())
            solo_sum = int(solo.sum())
            r = 1 - solo_sum/total_sum
            logger.debug(f'1 - {solo_sum}/{total_sum} = {r}')
            rate.append(r)

            files.append(os.path.basename(file))
            group_df = pd.concat([group_df, group], axis=0).fillna(0)
            unique_df = pd.concat([unique_df, unique], axis=0).fillna(0)
        except Exception:
            logger.exception("fatal error occured")
    file_rate = pd.Series(rate, index=files)
    logger.debug(f'files\n {pd.Series(rate, index=files)}')

    # commit
    # exp = re.compile(r'INFO:__main__:(?P<project>.*) : .* LOC , (?P<commit>.*) commits')
    # with open('repoinfo.log', 'r') as f:
    #     files = []
    #     commits = []
    #     for line in f:
    #         match = exp.match(line)
    #         if match != None:
    #             file = match.group("project")
    #             commit = match.group("commit")
    #             files.append(os.path.basename(file))
    #             commits.append(int(commit))
    # file_commit = pd.Series(commits, index=files)
    # rate_commit = pd.concat([file_rate, file_commit], axis=1)
    # rate_commit.columns = ['rate', 'commit']
    # # fabric8 workflow-plugin は何故か repo の中身が空なので手動入力
    # rate_commit.at['fabric8', 'commit'] = 13497
    # rate_commit.at['workflow-plugin', 'commit'] = 3007
    # logger.debug(f'rate_commit\n{rate_commit}')
    # logger.debug(f'{rate_commit[rate_commit.isnull().any(axis=1)]}')

    logger.info(f'total {len(rate)} repositories')

    fig_co = rq1CoRename(rate)
    # fig_scat = rq1RenameCommit(rate_commit)
    fig_group = rq1UnitSize(group_df)
    fig_unique = rq1UnitUniqueSize(group_df, unique_df)
    return fig_co, fig_group, fig_unique, # fig_scat

def unpack(dictionary):
    for k,v in dictionary.items():
        if isinstance(v, dict):
            yield from unpack(v)
        else:
            yield v

def rq1CoRename(rate):
    # RQ1 co
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    ax.boxplot(rate, showmeans=True, meanline=True)
    # ax1.violinplot(rate, showmeans=True, showmedians=True) のほうがいいかもしれない
    ax.set_ylabel('Rate', fontsize=20)
    ax.set_ylim([0, 1])
    ax.set_xticks([])
    ax.tick_params('y', labelsize=14)
    logger.info(f'co_rename_statistics\n{pd.Series(rate).describe()}')
    return fig

def rq1RenameCommit(rate_commit):
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    logger.debug(f'rate\n{list(rate_commit["rate"])}')
    logger.debug(f'commit\n{list(rate_commit["commit"])}')

    ax.scatter(list(rate_commit['commit']), list(rate_commit['rate']))
    ax.set_xlabel('Commit', fontsize=20)
    ax.set_ylabel('Rate', fontsize=20)
    # ax.set_ylim([0, 1])
    ax.tick_params('x', labelsize=14)
    ax.tick_params('y', labelsize=14)
    return fig

def rq1UnitSize(group_df):
    max_plot_size = 20
    group_df = group_df.groupby('unitsize', as_index=False).sum()
    x_ticks = group_df["unitsize"]
    y_ticks = group_df.drop(columns="unitsize").sum(axis=1).mul(x_ticks, axis=0)
    y_ticks = y_ticks.cumsum()/y_ticks.sum()
    x_ticks = x_ticks[:max_plot_size-1]
    y_ticks = y_ticks[:max_plot_size-1]
    logger.debug(f'group rate\n {y_ticks}')

    fig = plt.figure(figsize=(8,4))
    ax = fig.add_subplot(1,1,1)
    ax.bar(x_ticks, y_ticks)
    ax.set_xlabel('Number of Meaningful Rename Sets', fontsize=20)
    ax.set_ylabel('Rate', fontsize=20)
    ax.set_xticks(x_ticks)
    ax.set_ylim([0, 0.8])
    ax.tick_params('x', labelsize=14, labelrotation=90)
    ax.tick_params('y', labelsize=15)
    return fig


def rq1UnitUniqueSize(group_df, unique_df):
    max_plot_size = 20
    group_df = group_df.groupby('unitsize').sum()
    index = group_df.index
    # unit内の全reaname数'total'の和
    group_sum = group_df.sum(axis=1).mul(index, axis=0).sum()
    # unit内の全reaname数'total'の累積分布
    # rename数の累積和を取るため.mul(index, axis=0)が必要
    unique_all = group_df.sum(axis=1).mul(index, axis=0).cumsum() / group_sum

    # 累積分布
    # unique_df[unique_df['unique']==1].groupby('total').sum()['num'] -> unit内の全rename数'total'のうちユニークな識別子の数が'unique'個のunitがいくつあるか
    # .reindex(index).fillna(0).mul(index, axis=0).cumsum() -> index を'unique_all'に揃えて値がないところは0埋めして累積和を取る
    unique_1 = unique_df[unique_df['unique']==1].groupby('total').sum()['num'].reindex(index).fillna(0).mul(index, axis=0).cumsum() / group_sum
    unique_2 = unique_df[unique_df['unique']==2].groupby('total').sum()['num'].reindex(index).fillna(0).mul(index, axis=0).cumsum() / group_sum
    unique_3 = unique_df[unique_df['unique']==3].groupby('total').sum()['num'].reindex(index).fillna(0).mul(index, axis=0).cumsum() / group_sum
    unique_4 = unique_df[unique_df['unique']==4].groupby('total').sum()['num'].reindex(index).fillna(0).mul(index, axis=0).cumsum() / group_sum
    unique_5 = unique_df[unique_df['unique']==5].groupby('total').sum()['num'].reindex(index).fillna(0).mul(index, axis=0).cumsum() / group_sum
    unique_6 = unique_df[unique_df['unique']>=6].groupby('total').sum()['num'].reindex(index).fillna(0).mul(index, axis=0).cumsum() / group_sum

    logger.debug(f'unique all\n {dict(unique_all)}')
    logger.debug(f'unique\n {unique_1 + unique_2 + unique_3 + unique_4 + unique_5 + unique_6}')

    x_ticks = index[:max_plot_size-1]
    y1 = unique_1[:max_plot_size-1]
    y2 = unique_2[:max_plot_size-1]
    y3 = unique_3[:max_plot_size-1]
    y4 = unique_4[:max_plot_size-1]
    y5 = unique_5[:max_plot_size-1]
    y6 = unique_6[:max_plot_size-1]
    fig = plt.figure(figsize=(8,4))
    ax = fig.add_subplot(1,1,1)
    ax.bar(x_ticks, y1)
    bottom = y1
    ax.bar(x_ticks, y2, bottom=bottom)
    bottom += y2
    ax.bar(x_ticks, y3, bottom=bottom)
    bottom += y3
    ax.bar(x_ticks, y4, bottom=bottom)
    bottom += y4
    ax.bar(x_ticks, y5, bottom=bottom)
    bottom += y5
    ax.bar(x_ticks, y6, bottom=bottom)
    
    ax.set_xlabel('Number of Elements in Meaningful Rename Sets', fontsize=20)
    ax.set_ylabel('Rate', fontsize=20)
    ax.set_xticks(x_ticks)
    ax.tick_params('x', labelsize=14, labelrotation=90)
    ax.tick_params('y', labelsize=15)
    ax.set_ylim([0, 0.8])
    fig.legend(['1', '2', '3', '4', '5', '6~'], bbox_to_anchor=(1.06,0.9), borderaxespad=0, fontsize=18)
    return fig

def save(fig, path):
    fig.savefig(path, bbox_inches='tight')
    logger.info(f'save {path}')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', action='store_true', help="set debug mode")
    main_args = parser.parse_args()

    root_logger = getLogger()
    handler = StreamHandler()
    handler.setLevel(DEBUG if main_args.d else INFO)
    formatter = Formatter('[%(asctime)s] %(name)s -- %(levelname)s : %(message)s')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(INFO)

    output = os.path.join("output", "v2")
    normal = os.path.join(output, "normal")
    # lemmatized = os.path.join("lemmatized")
    project_list = [os.path.join(normal, d) for d in os.listdir(normal)]
    total = len(project_list)
    logger.info(f'analyze {total} repositories')
    fig_co, fig_group, fig_unique = createUnitFigure(project_list)

    # save fig
    output_dir = os.path.join("output", "fig")
    os.makedirs(output_dir, exist_ok=True)

    save(fig_co, os.path.join(output_dir, "RQ1_co_rename.pdf"))
    plt.close(fig_co)

    save(fig_group, os.path.join(output_dir, "RQ1_unit_rate.pdf"))
    plt.close(fig_group)

    save(fig_unique, os.path.join(output_dir, "RQ1_unit_size_unique.pdf"))
    plt.close(fig_unique)

    # save(fig_scat, os.path.join(output_dir, "RQ1_rate_commit.pdf"))
    # plt.close(fig_scat)