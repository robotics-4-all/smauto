import os

import jinja2

from smauto.language import build_model
from smauto.definitions import TEMPLATES_PATH
from smauto.utils import select_clock_broker, make_executable


jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATES_PATH), trim_blocks=True, lstrip_blocks=True
)

smauto_tpl = jinja_env.get_template("smauto.py.jinja")
clock_tpl = jinja_env.get_template("clock.py.jinja")


def rtm_set_defaults(model):
    if hasattr(model, "monitor"):
        if model.monitor is None:
            return
        model.monitor.ns = model.monitor.ns or "smauto"
        model.monitor.eTopic = model.monitor.eTopic or "events"
        model.monitor.lTopic = model.monitor.lTopic or "logs"


def build_smauto_code(model):
    rtm_set_defaults(model)
    context = {
        "entities": model.entities,
        "automations": model.automations,
        "system_clock": model.system_clock,
        "rt_monitor": model.monitor,
        "metadata": model.metadata,
    }
    return smauto_tpl.render(context)


def write_to_file(code, fpath):
    with open(fpath, "w") as fp:
        fp.write(code)
        make_executable(fpath)


def smauto_m2t(model_path: str, outdir: str = ""):
    model = build_model(model_path)
    if len(model.automations) < 1:
        raise ValueError("Model does not include any Automations")
    clock_broker = select_clock_broker(model)
    for m in model._tx_model_repository.all_models:
        if m.metadata:
            if m.metadata.name == "SystemClock":
                m.entities[0].broker = clock_broker
                ent = m.entities[0]
                model.entities.append(ent)
                model.system_clock = ent
    for auto in model.automations:
        auto.condition.build()
    scode = build_smauto_code(model)
    if outdir not in ("", None):
        write_to_file(scode, os.path.join(outdir, f"{model.metadata.name}.py"))
    return scode
