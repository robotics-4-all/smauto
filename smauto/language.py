import os
from textx import language, metamodel_from_file, get_children_of_type, TextXSemanticError
import pathlib
import textx.scoping.providers as scoping_providers

from smauto.lib.automation import (
    Action,
    Automation,
    BoolAction,
    FloatAction,
    IntAction,
    StringAction
)
from smauto.lib.types import (
    Dict, List, Time
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

from smauto.lib.condition import (
    Condition,
    ConditionGroup,
    PrimitiveCondition,
    AdvancedCondition,
    NumericCondition,
    BoolCondition,
    StringCondition,
    DictCondition,
    ListCondition
)


CURRENT_FPATH = pathlib.Path(__file__).parent.resolve()

CUSTOM_CLASSES = [
    Automation, Entity, Condition, ConditionGroup, PrimitiveCondition,
    AdvancedCondition, NumericCondition, BoolCondition, StringCondition,
    ListCondition, DictCondition,
    Attribute, IntAttribute, FloatAttribute,
    StringAttribute, BoolAttribute, ListAttribute,
    DictAttribute, Broker, MQTTBroker, AMQPBroker,
    RedisBroker, BrokerAuthPlain, Action,
    IntAction, FloatAction, StringAction, BoolAction,
    List, Dict, Time
]


def class_provider(name):
    classes = dict(map(lambda x: (x.__name__, x), CUSTOM_CLASSES))
    return classes.get(name)


def time_obj_processor(t):
    if t.hours > 24 or t.hours < 0:
        raise TextXSemanticError('Time.hours must be in range [0, 24]')
    if t.minutes > 60 or t.hours < 0:
        raise TextXSemanticError('Time.minutes must be in range [0, 60]')
    if t.seconds > 60 or t.hours < 0:
        raise TextXSemanticError('Time.seconds must be in range [0, 60]')


def process_time_class(model):
    types_time = get_children_of_type('Time', model)
    for t in types_time:
        if t.hours > 24 or t.hours < 0:
            raise TextXSemanticError('Time.hours must be in range [0, 24]')
        if t.minutes > 60 or t.hours < 0:
            raise TextXSemanticError('Time.minutes must be in range [0, 60]')
        if t.seconds > 60 or t.hours < 0:
            raise TextXSemanticError('Time.seconds must be in range [0, 60]')


def model_proc(model, metamodel):
    process_time_class(model)


def get_metamodel():
    metamodel = metamodel_from_file(
        CURRENT_FPATH.joinpath('grammar/smauto.tx'),
        classes=class_provider,
        auto_init_attributes=False
    )
    # obj_processors = {
    #     'Time': time_obj_processor,
    # }
    # metamodel.register_obj_processors(obj_processors)
    metamodel.register_model_processor(model_proc)

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


def get_model_grammar(model_path):
    mm = get_metamodel()
    grammar_model = mm.grammar_model_from_file(model_path)
    return grammar_model


@language('smauto', '*.auto')
def smauto_language():
    "SmartAutomation (SmAuto) language"
    mm = get_metamodel()
    return mm
