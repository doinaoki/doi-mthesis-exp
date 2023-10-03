# 1プロジェクトに対する処理をまとめたもの
import copy

from script.RelationType import RelationType
import time
import os
import json
import pandas as pd
import datetime
import collections

from .DataFrameCreator import DataFrameCreator
from .NameSplitter import NameSplitter 
from .DiffSearcher import DiffSearcher
from .ParameterExtractorV1 import ParameterExtractorV1
from .ParameterExtractorV2 import ParameterExtractorV2
from .PathCreator import PathCreator
from .FileFetcher import FileFetcher
from .XmlCreator import XmlCreator
from .RenameTypeCounter import RenameTypeCounter
from .Unit import Unit
from .Renaming import Renaming

# 並列
from concurrent.futures import ThreadPoolExecutor

# ゴミ集め
import gc

# log
from logging import getLogger
from .LogFormatter import LogFormatter

class ProjectRenameAnalyzer:
    def __init__(self, project_root, lemmatize, *, version="2"):
        self.project_root = project_root
        # output-dir: output/v{version}/{normal | lemmatized}/{project}
        output = os.path.join(os.path.join("v"+version, "lemmatized" if lemmatize else "normal"), os.path.split(self.project_root)[1])
        self.output_root = os.path.join("output", output)

        self._input_root = os.path.join(self.project_root, "repo")
        self._dfcreator = DataFrameCreator(version)
        self._splitter = NameSplitter()
        if version == "1":
            self._extractor = ParameterExtractorV1()
        elif version == "2":
            self._extractor = ParameterExtractorV2()
        self._searcher = DiffSearcher(lemmatize=lemmatize)
        self._path_creator = PathCreator(self.project_root)
        self._file_fetcher = FileFetcher(self._input_root)
        self._xml_creator = XmlCreator()
        self._counter = RenameTypeCounter()

        self.logger = getLogger(__name__)
        self.formatter = LogFormatter(project_root)
        self.lemmatize = lemmatize
        self.version = version
        self.max_workers = 16
        
    def analyze(self):
        os.makedirs(self.output_root, exist_ok=True)
        self.logger.info(self.formatter(f'lemmatize {self.lemmatize}'))

        start = time.time()
        rename_data = self._loadData()

        # unit create
        self.logger.info(self.formatter('genarate xml files'))
        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.map(self._generateFiles, rename_data["units"])

        self.logger.info(self.formatter('create unit'))
        rename_data["units"] = rename_data["units"].map(self._createUnit)
        
        self.logger.info(self.formatter('export unit.json'))
        with open(os.path.join(self.output_root, "unit.json"), "w") as output:
            json.dump(
                {commitId:{str(diff):rlist for unit in units for diff, rlist in unit.items()} for commitId, units in zip(rename_data["commitId"], rename_data["units"])},
                output,
                default=self._default,
                indent=4)
        del rename_data["commitId"], rename_data["count"]
        
        self.logger.info(self.formatter('export count_all.csv, count_unit_solo.csv, count_unit_group.csv'))
        self._counter.countAll(rename_data["units"]).sum().to_csv(os.path.join(self.output_root, "count_all.csv"))
        self._counter.countByUnitSize(rename_data["units"]).iloc[0].to_csv(os.path.join(self.output_root, "count_unit_solo.csv"))
        self._counter.countByUnitSize(rename_data["units"])[1:].to_csv(os.path.join(self.output_root, "count_unit_group.csv"))

        # unit analyze
        self.logger.info(self.formatter('analyze units'))
        count, count_type, details = self._analyzeUnit(rename_data["units"])
        del rename_data
        gc.collect()
                
        self.logger.info(self.formatter('export relaiton_count.json, relation_count_type.json, relation_details.json'))
        with open(os.path.join(self.output_root, "relation_count.json"), "w") as output:
            json.dump(count, output, indent=4)
        with open(os.path.join(self.output_root, "relation_count_type.json"), "w") as output:
            json.dump(count_type, output, indent=4) 
        with open(os.path.join(self.output_root, "relation_details.json"), "w") as output:
            json.dump(details, output, default=self._default, indent=4)

        self.logger.debug(self.formatter(f'{count}'))
        self.logger.debug(self.formatter(f'{count_type}'))
        self.logger.info(self.formatter('all process completed.'))
        end = time.time()

        self.logger.info(self.formatter(f'elapsed_time: {datetime.timedelta(seconds=end-start)}'))
        return

    def unit(self):
        os.makedirs(self.output_root, exist_ok=True)
        self.logger.info(self.formatter(f'lemmatize {self.lemmatize}'))

        start = time.time()
        rename_data = self._loadData()
                
        self.logger.info(self.formatter('genarate xml files'))
        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.map(self._generateFiles, rename_data["units"])

        self.logger.info(self.formatter('create unit'))
        rename_data["units"] = rename_data["units"].map(self._createUnit)
        
        self.logger.info(self.formatter('export unit.json'))
        with open(os.path.join(self.output_root, "unit.json"), "w") as output:
            json.dump(
                {commitId:{str(diff):rlist for unit in units for diff, rlist in unit.items()} for commitId, units in zip(rename_data["commitId"], rename_data["units"])},
                output,
                default=self._default,
                indent=4)
        del rename_data["commitId"], rename_data["count"]

        self.logger.info(self.formatter('export count_all.csv, count_unit_solo.csv, count_unit_group.csv'))
        self._counter.countAll(rename_data["units"]).sum().to_csv(os.path.join(self.output_root, "count_all.csv"))
        self._counter.countByUnitSize(rename_data["units"]).iloc[0].to_csv(os.path.join(self.output_root, "count_unit_solo.csv"))
        self._counter.countByUnitSize(rename_data["units"])[1:].to_csv(os.path.join(self.output_root, "count_unit_group.csv"))

        self.logger.info(self.formatter('all process completed.'))
        end = time.time()

        self.logger.info(self.formatter(f'elapsed_time: {datetime.timedelta(seconds=end-start)}'))

    def _loadData(self):
        self.logger.info(self.formatter('read json'))
        rename_data = self._dfcreator.fromJson(self.project_root)
        del self._dfcreator

        self.logger.info(self.formatter('get rename information'))
        for commit_id, units in zip(rename_data["commitId"], rename_data["units"]):
            self._addInfomation(commit_id, units)
        del self._splitter, self._extractor, self._searcher, self._path_creator
        return rename_data

    # renameの記録
    # renameの差分(difflib)
    # 差分(difflib)の調整
    # fileの場所
    # ファイルpath生成
    def _addInfomation(self, commit_id, units):
        for refactoring in units:
            renaming = self._extractor.extractRename(refactoring)
            splitted = {k: self._splitter.split(v) for k,v in renaming.items()}
            difftypes = self._searcher.search(splitted)
            location = self._extractor.extractLocation(refactoring)
            rename_type = self._extractor.extractType(refactoring)
            refactoring["name"]       = renaming
            refactoring["renameType"] = rename_type
            refactoring["location"]   = location
            refactoring["splitted"]   = splitted
            refactoring["difftypes"]  = difftypes   
            refactoring["filepaths"]  = self._path_creator.createFilePaths(commit_id, location)
        
    def _generateFiles(self, rename_list):
        for refactoring in rename_list:
            paths = refactoring["filepaths"]
            self._file_fetcher.getFileFromGit(paths)
            self._xml_creator.createXml(paths)
        return True

    def _createUnit(self, rename_list):
        units = {}
        for rename in rename_list:
            file_name = os.path.splitext(os.path.basename(rename["filepaths"]["xmlpath"]))[0]
            renaming = Renaming(rename["name"]["old"],
                                rename["name"]["new"],
                                rename["renameType"],
                                rename["filepaths"]["javapath"],
                                rename["filepaths"]["xmlpath"],
                                file_name)
            for difftype in rename["difftypes"]:
                if difftype not in units.keys():
                    units[difftype] = Unit()
                units[difftype].add(renaming)
        return collections.deque({diff: unit} for diff, unit in units.items())

    def _analyzeUnit(self, rename_data_units):
        types = ['Class', 'Method', 'Attribute', 'Variable', 'Parameter']
        details = {rtype.name: set() for rtype in list(RelationType)}
        details_type = {t:copy.deepcopy(details) for t in types}
        for units in rename_data_units:
            while units:
                _, unit = list(*units.popleft().items())
                included_types = unit.getIncludedTypes()
                for rtype, rlist in unit.analyze().items():
                    for t in included_types:
                        details_type[t][rtype.name].update(rlist)                
                del _, unit
        gc.collect()
        [details[rtype].update(rlist) for d in details_type.values() for rtype, rlist in d.items()]
        count_type = {t: {rtype: len(rlist) for rtype, rlist in detail.items()} for t, detail in details_type.items()}
        count = {rtype: len(rlist) for rtype, rlist in details.items()}
        return count, count_type, details_type

    def _default(self, item):
        if isinstance(item, set) or isinstance(item, frozenset) or isinstance(item, collections.deque):
            return list(item)
        elif isinstance(item, Unit):
            return item.export()
        elif isinstance(item, Renaming):
            return item.export()
        else:
            raise TypeError

# TestCode
if __name__ == "__main__":
    version = "2"
    ProjectRenameAnalyzer("script/testdata", True, version=version).analyze()
    ProjectRenameAnalyzer("script/testdata", False, version=version).analyze()
