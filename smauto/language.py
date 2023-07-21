import os
from textx import language, metamodel_from_file
import pathlib

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


def get_metamodel():
    metamodel = metamodel_from_file(
        CURRENT_FPATH.joinpath('grammar/smauto.tx'),
        classes=[
            Entity, Attribute, IntAttribute, FloatAttribute,
            StringAttribute, BoolAttribute, ListAttribute,
            DictAttribute, Broker, MQTTBroker, AMQPBroker,
            RedisBroker, BrokerAuthPlain, Automation, Action,
            IntAction, FloatAction, StringAction, BoolAction,
            List, Dict
        ]
    )
    return metamodel


def build_model(model_path):
    # Parse model
    model = get_metamodel().model_from_file(model_path)
    return model


@language('smauto', '*.smauto')
def smauto_language():
    "SmartAutomation (SmAuto) language"
    return get_metamodel()
