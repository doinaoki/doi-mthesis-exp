import os
import subprocess

# xml生成 
class XmlCreator:
    def __init__(self):
        return

    # paths: data["filepaths"]
    def createXml(self, paths):
        # javapath: path/to/file.java
        # xmlpath: path/to/file.xml
        is_success = True
        if not os.path.isfile(paths["xmlpath"]):
            try:
                # subprocessで実行するsrcmlコマンドの準備
                srcml = ["srcml",
                        paths["javapath"],
                         "-o",
                         paths["xmlpath"]]
                subprocess.run(srcml, check=True) # .java to .xml
            except subprocess.CalledProcessError as error:
                print("Something wrong: "+paths["javapath"])
                is_success = False
                os.remove(paths["xmlpath"])
        return is_success