import os
import pandas as pd
# to be modified

# 必要なjavaファイルの取得
class PathCreator:
    def __init__(self, project_root):
        self._gitroot = os.path.join(project_root, "repo")
        self._out = os.path.join("generated_files", project_root)
        return

    # commit_id: data["commit_id"]
    # location = data["location"]
    def createFilePaths(self, commit_id, location):
        # old_location = location.map(lambda x: x["old"])
        old_location = location["old"]
        gitpath = self._createJavaFilePathForGit(commit_id, old_location)
        javapath = self._createOutputJavaFilePath(commit_id, old_location)
        xmlpath = self._createOutputXmlFilePath(commit_id, old_location)
        return {"gitpath":gitpath, "javapath":javapath, "xmlpath":xmlpath}
                         

    def _createJavaFilePathForGit(self, commit_id, location):
        return commit_id+"^:"+location

    def _createOutputJavaFilePath(self, commit_id, location):
        return self._out +"/"+ commit_id +"/"+ location

    def _createOutputXmlFilePath(self, commit_id, location):
        return self._out +"/"+ commit_id +"/"+ location[:-4] + "xml"