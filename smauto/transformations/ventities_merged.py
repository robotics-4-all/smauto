from os.path import basename
import jinja2
from rich import print, pretty

from smauto.language import build_model
from smauto.definitions import TEMPLATES_PATH
from textx import get_children_of_type


jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATES_PATH), trim_blocks=True, lstrip_blocks=True
)

vent_tpl = jinja_env.get_template("ventity_merged.py.jinja")
clock_tpl = jinja_env.get_template("clock.py.jinja")


def build_source_code(sensors, actuators, hubrids, system_clock):
    print(system_clock.broker.host)
    context = {
        "sensors": sensors,
        "actuators": actuators,
        "hybrid": hubrids,
        "system_clock": system_clock,
    }
    modelf = vent_tpl.render(context)
    return modelf


def select_clock_broker(model):
    brokers = []
    for m in model._tx_model_repository.all_models:
        brokers += get_children_of_type("MQTTBroker", m)
        brokers += get_children_of_type("AMQPBroker", m)
        brokers += get_children_of_type("RedisBroker", m)
    for broker in brokers:
        if broker.name == "fake_broker":
            brokers.remove(broker)
    return brokers[0]


def model_to_vent(model_path: str):
    model = build_model(model_path)
    broker = select_clock_broker(model)
    system_clock = None
    for m in model._tx_model_repository.all_models:
        if m.metadata:
            if m.metadata.name == "SystemClock":
                m.entities[0].broker = broker
                ent = m.entities[0]
                system_clock = ent
    sensors = []
    actuators = []
    hybrids = []
    for e in model.entities:
        if e.etype == "sensor":
            sensors.append(e)
        elif e.etype == "actuator":
            actuators.append(e)
        elif e.etype == "hybrid":
            hybrids.append(e)
    ecode = build_source_code(sensors, actuators, hybrids, system_clock)
    return ecode
