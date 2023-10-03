import os
import subprocess

class FileFetcher:
    # gitroot: "プロジェクトのルートディレクトリ"
    def __init__(self, gitroot):
        self._root = os.path.join(gitroot, ".git")
        return

    # paths: data["filepaths"].map
    def getFileFromGit(self, paths):
        # "gitpath": hash:path/to/file.java 
        # "javapath": output-root/hash/path/to/file.java
        is_success = True
        if not os.path.isfile(paths["javapath"]):
            dirname, _ = os.path.split(paths["javapath"]) # dirname -> output-root/hash/path/to
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            # subprocessで実行する git show コマンドの準備
            git_show = ["git",
                        "--git-dir="+self._root,
                        "show",
                        paths["gitpath"]]
            # print(git_show)
            try:
                with open(paths["javapath"], "x") as newfile: 
                    subprocess.run(git_show, stdout=newfile, check=True) # git show > .java
            except subprocess.CalledProcessError as error:
                print("Something wrong: "+paths["gitpath"])
                is_success = False
                os.remove(paths["javapath"])
        return is_success