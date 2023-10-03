from lxml import etree
import itertools
import collections
import gc
from .RelationType import RelationType
class Unit:
    def __init__(self) -> None:
        self.namespaces = {"src": "http://www.srcML.org/srcML/src"}
        self._relation_list = {rtype: set() for rtype in list(RelationType)}
        self._all_size = 0
        # self._unit = collections.deque()
        self._unit = {"Class": set(), "Method": set(), "Attribute": set(), "Parameter": set(), "Variable": set()}
        return

    def add(self, renaming):
        # Unit全体の数。重複も含むため、 _unit の要素数の合計とは異なることもある。
        self._unit[renaming.type].add(renaming)
        self._all_size += 1
        return

    def getAllSize(self):
        return self._all_size
    
    def getIncludedTypes(self):
        return [t for t, r in self._unit.items() if len(r) > 0]

    def analyze(self):
        self._createPathToRoot()
        self._belongsC()
        self._belongsM()
        self._belongsF()
        self._belongsA()
        self._belongsL()
        self._coOccursM()
        self._extends()
        self._implements()
        self._typeM()
        self._typeV()
        self._invokes()
        self._accesses()
        self._assigns()
        self._passes()
        del self._unit, self._path_to_root
        # type debug
        # debugType = RelationType.Invokes
        # if self._relation_list[debugType]: print(self._relation_list[debugType])
        return self._relation_list

    def _createPathToRoot(self):
        self._path_to_root = {r.xmlpath: etree.parse(r.xmlpath, parser=etree.XMLParser(huge_tree=True)).getroot() for renamings in self._unit.values() for r in renamings}
        return

    def _belongsC(self):
        pairs = itertools.combinations(self._unit["Class"], 2)
        for pair in pairs:
            if pair[0].xmlpath != pair[1].xmlpath: continue
            path = pair[0].xmlpath
            root = self._path_to_root[path]
            c1_name = pair[0].oldname
            c2_name = pair[1].oldname
            query_1 = f'//src:class[./src:name[text()="{c1_name}"]]//src:class[./src:name[text()="{c2_name}"]]'
            query_2 = f'//src:class[./src:name[text()="{c2_name}"]]//src:class[./src:name[text()="{c1_name}"]]'
            nodes = root.xpath(query_1, namespaces=self.namespaces) + root.xpath(query_2, namespaces=self.namespaces)
            if len(nodes) > 0:
                self._relation_list[RelationType.BelongsC].add(frozenset(pair))
        return
    
    def _belongsM(self):
        pairs = itertools.product(self._unit["Class"], self._unit["Method"])
        for pair in pairs:
            if pair[0].xmlpath != pair[1].xmlpath: continue
            path = pair[0].xmlpath
            root = self._path_to_root[path]
            class_name = pair[0].oldname
            method_name = pair[1].oldname
            nodes = root.xpath(f'//src:class[./src:name[text()="{class_name}"]]/src:block/src:function[./src:name[text()="{method_name}"]]', namespaces=self.namespaces)
            if len(nodes) > 0:
                self._relation_list[RelationType.BelongsM].add(frozenset(pair))
        return

    def _belongsF(self):
        pairs = itertools.product(self._unit["Class"], self._unit["Attribute"])
        for pair in pairs:
            if pair[0].xmlpath != pair[1].xmlpath: continue
            path = pair[0].xmlpath
            root = self._path_to_root[path]
            class_name = pair[0].oldname
            field_name = pair[1].oldname
            nodes = root.xpath(f'//src:class[./src:name[text()="{class_name}"]]/src:block/src:decl_stmt/src:decl[./src:name[text()="{field_name}"]]', namespaces=self.namespaces)
            if len(nodes) > 0:
                self._relation_list[RelationType.BelongsF].add(frozenset(pair))
        return

    def _belongsA(self):
        pairs = itertools.product(self._unit["Method"], self._unit["Parameter"])
        for pair in pairs:
            if pair[0].xmlpath != pair[1].xmlpath: continue
            path = pair[0].xmlpath
            root = self._path_to_root[path]
            method_name = pair[0].oldname
            parameter_name = pair[1].oldname
            nodes = root.xpath(f'//src:function[./src:name[text()="{method_name}"]]/src:parameter_list//src:decl[./src:name[text()="{parameter_name}"]]', namespaces=self.namespaces)
            if len(nodes) > 0:
                self._relation_list[RelationType.BelongsA].add(frozenset(pair))
        return

    def _belongsL(self):
        pairs = itertools.product(self._unit["Method"], self._unit["Variable"])
        for pair in pairs:
            if pair[0].xmlpath != pair[1].xmlpath: continue
            path = pair[0].xmlpath
            root = self._path_to_root[path]
            method_name = pair[0].oldname
            variable_name = pair[1].oldname
            nodes = root.xpath(f'//src:function[./src:name[text()="{method_name}"]]/src:block/src:block_content//src:decl_stmt/src:decl[./src:name[text()="{variable_name}"]]', namespaces=self.namespaces)
            # src:classを除く処理を間に挟む必要があるかもしれない
            if len(nodes) > 0:
                self._relation_list[RelationType.BelongsL].add(frozenset(pair))
        return

    def _coOccursM(self):
        pairs = itertools.combinations(self._unit["Method"], 2)
        for pair in pairs:
            if pair[0].xmlpath != pair[1].xmlpath: continue
            path = pair[0].xmlpath
            root = self._path_to_root[path]
            m1_name = pair[0].oldname
            m2_name = pair[1].oldname
            nodes = root.xpath(f'//src:function[./src:name[text()="{m1_name}"] and ../src:function/src:name[text()="{m2_name}"]]', namespaces=self.namespaces)
            if len(nodes) > 0:
                self._relation_list[RelationType.CoOccursM].add(frozenset(pair))
        return

    def _extends(self):
        pairs = itertools.combinations(self._unit["Class"], 2)
        for pair in pairs:
            path_c1 = pair[0].xmlpath
            path_c2 = pair[1].xmlpath
            c1_name = pair[0].oldname
            c2_name = pair[1].oldname
            c1_root = self._path_to_root[path_c1]
            c2_root = self._path_to_root[path_c2]
            # c1 extends c2
            query_1 = f'//src:class[./src:name[text()="{c1_name}"] and ./src:super_list/src:extends//src:name[text()="{c2_name}"]]'
            # c2 extends c1
            query_2 = f'//src:class[./src:name[text()="{c2_name}"] and ./src:super_list/src:extends//src:name[text()="{c1_name}"]]'
            nodes = c1_root.xpath(query_1, namespaces=self.namespaces) + c2_root.xpath(query_2, namespaces=self.namespaces)
            if len(nodes) > 0:
                self._relation_list[RelationType.Extends].add(frozenset(pair))
        return

    def _implements(self):
        pairs = itertools.combinations(self._unit["Class"], 2)
        for pair in pairs:
            path_c1 = pair[0].xmlpath
            path_c2 = pair[1].xmlpath
            c1_name = pair[0].oldname
            c2_name = pair[1].oldname
            c1_root = self._path_to_root[path_c1]
            c2_root = self._path_to_root[path_c2]
            # c1 implements c2
            query_1 = f'//src:class[./src:name[text()="{c1_name}"] and ./src:super_list/src:implements//src:name[text()="{c2_name}"]]'
            # c2 implements c1
            query_2 = f'//src:class[./src:name[text()="{c2_name}"] and ./src:super_list/src:implements//src:name[text()="{c1_name}"]]'
            nodes = c1_root.xpath(query_1, namespaces=self.namespaces) + c2_root.xpath(query_2, namespaces=self.namespaces)
            if len(nodes) > 0:
                self._relation_list[RelationType.Implements].add(frozenset(pair))
        return

    def _typeM(self):
        # class <-> method
        pairs = itertools.product(self._unit["Class"], self._unit["Method"])
        for pair in pairs:
            path = pair[1].xmlpath # method
            root = self._path_to_root[path]
            class_name = pair[0].oldname
            method_name = pair[1].oldname
            nodes = root.xpath(f'//src:function[./src:type//src:name[text()="{class_name}"] and ./src:name[text()="{method_name}"]]', namespaces=self.namespaces)
            # src:classを除く処理を間に挟む必要があるかもしれない
            if len(nodes) > 0:
                self._relation_list[RelationType.TypeM].add(frozenset(pair))
        return

    def _typeV(self):
        # class <-> attribute, variable
        instances = self._unit["Attribute"] | self._unit["Variable"]
        pairs = itertools.product(self._unit["Class"], instances)
        for pair in pairs:
            path = pair[1].xmlpath
            root = self._path_to_root[path]
            class_name = pair[0].oldname
            instance_name = pair[1].oldname
            nodes = root.xpath(f'//src:decl_stmt/src:decl[./src:type/src:name[text()="{class_name}"] and ./src:name[text()="{instance_name}"]]', namespaces=self.namespaces)
            if len(nodes) > 0:
                self._relation_list[RelationType.TypeV].add(frozenset(pair))
        # class <-> parameter
        pairs = itertools.product(self._unit["Class"], self._unit["Parameter"])
        for pair in pairs:
            path = pair[1].xmlpath
            root = self._path_to_root[path]
            class_name = pair[0].oldname
            parameter_name = pair[1].oldname
            nodes = root.xpath(f'//src:function/src:parameter_list//src:decl[./src:type/src:name[text()="{class_name}"] and ./src:name[text()="{parameter_name}"]]', namespaces=self.namespaces)
            if len(nodes) > 0:
                self._relation_list[RelationType.TypeV].add(frozenset(pair))
        return

    def _invokes(self):
        pairs = itertools.combinations(self._unit["Method"], 2)
        for pair in pairs:
            method_name1 = pair[0].oldname
            method_name2 = pair[1].oldname
            if method_name1 == method_name2: continue
            nodes = set()
            path_m1 = pair[0].xmlpath
            path_m2 = pair[1].xmlpath
            # m1 invokes m2
            root_m1 = self._path_to_root[path_m1]
            m1_nodes = root_m1.xpath(f'//src:function[./src:name[text()="{method_name1}"]]//src:call/src:name/descendant-or-self::src:name[last()][text()="{method_name2}"]', namespaces=self.namespaces)
            m1_class_nodes = root_m1.xpath(f'//src:function[./src:name[text()="{method_name1}"]]//src:class//src:call/src:name/descendant-or-self::src:name[last()][text()="{method_name2}"]', namespaces=self.namespaces)
            nodes |= set(m1_nodes) - set(m1_class_nodes)
            # m2 invokes m1
            root_m2 = self._path_to_root[path_m2]
            m2_nodes = root_m2.xpath(f'//src:function[./src:name[text()="{method_name2}"]]//src:call/src:name/descendant-or-self::src:name[last()][text()="{method_name1}"]', namespaces=self.namespaces)
            m2_class_nodes = root_m2.xpath(f'//src:function[./src:name[text()="{method_name2}"]]//src:class//src:call//src:name/descendant-or-self::src:name[text()="{method_name1}"]', namespaces=self.namespaces)
            nodes |= set(m2_nodes) - set(m2_class_nodes)
            if len(nodes) > 0:
                self._relation_list[RelationType.Invokes].add(frozenset(pair))
        return
            
    def _accesses(self):
        pairs = itertools.product(self._unit["Method"], self._unit["Attribute"])
        # pairs = itertools.product(self._unit["Method"], self._unit["Variable"])
        for pair in pairs:
            if pair[0].xmlpath != pair[1].xmlpath: continue
            path = pair[0].xmlpath # method
            root = self._path_to_root[path]
            method_name = pair[0].oldname
            attribute_name = pair[1].oldname
            nodes = root.xpath(f'//src:function[./src:name[text()="{method_name}"]]/src:block//src:name[text()="{attribute_name}" and not(parent::src:call)]', namespaces=self.namespaces)
            # src:classを除く処理を間に挟む必要があるかもしれない
            if len(nodes) > 0:
                self._relation_list[RelationType.Accesses].add(frozenset(pair))
        return

    def _assigns(self):
        leftsides = self._unit["Attribute"] | self._unit["Variable"]
        rightsides = self._unit["Attribute"] | self._unit["Variable"] | self._unit["Parameter"] | self._unit["Method"]
        pairs = itertools.product(leftsides, rightsides)
        for pair in pairs:
            if pair[0] == pair[1]: continue
            if pair[1].type in ['Parameter', 'Variable'] and pair[0].javapath != pair[1].javapath: continue # 右辺値
            path = pair[0].xmlpath
            root = self._path_to_root[path]
            left_name = pair[0].oldname
            right_name = pair[1].oldname
            nodes = []
            # 変数宣言で初期値を代入する場合 root1のみで十分
            query_1 = f'//src:decl/src:name[text()="{left_name}" and ./following-sibling::src:init/src:expr//src:name[text()="{right_name}"]]'
            nodes += root.xpath(query_1, namespaces=self.namespaces)
            # 上以外の代入、外れることが多い気がするので条件を色々つけるかなくしてしまったほうが良さそう
            query_2 = f'//src:expr[not(parent::src:condition)]/src:operator[./preceding-sibling::*/descendant-or-self::src:name[text()="{left_name}"] and ./following-sibling::*/descendant-or-self::src:name[text()="{right_name}"]]'
            tmp_nodes = root.xpath(query_2, namespaces=self.namespaces)
            # 再現しただけ
            nodes += [node for node in tmp_nodes if "=" in node.text]
            if len(nodes) > 0:
                self._relation_list[RelationType.Assigns].add(frozenset(pair))
        return

    def _passes(self):
        # 引数の位置とmethodの情報
        node_map = {p: self._getFunctionNameAndPositionList(p) for p in self._unit["Parameter"]}
        # attribute と variable の場合。それぞれが宣言されたファイルのみを調べる
        arguments = self._unit["Attribute"] | self._unit["Variable"]
        pairs = itertools.product(self._unit["Parameter"], arguments)
        for pair in pairs:
            path = pair[1].xmlpath
            root = self._path_to_root[path]
            arg_name = pair[1].oldname
            nodes = []
            for function_name, pos in node_map[pair[0]]:
                query = f'//src:call[./src:name/descendant-or-self::src:name[text()="{function_name}"]]/src:argument_list/src:argument[position()={pos}]/src:expr[.//src:name[text()="{arg_name}"]]'
                nodes += root.xpath(query, namespaces=self.namespaces)
            if len(nodes) > 0:
                self._relation_list[RelationType.Passes].add(frozenset(pair))
        # method の場合。両方のファイルについて調べる
        pairs = itertools.product(self._unit["Parameter"], self._unit["Method"])
        for pair in pairs:
            path_1 = pair[0].xmlpath
            path_2 = pair[1].xmlpath
            root_1 = self._path_to_root[path_1]
            root_2 = self._path_to_root[path_2]
            arg_name = pair[1].oldname
            nodes = []
            for function_name, pos in node_map[pair[0]]:
                query = f'//src:call[./src:name/descendant-or-self::src:name[text()="{function_name}"]]/src:argument_list/src:argument[position()={pos}]/src:expr[.//src:name[text()="{arg_name}"]]'
                nodes += root_1.xpath(query, namespaces=self.namespaces) + root_2.xpath(query, namespaces=self.namespaces)
            if len(nodes) > 0:
                self._relation_list[RelationType.Passes].add(frozenset(pair))
        return

    def _getFunctionNameAndPositionList(self, renaming):
        path = renaming.xmlpath
        root = self._path_to_root[path]
        name = renaming.oldname
        root_tree = etree.ElementTree(root)
        nodes = root.xpath(f'//src:function/src:parameter_list/src:parameter[./src:decl/src:name[text()="{name}"]]', namespaces=self.namespaces)
        result = []
        for node in nodes:
            path = root_tree.getpath(node)
            fname = "".join(n.text for n in node.xpath(f'../../src:name', namespaces=self.namespaces))
            pos = path[path.rfind("[")+1:-1] if path[-1] == "]" else "last()"
            result.append((fname, pos))
        return result

    def export(self):
        return {"all_size": self._all_size, "unit": self._unit}

# Test
if __name__ == "__main__":
    import pandas as pd
    from .Renaming import Renaming
    def dictToRenaming(src):
        dst = Renaming(src["name"]["old"],
                       src["name"]["new"],
                       src["type"], 
                       src["javapath"],
                       src["xmlpath"],
                       src["filename"])
        return dst
    def convertUnit(src):
        return [dictToRenaming(d) for d in src]
    print("Test: Unit")
    test_data = pd.read_csv("./output/oldtestdata/normal/unit.csv")
    result = {rtype: 0 for rtype in list(RelationType)}
    for units in test_data["units"]:
        for unit in eval(units).values():
            tmp = Unit()
            converted = convertUnit(unit)
            [tmp.add(r) for r in converted]
            for rtype, rlist in tmp.analyze().items():
                result[rtype] += len(rlist) 
    print(result)
