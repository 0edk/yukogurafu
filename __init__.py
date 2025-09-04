import aqt
import aqt.utils
from aqt.qt import *
from . import gulliver
from .gui import FileLoadDialog

show_gui = QAction("Import graph notes", aqt.mw)
aqt.utils.qconnect(show_gui.triggered, lambda: FileLoadDialog(aqt.mw))
aqt.mw.form.menuCol.addAction(show_gui)
