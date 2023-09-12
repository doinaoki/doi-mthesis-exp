# 単語分割，差分を取得する時に使う
# spiralを利用，遅い
# separaterは分割してくれないのでそこは自前
import re
from spiral import ronin

class NameSplitter:
    def __init__(self):
        self._sep_exp = re.compile(r"([_\$])") # separater分割用
        self._store = {}
        
    # name: "identifier_name"
    def split(self, name):
        if name in self._store.keys():
            return self._store[name]
        else:
            splitted = ronin.split(name)
            self._store[name] = splitted
            return splitted

    # name: "identifier_name"
    def divide(self, word_list):
        words = []
        seps = []
        word_length = len(word_list)
         # 単語とセパレータの２つのリストを作成
        sep_memory = ""
        for i in range(word_length):
            if self._sep_exp.fullmatch(word_list[i]):
                sep_memory = word_list[i]
                continue
            else:
                words.append(word_list[i])
                seps.append(sep_memory)
                sep_memory = ""
        return words, seps

    # dataFrame操作用 
    # data[renamings]
    def __call__(self, renamings):
        old_words, old_seps = self.divide(self.split(renamings["old"]))
        new_words, new_seps = self.divide(self.split(renamings["new"]))
        return {"old":{"words":old_words, "seps":old_seps}, 
                "new":{"words":new_words, "seps":new_seps}}