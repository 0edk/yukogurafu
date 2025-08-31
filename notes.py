import re
import aqt
from anki.collection import Collection
from anki.notes import Note

from .models import graph_model
from .gulliver import Edge

BACKTICKED: re.Pattern = re.compile("`([^`]+)`")

def format_field(field: str) -> str:
    return BACKTICKED.sub(r"<code>\1</code>", field)

def note_from_graph(
    nodes: list[str], edges: list["Edge"],
    start: int, col: Collection,
) -> Note:
    selected = [edges[start][1]]
    queue_index = 0
    while queue_index < len(selected):
        branch = selected[queue_index]
        for from_id, to_id, label, _ in edges:
            if to_id != 0 and from_id == branch and to_id not in selected:
                selected.append(to_id)
            elif from_id != 0 and to_id == branch and from_id not in selected:
                selected.append(from_id)
        queue_index += 1
    print(selected)

    if len(selected) <= 8:
        model_name = f"Directed Graph [{len(selected)}]"
        model = col.models.id_for_name(model_name)
        if model is None:
            col.models.add_dict(graph_model(len(selected), col))
            model = col.models.id_for_name(model_name)
        note = Note(col, model)
        note["Context"] = format_field(edges[start][2])
        for field_index, graph_index in enumerate(selected):
            note[f"Node {field_index + 1}"] = format_field(nodes[graph_index])
        for from_id, to_id, label, directed in edges:
            if from_id in selected and to_id in selected:
                field_from = selected.index(from_id) + 1
                field_to = selected.index(to_id) + 1
                label = format_field(label)
                note[f"Edge {field_from} {field_to}"] = label
                if not directed:
                    note[f"Edge {field_to} {field_from}"] = label
        return note

if __name__ == "__main__":
    nodes = [
        'ANKI_ROOT', 'ModelManager', 'mw.col.models',
        'edit/store NotetypeDict',
        'ls A*.B | while read entry; do ... done',
        '| puts loop in subprocess', 'for entry in A*.B; do ... done'
    ]
    edges = [
        (0, 1, 'python Anki', True), (2, 1, 'what', True),
        (1, 2, 'how', True), (3, 1, 'how', True),
        (1, 3, 'why', True), (0, 4, 'sh', True),
        (4, 5, 'why not', True), (4, 6, 'fix', True)
    ]
    for i in range(len(edges)):
        print(i, note_from_graph(nodes, edges, i, None))
