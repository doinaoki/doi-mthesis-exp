import os
import time
import datetime
import argparse
from multiprocessing import Pool
from logging import getLogger, INFO, DEBUG

import resource

from .LogFormatter import LogFormatter
from .ProjectRenameAnalyzer import ProjectRenameAnalyzer

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze co-rename relationships.')
    parser.add_argument('source', nargs='+', help='directory')
    parser.add_argument('-p', nargs=1, help='process number', type=int)
    parser.add_argument('--skip', help='skip if analysis result exists in output/', action='store_true')

    main_args = parser.parse_args()
    root, *repos = main_args.source
    p = main_args.p

    # set root logger
    getLogger().setLevel(INFO)

    # set main logger
    logger = getLogger(__name__)
    format = LogFormatter("main")

    # relation analysis
    def analyzeProject(args):
        project, lemmatize = args
        if "__pycache__" in project: return
        try:
            analyzer = ProjectRenameAnalyzer(project, lemmatize)
            if main_args.skip and os.path.isdir(analyzer.output_root):
                logger.info(format(f'skip {project} -- result already exists'))
            else:
                logger.info(format(f'analyze {project}'))
                analyzer.analyze()
                # analyzer.unit()
            return 0
        except Exception as e:
            logger.exception(format("can not analyze repository"))
            return -1

    start = time.time()
    logger.debug(format(root))
    if len(repos) > 0:
        dirs = [os.path.join(root, d) for d in repos]
    else:
        dirs = [os.path.join(root, d) for d in os.listdir(root)]
    all_projects = [d for d in dirs if os.path.isdir(d)]

    normal_args_list = [(project, False) for project in all_projects]
    lemmatized_args_list = [(project, True) for project in all_projects]
    normal_args_list.sort()
    lemmatized_args_list.sort()
    
    if p != None:
        # multi processing
        logger.info(format('run parallel processing'))
        resource.setrlimit(resource.RLIMIT_DATA, (8/p[0] * 1000 * 1024 ** 2, -1))
        with Pool(p[0]) as pool:
            normal = pool.map(analyzeProject, normal_args_list, chunksize=1)
            lemmatized = pool.map(analyzeProject, lemmatized_args_list, chunksize=1)
    else:
        # single processing
        logger.info(format('run single processing'))
        for _ in map(analyzeProject, normal_args_list):
            pass
        for _ in map(analyzeProject, lemmatized_args_list):
            pass
    end = time.time()
    logger.info(format(f'total_elapsed_time: {datetime.timedelta(seconds=end-start)}'))