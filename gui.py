import re
from typing import Optional
from anki.notes import Note
from aqt import AnkiQt
from aqt.qt import *
from aqt.utils import qconnect, show_warning

from .models import graph_model
from .canvas import Canvas

Roles = QDialogButtonBox.ButtonRole

class GraphViewDialog(QMainWindow):
    def __init__(self, mw: AnkiQt, note: Note):
        super().__init__(mw)
        self.mw = mw
        self.note = note
        self.setWindowTitle("Graph view")

        layout = QVBoxLayout()
        self.editor = QTextEdit(self)
        self.editor.textChanged.connect(self.update_text)
        layout.addWidget(self.editor, 0)
        self.field_editors: dict[str, QLineEdit] = {}
        for field_name in ["Source", "Context"]:
            if field_name in self.note:
                container = QWidget()
                row = QHBoxLayout(container)
                row.addWidget(QLabel(f"{field_name}:"))
                field_editor = QLineEdit()
                field_editor.setText(self.note[field_name])
                # TODO: textChanged
                row.addWidget(field_editor)
                self.field_editors[field_name] = field_editor
                layout.addWidget(container, 0)
        self.canvas = Canvas(self)
        self.canvas.mousePressEvent = self.canvas_press
        self.canvas.mouseReleaseEvent = self.canvas_release
        self.canvas.mouseDoubleClickEvent = self.canvas_double_click
        layout.addWidget(self.canvas, 1)
        box = QDialogButtonBox()
        buttons = [
            ("Cancel", Roles.RejectRole, self.close),
            ("Save changes", Roles.AcceptRole, self.accept),
        ]
        for label, role, action in buttons:
            button = box.addButton(label, role)
            assert button is not None
            if role == Roles.AcceptRole:
                button.setAutoDefault(True)
            else:
                button.setAutoDefault(False)
            qconnect(button.clicked, action)
        layout.addWidget(box)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.node_fields: dict[int, str] = {}
        for fname in self.note.keys():
            match = re.match(r"Node (\d+)", fname)
            if match:
                self.node_fields[int(match.group(1))] = self.note[fname]
        self.canvas.node_fields = self.node_fields
        self.canvas.note = self.note
        self.press_node: Optional[int] = None
        self.edited_field: Optional[str] = None

    def keyPressEvent(self, evt: QKeyEvent | None) -> None:
        if evt and evt.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(evt)

    def canvas_press(self, event: QMouseEvent | None) -> None:
        if event:
            self.press_node = self.canvas.get_node_at_pos(event.pos())

    def canvas_release(self, event: QMouseEvent | None) -> None:
        if event:
            release_node = self.canvas.get_node_at_pos(event.pos())
            if self.press_node is not None and release_node is not None:
                if self.press_node == release_node:
                    self.fill_editor(self.node_fields[self.press_node])
                    self.edited_field = f"Node {self.press_node}"
                else:
                    edge = f"Edge {self.press_node} {release_node}"
                    if edge in self.note:
                        self.fill_editor(self.note[edge])
                        self.edited_field = edge

    def canvas_double_click(self, event: QMouseEvent | None) -> None:
        if event and self.canvas.get_node_at_pos(event.pos()) is None:
            self.edited_field = None
            self.mw.col.update_note(self.note)
            self.fill_editor("new node ...")
            new_index: int = len(self.node_fields) + 1
            if new_index >= 8:
                show_warning(
                    "Large graphs hurt performance."
                    f"Adding {new_index}th node."
                )
            self.node_fields[new_index] = "new node ..."
            models = self.mw.col.models
            new_model = models.by_name(f"Directed Graph [{new_index}]")
            if new_model is None:
                models.add_dict(graph_model(new_index, self.mw.col))
                new_model = models.by_name(f"Directed Graph [{new_index}]")
            info = models.change_notetype_info(
                old_notetype_id=self.note.mid,
                new_notetype_id=new_model["id"]
            )
            info.input.note_ids.extend([self.note.id])
            models.change_notetype_of_notes(info.input)
            self.note = self.mw.col.get_note(self.note.id)
            self.canvas.note = self.note
            self.edited_field = f"Node {new_index}"

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
            new_text = self.editor.toPlainText()
            self.note[self.edited_field] = new_text
            match = re.match(r"Node (\d+)", self.edited_field)
            if match:
                self.node_fields[int(match.group(1))] = new_text
            self.canvas.update()

    def accept(self) -> None:
        for field, editor in self.field_editors.items():
            self.note[field] = editor.text()
        self.mw.col.update_note(self.note)
        self.close()
