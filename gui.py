import os
from typing import Optional
from anki.collection import AddNoteRequest
from aqt import AnkiQt
from aqt.qt import *
from aqt.utils import qconnect, tooltip

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

    def keyPressEvent(self, evt: QKeyEvent) -> None:
        if evt.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(evt)

from aqt import mw, dialogs
from aqt.qt import *
from aqt.utils import showInfo
import math
import re

class CircularFieldDialog(QDialog):
    def __init__(self, note):
        super().__init__(mw)
        self.note = note
        self.setWindowTitle("Circular Field View")
        self.resize(800, 900)

        self.canvas = QWidget(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)

        self.canvas.paintEvent = self.paintEvent

    def paintEvent(self, event):
        painter = QPainter(self.canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.canvas.width()
        height = self.canvas.height()
        center_x = width / 2
        center_y = height / 2 + 100
        radius = min(width, height) / 3

        # Draw Source and Context at top
        y_offset = 20
        for field_name in ["Source", "Context"]:
            if field_name in self.note:
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(20, int(y_offset), f"{field_name}:")

                text_doc = QTextDocument()
                html = self.fix_media_paths(self.note[field_name])
                text_doc.setHtml(html)
                text_doc.setTextWidth(width - 40)

                painter.save()
                painter.translate(20, y_offset + 20)
                text_doc.drawContents(painter)
                painter.restore()

                y_offset += text_doc.size().height() + 40

        # Get node fields
        node_fields = []
        for fname in self.note.keys():
            match = re.match(r"Node (\d+)", fname)
            if match:
                node_num = int(match.group(1))
                node_fields.append((node_num, fname, self.note[fname]))
        node_fields.sort()

        count = len(node_fields)
        if count == 0:
            painter.drawText(int(center_x - 50), int(center_y), "No Node fields found")
            return

        # Calculate positions
        positions = {}
        for idx, (node_num, field_name, content) in enumerate(node_fields):
            angle = (2 * math.pi * idx / count) - (math.pi / 2)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            positions[node_num] = (x, y)

        # Draw edges
        painter.setPen(QPen(QColor(0, 255, 0), 3))
        for i in positions:
            for j in positions:
                if i != j:
                    edge_field = f"Edge {i} {j}"
                    if edge_field in self.note and self.note[edge_field].strip():
                        self.draw_arrow(painter, positions[i], positions[j])

        # Draw nodes
        for idx, (node_num, field_name, content) in enumerate(node_fields):
            x, y = positions[node_num]

            text_doc = QTextDocument()
            html = self.fix_media_paths(content)
            text_doc.setHtml(html)
            text_doc.setTextWidth(300)

            painter.save()
            painter.translate(x - 150, y - 100)
            text_doc.drawContents(painter)
            painter.restore()

    def fix_media_paths(self, html):
        media_dir = mw.col.media.dir()
        html = re.sub(r'src="([^"]+)"', f'src="file:///{media_dir}/\\1"', html)
        return html

    def draw_arrow(self, painter, start, end):
        x1, y1 = start
        x2, y2 = end

        # Draw line
        painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # Draw arrowhead
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_size = 15

        p1 = QPointF(x2 - arrow_size * math.cos(angle - math.pi / 6),
                     y2 - arrow_size * math.sin(angle - math.pi / 6))
        p2 = QPointF(x2 - arrow_size * math.cos(angle + math.pi / 6),
                     y2 - arrow_size * math.sin(angle + math.pi / 6))
        p3 = QPointF(x2, y2)

        painter.setBrush(QColor(0, 255, 0))
        painter.drawPolygon(QPolygonF([p1, p2, p3]))

def on_browse_selected():
    browser = dialogs._dialogs.get("Browser", [None, None])[1]
    if not browser:
        showInfo("Open browser first")
        return
    nids = browser.selectedNotes()
    if not nids:
        showInfo("Select a note")
        return
    note = mw.col.get_note(nids[0])
    dialog = CircularFieldDialog(note)
    dialog.show()

action = QAction("Show Circular Fields", mw)
action.triggered.connect(on_browse_selected)
mw.form.menuTools.addAction(action)
