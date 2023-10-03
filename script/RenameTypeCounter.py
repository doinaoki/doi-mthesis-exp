# 意図毎のカウント
# 一つの識別子に複数の意図がある場合(単語の挿入と単語の置換が同時に起きるなど)，全てカウント
import numpy as np
import pandas as pd

class RenameTypeCounter:
    def __init__(self):
        self._mapping = {"insert":0, "delete":1, "replace":2, "other":3, "inflect":4}
        return

    # unit_series; data_by_commit["units"]
    def countAll(self, unit_series):
        count_by_unit = self.countByUnitSize(unit_series)
        return pd.DataFrame(count_by_unit.mul(count_by_unit.index, axis=0).sum()).T

    # unit_series; data_by_commit["units"]
    # {(diff_type): [{rename1}, ...]}
    def countByUnitSize(self, units_series):
        unit_count = {}
        for units in list(units_series):
            for diff, rlist in [list(*unit.items()) for unit in units]:
                # diff: (rename_type, infomations) 変更意図
                # rlist: Unit ユニットに含まれる名前変更の一覧
                rename_type = diff[0]
                unit_size = rlist.getAllSize()
                if unit_size in unit_count.keys():
                    unit_count[unit_size][self._mapping[rename_type]] += 1
                else:
                    rename_type_array = np.eye(5)[self._mapping[rename_type]]
                    unit_count[unit_size] = rename_type_array 
        return pd.DataFrame(unit_count.values(), index=unit_count.keys(), columns=self._mapping.keys()).sort_index()