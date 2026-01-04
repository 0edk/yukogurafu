import itertools
from typing import Iterable, Optional

import aqt
from anki.models import TemplateDict
from anki.notes import NoteId

from .flashcard_topology import NoteTopology, TopologyDialog
from .gui import GraphViewDialog
from .models import make_edge, name_edge

class GraphTopology(NoteTopology):
    @staticmethod
    def description() -> str:
        return "Directed Graph"

    def make_templates(self, order: int) -> Iterable[TemplateDict]:
        manager = self.mw.col.models
        return itertools.chain(*((
            make_edge(manager, i, j) for j in range(1, i) if i != j
        ) for i in range(1, order + 1)))

    @staticmethod
    def make_fields(order: int) -> Iterable[str]:
        fields = ["Context", "Source"]
        for i in range(1, order + 1):
            fields.append(f"Node {i}")
            fields.extend(itertools.chain(*(
                (name_edge(j, i), name_edge(i, j))
                for j in range(1, i) if i != j
            )))
        return fields

    def custom_css(self, order: int) -> str:
        return ""

    @staticmethod
    def next_order(order: Optional[int] = None) -> int:
        return 2 if order is None else order + 1

    @staticmethod
    def measure_order(fields: dict[str, str]) -> int:
        i = 1
        while f"Node {i}" in fields and (i == 1 or f"Edge 1 {i}" in fields):
            i += 1
        return i - 1

    @classmethod
    def blank_example(cls) -> dict[str, str]:
        example = super().blank_example()
        example["Node 1"] = "A"
        example["Node 2"] = "B"
        return example

    def make_editor(
        self, fields: dict[str, str], note_id: Optional[NoteId]
    ) -> TopologyDialog:
        return GraphViewDialog(fields, note_id, self)

GraphTopology(aqt.mw)
