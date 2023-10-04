from .util.Rename import Rename
import pandas as pd
from .util.Name import ExpandManager



#_WORD_INFO = ["name","split","delimiter","case","pattern","heuristic","expanded","postag","normalized"]

#oldName = "isSSLClientsAuth"
#newName = "isRequireClientSslAuth"

def setRenameTest(oldName: dict, newName: str):
    _rename = Rename(oldName, True, True)
    _rename.setNewName(newName["name"])
    print(_rename.coRename(oldName))

    print(f"oldname = {_rename.getOld()}")
    print(f"newname = {_rename.getNew()}")
    print(f"difference = {_rename.getDiff()}")

#include 変更前単語省略後(H2), 単複数形変化, change case, 
def oldNameSet1():
    oldName = {}
    oldName["name"] = "isSSLClientsAuth"
    oldName["split"] = ["is", "ssl", "clients", "auth"]
    oldName["expanded"] = ["is", "ssl", "clients", "authorized"]
    oldName["normalized"] = ["be", "ssl", "client", "authorize"]
    oldName["heuristic"] = ["ST", "ST", "ST", "H2"]
    oldName["delimiter"] = ";;;;".split(';')
    oldName["postag"] = ['VBZ', 'NN', 'NNS', 'VBN']
    oldName["case"] = ["LOWER", "UPPER", "TITLE", "TITLE"]
    oldName["pattern"] = ["LCAMEL"]
    return oldName

def newNameSet1():
    newName = {}
    newName["name"] = "IsRequireClientSslAuth"
    newName["split"] = ["is", "require", "clients", "ssl", "auth"]
    newName["expanded"] = ["is", "require", "clients", "ssl", "authorized"]
    newName["normalized"] = ["be", "require", "client", "ssl", "authorize"]
    return newName

#include 変更前単語省略後(H3), change case
def oldNameSet2():
    oldName = {}
    oldName["name"] = "superContext"
    oldName["split"] = ["super", "context"]
    oldName["expanded"] = ["super", "context"]
    oldName["normalized"] = ["super", "context"]
    oldName["heuristic"] = ["ST", "ST"]
    oldName["delimiter"] = ";;".split(';')
    oldName["postag"] = ['NN', 'NN']
    oldName["case"] = ["LOWER", "TITLE"]
    oldName["pattern"] = ["LCAMEL"]
    return oldName

def newNameSet2():
    oldName = {}
    oldName["name"] = "super_ctx"
    oldName["split"] = ["super", "ctx"]
    oldName["expanded"] = ["super", "context"]
    oldName["normalized"] = ["super", "context"]
    oldName["pattern"] = ["SNAKE"]
    return oldName

#include 変更前単語省略後(H1)
def oldNameSet3():
    oldName = {}
    oldName["name"] = "stringBuilderWellSpecial"
    oldName["split"] = ["super", "builder", "well", "special"]
    oldName["expanded"] = ["string","builder", "well", "special"]
    oldName["normalized"] = ["string", "builder", "well", "special"]
    oldName["pattern"] = ["LCAMEL"]
    oldName["delimiter"] = ";;;;".split(';')
    oldName["case"] = ["LOWER", "TITLE", "TITLE", "TITLE"]
    oldName["postag"] = ['NN', 'NN', 'NN', 'JJ']
    oldName["heuristic"] = ["ST", "ST", "ST", "ST"]
    return oldName

def newNameSet3():
    oldName = {}
    oldName["name"] = "sbwSpecial"
    oldName["split"] = ["sbw", "Special"]
    oldName["expanded"] = ["string","builder", "well", "special"]
    oldName["normalized"] = ["string", "builder", "well", "special"]
    oldName["pattern"] = ["LCAMEL"]
    return oldName


#include record.json省略語
def oldNameSet4():
    oldName = {}
    oldName["name"] = "updateTasksStatusPosition"
    oldName["split"] = ["update", "tasks", "status","position"]
    oldName["expanded"] = ["update","tasks", "status", "position"]
    oldName["normalized"] = ["update", "task", "status", "position"]
    oldName["pattern"] = ["LCAMEL"]
    oldName["postag"] = ['NN', 'NNS', 'NN', 'NN']
    oldName["delimiter"] = ";;;;".split(';')
    oldName["case"] = ["LOWER", "TITLE", "TITLE", "TITLE"]
    oldName["heuristic"] = ["ST", "ST", "ST", "ST"]
    return oldName

def newNameSet4():
    oldName = {}
    oldName["name"] = "taskPos"
    oldName["split"] = ["task","pos"]
    oldName["expanded"] = ["task","position"]
    oldName["normalized"] = ["task","position"]
    oldName["pattern"] = ["LCAMEL"]
    return oldName

#include record.json省略語
def oldNameSet5():
    oldName = {}
    oldName["name"] = "itemValue"
    oldName["split"] = ["item", "value"]
    oldName["expanded"] = ["item", "value"]
    oldName["normalized"] = ["item", "value"]
    oldName["pattern"] = ["LCAMEL"]
    oldName["delimiter"] = ";;".split(';')
    oldName["postag"] = ['NN', 'NN']
    oldName["case"] = ["LOWER", "TITLE"]
    oldName["heuristic"] = ["ST", "ST"]
    return oldName

def newNameSet5():
    oldName = {}
    oldName["name"] = "itemsLbl"
    oldName["split"] = ["items","lbl"]
    oldName["expanded"] = ["items","lable"]
    oldName["normalized"] = ["item","label"]
    oldName["pattern"] = ["LCAMEL"]
    return oldName

#include 変更前単語省略後(H1)
def oldNameSet6():
    oldName = {}
    oldName["name"] = "sbwSpecial"
    oldName["split"] = ["sbw", "special"]
    oldName["expanded"] = ["string","builder", "well", "special"]
    oldName["normalized"] = ["string", "builder", "well", "special"]
    oldName["pattern"] = ["LCAMEL"]
    oldName["delimiter"] = ";;;;".split(';')
    oldName["case"] = ["LOWER", "TITLE", "TITLE", "TITLE"]
    oldName["postag"] = ['NN', 'NN', 'NN', 'JJ']
    oldName["heuristic"] = ["H1", "H1", "H1", "ST"]
    return oldName

def newNameSet6():
    oldName = {}
    oldName["name"] = "stringBuilderWellSpecial"
    oldName["split"] = ["string","builder", "well", "special"]
    oldName["expanded"] = ["string","builder", "well", "special"]
    oldName["normalized"] = ["string", "builder", "well", "special"]
    oldName["pattern"] = ["LCAMEL"]
    oldName["delimiter"] = ";;;;".split(';')
    oldName["case"] = ["LOWER", "TITLE", "TITLE", "TITLE"]
    oldName["postag"] = ['NN', 'NN', 'NN', 'JJ']
    oldName["heuristic"] = ["ST", "ST", "ST", "ST"]
    oldName["files"] = "a/a/a"
    return oldName

def oldNameSet7():
    oldName = {}
    oldName["name"] = "apiDao"
    oldName["split"] = ["api", "dao"]
    oldName["expanded"] = ["api","data", "access", "object"]
    oldName["normalized"] = ["api", "data", "access", "object"]
    oldName["pattern"] = ["LCAMEL"]
    oldName["delimiter"] = ";;;;".split(';')
    oldName["case"] = ["LOWER", "TITLE", "TITLE", "TITLE"]
    oldName["postag"] = ['NN', 'NN', 'NN', 'NN']
    oldName["heuristic"] = ["ST", "H1", "H1", "H1"]
    oldName["files"] = "a/a/a"
    return oldName

def newNameSet7():
    oldName = {}
    oldName["name"] = "apiAppDao"
    oldName["split"] = ["api","app", "dao"]
    oldName["expanded"] = ["api","app", "dao"]
    oldName["normalized"] = ["api", "app", "dao"]
    oldName["pattern"] = ["LCAMEL"]
    oldName["delimiter"] = ";;;".split(';')
    oldName["case"] = ["LOWER", "TITLE", "TITLE"]
    oldName["postag"] = ['NN', 'NN', 'JJ']
    oldName["heuristic"] = ["ST", "ST", "ST"]
    oldName["files"] = "a/a/a"
    return oldName

def oldNameSet8():
    oldName = {}
    oldName["name"] = "AppSettings"
    oldName["split"] = ["app", "settings"]
    oldName["expanded"] = ["application","settings"]
    oldName["normalized"] = ["application", "setting"]
    oldName["pattern"] = ["LCAMEL"]
    oldName["delimiter"] = ";;".split(';')
    oldName["case"] = ["LOWER", "TITLE"]
    oldName["postag"] = ['NN', 'NNS']
    oldName["heuristic"] = ["H2", "ST"]
    oldName["files"] = "a/a/a"
    return oldName

def newNameSet8():
    oldName = {}
    oldName["name"] = "ApiApp"
    oldName["split"] = ["api","app"]
    oldName["expanded"] = ["api","application"]
    oldName["normalized"] = ["api", "application"]
    oldName["pattern"] = ["LCAMEL"]
    oldName["delimiter"] = ";;".split(';')
    oldName["case"] = ["LOWER", "TITLE"]
    oldName["postag"] = ['NN', 'NN']
    oldName["heuristic"] = ["ST", "ST"]
    oldName["files"] = "a/a/a"
    return oldName

def oldNameSet9():
    oldName = {}
    oldName["name"] = "fingerprint"
    oldName["split"] = ["fingerprint"]
    oldName["expanded"] = ["fingerprint"]
    oldName["normalized"] = ["fingerprint"]
    oldName["pattern"] = ["LCAMEL"]
    oldName["delimiter"] = ";".split(';')
    oldName["case"] = ["LOWER"]
    oldName["postag"] = ['NN']
    oldName["heuristic"] = ["ST"]
    oldName["files"] = "a/a/a"
    return oldName

def newNameSet9():
    oldName = {}
    oldName["name"] = "fingerprints"
    oldName["split"] = ["fingerprints"]
    oldName["expanded"] = ["fingerprints"]
    oldName["normalized"] = ["fingerprint"]
    oldName["pattern"] = ["LCAMEL"]
    oldName["delimiter"] = ";".split(';')
    oldName["case"] = ["LOWER"]
    oldName["postag"] = ['NNS']
    oldName["heuristic"] = ["ST"]
    oldName["files"] = "a/a/a"
    return oldName

#em = ExpandManager("/Users/doinaoki/Documents/CodeTest/Osumi-OsmAnd/projects/OsmAnd/archives/30681c6f6485fc2314ea4b4e0841942db16ade43/record.json")
#print(em.expand(newNameSet1()["split"], oldNameSet1()))
#setRenameTest(oldNameSet1(), newNameSet1()["name"])
#setRenameTest(oldNameSet2(), newNameSet2()["name"])
#setRenameTest(oldNameSet3(), newNameSet3()["name"])
#setRenameTest(oldNameSet4(), newNameSet4()["name"])
#setRenameTest(oldNameSet5(), newNameSet5()["name"])
#setRenameTest(oldNameSet6(), newNameSet6()["name"])
setRenameTest(oldNameSet7(), newNameSet7())
setRenameTest(oldNameSet8(), newNameSet8())
setRenameTest(oldNameSet9(), newNameSet9())