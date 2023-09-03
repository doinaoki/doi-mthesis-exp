from .util.Rename import Rename
import pandas as pd
from .util.Name import ExpandManager



#_WORD_INFO = ["name","split","delimiter","case","pattern","heuristic","expanded","postag","normalized"]

#oldName = "isSSLClientsAuth"
#newName = "isRequireClientSslAuth"

def setRenameTest(oldName: dict, newName: str):
    _rename = Rename(oldName, True)
    _rename.setNewName(newName)

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
    oldName["name"] = "stringBuilderSpecial"
    oldName["split"] = ["super", "builder", "special"]
    oldName["expanded"] = ["string","builder", "special"]
    oldName["normalized"] = ["string", "builder", "special"]
    oldName["pattern"] = ["LCAMEL"]
    oldName["heuristic"] = ["ST", "ST", "ST"]
    return oldName

def newNameSet3():
    oldName = {}
    oldName["name"] = "sbSpecial"
    oldName["split"] = ["sb", "Special"]
    oldName["expanded"] = ["string","builder", "special"]
    oldName["normalized"] = ["string", "builder", "special"]
    oldName["pattern"] = ["LCAMEL"]
    return oldName


#include record.json省略語
def oldNameSet4():
    oldName = {}
    oldName["name"] = "updateTaskStatus"
    oldName["split"] = ["update", "task", "status"]
    oldName["expanded"] = ["update","task", "status"]
    oldName["normalized"] = ["update", "task", "status"]
    oldName["pattern"] = ["LCAMEL"]
    oldName["heuristic"] = ["ST", "ST", "ST"]
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

#em = ExpandManager("/Users/doinaoki/Documents/CodeTest/Osumi-OsmAnd/projects/OsmAnd/archives/30681c6f6485fc2314ea4b4e0841942db16ade43/record.json")
#print(em.expand(newNameSet1()["split"], oldNameSet1()))
#setRenameTest(oldNameSet1(), newNameSet1()["name"])
#setRenameTest(oldNameSet2(), newNameSet2()["name"])
#setRenameTest(oldNameSet3(), newNameSet3()["name"])
#setRenameTest(oldNameSet4(), newNameSet4()["name"])
#setRenameTest(oldNameSet5(), newNameSet5()["name"])