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
        parser = SweetParser(self.editor.toPlainText())
        parser.nodes.append(ROOT)
        parser.parse_sweet(0, None)
        print(parser.nodes, parser.edges)
        added = []
        col = self.mw.col
        for index, edge in enumerate(parser.edges):
            if edge[0] == 0:
                note = note_from_graph(parser.nodes, parser.edges, index, col)
                if note:
                    added.append(note)
                else:
                    tooltip(f"Note on {parser.nodes[edge[1]]} is too long")
                    break
        else:
            default = col.decks.id_for_name("Default")
            assert default is not None
            print("default is", default)
            for note in added:
                col.add_note(note, default)
            tooltip(f"Added {len(added)} notes")
            self.close()

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
            with open(filename, "r") as f:
                self.editor.document().setPlainText(f.read())
