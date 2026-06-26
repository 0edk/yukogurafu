import itertools
from typing import Iterable, Optional

import aqt
from aqt.utils import tooltip, show_warning
from anki.models import TemplateDict
from anki.notes import NoteId

from .flashcard_topology import indices, NoteTopology, TopologyDialog
from .gui import GraphViewDialog
from .models import make_edge, name_edge

class GraphTopology(NoteTopology):
    @staticmethod
    def description() -> str:
        return "Directed Graph"

    def make_templates(self, order: int) -> Iterable[TemplateDict]:
        manager = self.mw.col.models
        return itertools.chain(*((lambda i=i: (
            make_edge(manager, i, j) for j in indices(order) if i != j
        ))() for i in indices(order)))

    @staticmethod
    def make_fields(order: int) -> Iterable[str]:
        fields = ["Context", "Source"]
        for i in indices(order):
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

try:
    from subprocess import CalledProcessError
    import graphviz
    from aqt.editor import Editor
    from aqt.qt import *
    from aqt.gui_hooks import editor_did_load_note
    from PyQt6.QtSvgWidgets import QSvgWidget

    def escape_gv(text: str) -> str:
        for orig, rep in [("\\", "\\\\"), ("(", "\\("), (")", "\\)")]:
            text = text.replace(orig, rep)
        return "<" + text + ">"

    def on_load_note(editor: Editor):
        note_type_name: str = editor.note_type()["name"]
        tooltip(note_type_name)
        if GraphTopology.note_fits(editor.note):
            graph = graphviz.Digraph()
            for name, content in editor.note.items():
                if name.startswith("Node"):
                    if content:
                        graph.node(name.split()[1], escape_gv(content))
                elif name.startswith("Edge"):
                    if content:
                        graph.edge(
                            *name.split()[1:],
                            label=escape_gv(content),
                        )
                elif name in ["Context", "Source"]:
                    pass
                else:
                    tooltip("not a graph")
                    return
            try:
                svg: bytes = graph.pipe(format="svg", quiet=True)
                w = QSvgWidget()
                w.load(svg)
                natural: QSize = w.renderer().defaultSize()
                if natural.isValid():
                    w.setMaximumWidth(400)
                outer: QLayout = editor.widget.layout()
                old_index: int = outer.indexOf(editor.web)
                outer.removeWidget(editor.web)
                container = QWidget()
                hbox = QHBoxLayout(container)
                hbox.addWidget(w, alignment=Qt.AlignmentFlag.AlignVCenter)
                hbox.addWidget(editor.web)
                outer.insertWidget(old_index, container)
            except CalledProcessError as e:
                show_warning(f"error in graphviz: {e} from code {graph.source}")

    editor_did_load_note.append(on_load_note)
except ImportError as e:
    show_warning(f"missing module: {e.name}")
