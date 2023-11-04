import os
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

smauto_tpl = jinja_env.get_template('smauto.py.jinja')
clock_tpl = jinja_env.get_template('clock.py.jinja')


def build_system_clock(entity):
    context = {
        'entity': entity
    }
    return clock_tpl.render(context)


def build_smauto_code(model):
    context = {
        'entities': model.entities,
        'automations': model.automations,
    }
    return smauto_tpl.render(context)


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


def make_executable(path):
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2    # copy R bits to X
    os.chmod(path, mode)


def write_to_file(code, fpath):
    with open(fpath, 'w') as fp:
        fp.write(code)
        make_executable(fpath)


def smauto_m2t(model_path: str, outdir: str = ''):
    model = build_model(model_path)
    if len(model.automations) < 1:
        print('[ERROR]: Model does not include any Automations')
        return
    systeme = []
    for m in model._tx_model_repository.all_models:
        if m.metadata:
            if m.metadata.name == 'SystemClock':
                ent = m.entities[0]
                ecode = build_system_clock(ent)
                filename = f'{ent.name}.py'
                systeme.append((filename, ecode))
    for auto in model.automations:
        auto.condition.build()
    scode = build_smauto_code(model)
    write_to_file(scode, f'{model.metadata.name}.py')
    return scode
