import pathlib
import os
import sys
import glob
import time
import json
import datetime
import traceback
import subprocess
import argparse
import simplejson
from multiprocessing import Pool
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG, log
import re

import pandas as pd
from .util.Name import KgExpanderSplitter
from .util.Rename import Rename

gitRe = re.compile(r'(?:^commit)\s+(.+)\nAuthor:\s+(.+)\nDate:\s+(.+)\n', re.MULTILINE)
COMMIT = set()

def setArgument():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', help='set directory containing repositories to be analyzed')
    parser.add_argument('-D', help='dry run (only check how many archives will be created)', action='store_true', default=False)
    args = parser.parse_args()
    return args

def setGitlog(path):
    repoPath = os.path.join(path, "repo")
    cp = subprocess.run(f"cd {repoPath}; git log",shell=True, stdout=subprocess.PIPE)
    gitLog = cp.stdout.decode('utf-8','ignore')
    gitInfo = gitRe.findall(gitLog)
    for info in gitInfo:
        commit = info[0]
        COMMIT.add(commit)
    return

def doRefactoringMiner(commit, repoPath, RefactoringDict):
    rMiner = ["RefactoringMiner",
            "-c",
            f"{repoPath}",
            f"{commit}"]
    cp = subprocess.run(f'RefactoringMiner -c {repoPath} {commit}',shell=True, stdout=subprocess.PIPE)
    if cp.returncode != 0:
        return
    refactoring = cp.stdout.decode('utf-8','ignore')
    refactoringJson = json.loads(refactoring)
    if 'commits' not in refactoringJson:
        print(f"Warn: {commit} \n refactoringMiner is something wrong")
        return
    RefactoringDict['commits'] += json.loads(refactoring)['commits']

if __name__ == "__main__":
    args = setArgument()

    root = pathlib.Path(args.source)

    setGitlog(root)
    repoPath = root.joinpath('repo')
    if not os.path.exists(repoPath):
        print("error: repo is not existed")
        exit(1)
    # ここを変えると出力されるより細かくファイルを分けてrefactoring
    ratio = 30
    commitLength = len(COMMIT)
    for rMinerNumber in range(ratio):
        count = 0
        jsonPath = root.joinpath(f'result{rMinerNumber}.json')
        RefactoringDict = {"commits": []}
        for c in COMMIT:
            count += 1
            if count < (commitLength * rMinerNumber / ratio) or count >= (commitLength * (rMinerNumber+1) / ratio) :
                continue
            print(f'{count} / {int(commitLength * (rMinerNumber+1) / ratio)}')
            print(f'start RefactoringMiner: commit={c}')
            doRefactoringMiner(c, repoPath, RefactoringDict)
            print(f'end RefactoringMiner: commit={c}')
        with open(jsonPath, 'w') as jp:
            simplejson.dump(RefactoringDict, jp, indent=4, ignore_nan=True)
        print(f'{rMinerNumber+1} / {ratio} is done')

    #全ての結果を統合

    print(f'start merging refactoring')
    allResult = {"commits": []}
    allJsonPath = root.joinpath('result.json')
    for i in range(ratio):
        jsonPath = root.joinpath(f'result{i}.json')
        with open(jsonPath, 'r') as jp:
            renames = json.load(jp)
        allResult["commits"] += renames["commits"]

    with open(allJsonPath, 'w') as ajp:
        simplejson.dump(allResult, ajp, indent=4, ignore_nan=True)
    print(f'finish merging refactoring')



'''
if __name__ == "__main__":
    args = setArgument()

    root = pathlib.Path(args.source)

    setGitlog(root)
    jsonPath = root.joinpath('result.json')
    repoPath = root.joinpath('repo')
    if not os.path.exists(repoPath):
        print("error: repo is not existed")
        exit(1)
    count = 0
    ratio = 2
    rMinerNumber = 1
    commitLength = len(COMMIT)
    for c in COMMIT:
        count += 1
        if count < (commitLength * rMinerNumber / ratio) or count >= (commitLength * (rMinerNumber+1) / ratio) :
            continue
        print(f'{count} / {int(commitLength * (rMinerNumber+1) / ratio)}')
        if count == 58581:
            continue
        print(f'start RefactoringMiner: commit={c}')
        doRefactoringMiner(c, repoPath)
        print(f'end RefactoringMiner: commit={c}')
    with open(jsonPath, 'w') as jp:
        simplejson.dump(RefactoringDict, jp, indent=4, ignore_nan=True)
'''