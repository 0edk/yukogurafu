import aqt
import aqt.utils
from aqt.qt import *
from . import gulliver
from .gui import NewGraphDialog

show_gui = QAction("Add graph note", aqt.mw)
aqt.utils.qconnect(show_gui.triggered, lambda: NewGraphDialog(aqt.mw))
aqt.mw.form.menuTools.addAction(show_gui)
