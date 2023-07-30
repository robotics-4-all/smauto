import os
from textx import language, metamodel_from_file
import pathlib
import textx.scoping.providers as scoping_providers

from smauto.lib.automation import (
    Action,
    Automation,
    BoolAction,
    Dict,
    FloatAction,
    IntAction,
    List,
    StringAction
)
from smauto.lib.broker import (
    AMQPBroker,
    Broker,
    BrokerAuthPlain,
    MQTTBroker,
    RedisBroker
)
from smauto.lib.entity import (
    Attribute,
    BoolAttribute,
    DictAttribute,
    Entity,
    FloatAttribute,
    IntAttribute,
    ListAttribute,
    StringAttribute
)


CURRENT_FPATH = pathlib.Path(__file__).parent.resolve()

CUSTOM_CLASSES = [
    Automation, Entity, Attribute, IntAttribute, FloatAttribute,
    StringAttribute, BoolAttribute, ListAttribute,
    DictAttribute, Broker, MQTTBroker, AMQPBroker,
    RedisBroker, BrokerAuthPlain, Action,
    IntAction, FloatAction, StringAction, BoolAction,
    List, Dict
]

def class_provider(name):
    classes = dict(map(lambda x: (x.__name__, x), CUSTOM_CLASSES))
    return classes.get(name)


def get_metamodel():
    metamodel = metamodel_from_file(
        CURRENT_FPATH.joinpath('grammar/smauto.tx'),
        classes=class_provider,
        auto_init_attributes=False
    )
    # metamodel.register_scope_providers(
    #     {
    #         "*.*": scoping_providers.FQNImportURI(importAs=True),
    #     }
    # )
    return metamodel


def build_model(model_path):
    # Parse model
    mm = get_metamodel()
    model = mm.model_from_file(model_path)
    return model


@language('smauto', '*.auto')
def smauto_language():
    "SmartAutomation (SmAuto) language"
    mm = get_metamodel()
    return mm
