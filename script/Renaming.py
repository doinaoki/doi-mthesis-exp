from dataclasses import dataclass
import dataclasses
import json

@dataclasses.dataclass(frozen=True)
class Renaming:
    oldname: str
    newname: str
    type: str
    javapath: str
    xmlpath: str
    filename: str

    def export(self):
        return dataclasses.asdict(self)