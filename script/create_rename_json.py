import os
import pandas as pd
import argparse

from .DataFrameCreator import DataFrameCreator
from .ParameterExtractorV2 import ParameterExtractorV2

def setArgument():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', help='set directory containing result.json')
    args = parser.parse_args()
    return args

def addInformation(commitId, units): # add commit, oldname, newname, renameType, location
    extractor = ParameterExtractorV2()
    for refactoring in units:
        renaming = extractor.extractRename(refactoring)
        location = extractor.extractLocation(refactoring)
        rename_type = extractor.extractType(refactoring)
        refactoring["commit"] = commitId
        refactoring["oldname"] = renaming["old"]
        refactoring["newname"] = renaming["new"]
        refactoring["renameType"] = rename_type
        refactoring["location"] = location
    return

def flatten(data):
    newData = []
    [newData.extend(renameList) for renameList in data['units']]
    return pd.Series(newData)

if __name__ == "__main__":
    args = setArgument()
    dirPath = args.source
    outDirPath = os.path.join(dirPath, "rename.json")
    renameData = DataFrameCreator("2").fromJson(dirPath)

    for commitId, units in zip(renameData["commitId"], renameData["units"]):
        addInformation(commitId, units)
    # debug
    # print(renameData)
    renameData = flatten(renameData)
    # debug
    # print(renameData)
    renameData.to_json(outDirPath, orient="records", indent=4)