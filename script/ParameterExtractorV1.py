# to be modified
# from os import rename
import re
from .ParameterExtractor import ParameterExtractor

# data["parameters"]から色々取り出す
class ParameterExtractorV1(ParameterExtractor):
    def __init__(self):
        super().__init__("1")
    
    def extractLocation(self, data):
        data_parameters = data["parameters"]
        rename_location = {"new": "", "old": ""}
        for key, value in data_parameters.items():
            if "renamed" in key:
                rename_location["new"] = value["file"]
            elif "original" in key:
                rename_location["old"] = value["file"]      
        return rename_location

    def extractType(self, data):
        return data["name"].split()[-1]

    # renameの情報を取り出す
    # data_parameters: data["parameters"]
    def extractRename(self, data):
        data_parameters = data["parameters"]
        rename_string = self._extractString(data_parameters)
        return self._modifyString(rename_string)
