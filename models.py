import itertools
from anki.collection import Collection
from anki.models import ModelManager, NotetypeDict, TemplateDict

def make_edge(
    manager: ModelManager, i: int, j: int
) -> tuple[str, TemplateDict]:
    edge = f"Edge {i} {j}"
    template = manager.new_template(f"Card {i} {j}")
    template["qfmt"] = (f"{{{{#{edge}}}}}"
        f"<strong>{{{{Context}}}}</strong> {{{{Node {i}}}}} "
        f"<strong>{{{{{edge}}}}}</strong>{{{{/{edge}}}}}")
    template["afmt"] = (f"{{{{FrontSide}}}}\n<hr id=answer>\n"
        f"{{{{Node {j}}}}}")
    return edge, template

def graph_model(node_count: int, col: Collection) -> NotetypeDict:
    fields = []
    manager = col.models
    model = manager.new(f"Directed Graph [{node_count}]")
    fields.append("Context")
    fields.append("Source")
    for i in range(1, node_count + 1):
        node = f"Node {i}"
        fields.append(node)
        for j in range(1, i):
            if i != j:
                for _ in range(2):
                    i, j = j, i
                    edge, template = make_edge(manager, i, j)
                    fields.append(edge)
                    manager.add_template(model, template)
    for name in fields:
        manager.add_field(model, manager.new_field(name))
    model["sortf"] = 2
    model["css"] = model["css"].replace("arial", "sans-serif")
    return model
