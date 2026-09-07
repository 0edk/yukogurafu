from typing import Optional

import aqt
from aqt.utils import show_warning
from anki.notes import Note

from .topo import GraphTopology

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
            r = self.renderer()
            assert r is not None
            # reads from SVG width/height or viewBox
            s = r.defaultSize()
            if s.width() == 0:
                return s.height()
            return round(s.height() * min(w / s.width(), 1))

        def sizeHint(self) -> QSize:
            r = self.renderer()
            assert r is not None
            return r.defaultSize()

    EMPTY_GRAPH: graphviz.Graph = graphviz.Graph()
    MINIMAL_SVG: bytes = EMPTY_GRAPH.pipe(format="svg")
    GV_REPLACES: list[tuple[str, str]] = [
        ("\\", "\\\\"),
        ("<code>", "<font face=\"monospace\">"),
        ("</code>", "</font>"),
    ]
    _svg_widget: Optional[DimensionedSvgWidget] = None
    errored: bool = False

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
            global errored
            if not errored:
                errored = True
                show_warning(f"error in graphviz: {e} from code {graph.source}")
            return MINIMAL_SVG

    def on_init(editor: Editor):
        global _svg_widget
        _svg_widget = DimensionedSvgWidget()
        outer: QLayout | None = editor.widget.layout()
        assert isinstance(outer, QBoxLayout)
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
        global errored
        errored = False
        if editor.note is not None and GraphTopology.note_fits(editor.note):
            s = graphviz_svg(editor.note)
            _svg_widget.load(s)
        else:
            _svg_widget.load(MINIMAL_SVG)
        _svg_widget.updateGeometry()
 
    def on_focus_field(note: Note, current_field_idx: int):
        assert _svg_widget is not None
        if GraphTopology.note_fits(note):
            _svg_widget.load(graphviz_svg(
                note, note.keys()[current_field_idx]
                if current_field_idx >= 0 else ""
            ))

    def on_unfocus_field(
        changed: bool, note: Note, current_field_idx: int
    ) -> bool:
        on_focus_field(note, -1)
        assert _svg_widget is not None
        _svg_widget.updateGeometry()
        return False

    editor_did_init.append(on_init)
    editor_did_load_note.append(on_load_note)
    editor_did_focus_field.append(on_focus_field)
    editor_did_unfocus_field.append(on_unfocus_field)
except ImportError as e:
    show_warning(f"missing module: {e.name}")
