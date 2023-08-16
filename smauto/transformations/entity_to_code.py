from os.path import basename
import jinja2
from rich import print, pretty

from smauto.language import build_model
from smauto.definitions import TEMPLATES_PATH
from textx import get_children_of_type


jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATES_PATH),
    trim_blocks=True,
    lstrip_blocks=True
)

sensor_tpl = jinja_env.get_template('sensor.py.jinja')
actuator_tpl = jinja_env.get_template('actuator.py.jinja')
clock_tpl = jinja_env.get_template('clock.py.jinja')


def build_system_clock(entity):
    context = {
        'entity': entity
    }
    return clock_tpl.render(context)


def build_entity_code(entity):
    _type = entity.etype
    context = {
        'entity': entity
    }
    if _type == 'sensor':
        modelf = sensor_tpl.render(context)
    elif _type == 'actuator':
        modelf = actuator_tpl.render(context)
    return modelf


def select_clock_broker(model):
    brokers = []
    for m in model._tx_model_repository.all_models:
        brokers += get_children_of_type('MQTTBroker', m)
        brokers += get_children_of_type('AMQPBroker', m)
        brokers += get_children_of_type('RedisBroker', m)
    for broker in brokers:
        if broker.name == 'fake_broker':
            brokers.remove(broker)
    return brokers[0]


def model_to_vnodes(model_path: str):
    model = build_model(model_path)
    vnodes = []
    broker = select_clock_broker(model)
    for m in model._tx_model_repository.all_models:
        if m.metadata:
            if m.metadata.name == 'SystemClock':
                m.entities[0].broker = broker
                ent = m.entities[0]
                ecode = build_system_clock(ent)
                vnodes.append((ent, ecode))
    for e in model.entities:
        ecode = build_entity_code(e)
        # print(ecode)
        vnodes.append((e, ecode))
    return vnodes
