import os
from os.path import join
from textx import (
    language,
    metamodel_from_file,
    get_children_of_type,
    TextXSemanticError,
    get_location,
)
import pathlib
import textx.scoping.providers as scoping_providers
from rich import print
from textx.scoping import ModelRepository, GlobalModelRepository
from smauto.definitions import MODEL_REPO_PATH, BUILTIN_MODELS

from smauto.lib.automation import (
    Action,
    Automation,
    BoolAction,
    FloatAction,
    IntAction,
    StringAction,
)
from smauto.lib.types import Dict, List, Time, Date
from smauto.lib.broker import (
    AMQPBroker,
    Broker,
    BrokerAuthPlain,
    MQTTBroker,
    RedisBroker,
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
    TimeAttribute,
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
    InRangeCondition,
    ListCondition,
)


CURRENT_FPATH = pathlib.Path(__file__).parent.resolve()

CUSTOM_CLASSES = [
    Automation,
    Entity,
    Condition,
    ConditionGroup,
    PrimitiveCondition,
    AdvancedCondition,
    NumericCondition,
    BoolCondition,
    StringCondition,
    ListCondition,
    DictCondition,
    TimeCondition,
    InRangeCondition,
    Attribute,
    IntAttribute,
    FloatAttribute,
    TimeAttribute,
    StringAttribute,
    BoolAttribute,
    ListAttribute,
    DictAttribute,
    Broker,
    MQTTBroker,
    AMQPBroker,
    RedisBroker,
    BrokerAuthPlain,
    Action,
    IntAction,
    FloatAction,
    StringAction,
    BoolAction,
    List,
    Dict,
    Time,
    Date,
]


ENTITY_BUILTINS = {
    "system_clock": Entity(
        None,
        name="system_clock",
        etype="sensor",
        freq=1,
        topic="system.clock",
        broker=MQTTBroker(None, name="fake", host="localhost", port=1883, auth=None),
        attributes=[TimeAttribute(None, "time", None)],
    )
}

GLOBAL_REPO = GlobalModelRepository()


def class_provider(name):
    classes = dict(map(lambda x: (x.__name__, x), CUSTOM_CLASSES))
    return classes.get(name)


def time_obj_processor(t):
    if t.hour > 24 or t.hour < 0:
        raise TextXSemanticError("Time.hours must be in range [0, 24]")
    if t.minute > 60 or t.minute < 0:
        raise TextXSemanticError("Time.minutes must be in range [0, 60]")
    if t.second > 60 or t.second < 0:
        raise TextXSemanticError("Time.seconds must be in range [0, 60]")


def process_time_class(model):
    types_time = get_children_of_type("Time", model)
    for t in types_time:
        if t.hour > 24 or t.hour < 0:
            raise TextXSemanticError("Time.hours must be in range [0, 24]")
        if t.minute > 60 or t.minute < 0:
            raise TextXSemanticError("Time.minutes must be in range [0, 60]")
        if t.second > 60 or t.second < 0:
            raise TextXSemanticError("Time.seconds must be in range [0, 60]")


def verify_broker_names(model):
    _ids = []
    brokers = get_children_of_type("MQTTBroker", model)
    brokers += get_children_of_type("AMQPBroker", model)
    brokers += get_children_of_type("RedisBroker", model)
    for b in brokers:
        if b.name in _ids:
            raise TextXSemanticError(
                f"Broker with name <{b.name}> already exists", **get_location(b)
            )
        _ids.append(b.name)


def verify_entity_names(model):
    _ids = []
    entities = get_children_of_type("Entity", model)
    for e in entities:
        if e.name in _ids:
            raise TextXSemanticError(
                f"Entity with name <{e.name}> already exists", **get_location(e)
            )
        _ids.append(e.name)
        verify_entity_attrs(e)


def verify_entity_attrs(entity):
    _ids = []
    for attr in entity.attributes:
        if attr.name in _ids:
            raise TextXSemanticError(
                f"Entity attribute <{attr.name}> already exists", **get_location(attr)
            )
        _ids.append(attr.name)


def verify_automation_names(model):
    _ids = []
    autos = get_children_of_type("Automation", model)
    for a in autos:
        if a.name in _ids:
            raise TextXSemanticError(
                f"Automation with name <{a.name}> already exists", **get_location(a)
            )
        _ids.append(a.name)


def model_proc(model, metamodel):
    process_time_class(model)
    verify_entity_names(model)
    verify_automation_names(model)
    verify_broker_names(model)


def get_metamodel(debug: bool = False, global_repo: bool = False):
    metamodel = metamodel_from_file(
        CURRENT_FPATH.joinpath("grammar/smauto.tx"),
        classes=class_provider,
        auto_init_attributes=False,
        textx_tools_support=True,
        # global_repository=GLOBAL_REPO,
        global_repository=global_repo,
        debug=debug,
    )

    metamodel.register_scope_providers(get_scode_providers())
    metamodel.register_model_processor(model_proc)
    return metamodel


def get_scode_providers():
    sp = {"*.*": scoping_providers.FQNImportURI(importAs=True)}
    if BUILTIN_MODELS:
        sp["brokers*"] = scoping_providers.FQNGlobalRepo(
            join(BUILTIN_MODELS, "broker", "*.smauto"))
        sp["entities*"] = scoping_providers.FQNGlobalRepo(
            join(BUILTIN_MODELS, "entity", "*.smauto"))
    if MODEL_REPO_PATH:
        sp["brokers*"] = scoping_providers.FQNGlobalRepo(
            join(MODEL_REPO_PATH, "broker", "*.smauto"))
        sp["entities*"] = scoping_providers.FQNGlobalRepo(
            join(MODEL_REPO_PATH, "entity", "*.smauto"))
    return sp


def build_model(model_path):
    mm = get_metamodel(debug=False)
    model = mm.model_from_file(model_path)
    # entities = get_children_of_type('Entity', model)
    return model


def get_model_grammar(model_path):
    mm = get_metamodel()
    grammar_model = mm.grammar_model_from_file(model_path)
    return grammar_model


@language("smauto", "*.auto")
def smauto_language():
    "SmartAutomation (SmAuto) language"
    mm = get_metamodel()
    return mm
