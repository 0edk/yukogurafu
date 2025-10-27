import math
import os
import re
from typing import Optional
from anki.collection import AddNoteRequest
from anki.notes import Note
from aqt import AnkiQt, dialogs
from aqt.qt import *
from aqt.utils import qconnect, showInfo, tooltip

from .gulliver import SweetParser
from .gulliver.assemble import load_tgf
from .notes import note_from_graph

Roles = QDialogButtonBox.ButtonRole

def describe_path(path: str) -> str:
    head, tail = os.path.split(path)
    return os.path.join(os.path.basename(head), tail)

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

class GraphViewDialog(QDialog):
    def __init__(self, mw: AnkiQt, note: Note):
        super().__init__(mw)
        self.mw = mw
        self.note = note
        self.setWindowTitle("Graph view")
        self.canvas = QWidget(self)
        self.canvas.paintEvent = self.paintEvent
        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        painter = QPainter(self.canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width: int = self.canvas.width()
        height: int = self.canvas.height()
        center_x: int = width // 2
        center_y: int = height // 2 + 100
        radius: int = min(width, height) // 3

        painter.setPen(Qt.GlobalColor.white)
        y_offset: int = 20
        for field_name in ["Source", "Context"]:
            if field_name in self.note:
                painter.drawText(20, y_offset, f"{field_name}:")
                text_doc = QTextDocument()
                text_doc.setHtml(self.fix_media_paths(self.note[field_name]))
                text_doc.setTextWidth(width - 40)
                painter.save()
                painter.translate(70, y_offset)
                text_doc.drawContents(painter)
                painter.restore()
                y_offset += int(text_doc.size().height() + 40)

        node_fields: dict[int, str] = {}
        for fname in self.note.keys():
            match = re.match(r"Node (\d+)", fname)
            if match:
                node_fields[int(match.group(1))] = self.note[fname]
        if not node_fields:
            painter.drawText(
                int(center_x - 50), int(center_y),
                "No Node fields found"
            )
            return

        positions: dict[int, tuple[float, float]] = {}
        count: int = len(node_fields)
        for index in node_fields:
            angle: float = math.tau * index / count
            positions[index] = (
                center_x + radius * math.cos(angle),
                center_y + radius * math.sin(angle)
            )

        painter.setPen(QPen(QColor(0, 255, 0), 3))
        for i in positions:
            for j in positions:
                if i != j:
                    field = f"Edge {i} {j}"
                    if field in self.note and self.note[field].strip():
                        self.draw_arrow(painter, positions[i], positions[j])

        for index, content in node_fields.items():
            x, y = positions[index]
            text_doc = QTextDocument()
            text_doc.setHtml(self.fix_media_paths(content))
            text_doc.setTextWidth(300)
            painter.save()
            painter.translate(x - 150, y - 100)
            text_doc.drawContents(painter)
            painter.restore()

    def fix_media_paths(self, html):
        return re.sub(
            r'src="([^"]+)"',
            f'src="file:///{self.mw.col.media.dir()}/\\1"',
            html
        )

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
