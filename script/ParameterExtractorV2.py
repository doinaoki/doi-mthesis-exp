# to be modified
# from os import rename
import re
from .ParameterExtractor import ParameterExtractor

# data["parameters"]から色々取り出す
class ParameterExtractorV2(ParameterExtractor):
    def __init__(self):
        super().__init__("2")

    def extractLocation(self, data):
        rename_location = {"new": "", "old": ""}
        rename_location["old"] = data["leftSideLocations"][0]["filePath"]
        rename_location["new"] = data["rightSideLocations"][0]["filePath"]
        return rename_location

    def extractType(self, data):
        return data["type"].split()[-1]

    def extractRename(self, data):
        old = data["leftSideLocations"][0]["codeElement"]
        new = data["rightSideLocations"][0]["codeElement"]
        rename_str = {"new": new, "old": old}
        return self._modifyString(rename_str)
