import argparse
import json
import pathlib
import os
import simplejson

def setArgument():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', help='set directory containing repositories to be analyzed')
    args = parser.parse_args()
    return args

#統合するresult.jsonの数を指定
numberOfFile = 2

args = setArgument()
root = pathlib.Path(args.source)
allJsonPath = root.joinpath("result.json")
allResult = {"commits": []}

for i in range(numberOfFile):
    jsonPath = root.joinpath(f'result{i}.json')
    with open(jsonPath, 'r') as jp:
        renames = json.load(jp)
    allResult["commits"] += renames["commits"]

with open(allJsonPath, 'w') as ajp:
    simplejson.dump(allResult, ajp, indent=4, ignore_nan=True)
