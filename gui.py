from typing import Optional
from aqt.qt import *
from aqt.utils import show_warning

from .canvas import Canvas
from .flashcard_topology import TopologyDialog

class GraphViewDialog(TopologyDialog):
    def build_interface(self, layout: QBoxLayout) -> None:
        inner_layout = QVBoxLayout()
        layout.addLayout(inner_layout)

        self.editor = QTextEdit(self)
        self.editor.textChanged.connect(self.update_text)
        inner_layout.addWidget(self.editor, 0)
        self.field_editors: dict[str, QLineEdit] = {}
        for field_name in ["Source", "Context"]:
            if field_name in self.fields:
                container = QWidget()
                row = QHBoxLayout(container)
                row.addWidget(QLabel(f"{field_name}:"))
                field_editor = QLineEdit()
                field_editor.setText(self.fields[field_name])
                row.addWidget(field_editor)
                self.field_editors[field_name] = field_editor
                inner_layout.addWidget(container, 0)

        self.canvas = Canvas(self, self.topo.measure_order(self.fields))
        self.canvas.mousePressEvent = self.canvas_press
        self.canvas.mouseReleaseEvent = self.canvas_release
        self.canvas.mouseDoubleClickEvent = self.canvas_double_click
        inner_layout.addWidget(self.canvas, 1)

        self.press_node: Optional[int] = None
        self.edited_field: Optional[str] = None

    def canvas_press(self, event: QMouseEvent | None) -> None:
        if event:
            self.press_node = self.canvas.get_node_at_pos(event.pos())

    def canvas_release(self, event: QMouseEvent | None) -> None:
        if event:
            release_node = self.canvas.get_node_at_pos(event.pos())
            if self.press_node is not None and release_node is not None:
                if self.press_node == release_node:
                    self.edited_field = f"Node {self.press_node}"
                    self.fill_editor(self.fields[self.edited_field])
                else:
                    edge = f"Edge {self.press_node} {release_node}"
                    if edge in self.fields:
                        self.fill_editor(self.fields[edge])
                        self.edited_field = edge

    def canvas_double_click(self, event: QMouseEvent | None) -> None:
        if event and self.canvas.get_node_at_pos(event.pos()) is None:
            self.edited_field = None
            new_order = self.topo.next_order(self.canvas.order)
            if new_order >= 8:
                show_warning(
                    "Large graphs hurt performance.\n"
                    f"Adding {new_order}th node."
                )
            self.fill_editor("new node ...")
            self.fields[f"Node {new_order}"] = "new node ..."
            for i in range(1, new_order):
                self.fields[f"Edge {i} {new_order}"] = ""
                self.fields[f"Edge {new_order} {i}"] = ""
            self.edited_field = f"Node {new_order}"
            self.canvas.order = new_order
            self.canvas.update()

    def fill_editor(self, text: str):
        old_field, self.edited_field = self.edited_field, None
        doc = self.editor.document()
        if doc:
            doc.setPlainText(text)
        else:
            doc = QTextDocument()
            doc.setPlainText(text)
            self.editor.setDocument(doc)
        self.edited_field = old_field

    def update_text(self) -> None:
        if self.edited_field is not None:
            self.fields[self.edited_field] = self.editor.toPlainText()
            self.canvas.update()

    def capture_fields(self) -> None:
        for field_name, editor in self.field_editors.items():
            self.fields[field_name] = editor.text()
