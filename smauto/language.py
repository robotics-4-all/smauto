import os
from os.path import join
from textx import language, metamodel_from_file, get_children_of_type, TextXSemanticError
import pathlib
import textx.scoping.providers as scoping_providers
from rich import print
from textx.scoping import ModelRepository, GlobalModelRepository
from smauto.definitions import MODEL_REPO_PATH

from smauto.lib.automation import (
    Action,
    Automation,
    BoolAction,
    FloatAction,
    IntAction,
    StringAction
)
from smauto.lib.types import (
    Dict, List, Time, Date
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
    StringAttribute,
    TimeAttribute
)

from smauto.lib.condition import (
    Condition,
    ConditionGroup,
    PrimitiveCondition,
    AdvancedCondition,
    NumericCondition,
    BoolCondition,
    TimeCondition,
    StringCondition,
    DictCondition,
    ListCondition
)


CURRENT_FPATH = pathlib.Path(__file__).parent.resolve()

CUSTOM_CLASSES = [
    Automation, Entity, Condition, ConditionGroup, PrimitiveCondition,
    AdvancedCondition, NumericCondition, BoolCondition, StringCondition,
    ListCondition, DictCondition, TimeCondition,
    Attribute, IntAttribute, FloatAttribute, TimeAttribute,
    StringAttribute, BoolAttribute, ListAttribute,
    DictAttribute, Broker, MQTTBroker, AMQPBroker,
    RedisBroker, BrokerAuthPlain, Action,
    IntAction, FloatAction, StringAction, BoolAction,
    List, Dict, Time, Date
]


ENTITY_BUILDINS = {
    'system_clock': Entity(
        None,
        name='system_clock',
        etype='sensor',
        freq=1,
        topic='system.clock',
        broker=MQTTBroker(None, name='fake', host='localhost',
                          port=1883, auth=None),
        attributes=[
            TimeAttribute(None, 'time', None)
        ]
    )
}

FakeBroker = """
MQTT:
    name: fake_broker
    host: "localhost"
    port: 1883
    auth:
        username: ""
        password: ""
"""

SystemClock = """
Entity:
    name: system_clock
    type: sensor
    topic: "system.clock"
    broker: fake_broker
    attributes:
        - time: time
"""

GLOBAL_REPO = GlobalModelRepository()


def class_provider(name):
    classes = dict(map(lambda x: (x.__name__, x), CUSTOM_CLASSES))
    return classes.get(name)


def time_obj_processor(t):
    if t.hour > 24 or t.hour < 0:
        raise TextXSemanticError('Time.hours must be in range [0, 24]')
    if t.minute > 60 or t.minute < 0:
        raise TextXSemanticError('Time.minutes must be in range [0, 60]')
    if t.second > 60 or t.second < 0:
        raise TextXSemanticError('Time.seconds must be in range [0, 60]')


def process_time_class(model):
    types_time = get_children_of_type('Time', model)
    for t in types_time:
        if t.hour > 24 or t.hour < 0:
            raise TextXSemanticError('Time.hours must be in range [0, 24]')
        if t.minute > 60 or t.minute < 0:
            raise TextXSemanticError('Time.minutes must be in range [0, 60]')
        if t.second > 60 or t.second < 0:
            raise TextXSemanticError('Time.seconds must be in range [0, 60]')


def model_proc(model, metamodel):
    process_time_class(model)


def get_metamodel(debug=False):
    metamodel = metamodel_from_file(
        CURRENT_FPATH.joinpath('grammar/smauto.tx'),
        classes=class_provider,
        auto_init_attributes=False,
        global_repository=GLOBAL_REPO,
        debug=debug
    )
    # metamodel.register_obj_processors(obj_processors)
    metamodel.register_model_processor(model_proc)

    metamodel.register_scope_providers(
        {
            "*.*": scoping_providers.FQNImportURI(importAs=True),
            "brokers*": scoping_providers.FQNGlobalRepo(
                join(MODEL_REPO_PATH, 'broker', 'fake_broker.smauto')
            ),
            "entities*": scoping_providers.FQNGlobalRepo(
                join(MODEL_REPO_PATH, 'entity', 'system_clock.smauto')
            ),
        }
    )
    return metamodel


def get_buildin_models(metamodel):
    buildin_models = ModelRepository()
    buildin_models.add_model(metamodel.model_from_str(FakeBroker))
    buildin_models.add_model(metamodel.model_from_str(SystemClock))
    return buildin_models


def build_model(model_path):
    # Parse model
    mm = get_metamodel(debug=False)
    model = mm.model_from_file(model_path)
    # entities = get_children_of_type('Entity', model)
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
