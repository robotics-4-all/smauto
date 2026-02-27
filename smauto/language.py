from os.path import join

from rich import print
from textx import (
    language,
    metamodel_from_file,
    get_children_of_type,
    TextXSemanticError,
    get_location,
)
import pathlib
import textx.scoping.providers as scoping_providers
from textx.scoping import GlobalModelRepository
from smauto.definitions import MODEL_REPO_PATH, BUILTIN_MODELS

from smauto.lib.automation import (
    Action,
    Automation,
    SetAction,
    BoolSetAction,
    FloatSetAction,
    IntSetAction,
    StringSetAction,
    ListSetAction,
    DictSetAction,
    ExprSetAction,
)
from smauto.lib.types import Dict, List, Time, Date
from smauto.lib.broker import (
    AMQPBroker,
    Broker,
    BrokerAuthPlain,
    EntitySource,
    MQTTBroker,
    Property,
    RedisBroker,
    RESTEndpoint,
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
    TimeRangeCondition,
    ListCondition,
    AutomationStatusCondition,
    AutomationStatusRef,
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
    TimeRangeCondition,
    AutomationStatusCondition,
    AutomationStatusRef,
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
    RESTEndpoint,
    EntitySource,
    Property,
    BrokerAuthPlain,
    Action,
    SetAction,
    IntSetAction,
    FloatSetAction,
    StringSetAction,
    BoolSetAction,
    ListSetAction,
    DictSetAction,
    ExprSetAction,
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
        uri="system.clock",
        source=MQTTBroker(None, name="fake", host="localhost", port=1883, auth=None),
        attributes=[TimeAttribute(None, "time", None)],
    )
}

GLOBAL_REPO = GlobalModelRepository()


def class_provider(name):
    classes = {x.__name__: x for x in CUSTOM_CLASSES}
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


def verify_source_names(model):
    _ids = []
    sources = get_children_of_type("MQTTBroker", model)
    sources += get_children_of_type("AMQPBroker", model)
    sources += get_children_of_type("RedisBroker", model)
    sources += get_children_of_type("RESTEndpoint", model)
    for s in sources:
        if s.name in _ids:
            raise TextXSemanticError(
                f"Source with name <{s.name}> already exists", **get_location(s)
            )
        _ids.append(s.name)


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


def verify_entity_semantics(model):
    entities = get_children_of_type("Entity", model)
    for e in entities:
        if e.etype == "actuator":
            for attr in e.attributes:
                if hasattr(attr, "generator") and attr.generator is not None:
                    raise TextXSemanticError(
                        f"Actuator entity '{e.name}' attribute '{attr.name}' "
                        f"cannot have a value generator",
                        **get_location(attr),
                    )
            if e.freq not in (None, 0, 1):
                print(
                    f"[bold yellow][WARNING] Actuator entity '{e.name}' has freq={e.freq} "
                    f"which is semantically meaningless for actuators[/bold yellow]"
                )


def verify_entity_sources_for_codegen(model):
    """Warn about entities using REST endpoints — codegen only supports broker-based sources."""
    entities = get_children_of_type("Entity", model)
    for e in entities:
        source = e.source
        if source.__class__.__name__ == "RESTEndpoint":
            print(
                f"[bold yellow][WARNING] Entity '{e.name}' uses REST endpoint "
                f"'{source.name}' as source. Code generation only supports "
                f"broker-based sources (MQTT, AMQP, Redis). Generated code "
                f"for this entity will not function correctly.[/bold yellow]"
            )


def verify_action_targets(model):
    """Validate that all SetAction targets point to actuator or hybrid entities."""
    automations = get_children_of_type("Automation", model)
    for auto in automations:
        all_actions = list(auto.actions) + list(auto.elseActions or [])
        for action in all_actions:
            entity = action.attribute.parent
            if entity.etype == "sensor":
                raise TextXSemanticError(
                    f"Automation '{auto.name}' action targets sensor entity "
                    f"'{entity.name}.{action.attribute.name}' — "
                    f"actions can only target actuator or hybrid entities",
                    **get_location(action),
                )


def verify_automation_status_refs(model):
    """Validate that AutomationStatusCondition references existing automations."""
    automation_names = {a.name for a in get_children_of_type("Automation", model)}
    status_refs = get_children_of_type("AutomationStatusRef", model)
    for ref in status_refs:
        if ref.automation not in automation_names:
            raise TextXSemanticError(
                f"AutomationStatusCondition references non-existent automation '{ref.automation}'",
                **get_location(ref),
            )


def model_proc(model, metamodel):
    process_time_class(model)
    verify_entity_names(model)
    verify_automation_names(model)
    verify_source_names(model)
    verify_entity_semantics(model)
    verify_action_targets(model)
    verify_automation_status_refs(model)
    verify_entity_sources_for_codegen(model)


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

    metamodel.register_scope_providers(get_scope_providers())
    metamodel.register_model_processor(model_proc)
    return metamodel


def get_scope_providers():
    sp = {"*.*": scoping_providers.FQNImportURI(importAs=True)}
    if BUILTIN_MODELS:
        sp["brokers*"] = scoping_providers.FQNGlobalRepo(join(BUILTIN_MODELS, "broker", "*.br"))
        sp["entities*"] = scoping_providers.FQNGlobalRepo(join(BUILTIN_MODELS, "entity", "*.ent"))
        # sp["automations*"] = scoping_providers.FQNGlobalRepo(
        #     join(BUILTIN_MODELS, "automations", "*.smauto"))
    if MODEL_REPO_PATH:
        sp["brokers*"] = scoping_providers.FQNGlobalRepo(join(MODEL_REPO_PATH, "broker", "*.br"))
        sp["entities*"] = scoping_providers.FQNGlobalRepo(join(MODEL_REPO_PATH, "entity", "*.ent"))
        # sp["automations*"] = scoping_providers.FQNGlobalRepo(
        #     join(BUILTIN_MODELS, "automations", "*.smauto"))
    return sp


def build_model(model_path):
    mm = get_metamodel(debug=False)
    model = mm.model_from_file(model_path)
    return model


@language("smauto", "*.smauto")
def smauto_language():
    "SmartAutomation (SmAuto) language"
    mm = get_metamodel()
    return mm
