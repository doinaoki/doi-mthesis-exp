# to be modified
# from os import rename
import re

# data["parameters"]から色々取り出す
class ParameterExtractor:
    def __init__(self, version):
        # type_exp: "identifier : identifier_type"の形の文字列の分割に使う
        self._type_exp = re.compile(r" : ") 
        # id_exp: "identifier" = "variable_name" | "{public, private} method_name(argtype, args...)" | "path.to.class_name"
        # identfier から *_name 部分を取り出すために使う
        # method: re.compile(r"(?<=\s).+(?=\()") # アクセス修飾子ないパターンあったら死ぬかも
        # class, variable: re.compile(r"[^\.\)]+$") \)はmethodとの競合回避用
        self._id_exp = re.compile(r"(?<=\s).+(?=\()|[^\.\)]+$")
        self._version = version

    def extractLocation(self, data):
        pass

    def extractType(self, data):
        pass

    def extractRename(self, data):
        pass

    # "string"を取り出す
    # data_parameters: data["parameters"]
    def _extractString(self, data_parameters):
        rename_str = {"new": "", "old": ""}
        for key, value in data_parameters.items():
            if "rename" in key:
                rename_str["new"] = value["string"]
            elif "original" in key:
                rename_str["old"] = value["string"]
        return rename_str

    # 識別子の名前だけにする
    # raw_str: {"old": "oldstring", "new": "newstring"}
    def _modifyString(self, raw_str):
        modified_str = {}
        for key, string in raw_str.items(): # key = "old", "new"
            # typeを除外する
            splitted_str = self._type_exp.split(string)[0]
            # identifier部分の抽出
            modified_str[key] = self._id_exp.search(splitted_str).group()
        return modified_str