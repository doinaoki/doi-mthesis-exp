import argparse
import pandas as pd
import pathlib
from ast import literal_eval
# import nltk
# from nltk.tag import pos_tag
# from nltk.stem import WordNetLemmatizer 
# from nltk.corpus import wordnet
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG, log

from .util.Name import LemmaManager

logger = getLogger(__name__)
logger.setLevel(DEBUG)

# nltk.download('averaged_perceptron_tagger')
# nltk.download('wordnet')

def setLogger():
    root_logger = getLogger()
    handler = StreamHandler()
    handler.setLevel(INFO)
    formatter = Formatter('[%(asctime)s] %(name)s -- %(levelname)s : %(message)s')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(INFO)
    return root_logger

def setArgument():
    parser = argparse.ArgumentParser()
    parser.add_argument('dir', help="path to the directory of exTable.csv (or extable.csv.gz)")
    main_args = parser.parse_args()
    return main_args


if __name__ == '__main__':
    args = setArgument()
    setLogger()

    logger.info("start normalize")
    wnl = LemmaManager()
    csvRoot = pathlib.Path(args.dir)
    csvFile = csvRoot.joinpath('exTable.csv')
    csvGzFile = csvRoot.joinpath('exTable.csv.gz')

    try:
        identifierList = pd.read_csv(csvGzFile)
        identifierList['expanded'] = identifierList['expanded'].map(
            lambda x: literal_eval(x)
        )
    except:
        identifierList = pd.read_csv(csvFile)
        identifierList['expanded'] = identifierList['expanded'].map(lambda x: str(x).split(';'))
        identifierList['heuristic'] = identifierList['heuristic'].map(lambda x: str(x).split(';'))
    
    expanded = identifierList['expanded'].values
    posTagRows = []
    NormalizedRows = []
    for e in expanded:
        posTag = wnl.getPosTags(e)
        normalized = wnl.normalize(e, posTag)
        posTagRows.append(posTag)
        NormalizedRows.append(normalized)
    identifierList['postag'] = pd.Series(posTagRows)
    identifierList['normalized'] = pd.Series(NormalizedRows)
    identifierList.to_csv(csvFile, index=False)
    logger.info("end normalize")

    