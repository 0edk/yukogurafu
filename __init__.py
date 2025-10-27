import aqt
import aqt.utils
from anki.notes import Note, NoteId
from aqt.qt import *
from collections.abc import Sequence
from . import gulliver
from .gui import FileLoadDialog, GraphViewDialog

def on_browse_selected() -> None:
    browser = aqt.dialogs._dialogs.get("Browser", [None, None])[1]
    if not browser:
        aqt.utils.showInfo("Open browser first")
        return
    nids: Sequence[NoteId] = browser.selected_notes()
    if not nids:
        aqt.utils.showInfo("Select a note")
        return
    note: Note = aqt.mw.col.get_note(nids[0])
    dialog = GraphViewDialog(aqt.mw, note)
    dialog.show()

show_graph = QAction("Show graph note", aqt.mw)
show_graph.triggered.connect(on_browse_selected)
aqt.mw.form.menuTools.addAction(show_graph)

show_gui = QAction("Import graph notes", aqt.mw)
aqt.utils.qconnect(show_gui.triggered, lambda: FileLoadDialog(aqt.mw))
aqt.mw.form.menuCol.addAction(show_gui)
