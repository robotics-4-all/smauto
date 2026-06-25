import click
from rich import print, pretty

from smauto.language import build_model
from smauto.transformations import model_to_vnodes, smauto_m2t
from smauto.transformations import model_to_vent
from smauto.utils import make_executable

pretty.install()


@click.group()
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)


@cli.command("validate", help="Model Validation")
@click.pass_context
@click.argument("model_path")
def validate(ctx, model_path):
    build_model(model_path)
    print("[*] Model validation success!!")


@cli.command("gen", help="Generate in Python")
@click.pass_context
@click.argument("model_path")
def generate_py(ctx, model_path):
    pycode = smauto_m2t(model_path)
    model = build_model(model_path)
    filepath = f"{model.metadata.name}.py"
    with open(filepath, "w") as fp:
        fp.write(pycode)
        make_executable(filepath)
    print(f"[CLI] Compiled Automations: [bold]{filepath}")


@cli.command("genv", help="Entities to Code - Generate executable virtual entities")
@click.pass_context
@click.argument("model_path")
@click.option(
    "--merged",
    "-m",
    is_flag=True,
    help="Merge virtual entities into a single output file",
)
def generate_vent(ctx, model_path: str, merged: bool):
    model = build_model(model_path)
    if merged:
        vent_code = model_to_vent(model_path)
        filepath = f"{model.metadata.name.lower()}_entities.py"
        with open(filepath, "w") as fp:
            fp.write(vent_code)
            make_executable(filepath)
            print(f"[CLI] Compiled virtual Entities: [bold]{filepath}")
    else:
        vnodes = model_to_vnodes(model_path)
        for vn in vnodes:
            filepath = f"{vn[0].name}.py"
            with open(filepath, "w") as fp:
                fp.write(vn[1])
                make_executable(filepath)
            print(f"[CLI] Compiled virtual Entity: [bold]{filepath}")


@cli.command("graph", help="Generate Mermaid diagram of model relationships")
@click.pass_context
@click.argument("model_path")
@click.option(
    "--output",
    "-o",
    default=None,
    help="Write diagram to file instead of stdout",
)
def graph(ctx, model_path: str, output: str):
    model = build_model(model_path)
    mermaid = _build_mermaid(model)
    if output:
        with open(output, "w") as fp:
            fp.write(mermaid)
        print(f"[CLI] Graph written to: [bold]{output}")
    else:
        print(mermaid)


def _build_mermaid(model):
    """Build a Mermaid flowchart from a parsed SmAuto model."""
    lines = ["graph TD"]

    # Style classes
    lines.append("    classDef broker fill:#4a90d9,stroke:#2c5f8a,color:#fff")
    lines.append("    classDef sensor fill:#27ae60,stroke:#1e8449,color:#fff")
    lines.append("    classDef actuator fill:#e67e22,stroke:#d35400,color:#fff")
    lines.append("    classDef hybrid fill:#8e44ad,stroke:#6c3483,color:#fff")
    lines.append("    classDef automation fill:#e74c3c,stroke:#c0392b,color:#fff")
    lines.append("")

    # Brokers
    for b in model.brokers:
        proto = b.__class__.__name__.replace("Broker", "")
        lines.append(f'    {b.name}["{b.name}<br/><small>{proto} {b.host}:{b.port}</small>"]')
        lines.append(f"    class {b.name} broker")

    # Entities
    for e in model.entities:
        etype = e.etype
        attrs = ", ".join(a.name for a in e.attributes)
        lines.append(f'    {e.name}["{e.name}<br/><small>{etype} | {attrs}</small>"]')
        lines.append(f"    class {e.name} {etype}")
        # Entity → Broker connection
        source = e.source
        lines.append(f"    {e.name} -.->|{e.uri}| {source.name}")

    lines.append("")

    # Automations
    for a in model.automations:
        cond_str = ""
        if a.condition:
            a.condition.build()
            cond_str = a.condition.cond_lambda or ""
            # Truncate long conditions for readability
            if len(cond_str) > 60:
                cond_str = cond_str[:57] + "..."
            # Escape Mermaid special chars
            cond_str = cond_str.replace('"', "'").replace("|", "\\|")
        lines.append(f"    {a.name}{{{{{a.name}}}}}")
        lines.append(f"    class {a.name} automation")

        # Automation reads from entities (condition references)
        _seen_entities = set()
        for action in a.actions:
            entity = action.attribute.parent
            if entity.name not in _seen_entities:
                lines.append(f"    {a.name} -->|{action.attribute.name} ← ...| {entity.name}")
                _seen_entities.add(entity.name)

        # Else actions
        for action in a.elseActions or []:
            entity = action.attribute.parent
            if entity.name not in _seen_entities:
                lines.append(f"    {a.name} -.->|else| {entity.name}")
                _seen_entities.add(entity.name)

        # Triggers
        for t in a.triggers:
            lines.append(f"    {a.name} ==>|triggers| {t.name}")

        # Terminates
        for t in a.terminates:
            lines.append(f"    {a.name} -.->|terminates| {t.name}")

    return "\n".join(lines)


def main():
    cli(prog_name="smauto")
