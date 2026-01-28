import math
import re
from anki.notes import Note
from aqt.qt import *

from .flashcard_topology import indices

Point = tuple[float, float]

def march(start: Point, end: Point, step: float) -> Point:
    x1, y1 = start
    x2, y2 = end
    dist = math.dist(start, end)
    return (x1 + step * (x2 - x1) / dist, y1 + step * (y2 - y1) / dist)

class Canvas(QWidget):
    def __init__(self, parent: QWidget, order: int):
        super().__init__(parent)
        self.framer = parent
        self.center: tuple[int, int] = (0, 0)
        self.order = order

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.GlobalColor.white)

        width: int = self.width()
        height: int = self.height()
        self.center = (width // 2, height // 2)
        radius: int = min(width, height) * 2 // 5
        if radius < 20:
            return

        positions: dict[int, Point] = {}
        count: int = self.order
        for index in indices(self.order):
            angle: float = math.tau * index / count
            positions[index] = (
                self.center[0] + radius * math.cos(angle),
                self.center[1] + radius * math.sin(angle)
            )

        painter.setPen(QPen(QColor(0, 255, 0), 3))
        note = self.framer.fields
        for i in positions:
            for j in positions:
                if i != j:
                    field = f"Edge {i} {j}"
                    if field in note and note[field].strip():
                        self.draw_arrow(
                            painter,
                            march(positions[i], positions[j], 40),
                            march(positions[j], positions[i], 40)
                        )
                        ex, ey = march(positions[j], positions[i], 90)
                        ex -= 30
                        self.show_field(painter, note[field], ex, ey, 80)

        for index in indices(self.order):
            x, y = positions[index]
            self.show_field(
                painter, note[f"Node {index}"], x - 60, y - 20, 120
            )

    def fix_media_paths(self, html):
        return re.sub(
            r'src="([^"]+)"',
            f'src="file:///{self.framer.mw.col.media.dir()}/\\1"',
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

    def get_node_at_pos(
        self, pos: QPoint
    ) -> int | None:
        angle = math.atan2(pos.y() - self.center[1], pos.x() - self.center[0])
        n = self.order
        epsilon = 1 / (3 * n)
        for i in indices(n):
            node_angle = i * math.tau / n
            turns = (angle - node_angle) / math.tau
            if abs(turns - round(turns)) < epsilon:
                return i
        return None
