import math
import re
from aqt.qt import *

from .flashcard_topology import indices

Point = list[float]

def march(start: Point, end: Point, step: float) -> Point:
    x1, y1 = start
    x2, y2 = end
    dist = math.dist(start, end)
    return [x1 + step * (x2 - x1) / dist, y1 + step * (y2 - y1) / dist]

def remap(bounds: tuple[float, float], point: float) -> float:
    return (point - bounds[0]) / (bounds[1] - bounds[0])

class Canvas(QWidget):
    def __init__(self, parent: QWidget, order: int):
        super().__init__(parent)
        self.framer = parent
        self.center: tuple[int, int] = (0, 0)
        self.order = order
        self.positions: dict[int, Point] = {}

    def layout(self) -> None:
        width: int = self.width()
        height: int = self.height()
        self.center = (width // 2, height // 2)
        radius: int = min(width, height) * 2 // 5
        if radius < 20:
            return

        for index in indices(self.order):
            angle: float = math.tau * index / self.order
            self.positions[index] = [
                self.center[0] + radius * math.cos(angle),
                self.center[1] + radius * math.sin(angle)
            ]

        note = self.framer.fields
        nbs: dict[int, set[int]] = {n: set() for n in self.positions}
        for i in self.positions:
            for j in self.positions:
                if i != j:
                    field = f"Edge {i} {j}"
                    if field in note and note[field].strip():
                        nbs[i].add(j)
                        nbs[j].add(i)

        def score(positions: dict[int, Point]) -> float:
            angles: list[float] = []
            for n in positions:
                if len(nbs[n]) >= 2:
                    x0, y0 = positions[n]
                    inner = sorted(math.atan2(
                        positions[k][1] - y0, positions[k][0] - x0,
                    ) for k in nbs[n])
                    angles.append(min(
                        (math.tau if i == 0 else 0) + inner[i] - inner[i - 1]
                        for i in range(len(inner))
                    ))
            return min(angles) if angles else math.pi

        improved = True
        base = score(self.positions)
        while improved:
            improved = False
            for i in self.positions:
                for j in self.positions:
                    if i != j:
                        self.positions[i], self.positions[j] = (
                            self.positions[j], self.positions[i]
                        )
                        new_score = score(self.positions)
                        if new_score > base:
                            base = new_score
                            improved = True
                        else:
                            self.positions[i], self.positions[j] = (
                                self.positions[j], self.positions[i]
                            )

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.GlobalColor.white)

        self.layout()
        painter.setPen(QPen(QColor(0, 255, 0), 3))
        note = self.framer.fields
        for i in self.positions:
            for j in self.positions:
                if i != j:
                    field = f"Edge {i} {j}"
                    if field in note and note[field].strip():
                        self.draw_arrow(
                            painter,
                            march(self.positions[i], self.positions[j], 40),
                            march(self.positions[j], self.positions[i], 40)
                        )
                        ex, ey = march(
                            self.positions[j], self.positions[i], 90,
                        )
                        ex -= 30
                        self.show_field(painter, note[field], ex, ey, 80)

        for index in indices(self.order):
            x, y = self.positions[index]
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
        dists = sorted((math.dist((pos.x(), pos.y()), self.positions[n]), n)
            for n in self.positions)
        if dists[0][0] > 50 and dists[0][0] / dists[1][0] > 0.7:
            return None
        return dists[0][1]
