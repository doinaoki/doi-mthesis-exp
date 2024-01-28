import difflib
from copy import deepcopy
from ast import literal_eval
from .Name import KgExpanderSplitter, LemmaManager, AbbreviationManager, CaseManager, ExpandManager
from .common import getPaddingList, printDict, splitIdentifier
from logging import getLogger, DEBUG
from itertools import zip_longest
import pandas as pd
import math
import os

_lemmatizer = LemmaManager()
_abbrManager = None
_caseManager = CaseManager()
_expandManager = None
_logger = getLogger('util.Rename')
_logger.setLevel(DEBUG)
#_abbrManager = AbbreviationManager("/Users/doinaoki/Documents/GitHub/doi-mthesis-exp/projects/open-keychain/archives/a8782272b3db20ba6e88acab1d035d4699aa7166/record.json")
#_expandManager = ExpandManager("/Users/doinaoki/Documents/GitHub/doi-mthesis-exp/projects/open-keychain/archives/a8782272b3db20ba6e88acab1d035d4699aa7166/record.json")
def setAbbrDic(abbrDicPath):
    global _abbrManager, _expandManager
    _abbrManager = AbbreviationManager(abbrDicPath)
    _expandManager = ExpandManager(abbrDicPath)
    _logger.info('set abbrDic record')

# 命名規則の変化（POSタグ？、省略、Case、区切り文字）は扱いません。
class Rename:
    def __init__(self, old, normalize, all=False):
        self.__normalize = normalize
        self.__all = all
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
    
    def getOp(self):
        return [self.__old["files"]+str(self.__old["line"])+self.__old["name"], self.getDiff()]

    def debugOperation(self, oldName, newName):
        global _abbrManager, _expandManager
        _abbrManager = AbbreviationManager("/Users/doinaoki/Documents/GitHub/doi-mthesis-exp/projects/open-keychain/archives/a8782272b3db20ba6e88acab1d035d4699aa7166/record.json")
        _expandManager = ExpandManager("/Users/doinaoki/Documents/GitHub/doi-mthesis-exp/projects/open-keychain/archives/a8782272b3db20ba6e88acab1d035d4699aa7166/record.json")
        self.__all = True
        self.setNewName(newName["name"])
        return self.coRename(oldName)

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
        beforeCaseList = deepcopy(idDict["pattern"])
        # apply diff
        for diff in self.__diff:
            self.__applyDiff(diff, idDict)
        if idDict[self.__wordColumn] == beforeWordList and beforeCaseList == idDict["pattern"]:
            _logger.debug(f'not a candidate')
            return None
        _logger.debug(f'AFTER {printDict(idDict, "case", "pattern", "delimiter", "heuristic", "postag", self.__wordColumn)}')
        #類似度を測る
        idDict["similarity"] = self.wordSimilarity(beforeWordList)
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
        idDict["diffLine"] = abs(idDict["line"] - self.__old["line"])
        #idDict["sameFile"] = 1 if idDict["files"] == self.__old["files"] else 2
        idDict["sameFile"] = self.calculateFileDistance(idDict["files"], self.__old["files"])
        return idDict

    def calculateFileDistance(self, recFile, trigFile):
        recFileLength = len(recFile.split('/'))
        trigFileLength = len(trigFile.split('/'))
        #print(recFile, trigFile)

        try:
            common = os.path.commonpath([recFile, trigFile])
            commonFileLength = len(common.split('/'))
            #print(commonFileLength)
            return recFileLength + trigFileLength - 2*commonFileLength
        except:
            print("something wrong")
            return recFileLength + trigFileLength

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

        if self.__all:
            result["expanded"], result["heuristic"], result["case"] = _expandManager.expand(result, self.__old)
            postags = _lemmatizer.getPosTags(result["expanded"])
            result['postag'] = postags
            result['normalized'] = _lemmatizer.normalize(result["expanded"], postags)
        elif self.__normalize:
            postags = _lemmatizer.getPosTags(words)
            result['postag'] = postags
            result['normalized'] = _lemmatizer.normalize(words, postags)
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
            oldSplit = self.__old["normalized"]
            self.__diff = []
        
            if self.__all == True:
                #self.__diff += self.extractChangeCase()
                self.__diff += self.extractOrder()
                self.__diff += self.extractFormat()
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

    def wordSimilarity(self, recommendName):
        oldName = self.__old["normalized"]
        similarity = len(set(oldName) & set(recommendName)) * 2 / (len(oldName) + len(recommendName))
        
        return 1 - similarity

    #変更操作format抽出
    def extractFormat(self):
        oldNormalize = self.__old[self.__wordColumn]
        newNormalize = self.__new[self.__wordColumn]
        #print(self.__old)
        oldExpanded = self.__old["expanded"]
        newExpanded = self.__new["expanded"]
        oldSplit = self.__old["split"]
        newSplit = self.__new["split"]

        equalSplitWords = set(oldSplit)&set(newSplit)
        equalExpandedWords = set(oldExpanded)&set(newExpanded)
        equalNormalizeWords = set(oldNormalize)&set(newNormalize)
        equalExpandedWordsIndex = [oldExpanded.index(word) for word in equalExpandedWords]

        abbrCandidate = equalExpandedWords-equalSplitWords
        abbrCandidate = [i for i in oldExpanded if i in abbrCandidate]
        formatAbbreviation = []
        heuH1 = ["Abbreviation", "H1", []]
        for word in abbrCandidate:
            print(f"AbbrCandidate = {word}")
            oldHeu = self.__old["heuristic"][oldExpanded.index(word)]
            newHeu = self.__new["heuristic"][newExpanded.index(word)]
            if oldHeu == newHeu:
                continue
            elif oldHeu == "H1":
                heuH1[2].append((word[0], word))
            elif newHeu == "H1":
                heuH1[2].append((word, word[0]))
            elif oldHeu == "H2" or newHeu == "H2":
                formatAbbreviation.append(["format", ("Abbreviation", "H2", oldSplit[oldExpanded.index(word)], newSplit[newExpanded.index(word)])])
            else:
                formatAbbreviation.append(["format", ("Abbreviation", "H3", oldSplit[oldExpanded.index(word)], newSplit[newExpanded.index(word)])])

        #formatAbbreviation = [["format", word, ("Abbreviation", oldSplit[oldExpanded.index(word)], newSplit[newExpanded.index(word)])] for word in equalExpandedWords-equalSplitWords if oldExpanded.index(word) not in equalSplitWordsIndex]
        formatConjugate = []
        formatPlural = []
        for word in equalNormalizeWords-equalExpandedWords :
            if oldNormalize.index(word) not in equalExpandedWordsIndex:
                oldIndex = oldNormalize.index(word)
                newIndex = newNormalize.index(word)
                if "V" in self.__old["postag"][oldIndex]:
                    formatConjugate.append(["format", ("Conjugate", oldExpanded[oldIndex], newExpanded[newIndex])])
                else:
                    formatPlural.append(["format", ("Plural", oldExpanded[oldIndex], newExpanded[newIndex])])

        #formatNormalize = [["format", ("Normalize", oldExpanded[oldNormalize.index(word)], newExpanded[newNormalize.index(word)])] for word in equalNormalizeWords-equalExpandedWords if oldNormalize.index(word) not in equalExpandedWordsIndex]
        heuH1 = [["format", heuH1]] if heuH1[2] != [] else []
        _logger.debug(formatAbbreviation + formatConjugate + formatPlural)
        return formatAbbreviation + formatConjugate + formatPlural + heuH1
        
    #変更操作changeCase抽出
    def extractChangeCase(self):
        exChangeCase = []
        if self.__new["pattern"] == [] or self.__old["pattern"] == []:
            oldNormalized = self.__old["normalized"]
            newNormalized = self.__new["normalized"]
            commonWord = set(oldNormalized) & set(newNormalized)
            for word in commonWord:
                oldIndex = oldNormalized.index(word)
                oldCase = self.__old["case"][oldIndex]
                newIndex = newNormalized.index(word)
                newCase = self.__new["case"][newIndex]
                if oldCase != newCase:
                    exChangeCase.append(["changeCase", (word, newCase)])
            return exChangeCase
        elif self.__old["pattern"] != self.__new["pattern"]:   
            exChangeCase.append(["changePattern", (self.__old["normalized"][0], self.__new["pattern"])])
            return exChangeCase
        return exChangeCase

    #変更操作order抽出
    def extractOrder(self):
        oldNormalize = self.__old[self.__wordColumn]
        newNormalize = self.__new[self.__wordColumn]
        equalNormalizeWords = set(oldNormalize)&set(newNormalize)
        self.__old["ordered"] = oldNormalize
        if len(equalNormalizeWords) > 1:
            oldWordsOrder = [word for word in oldNormalize if word in equalNormalizeWords]
            newWordsOrder = [word for word in newNormalize if word in equalNormalizeWords]
            """
            oldOrder = []
            newOrder = []
            for index in range(len(oldWordsOrder)):
                if oldWordsOrder[index] != newWordsOrder[index]:
                    oldOrder.append(oldWordsOrder[index])
                    newOrder.append(newWordsOrder[index])
            """
            if not self.__checkUnique(oldWordsOrder):
                return [] 
            if not self.__checkUnique(newWordsOrder):
                return []
            if len(oldWordsOrder) > 1 and oldWordsOrder != newWordsOrder:
                order = ["order", (oldWordsOrder, newWordsOrder)]
                self.__old["ordered"] = [word if word not in oldWordsOrder else newWordsOrder[oldWordsOrder.index(word)] for word in oldNormalize ]
                _logger.debug(order)
                print(f"extractOrder: {order}")
                return [order]
            return []

        return []
    
    def __checkUnique(self, wordList):
        if len(wordList) != len(set(wordList)):
            return False
        return True

#todo 適用方法変更
    def __applyDiff(self, diff, oldDict):
        dType, *dWords = diff
        if dType == 'format':
            self.__applyFormat(oldDict, diff[1])
        elif dType == 'order':
            self.__applyOrder(oldDict, diff[1])
        elif dType == 'changeCase':
            self.__applyChangeCase(oldDict, diff[1])
        elif dType == 'changePattern':
            self.__applyChangePattern(oldDict, diff[1])
        elif dType == 'delete':
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

    def __applyChangeCase(self, oldDict, changeCase):
        changeWord = changeCase[0]
        newCase = changeCase[1]
        for i in range(len(oldDict["normalized"])):
            word = oldDict["normalized"][i]
            if word == changeWord and oldDict["case"][i] != newCase:
                oldDict["case"][i] = newCase
                oldDict["pattern"].append("change")
        return
    

    def __applyChangePattern(self, oldDict, changePattern):
        '''
        changeWord = changePattern[0]
        newPattern = changePattern[1]

        if changeWord in oldDict["normalized"] and oldDict["pattern"] != newPattern:
            oldDict["pattern"] = newPattern
        '''

        return


    def __applyFormat(self, oldDict, format):
        operation = format[0]
        #省略語の展開はする
        #省略語にする操作の適用は考え中
        if operation == "Abbreviation":
            heu = format[1]
            if heu  == "H1":
                ops = format[2]
                toAbbr = []
                toExpan = []
                for op in ops:
                    old = op[0]
                    new = op[1]
                    if len(old) == 1:
                        toExpan.append([old, new])
                    else:
                        toAbbr.append([old, new])
                if len(toExpan) >= 2:
                    n = len(toExpan)
                    newExpan = []
                    for i in range(2**n):
                        exWord = ["",""]
                        for k in range(n):
                            if ((i >> k) & 1):
                                exWord = [exWord[0]+toExpan[k][0], exWord[1]+toExpan[k][1]]
                        if exWord != ["",""]:
                            newExpan.append(exWord)
                    toExpan = newExpan

                #Expan
                for i in toExpan:
                    #this if statement is unnecessary
                    if i[0] in oldDict["normalized"]:
                        id = oldDict["normalized"].index(i[0])
                        oldDict["normalized"][id] = i[1]
                        oldDict["heuristic"][id] = "ST"
                    elif i[1] in oldDict["normalized"]:
                        id = oldDict["normalized"].index(i[1])
                        oldDict["heuristic"][id] = "ST"
                for i in toAbbr:
                    if i[0] in oldDict["normalized"]:
                        id = oldDict["normalized"].index(i[0])
                        oldDict["normalized"][id] = i[1]
                        oldDict["heuristic"][id] = "ST"
                        oldDict["postag"][id] = "NN"
                        oldDict["pattern"] = []

            elif heu == "H2":
                oldWord = format[2]
                newWord = format[3]
                if len(oldWord) < len(newWord):
                    if oldWord in oldDict["split"]:
                        id = oldDict["split"].index(oldWord)
                        oldDict["normalized"][id] = newWord
                        oldDict["heuristic"][id] = "ST"
                        print("Expand2")
                    '''
                    if newWord in oldDict["normalized"]:
                        id = oldDict["normalized"].index(newWord)
                        oldDict["heuristic"][id] = "ST"
                    return
                    '''
                else:
                    ##H2の省略語作成実装
                    if oldWord in oldDict["split"]:
                        id = oldDict["split"].index(oldWord)
                        oldDict["normalized"][id] = newWord
                        oldDict["heuristic"][id] = "ST"
                        oldDict["postag"][id] = "NN"
                    print("Abbreviation2")
                    return
            elif heu == "H3":
                oldWord = format[2]
                newWord = format[3]
                if len(oldWord) < len(newWord):
                    if oldWord in oldDict["split"]:
                        id = oldDict["split"].index(oldWord)
                        oldDict["normalized"][id] = newWord
                        oldDict["heuristic"][id] = "ST"
                    '''
                    if newWord in oldDict["normalized"]:
                        id = oldDict["normalized"].index(newWord)
                        oldDict["heuristic"][id] = "ST"
                    return
                    '''
                else:
                    ##H3の省略語作成実装
                    if oldWord in oldDict["split"]:
                        id = oldDict["split"].index(oldWord)
                        oldDict["normalized"][id] = newWord
                        oldDict["heuristic"][id] = "ST"
                        oldDict["postag"][id] = "NN"
                    print("Abbreviation3")
                    return
        elif operation == "Conjugate" or operation == "Plural":
            oldWord = format[1]
            newWord = format[2]
            #ToDo: newwordが既に含まれていた場合returnを返す
            if oldWord in oldDict["expanded"]:
                id = oldDict["expanded"].index(oldWord)
                oldDict["postag"][id] = "NN"
                #仮
                oldDict["normalized"][id] = newWord
            '''
            elif oldWord in oldDict["expanded"]:
                id = oldDict["expanded"].index(oldWord)
                oldDict["postag"][id] = "NN"
                oldDict["normalized"][id] = newWord
            return
            '''
        else:
            _logger.error("undefined format operation")
# Todo same word handling
    def __applyOrder(self, oldDict, order):
        oldWords = deepcopy(oldDict["normalized"])
        oldOrder = order[0]
        newOrder = order[1]
        useOrderWords = []
        #print(oldWords)
        for w in oldWords:
            if w in oldOrder:
                useOrderWords.append(w)
        if len(useOrderWords) <= 1:
            return

        #仮実装
        if len(useOrderWords) != len(set(useOrderWords)):
            return
        
        orderedWords = []
        newHeu = []
        newPostag = []
        for w in newOrder:
            if w in useOrderWords:
                orderedWords.append(w)
                oldId = oldWords.index(w)
                newHeu.append(oldDict["heuristic"][oldId])
                newPostag.append(oldDict["postag"][oldId])
        if useOrderWords == orderedWords:
            return
        for i in range(len(useOrderWords)):
            oldId = oldWords.index(useOrderWords[i])
            oldDict["normalized"][oldId] = orderedWords[i]
            oldDict["heuristic"][oldId] = newHeu[i]
            oldDict["postag"][oldId] = newPostag[i]
            #print(f"{oldId}, {orderedWords[i]}, {newHeu[i]}, {newPostag[i]}")
                

        return


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
    '''
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
            #newPostag = [oldDict['postag'][contextIdx]] * insertedWordLen
            newPostag = ["NN"] * insertedWordLen
            self.__replaceSlice(oldDict['postag'], replIdx, replIdx, newPostag)
            # heuristic
            newHeuristic = [oldDict['heuristic'][contextIdx]] * insertedWordLen
            self.__replaceSlice(oldDict['heuristic'], replIdx, replIdx, newHeuristic)
    '''
# new Insert
    def __applyInsert(self, oldDict, insertedWords):
        _logger.debug(f'insert {insertedWords}')
        insertedWordLen = len(insertedWords)
        newNorm = self.__new[self.__wordColumn]
        oldNorm = oldDict[self.__wordColumn]
        edge = False
        idx = self.__findIndex(insertedWords, newNorm)
        before = idx - 1
        beforeWord = [newNorm[before] if before >= 0 else '']
        after = idx + insertedWordLen
        afterWord = [newNorm[after] if after < len(newNorm) else '']
        if beforeWord == [''] or afterWord == ['']:
            edge = True
        beforeIdx = self.__findIndex(beforeWord, oldNorm)
        afterIdx = self.__findIndex(afterWord, oldNorm)

        #真ん中
        if afterIdx != -1 and beforeIdx != -1 and beforeIdx + 1 == afterIdx:
            contextIdx = afterIdx
            replIdx = afterIdx
        #左端
        elif edge and afterIdx != -1:
            contextIdx = afterIdx
            replIdx = afterIdx
        #右端
        elif edge and beforeIdx != -1:
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
            newPostag = ["NN"] * insertedWordLen
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
