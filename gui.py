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
        with open(self.path, "r") as f:
            parser = SweetParser(f.read())
        self.forest = []
        self.checks = []
        while (bush_root := parser.parse_single()):
            print(parser.show_context())
            self.forest.append((parser.nodes, parser.edges, *bush_root))
            check = QCheckBox(parser.nodes[0], self)
            self.checks.append(check)
            layout.addWidget(check)
            parser.nodes = []
            parser.edges = []
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
