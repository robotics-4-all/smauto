import os

from textx import generator

from smauto.transformations.smauto_m2t import build_smauto_code, rtm_set_defaults
from smauto.transformations.entity_to_code import build_entity_code, build_system_clock
from smauto.transformations.ventities_merged import build_source_code
from smauto.utils import select_clock_broker, make_executable


def _inject_system_clock(model):
    clock_broker = select_clock_broker(model)
    for m in model._tx_model_repository.all_models:
        if m.metadata and m.metadata.name == "SystemClock":
            m.entities[0].source = clock_broker
            ent = m.entities[0]
            if ent not in model.entities:
                model.entities.append(ent)
            model.system_clock = ent
            return ent
    return None


def _write(content, filepath):
    with open(filepath, "w") as f:
        f.write(content)
    make_executable(filepath)


@generator("smauto", "automations")
def smauto_gen_automations(metamodel, model, output_path, overwrite, debug, **kwargs):
    """Generate executable Python code for all automations in the model."""
    if not model.automations:
        return

    _inject_system_clock(model)
    for auto in model.automations:
        auto.condition.build()

    rtm_set_defaults(model)
    code = build_smauto_code(model)

    name = model.metadata.name if model.metadata else "automations"
    _write(code, os.path.join(output_path, f"{name}.py"))


@generator("smauto", "ventities")
def smauto_gen_ventities(metamodel, model, output_path, overwrite, debug, **kwargs):
    """Generate one Python file per entity (virtual entity simulators)."""
    system_clock = _inject_system_clock(model)

    if system_clock:
        code = build_system_clock(system_clock)
        _write(code, os.path.join(output_path, f"{system_clock.name}.py"))

    for entity in model.entities:
        if entity is system_clock:
            continue
        code = build_entity_code(entity)
        _write(code, os.path.join(output_path, f"{entity.name}.py"))


@generator("smauto", "ventities_merged")
def smauto_gen_ventities_merged(metamodel, model, output_path, overwrite, debug, **kwargs):
    """Generate a single Python file with all virtual entities merged."""
    system_clock = _inject_system_clock(model)

    sensors = [e for e in model.entities if e.etype == "sensor" and e is not system_clock]
    actuators = [e for e in model.entities if e.etype == "actuator"]
    hybrids = [e for e in model.entities if e.etype == "hybrid"]

    code = build_source_code(sensors, actuators, hybrids, system_clock)

    name = model.metadata.name if model.metadata else "entities"
    _write(code, os.path.join(output_path, f"{name.lower()}_entities.py"))
