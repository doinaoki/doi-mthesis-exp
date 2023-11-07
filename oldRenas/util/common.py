import difflib
from ast import literal_eval
from .Name import KgExpanderSplitter, LemmaManager
from logging import getLogger, DEBUG

_logger = getLogger(__name__)
_splitter = KgExpanderSplitter()

def convertRenameType(rt):
    if rt == 'Class':
        return 'ClassName'
    elif rt == 'Method':
        return 'MethodName'
    elif rt == 'Attribute':
        return 'FieldName'
    elif rt == 'Parameter':
        return 'ParameterName'
    elif rt == 'Variable':
        return 'VariableName'

def splitIdentifier(name):
    return _splitter.split(name)

def getPaddingList(elements, length):
    if len(elements) < length:
        last = elements[-1]
        paddingLen = length - len(elements)
        return elements + [last] * paddingLen
    else:
        return elements[:length]

def printDict(dict, *keys):
    result = ""
    for k in keys:
        if k not in dict.keys():
            continue
        result += f'{k}: {dict[k]}, '
    return result