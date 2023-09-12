from typing import Collection
import pandas as pd
import os 

from .NameSplitter import NameSplitter
from .DiffSearcher import DiffSearcher
from .ParameterExtractor import ParameterExtractor

# class UnitMakerV2:
class DataFrameCreator:
    def __init__(self, v="2"):
        self._version = v
        self._extractor = ParameterExtractor(v)
        self._splitter = NameSplitter()
        self._searcher = DiffSearcher()
        return

    def fromJson(self, path):
        if self._version == "1":
            path = os.path.join(path, "all_refactorings.json")
            data = self._readJsonV1(path)
            return data
        elif self._version == "2":
            path = os.path.join(path, "result.json")
            data = self._readJsonV2(path)
            return data

    def _readJsonV1(self, path):
        data = pd.read_json(path, encoding="UTF-8", lines=True)
        data = data[data["name"].map(lambda x: "Rename" in x)]
        data = pd.DataFrame(data.groupby("commitId"), columns=["commitId", "units"])
        data["units"] = data["units"].map(lambda x: list(x.T.to_dict().values()))
        data["count"] = data["units"].map(len)
        return data.reindex(columns=["commitId", "count", "units"])

    def _readJsonV2(self, path):
        data = pd.read_json(path, encoding="UTF-8").rename(columns={"commits": "units"})
        # filter rename refactoring
        data["commitId"] = data["units"].map(lambda x: x["sha1"])
        data["units"] = data["units"].map(lambda x: [r for r in x["refactorings"] if "Rename" in r["type"]])
        data["count"] = data["units"].map(len)
        data = data[data["count"]>0].reset_index(drop=True)
        return data
    
if __name__ == "__main__":
    dfc = DataFrameCreator("1").fromJson("script/testdata")
    part_of_dfc = dfc["units"][0]
    print(dfc)
    print(len(part_of_dfc))
    print(part_of_dfc)