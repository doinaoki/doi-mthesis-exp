import argparse
import os
import re
import json
import matplotlib.pyplot as plt
from matplotlib import rcParams
import pandas as pd
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG

from pandas.core.arrays import base

rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['Hiragino Maru Gothic Pro', 'Yu Gothic', 'Meirio', 'Takao', 'IPAexGothic', 'IPAGothic', 'VL Gothic', 'Noto Sans CJK JP']
rcParams['text.usetex'] = True
logger = getLogger(__name__)
logger.setLevel(DEBUG)
latexLabel = {
    "BelongsC": r'$\textsc{Belongs}_C$',
    "BelongsM": r'$\textsc{Belongs}_M$',
    "BelongsF": r'$\textsc{Belongs}_F$',
    "BelongsA": r'$\textsc{Belongs}_A$',
    "BelongsL": r'$\textsc{Belongs}_L$',
    "CoOccursM": r'$\textsc{Co-occurs}_M$',
    "Extends": r'$\textsc{Extends}$',
    "Implements": r'$\textsc{Implements}$',
    "TypeM": r'$\textsc{Type}_M$',
    "TypeV": r'$\textsc{Type}_V$',
    "Invokes": r'$\textsc{Invokes}$',
    "Accesses": r'$\textsc{Accesses}$',
    "Assigns": r'$\textsc{Assigns}$',
    "Passes": r'$\textsc{Passes}$'
}

def createRelationFigure(file_list):
    id_exp = re.compile(r'(?<=/)[0-9a-f]+(?=/)')
    all_count = pd.DataFrame()
    type_count = {t: pd.DataFrame() for t in ['Class', 'Method', 'Attribute', 'Parameter', 'Variable']}

    for file in file_list:
        try:
            logger.info("(Relation) reading result " + file)
            with open(os.path.join(file, 'relation_count.json')) as f:
                count = json.load(f)
                count = pd.Series(count, name=file)
                logger.debug(count)
                logger.debug(f'{count.sum()} relations found')

                all_count = pd.concat([all_count, count], axis=1)
            logger.debug(f'all_relation\n{count}')
            with open(os.path.join(file, 'relation_count_type.json')) as f:
                counts = json.load(f)
                for t, count in counts.items():
                    count = pd.Series(count, name=file)
                    type_count[t] = pd.concat([type_count[t], count], axis=1)
        except Exception:
            logger.exception("fatal error occured")
    logger.debug(f'total count\n{all_count}')
    logger.debug(f'sum\n {all_count.sum().sort_values()}')
    # 足切り
    all_count.drop(index=[])
    repositories = all_count.columns

    # unit数
    unit_num = 0
    for repo in repositories:
        with open(os.path.join(repo, 'unit.json')) as f:
            all_units = json.load(f)
            num = 0
            for units in all_units.values():
                num += len([unit for unit in units.values() if unit['all_size'] > 1])
            # num = sum(len(units) for units in all_units.values() if len(units) > 1)
            logger.debug(f'{repo} {num} units')
            unit_num += num

    logger.debug(f'rate\n {all_count / all_count.sum()}')
    logger.info(f'end reading result\n')
    logger.info(f'total {len(all_count.columns)} repositories, {unit_num} units, {all_count.sum().sum()} relationships\n')

    # all
    fig_all, bp_all = createFigure(all_count, 24, 20)
    toLatexLabel(fig_all)
    coloring(fig_all, bp_all)

    # class
    fig_class, bp_class = createFigure(type_count['Class'], 38, 38)
    toLatexLabel(fig_class)
    coloring(fig_class, bp_class, 'BelongsC', 'BelongsM', 'BelongsF', 'TypeV', 'TypeM', 'Extends', 'Implements')

    # method
    fig_method, bp_method = createFigure(type_count['Method'], 38, 38)
    toLatexLabel(fig_method)
    coloring(fig_method, bp_method, 'BelongsM', 'BelongsA', 'CoOccursM', 'TypeM', 'Invokes', 'Accesses', 'Assigns', 'Passes')

    # attribute
    fig_attribute, bp_attribute = createFigure(type_count['Attribute'], 38, 38)
    toLatexLabel(fig_attribute)
    coloring(fig_attribute, bp_attribute, 'BelongsF', 'TypeV', 'Accesses', 'Assigns', 'Passes')

    # parameter
    fig_parameter, bp_parameter = createFigure(type_count['Parameter'], 38, 38)
    toLatexLabel(fig_parameter)
    coloring(fig_parameter, bp_parameter, 'BelongsA', 'TypeV', 'Assigns', 'Passes')

    # variable
    fig_variable, bp_variable = createFigure(type_count['Variable'], 38, 38)
    toLatexLabel(fig_variable)
    coloring(fig_variable, bp_variable, 'BelongsL', 'TypeV', 'Assigns', 'Passes')

    return fig_all, fig_class, fig_method, fig_attribute, fig_parameter, fig_variable


def createFigure(count, fontsize_x, fontsize_y):
    rate = count/count.sum()
    rate = rate.fillna(0)
    logger.info(f'relation-statistics\n{rate.T.describe()}')

    fig = plt.figure(figsize=[14,8])
    ax = fig.add_subplot(1,1,1)
    bp = ax.boxplot(rate.T, showmeans=True, patch_artist=True)
    # ax.violinplot(all_rate.T, showmeans=True)
    ax.set_xlabel('Relationships', fontsize=fontsize_x)
    ax.set_ylabel('Rate', fontsize=fontsize_y)
    ax.set_xticklabels(rate.index)
    ax.tick_params('x', labelsize=fontsize_x, labelrotation=90)
    ax.tick_params('y', labelsize=fontsize_y)
    return fig, bp

def coloring(fig, boxplot, *rtypes):
    rtypes_latex = [latexLabel[t] for t in rtypes]
    logger.debug(f'{rtypes}')
    ax = fig.axes[0]
    labels = ax.get_xticklabels()
    for box, label in zip(boxplot['boxes'], labels):
        if label.get_text() in rtypes_latex:
            logger.debug(f'cyan {label}')
            box.set_facecolor('#42E1EF80') # cyan
        else:
            logger.debug(f'white {label}')
            box.set_facecolor('#FFFFFF80') # white
    return boxplot

def toLatexLabel(fig):
    ax = fig.axes[0]
    labels = ax.get_xticklabels()
    ax.set_xticklabels([latexLabel[l.get_text()] for l in labels])

def save(fig, path):
    fig.savefig(path, bbox_inches='tight')
    logger.info(f'save {path}')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', action='store_true', help="set debug mode")
    main_args = parser.parse_args()

    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
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
    fig_all, fig_class, fig_method, fig_attribute, fig_parameter, fig_variable = createRelationFigure(project_list)

    output_dir = os.path.join("output", "fig")
    os.makedirs(output_dir, exist_ok=True)

    save(fig_all, os.path.join(output_dir, "RQ2_relation_all.pdf"))
    plt.close(fig_all)
    
    save(fig_class, os.path.join(output_dir, "RQ2_relation_class.pdf"))
    plt.close(fig_class)

    save(fig_method, os.path.join(output_dir, "RQ2_relation_method.pdf"))
    plt.close(fig_method)

    save(fig_attribute, os.path.join(output_dir, "RQ2_relation_attribute.pdf"))
    plt.close(fig_attribute)

    save(fig_parameter, os.path.join(output_dir, "RQ2_relation_parameter.pdf"))
    plt.close(fig_parameter)

    save(fig_variable, os.path.join(output_dir, "RQ2_relation_variable.pdf"))
    plt.close(fig_variable)
    
    # create figure using only icse2018 dataset

    # project_icse_list = [project for project in project_list if os.path.basename(project) in os.listdir('projects_icse2018')]
    # total_icse = len(project_icse_list)
    # fig_all_icse, fig_class_icse, fig_method_icse, fig_attribute_icse, fig_parameter_icse, fig_variable_icse = createRelationFigure(project_icse_list)

    # save(fig_all_icse, os.path.join(output_dir, "RQ2_relation_all_icse.pdf"))
    # plt.close(fig_all_icse)

    # save(fig_class_icse, os.path.join(output_dir, "RQ2_relation_class_icse.pdf"))
    # plt.close(fig_class_icse)

    # save(fig_method_icse, os.path.join(output_dir, "RQ2_relation_method_icse.pdf"))
    # plt.close(fig_method_icse)

    # save(fig_attribute_icse, os.path.join(output_dir, "RQ2_relation_attribute_icse.pdf"))
    # plt.close(fig_attribute_icse)

    # save(fig_parameter_icse, os.path.join(output_dir, "RQ2_relation_parameter_icse.pdf"))
    # plt.close(fig_parameter_icse)

    # save(fig_variable_icse, os.path.join(output_dir, "RQ2_relation_variable_icse.pdf"))
    # plt.close(fig_variable_icse)
