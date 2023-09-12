import argparse
import os
import re
import json
import matplotlib.pyplot as plt
from matplotlib import rcParams
import pandas as pd
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG

from .rq1 import createUnitFigure
from .rq2 import createFigure, coloring, toLatexLabel

rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['Hiragino Maru Gothic Pro', 'Yu Gothic', 'Meirio', 'Takao', 'IPAexGothic', 'IPAGothic', 'VL Gothic', 'Noto Sans CJK JP']
rcParams['text.usetex'] = True
logger = getLogger(__name__)
logger.setLevel(DEBUG)

label_dict = {
    "insert": r'$\textsc{Insert}$',
    "delete": r'$\textsc{Delete}$',
    "replace": r'$\textsc{Replace}$',
    "other": r'$\textsc{Other}$',
    "inflect": r'$\textsc{Inflect}$'
}

def createRelationFigure(file_list):
    id_exp = re.compile(r'(?<=/)[0-9a-f]+(?=/)')
    all_count = pd.DataFrame()
    type_count = {t: pd.DataFrame() for t in ['Class', 'Method', 'Attribute', 'Parameter', 'Variable']}

    for file in file_list:
        try:
            with open(os.path.join(file, 'relation_count_affected.json')) as f:
                count = json.load(f)
                count = pd.Series(count, name=file)
                logger.debug(count)
                logger.debug(f'{count.sum()} relations found')
                all_count = pd.concat([all_count, count], axis=1)

            logger.info("(Relation) reading result " + file)
            with open(os.path.join(file, 'relation_count_type_affected.json')) as f:
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
            num = sum(len(units) for units in all_units.values())
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


def createOperationalChunkFigure(file_normal_list, file_lemmatized_list):
    normal_total = pd.DataFrame()
    lemmatized_total = pd.DataFrame()

    for file_normal, file_lemmatized in zip(file_normal_list, file_lemmatized_list):
        try:
            logger.info(f"(Operational Chunk) reading result {file_normal} / {file_lemmatized}")
            normal = pd.read_csv(os.path.join(file_normal, "count_all.csv"), index_col="Unnamed: 0")
            normal.columns = [file_normal]
            normal_total = pd.concat([normal_total, normal], axis=1)
            lemmatized = pd.read_csv(os.path.join(file_lemmatized, "count_all.csv"), index_col="Unnamed: 0")
            lemmatized.columns = [file_lemmatized]
            lemmatized_total = pd.concat([lemmatized_total, lemmatized], axis=1)
        except Exception:
            logger.exception("fatal error occured")

    normal_total = normal_total/normal_total.sum()
    logger.info(f'normal_other\n{normal_total.T["other"].describe()}')
    normal_total = normal_total.drop(index=['other'])
    lemmatized_total = lemmatized_total/lemmatized_total.sum()
    logger.info(f'lemmatized_other\n{lemmatized_total.T["other"].describe()}')
    lemmatized_total = lemmatized_total.drop(index=['other'])
    logger.info(f'normal_rate\n{normal_total.T.describe()}')
    logger.info(f'lemmatized_rate\n{lemmatized_total.T.describe()}')

    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    normal_x = [0,1,2,3]
    lemmatized_x = [x+0.3 for x in normal_x]
    ax.bar(normal_x, normal_total.T.mean(), width=0.3, label='without\nignoring\ninflection')
    ax.bar(lemmatized_x, lemmatized_total.T.mean(), width=0.3, label='ignoring\ninflection')
    ax.set_ylim([0, 0.65])
    ax.set_xlabel('Type of Operational Chunks', fontsize=18)
    ax.set_ylabel('Rate', fontsize=22)
    ax.set_xticks([(x1+x2)/2 for x1, x2 in zip(normal_x, lemmatized_x)])
    ax.set_xticklabels([label_dict[l] for l in normal_total.index])
    ax.tick_params('x', labelsize=18)
    ax.tick_params('y', labelsize=22)
    fig.legend(fontsize=16, bbox_to_anchor=(1.2, 0.88), borderaxespad=0)
    return fig

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
    lemmatized = os.path.join(output, "lemmatized")
    project_normal_list = [os.path.join(normal, d) for d in os.listdir(normal)]
    project_lemmatized_list = [os.path.join(lemmatized, d) for d in os.listdir(lemmatized)]

    fig_co, _, _ = createUnitFigure(project_lemmatized_list)
    fig_chunk = createOperationalChunkFigure(project_normal_list, project_lemmatized_list)
    fig_all, fig_class, fig_method, fig_attribute, fig_parameter, fig_variable = createRelationFigure(project_lemmatized_list)

    # save fig
    output_dir = os.path.join("output", "fig")
    os.makedirs(output_dir, exist_ok=True)

    save(fig_co, os.path.join(output_dir, "RQ3_co_rename.pdf"))
    plt.close(fig_co)

    save(fig_chunk, os.path.join(output_dir, "RQ3_operational_chunk.pdf"))
    plt.close(fig_chunk)

    save(fig_all, os.path.join(output_dir, "RQ3_relation_all.pdf"))
    plt.close(fig_all)
    
    save(fig_class, os.path.join(output_dir, "RQ3_relation_class.pdf"))
    plt.close(fig_class)

    save(fig_method, os.path.join(output_dir, "RQ3_relation_method.pdf"))
    plt.close(fig_method)

    save(fig_attribute, os.path.join(output_dir, "RQ3_relation_attribute.pdf"))
    plt.close(fig_attribute)

    save(fig_parameter, os.path.join(output_dir, "RQ3_relation_parameter.pdf"))
    plt.close(fig_parameter)

    save(fig_variable, os.path.join(output_dir, "RQ3_relation_variable.pdf"))
    plt.close(fig_variable)