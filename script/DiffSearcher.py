import difflib
from .WordLemmatizer import WordLemmatizer

# 意図解析(difflibで)
# prefix は今回の実験では見ない
class DiffSearcher:
    def __init__(self, lemmatize=False):
        self._lemmatize = lemmatize
        self._lemmatizer = WordLemmatizer()
        return

    def search(self, splitted_names):
        return self._search(splitted_names["old"], [], splitted_names["new"], [])

    # old_words: [word, ...]
    # old_seps:  [separator, ...]
    # new_words: [word, ...]
    # new_seps:  [separator, ...]
    def _search(self, old_words, old_seps, new_words, new_seps):
        result = []
        if self._lemmatize:
            old_lower_words = tuple(self._lemmatizer.lemmatize(word.lower()) for word in old_words)
            new_lower_words = tuple(self._lemmatizer.lemmatize(word.lower()) for word in new_words)
        else:
            old_lower_words = tuple(word.lower() for word in old_words)
            new_lower_words = tuple(word.lower() for word in new_words)
        
        diff_list = difflib.SequenceMatcher(None, old_lower_words, new_lower_words).get_opcodes()
        # 0:操作 1:旧名変更開始位置 2:旧名変更終了位置 3:新名変更開始位置 4:新名変更終了位置
        # (insert, deleteの位置情報はなくす)
        for diff in diff_list:
            if diff[0] == "insert":
                result.append((diff[0], tuple(new_lower_words[diff[3]:diff[4]])))
            elif diff[0] == "replace":
                result.append((diff[0], tuple(old_lower_words[diff[1]:diff[2]]), tuple(new_lower_words[diff[3]:diff[4]])))
            elif diff[0] == "delete":
                result.append((diff[0], tuple(old_lower_words[diff[1]:diff[2]])))
        # other どこにも違いが見つからなかったら (RefactoringMiner が検出したのは) other しかない
        # んだけど，語形吸収と差をつけたいので inflect も考える
        if len(result) == 0:
            for i in range(len(old_words)):
                if old_words[i].lower() != new_words[i].lower():
                    result.append(("inflect", (old_lower_words[i],)))
                elif old_words[i] != new_words[i]:
                    result.append(("other", (old_lower_words[i],)))
        # # prefix 今回の実験では見ない
        # if old_seps[0] != new_seps[0]:
        #     result.append(("prefix", (old_seps[0], ), (new_seps[0], )))
        #result: ((操作, 内容, 内容), (操作, 内容, 内容), ....)
        # ハッシュ化できるtupleに
        return tuple(result)

    # dataFrame操作用
    # data["renamings"]
    def __call__(self, renamings):
        return self.search(renamings["old"]["words"], renamings["old"]["seps"], renamings["new"]["words"], renamings["new"]["seps"])