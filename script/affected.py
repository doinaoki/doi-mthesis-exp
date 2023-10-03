import argparse
import os
import itertools
import json
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG

from .Renaming import Renaming
from .RelationType import RelationType

logger = getLogger(__name__)
logger.setLevel(DEBUG)

def createAffectedJson(file_normal_list, file_lemmatized_list):
    affected_num = 0

    for file_normal, file_lemmatized in zip(file_normal_list, file_lemmatized_list):
        try:
            logger.info(f"(Relation) reading result {file_normal} / {file_lemmatized}")
            with open(os.path.join(file_normal, 'unit.json')) as f:
                normal = set()
                all_units = json.load(f)
                for id, units in all_units.items():
                    normal.update((id, d) for d in units.keys())
                
            with open(os.path.join(file_lemmatized, 'unit.json')) as f:
                lemmatized = set()
                all_units = json.load(f)
                for id, units in all_units.items():
                    lemmatized.update((id, d) for d in units.keys())
            
            affected = lemmatized - normal
            logger.debug(f'{affected}')

            # filter affected units
            affected_unit = []
            for id, units in all_units.items():
                for diff, unit in units.items():
                    if (id, diff) in affected:
                        # print(sum(unit['unit'].values(), []))
                        affected_unit.extend(list(itertools.chain.from_iterable(unit['unit'].values())))
            # print(affected_unit)
            with open(os.path.join(file_lemmatized, 'relation_details.json')) as f:
                affected_type = json.load(f)
                for kind, relations in affected_type.items():
                    for type, pairs in relations.items():
                        filtered_pairs = [convert(pair) for pair in pairs if (pair[0] in affected_unit or pair[1] in affected_unit)]
                        relations[type] = filtered_pairs
    
            affected_all = {rtype.name: set() for rtype in list(RelationType)}
            [affected_all[rtype].update(rlist) for d in affected_type.values() for rtype, rlist in d.items()]

            affected_count = {kind: {type: len(pairs) for type, pairs in relations.items()} for kind, relations in affected_type.items()}
            affected_all_count = {rtype: len(rlist) for rtype, rlist in affected_all.items()}

            # write
            with open(os.path.join(file_lemmatized, 'relation_count_affected.json'), 'w') as f:
                json.dump(affected_all_count, f, indent=4, default=default)
            logger.info(f"(Relation) export relation_count_affected.json")

            with open(os.path.join(file_lemmatized, 'relation_count_type_affected.json'), 'w') as f:
                json.dump(affected_count, f, indent=4, default=default)
            logger.info(f"(Relation) export relation_count_type_affected.json")

            with open(os.path.join(file_lemmatized, 'relation_details_affected.json'), 'w') as f:
                json.dump(affected_all, f, indent=4, default=default)
            logger.info(f"(Relation) export relation_details_affected.json")

            with open(os.path.join(file_lemmatized, 'relation_details_type_affected.json'), 'w') as f:
                json.dump(affected_type, f, indent=4, default=default)
            logger.info(f"(Relation) export relation_details_type_affected.json")

            affected_num += len(affected)
            logger.debug(f'{affected}')

        except Exception:
            logger.exception("fatal error occured")

    logger.info(f'total {affected_num} changed units')

def convert(pair):
    return frozenset(Renaming(**r) for r in pair)

def default(item):
    if isinstance(item, set) or isinstance(item, frozenset):
        return list(item)
    elif isinstance(item, Renaming):
        return item.export()
    else:
        raise TypeError


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', action='store_true', help="set debug mode")
    main_args = parser.parse_args()

    root_logger = getLogger()
    handler = StreamHandler()
    handler.setLevel(DEBUG if main_args.d else INFO)
    formatter = Formatter('[%(asctime)s] %(name)s -- %(levelname)s : %(message)s')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(INFO)

    output = os.path.join("output", "v2")
    normal = os.path.join(output, "normal")
    lemmatized = os.path.join(output, "lemmatized")
    project_normal_list = [os.path.join(normal, d) for d in os.listdir(normal)]
    project_lemmatized_list = [os.path.join(lemmatized, d) for d in os.listdir(lemmatized)]

    createAffectedJson(project_normal_list, project_lemmatized_list)
