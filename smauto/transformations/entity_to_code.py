from os.path import basename
import jinja2
from rich import print, pretty

from smauto.language import build_model
from smauto.definitions import TEMPLATES_PATH


jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATES_PATH),
    trim_blocks=True,
    lstrip_blocks=True
)

entity_tpl = jinja_env.get_template('entity.py.jinja')


def build_entity_code(entity):
    context = {
        'entity': entity
    }
    modelf = entity_tpl.render(context)
    return modelf


def model_to_vnodes(model_path: str):
    model = build_model(model_path)
    vnodes = []
    for e in model.entities:
        ecode = build_entity_code(e)
        # print(ecode)
        vnodes.append((e, ecode))
    return vnodes
