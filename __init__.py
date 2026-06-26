import itertools
from typing import Iterable, Optional

import aqt
from aqt.utils import tooltip, show_warning
from anki.models import TemplateDict
from anki.notes import Note, NoteId

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

    CONTAINER_NAME = "graphviz_svg"

    def escape_gv(text: str) -> str:
        for orig, rep in [("\\", "\\\\")]:
            text = text.replace(orig, rep)
        return "<" + text + ">"

    def graphviz_svg(note: Note) -> bytes:
        graph = graphviz.Digraph()
        for name, content in note.items():
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
                show_warning(
                    f"tried to show non-graph as graph, violated by {name}"
                )
                return b""
        try:
            return graph.pipe(format="svg", quiet=True)
        except CalledProcessError as e:
            show_warning(f"error in graphviz: {e} from code {graph.source}")
            return b""

    def on_load_note(editor: Editor):
        note_type_name: str = editor.note_type()["name"]
        tooltip(note_type_name)
        if GraphTopology.note_fits(editor.note):
            w = QSvgWidget()
            w.load(graphviz_svg(editor.note))
            natural: QSize = w.renderer().defaultSize()
            outer: QLayout = editor.widget.layout()
            for item in map(outer.itemAt, range(outer.count())):
                if (item and item.widget() and
                    item.widget().objectName() == CONTAINER_NAME):
                    old = item.widget()
                    outer.removeWidget(old)
                    old.deleteLater()
                    break
            old_index: int = outer.indexOf(editor.web)
            outer.removeWidget(editor.web)
            container = QWidget()
            container.setObjectName(CONTAINER_NAME)
            box = (QHBoxLayout(container)
               if natural.height() > natural.width()
               else QVBoxLayout(container))
            box.addWidget(w, alignment=
                Qt.AlignmentFlag.AlignVCenter |
                Qt.AlignmentFlag.AlignLeft)
            box.addWidget(editor.web)
            outer.insertWidget(old_index, container)

    editor_did_load_note.append(on_load_note)
except ImportError as e:
    show_warning(f"missing module: {e.name}")
