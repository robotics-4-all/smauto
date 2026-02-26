import jinja2

from smauto.language import build_model
from smauto.definitions import TEMPLATES_PATH
from smauto.utils import inject_system_clock


jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATES_PATH), trim_blocks=True, lstrip_blocks=True
)

sensor_tpl = jinja_env.get_template("sensor.py.jinja")
actuator_tpl = jinja_env.get_template("actuator.py.jinja")
hybrid_tpl = jinja_env.get_template("hybrid.py.jinja")
clock_tpl = jinja_env.get_template("clock.py.jinja")


def build_system_clock(entity):
    context = {"entity": entity}
    return clock_tpl.render(context)


def build_entity_code(entity):
    _type = entity.etype
    context = {"entity": entity}
    if _type == "sensor":
        modelf = sensor_tpl.render(context)
    elif _type == "actuator":
        modelf = actuator_tpl.render(context)
    elif _type == "hybrid":
        modelf = hybrid_tpl.render(context)
    else:
        raise NotImplementedError(f"{_type} Entities not yet supported")
    return modelf


def model_to_vnodes(model_path: str):
    model = build_model(model_path)
    vnodes = []
    system_clock = inject_system_clock(model)
    if system_clock:
        ecode = build_system_clock(system_clock)
        vnodes.append((system_clock, ecode))
    for e in model.entities:
        if e is system_clock:
            continue
        ecode = build_entity_code(e)
        vnodes.append((e, ecode))
    return vnodes
