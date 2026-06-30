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
    from aqt.gui_hooks import (
        editor_did_init,
        editor_did_load_note,
        editor_did_focus_field,
        editor_did_unfocus_field,
    )
    from PyQt6.QtSvgWidgets import QSvgWidget

    class DimensionedSvgWidget(QSvgWidget):
        def hasHeightForWidth(self) -> bool:
            return True

        def heightForWidth(self, w: int) -> int:
            # reads from SVG width/height or viewBox
            s = self.renderer().defaultSize()
            if s.width() == 0:
                return s.height()
            return round(s.height() * min(w / s.width(), 1))

        def sizeHint(self) -> QSize:
            return self.renderer().defaultSize()

    EMPTY_GRAPH: graphviz.Graph = graphviz.Graph()
    MINIMAL_SVG: bytes = EMPTY_GRAPH.pipe(format="svg")
    GV_REPLACES: list[tuple[str, str]] = [
        ("\\", "\\\\"),
        ("<code>", "<font face=\"monospace\">"),
        ("</code>", "</font>"),
    ]
    _svg_widget: Optional[DimensionedSvgWidget] = None

    def escape_gv(text: str) -> str:
        for orig, rep in GV_REPLACES:
            text = text.replace(orig, rep)
        return "<" + text + ">"

    def graphviz_svg(note: Note, focus: str = "") -> bytes:
        graph = graphviz.Digraph()
        for name, content in note.items():
            if name.startswith("Node"):
                if content:
                    graph.node(
                        name.split()[1],
                        escape_gv(content),
                        penwidth="4" if name == focus else "1",
                    )
            elif name.startswith("Edge"):
                if content:
                    graph.edge(
                        *name.split()[1:],
                        label=escape_gv(content),
                        penwidth="4" if name == focus else "1",
                    )
            elif name in ["Context", "Source"]:
                pass
            else:
                show_warning(
                    f"tried to show non-graph as graph, violated by {name}"
                )
                return MINIMAL_SVG
        try:
            return graph.pipe(format="svg", quiet=True)
        except CalledProcessError as e:
            show_warning(f"error in graphviz: {e} from code {graph.source}")
            return MINIMAL_SVG

    def on_init(editor: Editor):
        global _svg_widget
        _svg_widget = DimensionedSvgWidget()
        outer: QLayout = editor.widget.layout()
        old_index: int = outer.indexOf(editor.web)
        outer.removeWidget(editor.web)
        container = QWidget()
        box = QVBoxLayout(container)
        box.addWidget(_svg_widget, stretch=0, alignment=
            Qt.AlignmentFlag.AlignVCenter |
            Qt.AlignmentFlag.AlignLeft)
        box.addWidget(editor.web, stretch=1)
        outer.insertWidget(old_index, container)

    def on_load_note(editor: Editor):
        assert _svg_widget is not None
        if GraphTopology.note_fits(editor.note):
            _svg_widget.load(graphviz_svg(editor.note))
        else:
            _svg_widget.load(MINIMAL_SVG)
        _svg_widget.updateGeometry()
 
    def on_focus_field(note: Note, current_field_idx: int):
        if GraphTopology.note_fits(editor.note):
            _svg_widget.load(graphviz_svg(
                note, note.keys()[current_field_idx]
                if current_field_idx >= 0 else ""
            ))

    def on_unfocus_field(
        changed: bool, note: Note, current_field_idx: int
    ) -> bool:
        if changed:
            on_focus_field(note, -1)
        return False

    editor_did_init.append(on_init)
    editor_did_load_note.append(on_load_note)
    editor_did_focus_field.append(on_focus_field)
    editor_did_unfocus_field.append(on_unfocus_field)
except ImportError as e:
    show_warning(f"missing module: {e.name}")
