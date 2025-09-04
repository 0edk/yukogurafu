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

ROOT = "ANKI_ROOT"

class NewGraphDialog(QMainWindow):
    def __init__(self, mw: AnkiQt) -> None:
        super().__init__(mw)
        self.mw = mw
        self.setWindowTitle("Graph notes")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Notes"))
        self.editor = QPlainTextEdit()
        layout.addWidget(self.editor)
        box = QDialogButtonBox()
        buttons = [
            ("Load from file", Roles.ActionRole, self.pick_file),
            ("Cancel", Roles.RejectRole, self.close),
            ("Add", Roles.AcceptRole, self.accept),
            ("Add (TGF)", Roles.AcceptRole, self.accept_tgf),
        ]
        for label, role, action in buttons:
            button = box.addButton(label, role)
            assert button is not None
            qconnect(button.clicked, action)
        layout.addWidget(box)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)
        self.show()

    def accept(self) -> None:
        tooltip("Deprecated!")

    def accept_tgf(self) -> None:
        nodes, edges = load_tgf(self.editor.toPlainText(), True)
        print(nodes, edges)
        tooltip(f"TGF: Detected {len(nodes)}:{len(edges)}")
        # TODO
        self.close()

    def pick_file(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open file", os.environ["HOME"], "GULliVer notes (*.guv)"
        )
        print("got filename", filename)
        if filename:
            FileLoadDialog(self.mw, filename)
            return
            with open(filename, "r") as f:
                self.editor.document().setPlainText(f.read())

class FileLoadDialog(QMainWindow):
    def __init__(self, mw: AnkiQt, path: str) -> None:
        super().__init__(mw)
        self.mw = mw
        self.path = path
        self.setWindowTitle("Graph notes from file")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Notes"))
        with open(path, "r") as f:
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
