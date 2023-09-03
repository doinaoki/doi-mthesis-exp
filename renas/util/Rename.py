import difflib
from copy import deepcopy
from ast import literal_eval
from .Name import KgExpanderSplitter, LemmaManager, AbbreviationManager, CaseManager, ExpandManager
from .common import getPaddingList, printDict, splitIdentifier
from logging import getLogger, DEBUG
from itertools import zip_longest
import pandas as pd

_lemmatizer = LemmaManager()
_abbrManager = None
_caseManager = CaseManager()
_expandManager = None
_logger = getLogger('util.Rename')
_logger.setLevel(DEBUG)

def setAbbrDic(abbrDicPath):
    global _abbrManager, _expandManager
    _abbrManager = AbbreviationManager(abbrDicPath)
    _expandManager = ExpandManager(abbrDicPath)
    _logger.info('set abbrDic record')

# 命名規則の変化（POSタグ？、省略、Case、区切り文字）は扱いません。
class Rename:
    def __init__(self, old, normalize):
        self.__normalize = normalize
        if isinstance(old, str):
            self.__old = self.__getNameDetail(old)
        elif isinstance(old, dict):
            self.__old = old
        if not normalize:
            self.__overWriteDetail(self.__old)
        self.__new = None
        self.__diff = None
        self.__wordColumn = 'normalized' # if normalize else 'split'
        pass

# after Debug, should delete this function
    def getOld(self):
        return self.__old
    
    def getNew(self):
        return self.__new

    def getDiff(self):
        return self.__diff

    def setNewName(self, newName):
        if self.__new == None:
            self.__new = self.__getNameDetail(newName)
            self.newSetDiff()
        else:
            _logger.error(f'new name is already set: {self.__new}')
        return

    def getDiff(self):
        if self.__diff == None:
            _logger.error('you first need to call setNewName() to get diff')
        return self.__diff

    def coRename(self, idDict):
        if not self.__normalize:
            self.__overWriteDetail(idDict)
        if idDict == self.__old:
            _logger.debug('candidate is the same as trigger')
            return None
        _logger.debug(f'BEFORE {printDict(idDict, "case", "pattern", "delimiter", "heuristic", "postag", self.__wordColumn)}')
        beforeWordList = deepcopy(idDict[self.__wordColumn])
        # apply diff
        for diff in self.__diff:
            self.__applyDiff(diff, idDict)
        if idDict[self.__wordColumn] == beforeWordList:
            _logger.debug(f'not a candidate')
            return None
        _logger.debug(f'AFTER {printDict(idDict, "case", "pattern", "delimiter", "heuristic", "postag", self.__wordColumn)}')
        # word generation
        if self.__normalize:
            # inflect
            inflectedWords = _lemmatizer.inflect(idDict['normalized'], idDict['postag'])
            _logger.debug(f'inflect: {inflectedWords}')
            # abbreviate
            abbreviatedWords = _abbrManager.abbreviate(inflectedWords, idDict['heuristic']) if 'heuristic' in idDict else inflectedWords
            _logger.debug(f'abbreviate: {abbreviatedWords}')
        else:
            abbreviatedWords = idDict[self.__wordColumn]
        # case
        casedWords = _caseManager.transform(abbreviatedWords, idDict['pattern'], idDict['case'])
        _logger.debug(f'case: {casedWords}')
        # join
        joinedWords = self.__join(casedWords, idDict['pattern'], idDict['delimiter'])
        idDict['join'] = joinedWords
        _logger.debug(f'join: {joinedWords}')
        _logger.debug(f'{idDict["name"]} should be renamed to {idDict["join"]}')

        return idDict

    def __overWriteDetail(self, old):
        detail = splitIdentifier(old['name'])
        old['split'] = detail['split']
        old['case'] = detail['case']
        old['pattern'] = detail['pattern']
        old['delimiter'] = detail['delimiter']
        old['normalized'] = deepcopy(old['split'])
        return
    
#todo 標準化するときに省略後展開も行うexpandedを追加.
    def __getNameDetail(self, name):
        result = splitIdentifier(name)
        words = result['split']

        if self.__normalize:
            _expandManager = ExpandManager("/Users/doinaoki/Documents/CodeTest/Osumi-saigen2/projects/ratpack/archives/beb8cabeedcdb42db742e808228408b1e2cc6513/record.json")
            result["expanded"], result["heuristic"] = _expandManager.expand(words, self.__old)
            postags = _lemmatizer.getPosTags(result["expanded"])
            result['postag'] = postags
            result['normalized'] = _lemmatizer.normalize(result["expanded"], postags)
        else:
            postags = _lemmatizer.getPosTags(words)
            result['postag'] = postags
            result['normalized'] = deepcopy(words)
        return result

# 新しいoperation chunkを定義.
    def __setDiff(self):
        if self.__diff == None:
            self.__diff = []
            oldSplit = self.__old[self.__wordColumn]
            newSplit = self.__new[self.__wordColumn]
            diff_list = difflib.SequenceMatcher(None, oldSplit, newSplit).get_opcodes()
            # 0:操作 1:旧名変更開始位置 2:旧名変更終了位置 3:新名変更開始位置 4:新名変更終了位置
            # (insert, deleteの位置情報はなくす)
            for diff in diff_list:
                if diff[0] == "insert":
                    self.__diff.append((diff[0], tuple(newSplit[diff[3]:diff[4]])))
                elif diff[0] == "replace":
                    self.__diff.append((diff[0], tuple(oldSplit[diff[1]:diff[2]]), tuple(newSplit[diff[3]:diff[4]])))
                elif diff[0] == "delete":
                    self.__diff.append((diff[0], tuple(oldSplit[diff[1]:diff[2]])))
        return self.__diff
    
    def newSetDiff(self):
        if self.__diff == None:
            self.__diff = []
            #expand実装後消去
            #self.__old["expanded"] = ["is","ssl","clients","auth"]
            #self.__new["expanded"] = ["is", "require", "client", "ssl", "auth"]
            #self.__old["expanded"] = ["load", "entity"]
            #self.__new["expanded"] = ["read", "e"]
            #self.__old["normalized"] = ["load", "entity"]
            #self.__new["normalized"] = ["read", "e"]
            self.__diff += self.extractFormat()
            self.__diff += self.extractChangeCase()
            self.__diff += self.extractOrder()

            oldSplit = self.__old["ordered"]
            newSplit = self.__new[self.__wordColumn]
            diff_list = difflib.SequenceMatcher(None, oldSplit, newSplit).get_opcodes()
            # 0:操作 1:旧名変更開始位置 2:旧名変更終了位置 3:新名変更開始位置 4:新名変更終了位置
            # (insert, deleteの位置情報はなくす)
            for diff in diff_list:
                if diff[0] == "insert":
                    self.__diff.append((diff[0], tuple(newSplit[diff[3]:diff[4]])))
                elif diff[0] == "replace":
                    self.__diff.append((diff[0], tuple(oldSplit[diff[1]:diff[2]]), tuple(newSplit[diff[3]:diff[4]])))
                elif diff[0] == "delete":
                    self.__diff.append((diff[0], tuple(oldSplit[diff[1]:diff[2]])))

    #変更操作format抽出
    def extractFormat(self):
        oldNormalize = self.__old[self.__wordColumn]
        newNormalize = self.__new[self.__wordColumn]
        oldExpanded = self.__old["expanded"]
        newExpanded = self.__new["expanded"]
        oldSplit = self.__old["split"]
        newSplit = self.__new["split"]

        equalSplitWords = set(oldSplit)&set(newSplit)
        equalExpandedWords = set(oldExpanded)&set(newExpanded)
        equalNormalizeWords = set(oldNormalize)&set(newNormalize)
        equalSplitWordsIndex = [oldSplit.index(word) for word in equalSplitWords]
        equalExpandedWordsIndex = [oldExpanded.index(word) for word in equalExpandedWords]

        abbrCandidate = equalExpandedWords-equalSplitWords
        formatAbbreviation = []
        abbrCandidateOldIndex = [oldExpanded.index(word) for word in abbrCandidate]
        abbrCandidateNewIndex = [newExpanded.index(word) for word in abbrCandidate]
        for word in abbrCandidate:
            oldHeu = self.__old["heuristic"][oldExpanded.index(word)]
            newHeu = self.__new["heuristic"][newExpanded.index(word)]
            if oldHeu == newHeu:
                continue
            if oldHeu == "H1":
                formatAbbreviation.append(["format", ("Abbreviation", "H1", word[0], word)])
            elif newHeu == "H1":
                formatAbbreviation.append(["format", ("Abbreviation", "H1", word, word[0])])
            elif oldHeu == "H2" or newHeu == "H2":
                formatAbbreviation.append(["format", ("Abbreviation", "H2", oldSplit[oldExpanded.index(word)], newSplit[newExpanded.index(word)])])
            else:
                formatAbbreviation.append(["format", ("Abbreviation", "H3", oldSplit[oldExpanded.index(word)], newSplit[newExpanded.index(word)])])

        #formatAbbreviation = [["format", word, ("Abbreviation", oldSplit[oldExpanded.index(word)], newSplit[newExpanded.index(word)])] for word in equalExpandedWords-equalSplitWords if oldExpanded.index(word) not in equalSplitWordsIndex]
        formatNormalize = [["format", word, ("Normalize", oldExpanded[oldNormalize.index(word)], newExpanded[newNormalize.index(word)])] for word in equalNormalizeWords-equalExpandedWords if oldNormalize.index(word) not in equalExpandedWordsIndex]
        _logger.debug(formatAbbreviation + formatNormalize)
        return formatAbbreviation + formatNormalize
        
    #変更操作changeCase抽出
    def extractChangeCase(self):
        if self.__new["pattern"] != [] and self.__old["pattern"] != [] and self.__old["pattern"] != self.__new["pattern"]:
            return [["changeCase", (self.__old["pattern"], self.__new["pattern"])]]
        return [] 

    #変更操作order抽出
    def extractOrder(self):
        oldNormalize = self.__old[self.__wordColumn]
        newNormalize = self.__new[self.__wordColumn]
        equalNormalizeWords = set(oldNormalize)&set(newNormalize)
        self.__old["ordered"] = oldNormalize
        if len(equalNormalizeWords) > 1:
            oldWordsOrder = [word for word in oldNormalize if word in equalNormalizeWords]
            newWordsOrder = [word for word in newNormalize if word in equalNormalizeWords]
            oldOrder = []
            newOrder = []
            for index in range(len(oldWordsOrder)):
                if oldWordsOrder[index] != newWordsOrder[index]:
                    oldOrder.append(oldWordsOrder[index])
                    newOrder.append(newWordsOrder[index])
            if len(oldOrder) > 1:
                order = ["order", (oldOrder, newOrder)]
                self.__old["ordered"] = [word if word not in oldOrder else newOrder[oldOrder.index(word)] for word in oldNormalize ]
                _logger.debug(order)
                return [order]
            return []

        return []

#todo 適用方法変更
    def __applyDiff(self, diff, oldDict):
        dType, *dWords = diff
        if dType == 'delete':
            self.__applyDelete(oldDict, dWords[0])
        elif dType == 'replace':
            self.__applyReplace(oldDict, dWords[0], dWords[1])
        elif dType == 'insert':
            self.__applyInsert(oldDict, dWords[0])
        return

    def __join(self, words, pattern, delimiters):
        if 'SNAKE' not in pattern:
            concated = [None] * (len(words) + len(delimiters))
            _logger.debug(words)
            _logger.debug(delimiters)
            _logger.debug(concated)
            concated[0::2] = delimiters
            concated[1::2] = words
            return ''.join(concated)
        elif 'SNAKE' in pattern:
            return '_'.join(words)

#todo 変更
    def __applyDelete(self, oldDict, deletedWords):
        _logger.debug(f'delete {deletedWords}')
        idx = self.__findIndex(deletedWords, oldDict[self.__wordColumn])
        if idx == -1:
            return
        deletedWordLen = len(deletedWords)
        if deletedWordLen == len(oldDict[self.__wordColumn]):
            _logger.debug(f'cannot delete {deletedWords} because words will be empty')
            return
        newSep = max(oldDict['delimiter'][idx : idx+deletedWordLen +1], key=len)
        # word
        self.__replaceSlice(oldDict[self.__wordColumn], idx, idx+deletedWordLen, [])
        # case
        self.__replaceSlice(oldDict['case'], idx, idx+deletedWordLen, [])
        # delimiter
        self.__replaceSlice(oldDict['delimiter'], idx, idx+deletedWordLen + 1, [newSep])
        if self.__normalize:
            # postag
            self.__replaceSlice(oldDict['postag'], idx, idx+deletedWordLen, [])
            # heuristic
            self.__replaceSlice(oldDict['heuristic'], idx, idx+deletedWordLen, [])

#todo 変更
    def __applyReplace(self, oldDict, deletedWords, insertedWords):
        _logger.debug(f'replace {deletedWords} to {insertedWords}')
        idx = self.__findIndex(deletedWords, oldDict[self.__wordColumn])
        if idx == -1:
            return
        deletedWordLen = len(deletedWords)
        insertedWordLen = len(insertedWords)
        # word
        self.__replaceSlice(oldDict[self.__wordColumn], idx, idx+deletedWordLen, insertedWords)
        # case
        toCases = getPaddingList(oldDict['case'][idx:idx+deletedWordLen], insertedWordLen)
        self.__replaceSlice(oldDict['case'], idx, idx+deletedWordLen, toCases)
        # delimiter
        fromDelims = oldDict['delimiter'][idx:idx+deletedWordLen+1]
        toDelims = [fromDelims[0]] + [''] * (insertedWordLen - 1) + [fromDelims[-1]]
        self.__replaceSlice(oldDict['delimiter'], idx, idx+deletedWordLen+1, toDelims)
        if self.__normalize:
            # postag
            toPostags = getPaddingList(oldDict['postag'][idx:idx+deletedWordLen], insertedWordLen)
            self.__replaceSlice(oldDict['postag'], idx, idx+deletedWordLen, toPostags)
            # heuristic
            toHeuristics = getPaddingList(oldDict['heuristic'][idx:idx+deletedWordLen], insertedWordLen)
            self.__replaceSlice(oldDict['heuristic'], idx, idx+deletedWordLen, toHeuristics)

#todo 変更
    def __applyInsert(self, oldDict, insertedWords):
        _logger.debug(f'insert {insertedWords}')
        insertedWordLen = len(insertedWords)
        newNorm = self.__new[self.__wordColumn]
        oldNorm = oldDict[self.__wordColumn]
        idx = self.__findIndex(insertedWords, newNorm)
        before = idx - 1
        beforeWord = [newNorm[before] if before >= 0 else '']
        after = idx + insertedWordLen
        afterWord = [newNorm[after] if after < len(newNorm) else '']
        beforeIdx = self.__findIndex(beforeWord, oldNorm)
        afterIdx = self.__findIndex(afterWord, oldNorm)

        if afterIdx != -1:
            contextIdx = afterIdx
            replIdx = afterIdx
        elif beforeIdx != -1:
            contextIdx = beforeIdx
            replIdx = beforeIdx + 1
        else:
            return
        # word
        self.__replaceSlice(oldDict[self.__wordColumn], replIdx, replIdx, insertedWords)
        # case
        newCase = [oldDict['case'][contextIdx]] * insertedWordLen
        self.__replaceSlice(oldDict['case'], replIdx, replIdx, newCase)
        # delim
        newDelim = [''] * insertedWordLen
        self.__replaceSlice(oldDict['delimiter'], replIdx, replIdx, newDelim)
        if self.__normalize:
            # postag
            newPostag = [oldDict['postag'][contextIdx]] * insertedWordLen
            self.__replaceSlice(oldDict['postag'], replIdx, replIdx, newPostag)
            # heuristic
            newHeuristic = [oldDict['heuristic'][contextIdx]] * insertedWordLen
            self.__replaceSlice(oldDict['heuristic'], replIdx, replIdx, newHeuristic)

    def __findIndex(self, words, target):
        iterRange = len(target) - len(words) + 1
        _logger.debug(f'find {words} from {target}')
        for i in range(iterRange):
            if target[i:i+len(words)] == list(words):
                _logger.debug(f'found at {i}')
                return i
        return -1

    def __replaceSlice(self, target, start, end, value):
        target[start:end] = list(value)
