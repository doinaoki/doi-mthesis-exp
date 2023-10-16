import re
import json
from copy import deepcopy
import pandas as pd

import nltk
from nltk.tag import pos_tag
from nltk.stem import WordNetLemmatizer 
from nltk.corpus import wordnet
from pattern.en import conjugate, pluralize, comparative, superlative
import os

from logging import getLogger, DEBUG, StreamHandler

_logger = getLogger('util.Name')
# _logger.addHandler(StreamHandler())
_logger.setLevel(DEBUG)

class KgExpanderSplitter:
    def __init__(self):
        self.__delimiter = re.compile(r'[\_\$\d]+')
        self.__upper = re.compile(r'([A-Z]+)')
        self.__title = re.compile(r'([A-Z][a-z]+)')
        self.__lower = re.compile(r'([a-z]+)')
        self.__split = re.compile(r'([a-z]+|[A-Z][a-z]+)')
        self.__cache = {}
        pass

    def split(self, name):
        if name in self.__cache.keys():
            return deepcopy(self.__cache[name])        
        result = {'split': [], 'delimiter': [], 'case': [], 'pattern': []}
        preName = self.__remove(name, '<', '>')
        preName = self.__remove(preName, '[', ']')
        if len(preName) == 0:
            return deepcopy(result)

        delimList = list(self.__delimiter.finditer(name))

        self.__addFirstDelim(delimList, result)
        startIdx = 0
        for match in delimList:
            endIdx = match.start()
            self.__splitBigLetter(preName[startIdx:endIdx], match.group(0), result)
            startIdx = match.end()
        self.__splitBigLetter(preName[startIdx:], '', result)        
        self.__setPattern(result)

        self.__cache[name] = result

        return deepcopy(result)

    def __remove(self, name, left, right):
        tmp1 = name.find(left)
        tmp2 = name.rfind(right)
        if tmp1 != -1 and tmp2 != -1:
            return name[:tmp1] + name[tmp2+1:]
        else:
            return name

    def __addFirstDelim(self, delim, result):
        if len(delim) > 0:
            firstDelim = delim[0]
            if firstDelim.start() == 0:
                result['delimiter'].append(firstDelim.group())
            else:
                result['delimiter'].append('')
        else:
            result['delimiter'].append('')            
        return

    def __splitBigLetter(self, letters, lastSep, result):
        split = self.__split.split(letters)
        split = [s for s in split if len(s) > 0]
        for idx, letter in enumerate(split):
            result['split'].append(letter.lower())
            result['case'].append(self.__getCase(letter))
            if idx == len(split) - 1:
                result['delimiter'].append(lastSep)
            else:
                result['delimiter'].append('')
        return

    def __setPattern(self, rename):
        cases = rename['case']
        delims = rename['delimiter']
        if len(cases) == 0:
            return

        case0 = cases[0]
        restCase = cases[1:] if len(cases) > 1 else None
        centerDelim = delims[1:len(delims)-1] if len(delims) > 2 else None

        if restCase == None or all([c == 'TITLE' for c in restCase]):
            if case0 == 'LOWER':
                rename['pattern'].append('LCAMEL')
            elif case0 == 'TITLE':
                rename['pattern'].append('TCAMEL')
        if centerDelim != None and \
            all(['_' in d for d in centerDelim]):
            rename['pattern'].append('SNAKE')

        return

    def __getCase(self, letter):
        if self.__upper.fullmatch(letter):
            return 'UPPER'
        elif self.__title.fullmatch(letter):
            return 'TITLE'
        elif self.__lower.fullmatch(letter):
            return 'LOWER'
        else:
            return 'UNKNOWN'

class CaseManager:
    def __init__(self):
        pass

    def transform(self, words, pattern, cases):
        result = []
        if (('LCAMEL' not in pattern) and ('TCAMEL' not in pattern)):
            if pattern == 'LCAMEL':
                _logger.error(f'pattern is LCAMEL')
                exit(1)
            for w, c in zip(words, cases):
                if c == 'UPPER':
                    result.append(w.upper())
                elif c == 'TITLE':
                    result.append(w.capitalize())
                elif c == 'LOWER':
                    result.append(w.lower())
                else:
                    _logger.error(f'unknown cases {c}: {w}')
                    result.append(w)
        elif 'LCAMEL'in pattern:
            word0 = words[0]
            restWords = words[1:] if len(words) > 1 else []
            result.append(word0.lower())
            result.extend([w.capitalize() for w in restWords])
        elif 'TCAMEL' in pattern:
            result.extend([w.capitalize() for w in words])
        else:
            _logger.error(f'Unexpected pattern: {pattern}')
        return result

class LemmaManager:
    def __init__(self):
        self.__wnl = WordNetLemmatizer()
        self.__tag = PosTagManager()
        self.__loadConjugate()

    def getPosTags(self, words):
        return self.__tag.getPosTags(words)

    def normalize(self, words, posTags):
        result = []
        for w, p in zip(words, posTags):
            simplePos = self.__tag.toSimplePosTag(p)
            if simplePos == '':
                result.append(w)
            else:
                result.append(self.__wnl.lemmatize(w, pos=simplePos))
        return result
    
    def inflect(self, words, posTags):
        return [self.__inflectWord(w, p) for w, p in zip(words, posTags)]
    
    def __inflectWord(self, word, posTag):
        if 'V' in posTag:
            return conjugate(word, posTag, negated=False)
        elif posTag == 'NNS' or posTag == 'NPS':
            return pluralize(word)
        elif posTag == 'JJR' or posTag == 'RBR':
            return comparative(word)
        elif posTag == 'JJS' or posTag == 'RBS':
            return superlative(word)
        else:
            return word
    
    # ライブラリ側にバグがあるため、その回避を行う（雑なやり方）
    # 本来はバグ箇所を直すべきだが手間なので放置
    # https://github.com/clips/pattern/issues/308
    def __loadConjugate(self):
        _logger.info('load conjugate from pattern-en')
        try:
            conjugate('be', 'VBP')
            _logger.info('successfully loaded')
        except:
            _logger.info('load failed, try again')
            self.__loadConjugate()

class PosTagManager:
    def __init__(self):
        pass
    
    # pos_tag([w]) -> [(w, tag),]
    def getPosTags(self, words):
        return [pos_tag([w])[0][1] for w in words]

    def toSimplePosTag(self, tag):
        if tag.startswith('J'):
            return wordnet.ADJ
        elif tag.startswith('V'):
            return wordnet.VERB
        elif tag.startswith('N'):
            return wordnet.NOUN
        elif tag.startswith('R'):
            return wordnet.ADV
        else:
            return ''

class AbbreviationManager:
    def __init__(self, dictPath) -> None:
        with open(dictPath, 'r') as f:
            self.__abbrDict = json.load(f)
        _logger.debug(f'abbrDict {self.__abbrDict}')
        pass

    def abbreviate(self, words, heuristics):
        return [self.__abbreviateWord(w, h) for w, h in zip(words, heuristics)]
    
    def __abbreviateWord(self, word, heuristic):
        if heuristic == 'H1':
            return word[0]
        elif heuristic == 'ST':
            return word
        else:
            if word in self.__abbrDict[heuristic]:
                return self.__abbrDict[heuristic][word]
            else:
                return word
            

class ExpandManager:
    def __init__(self, dictPath) -> None:
        self.__abbrPath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "AbbreviationDataset")
        with open(os.path.join(self.__abbrPath, "EnglishDic.txt"), "r") as f:
            self.__englishSet = set(f.read().split("\n"))
        
        self.__classRecordDict = {}
        with open(os.path.join(os.path.dirname(dictPath), "classRecord.json"), 'r') as f:
            __classRecordJson = json.load(f)
        for className, records in __classRecordJson.items():
            self.__classRecordDict[className] = {}
            temp = {}
            for rec, count in records.items():
                abbr, expan = rec.split("==")
                if abbr in temp:
                    if count > temp[abbr]:
                        temp[abbr] = count
                        self.__classRecordDict[className][abbr] = expan
                else:
                    self.__classRecordDict[className][abbr] = expan
                    

        self.__recordDict = {}
        with open(dictPath, 'r') as f:
            __recordJson = json.load(f)
        for records in __recordJson.values():
            for k, v in records.items():
                if v in self.__recordDict:
                    self.__recordDict[v].append(k)
                else:
                    self.__recordDict[v] = [k]

        self.__expandDict = {}
        self.__skipDict = {}
        self.addAbbrDic()
        self.skipAbbrDic()
        #print(self.__expandDict)
        #print(len(self.__expandDict))
        #print(len(self.__englishSet))
        pass

    def addAbbrDic(self):
        with open(os.path.join(self.__abbrPath, "abbrDic.txt"), "r") as f:
            for abbrData in f:
                abbr, expan = abbrData.split(":=")
                if abbr in self.__expandDict:
                    self.__expandDict[abbr].add(expan.rstrip("\n"))
                else:
                    self.__expandDict[abbr] = {expan.rstrip("\n")}
    
    def skipAbbrDic(self):
        with open(os.path.join(self.__abbrPath, "computerAbbr.txt"), "r") as f:
            for abbrData in f:
                abbr, expan = abbrData.split(":=")
                splitWord = expan.rstrip("\n").split(" ")
                if len(splitWord) >= 3:
                    self.__skipDict[abbr.lower()] = [w.lower for w in splitWord]
    
    #必要だと感じたら実装
    def addAbbrDataset(self, Dict):
        pass


    def expand(self, result, beforeWordDic):
        words = result['split']
        wordsCase = result['case']
        identifier = []
        heuList = []
        newCase = []
        for word in words:
            identifiers, hue = self.expandWord(word, beforeWordDic)                
            if word in self.__skipDict:
                if hue != ["H1"]*len(word):
                    identifiers = [word]
                    hue = ["ST"]
            wc = wordsCase[words.index(word)]
            for i in range(len(identifiers)):
                identifier.append(identifiers[i])
                heuList.append(hue[i])
                newCase.append(wc)
        return identifier, heuList, newCase

    '''
        identifierList = [self.expandWord(word, beforeWordDic) for word in words]
        identifier = []
        for i in identifierList:
            identifier += i
        return identifier
    '''
    def expandWord(self, word, beforeWordDic):
        # 省略後か確認
        if word in self.__englishSet:
            return [word], ["ST"]
        
        #変更前の識別子でも展開されていない場合
        if word in beforeWordDic["expanded"]:
            return [word], ["ST"]

        # 変更前の単語から探す
        w, hue = self.Heuristics(word, beforeWordDic["expanded"])
        if w != [word]:
            return w, hue
        
        #同クラス内から探索 '''

        if beforeWordDic["files"] in self.__classRecordDict:
            if word in self.__classRecordDict[beforeWordDic["files"]]:
                return self.Heuristics(word, self.__classRecordDict[beforeWordDic["files"]][word].split(" "))
        #record.jsonから探す(プロジェクト全体から探索)
        if word in self.__recordDict:
            return self.Heuristics(word, [max(self.__recordDict[word])])

        #省略後のデータセットから探す
        if word in self.__expandDict:
            return self.Heuristics(word, max(list(self.__expandDict[word])).split(" "))

        return [word], ["ST"]
    

    #acronym, prefix, dropped-letterを探索
    def Heuristics(self, word, beforeWords):
        #acromym
        if len(word) != 1 and len(word) <= len(beforeWords):
            for i in range(len(beforeWords)-len(word)+1):
                candidateWords = []
                for j in range(i, len(word)+i):
                    candidateWords.append(beforeWords[j][0])
                
                if "".join(candidateWords) == word:
                    print("acronym", word)
                    return [beforeWords[w] for w in range(i, len(word)+i)], ["H1" for _ in range(len(word))]
        
        #prefix
        candidateWords = []
        for beforeword in beforeWords:
            if beforeword.startswith(word):
                candidateWords.append(beforeword)
        if candidateWords != []:
            print("prefix", max(candidateWords))
            return [max(candidateWords)], ["H2"]
        
        #dropped-letter
        for beforeword in beforeWords:
            if beforeword[0] != word[0]:
                continue
            j = 0
            for i in range(len(beforeword)):
                if j < len(word) and word[j] == beforeword[i]:
                    j += 1
            
            if j == len(word):
                print("dropped-letter", word)
                return [beforeword], ["H3"]
        
        return [word], ["ST"]
