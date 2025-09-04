import re
from typing import Optional
import aqt
from anki.collection import Collection
from anki.notes import Note

from .models import graph_model
from .gulliver import Edge, EdgeAttr

BACKTICKED: re.Pattern = re.compile("`([^`]+)`")

def format_field(field: Optional[str]) -> Optional[str]:
    if isinstance(field, str):
        return BACKTICKED.sub(r"<code>\1</code>", field)
    return field

def note_from_graph(
    nodes: list[str], edges: list["Edge"],
    bush: int, root: EdgeAttr, col: Collection,
) -> Note:
    n = len(nodes)
    if n <= 8:
        model_name = f"Directed Graph [{n}]"
        model = col.models.id_for_name(model_name)
        if model is None:
            col.models.add_dict(graph_model(n, col))
            model = col.models.id_for_name(model_name)
        note = Note(col, model)
        note["Context"] = format_field(root[1] if len(root) == 2 else root[0])
        for field_index, node in enumerate(nodes):
            note[f"Node {field_index + 1}"] = format_field(node)
        for from_id, to_id, label, directed in edges:
            label = format_field(label)
            note[f"Edge {from_id + 1} {to_id + 1}"] = label
            if not directed:
                note[f"Edge {to_id + 1} {to_id + 1}"] = label
        return note
