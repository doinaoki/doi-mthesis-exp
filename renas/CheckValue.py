from .util.Rename import Rename
import pandas as pd




#_WORD_INFO = ["name","split","delimiter","case","pattern","heuristic","expanded","postag","normalized"]

oldName = "isSSLClientsAuth"
newName = "isRequireClientSslAuthorize"

_rename = Rename(oldName, True)
_rename.setNewName(newName)

print(f"oldname = {_rename.getOld()}")
print(f"newname = {_rename.getNew()}")
print(f"difference = {_rename.getDiff()}")