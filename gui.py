import math
import os
import re
from typing import Optional
from anki.notes import Note
from aqt import AnkiQt, dialogs
from aqt.qt import *
from aqt.utils import qconnect, showInfo, tooltip

from .gulliver import SweetParser
from .gulliver.assemble import load_tgf
from .notes import note_from_graph

Roles = QDialogButtonBox.ButtonRole
Point = tuple[float, float]

def describe_path(path: str) -> str:
    head, tail = os.path.split(path)
    return os.path.join(os.path.basename(head), tail)

def march(start: Point, end: Point, step: float) -> Point:
    x1, y1 = start
    x2, y2 = end
    dist = math.dist(start, end)
    return (x1 + step * (x2 - x1) / dist, y1 + step * (y2 - y1) / dist)

class FileLoadDialog(QMainWindow):
    def __init__(self, mw: AnkiQt, path: Optional[str] = None) -> None:
        super().__init__(mw)
        self.mw = mw
        if path is None:
            self.path, _ = QFileDialog.getOpenFileName(
                self, "Open file", os.environ["HOME"], "GULliVer notes (*.guv)"
            )
        else:
            self.path = path
        self.setWindowTitle("Graph notes from file")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Notes"))
        if self.path:
            with open(self.path, "r") as f:
                parser = SweetParser(f.read())
        else:
            self.close()
            return
        check_container = QWidget()
        check_layout = QVBoxLayout(check_container)
        self.forest = []
        self.checks = []
        while (bush_root := parser.parse_single()):
            print(parser.show_context())
            self.forest.append((parser.nodes, parser.edges, *bush_root))
            check = QCheckBox(parser.nodes[0], check_container)
            self.checks.append(check)
            check_layout.addWidget(check)
            parser.nodes = []
            parser.edges = []
        scroll = QScrollArea()
        scroll.setWidget(check_container)
        layout.addWidget(scroll)
        box = QDialogButtonBox()
        buttons = [
            ("Cancel", Roles.RejectRole, self.close),
            ("Add selected", Roles.AcceptRole, self.accept),
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
        vertical = scroll.verticalScrollBar()
        if vertical:
            vertical.setValue(vertical.maximum())
        self.show()

    def accept(self) -> None:
        added = []
        col = self.mw.col
        for entry, picked in zip(self.forest, self.checks):
            if picked.checkState() == Qt.CheckState.Checked:
                note = note_from_graph(*entry, col)
                note["Source"] = note["Source"] or describe_path(self.path)
                if note:
                    added.append(note)
                else:
                    tooltip(f"Note on {entry[0][0]} is too long")
                    break
        else:
            default = col.decks.id_for_name("Default")
            assert default is not None
            for note in added:
                col.add_note(note, default)
            tooltip(f"Added {len(added)} notes")
            self.close()

    def keyPressEvent(self, evt: QKeyEvent | None) -> None:
        if evt and evt.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(evt)

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
        self.canvas = QWidget(self)
        self.canvas.paintEvent = self.paintEvent
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

        self.center: tuple[int, int] = (0, 0)
        self.node_fields: dict[int, str] = {}
        for fname in self.note.keys():
            match = re.match(r"Node (\d+)", fname)
            if match:
                self.node_fields[int(match.group(1))] = self.note[fname]
        self.press_node: Optional[int] = None
        self.edited_field: Optional[str] = None

    def keyPressEvent(self, evt: QKeyEvent | None) -> None:
        if evt and evt.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(evt)

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        painter = QPainter(self.canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width: int = self.canvas.width()
        height: int = self.canvas.height()
        self.center = (width // 2, height // 2)
        radius: int = min(width, height) * 2 // 5
        if radius < 20:
            return

        painter.setPen(Qt.GlobalColor.white)
        if not self.node_fields:
            painter.drawText(
                self.center[0] - 50, self.center[1],
                "No Node fields found"
            )
            return

        positions: dict[int, Point] = {}
        count: int = len(self.node_fields)
        for index in self.node_fields:
            angle: float = math.tau * index / count
            positions[index] = (
                self.center[0] + radius * math.cos(angle),
                self.center[1] + radius * math.sin(angle)
            )

        painter.setPen(QPen(QColor(0, 255, 0), 3))
        for i in positions:
            for j in positions:
                if i != j:
                    field = f"Edge {i} {j}"
                    if field in self.note and self.note[field].strip():
                        self.draw_arrow(
                            painter,
                            march(positions[i], positions[j], 40),
                            march(positions[j], positions[i], 40)
                        )
                        ex, ey = march(positions[j], positions[i], 90)
                        ex -= 30
                        self.show_field(painter, self.note[field], ex, ey, 80)

        for index, content in self.node_fields.items():
            x, y = positions[index]
            self.show_field(painter, content, x - 60, y - 20, 120)

    def fix_media_paths(self, html):
        return re.sub(
            r'src="([^"]+)"',
            f'src="file:///{self.mw.col.media.dir()}/\\1"',
            html
        )

    def show_field(self, painter: QPainter, content: str,
        x: float, y: float, width: float) -> QTextDocument:
        text_doc = QTextDocument()
        font = QFont()
        font.setPointSize(16)
        text_doc.setDefaultFont(font)
        text_doc.setHtml(self.fix_media_paths(content))
        text_doc.setTextWidth(width)
        options = QTextOption()
        options.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_doc.setDefaultTextOption(options)
        painter.save()
        painter.translate(x, y)
        text_doc.drawContents(painter)
        painter.restore()
        return text_doc

    def draw_arrow(self, painter, start, end):
        x1, y1 = start
        x2, y2 = end
        painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_size = 15
        p1 = QPointF(x2 - arrow_size * math.cos(angle - math.pi / 6),
                     y2 - arrow_size * math.sin(angle - math.pi / 6))
        p2 = QPointF(x2 - arrow_size * math.cos(angle + math.pi / 6),
                     y2 - arrow_size * math.sin(angle + math.pi / 6))
        p3 = QPointF(x2, y2)
        painter.setBrush(QColor(0, 255, 0))
        painter.drawPolygon(QPolygonF([p1, p2, p3]))

    def canvas_press(self, event: QMouseEvent | None) -> None:
        if event:
            self.press_node = self.get_node_at_pos(event.pos())

    def canvas_release(self, event: QMouseEvent | None) -> None:
        if event:
            release_node = self.get_node_at_pos(event.pos())
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
        if event and self.get_node_at_pos(event.pos()) is None:
            self.edited_field = None
            self.note.flush()
            self.fill_editor("new node ...")
            new_index: int = len(self.node_fields) + 1
            self.node_fields[new_index] = "new node ..."
            models = self.mw.col.models
            new_model = models.by_name(f"Directed Graph [{new_index}]")
            info = models.change_notetype_info(
                old_notetype_id=self.note.mid,
                new_notetype_id=new_model["id"]
            )
            info.input.note_ids.extend([self.note.id])
            models.change_notetype_of_notes(info.input)
            self.note = self.mw.col.get_note(self.note.id)
            self.edited_field = f"Node {new_index}"

    def get_node_at_pos(self, pos: QPoint) -> int | None:
        angle = math.atan2(pos.y() - self.center[1], pos.x() - self.center[0])
        if angle < 0:
            angle += math.tau
        n = len(self.node_fields)
        epsilon = math.tau / (3 * n)
        for i in range(1, n + 1):
            node_angle = (i % n) * math.tau / n
            if abs(angle - node_angle) < epsilon:
                return i
        return None

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
        self.note.flush()
        self.close()
