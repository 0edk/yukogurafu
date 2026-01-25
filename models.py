from anki.models import ModelManager, TemplateDict

def name_edge(i: int, j: int) -> str:
    return f"Edge {i} {j}"

def make_edge(manager: ModelManager, i: int, j: int) -> TemplateDict:
    edge = name_edge(i, j)
    template = manager.new_template(f"Card {i} {j}")
    template["qfmt"] = (f"{{{{#{edge}}}}}"
        f"<strong>{{{{Context}}}}</strong> {{{{Node {i}}}}} "
        f"<strong>{{{{{edge}}}}}</strong>{{{{/{edge}}}}}")
    template["afmt"] = (f"{{{{FrontSide}}}}\n<hr id=answer>\n"
        f"{{{{Node {j}}}}}")
    return template
