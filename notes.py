import re
from typing import Optional
import aqt
from anki.collection import Collection
from anki.notes import Note

from .models import graph_model
from .gulliver import Edge, EdgeAttr

FORMAT_SYNTAX: list[tuple[re.Pattern, str]] = [(re.compile(s), d) for s, d in [
    ("`([^`]+)`", r"<code>\1</code>"),
    (r"\$([^$]+)\$", r"\(\1\)"),
    (r"\^\(([^)]+)\)", r"<sup>\1</sup>"),
    (r"_\(([^)]+)\)", r"<sub>\1</sub>"),
]]

def format_field(field: Optional[str]) -> Optional[str]:
    if isinstance(field, str):
        for short, long in FORMAT_SYNTAX:
            field = short.sub(long, field)
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
        if len(root) == 2:
            note["Source"] = format_field(root[0])
            note["Context"] = format_field(root[1])
        else:
            note["Context"] = format_field(root[0])
        for field_index, node in enumerate(nodes):
            note[f"Node {field_index + 1}"] = format_field(node)
        for from_id, to_id, label, directed in edges:
            label = format_field(label)
            note[f"Edge {from_id + 1} {to_id + 1}"] = label
            if not directed:
                note[f"Edge {to_id + 1} {from_id + 1}"] = label
        return note
