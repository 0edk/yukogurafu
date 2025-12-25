import aqt
import aqt.utils
from anki.notes import Note, NoteId
from aqt.qt import *
from collections.abc import Sequence
from .gui import FileLoadDialog, GraphViewDialog

def on_browse_selected() -> None:
    col = aqt.mw.col
    browser = aqt.dialogs._dialogs.get("Browser", [None, None])[1]
    if browser:
        nids: Sequence[NoteId] = browser.selected_notes()
        if not nids:
            aqt.utils.showInfo("Select a note")
            return
        note: Note = col.get_note(nids[0])
    else:
        note = col.new_note(col.models.by_name("Directed Graph [2]"))
        note["Node 1"] = "A"
        note["Node 2"] = "B"
        col.add_note(note, col.default_deck_for_notetype(note.mid) or
            col.decks.get_current_id())
    dialog = GraphViewDialog(aqt.mw, note)
    dialog.setWindowState(Qt.WindowState.WindowMaximized)
    dialog.showMaximized()

show_graph = QAction("Edit graph note", aqt.mw)
show_graph.triggered.connect(on_browse_selected)
aqt.mw.form.menuTools.addAction(show_graph)
