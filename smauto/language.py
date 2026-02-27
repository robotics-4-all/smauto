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
    ApplySceneAction,
    Automation,
    ConstSetAction,
    GroupSetAction,
    HttpAction,
    HttpHeader,
    LogAction,
    SceneDef,
    WaitAction,
    SetAction,
    BoolSetAction,
    FloatSetAction,
    IntSetAction,
    StringSetAction,
    ListSetAction,
    DictSetAction,
    ExprSetAction,
)
from smauto.lib.types import ConstDef, ConstRef, Dict, List, Time, Date
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
    EntityGroup,
    FloatAttribute,
    IntAttribute,
    ListAttribute,
    StringAttribute,
    TimeAttribute,
)

from smauto.lib.condition import (
    Condition,
    ConditionGroup,
    ConstRefCondition,
    GenericAttrRef,
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
    ConstRefCondition,
    GenericAttrRef,
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
    EntityGroup,
    Broker,
    MQTTBroker,
    AMQPBroker,
    RedisBroker,
    RESTEndpoint,
    EntitySource,
    Property,
    BrokerAuthPlain,
    Action,
    ApplySceneAction,
    GroupSetAction,
    HttpAction,
    HttpHeader,
    SceneDef,
    LogAction,
    WaitAction,
    SetAction,
    ConstSetAction,
    IntSetAction,
    FloatSetAction,
    StringSetAction,
    BoolSetAction,
    ListSetAction,
    DictSetAction,
    ExprSetAction,
    ConstDef,
    ConstRef,
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
    _errors = []
    entities = get_children_of_type("Entity", model)
    for e in entities:
        if e.name in _ids:
            _errors.append(
                TextXSemanticError(
                    f"Entity with name <{e.name}> already exists", **get_location(e)
                )
            )
        _ids.append(e.name)
        try:
            verify_entity_attrs(e)
        except TextXSemanticError as err:
            _errors.append(err)
    if _errors:
        raise TextXSemanticError("\n".join(str(e) for e in _errors))


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
    _errors = []
    autos = get_children_of_type("Automation", model)
    for a in autos:
        if a.name in _ids:
            _errors.append(
                TextXSemanticError(
                    f"Automation with name <{a.name}> already exists", **get_location(a)
                )
            )
        _ids.append(a.name)
    if _errors:
        raise TextXSemanticError("\n".join(str(e) for e in _errors))


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
    _errors = []
    automations = get_children_of_type("Automation", model)
    for auto in automations:
        all_actions = list(auto.actions) + list(auto.elseActions or [])
        for action in all_actions:
            if isinstance(
                action, (WaitAction, LogAction, ApplySceneAction, GroupSetAction, HttpAction)
            ):
                continue
            entity = action.attribute.parent
            if entity.etype == "sensor":
                _errors.append(
                    TextXSemanticError(
                        f"Automation '{auto.name}' action targets sensor entity "
                        f"'{entity.name}.{action.attribute.name}' — "
                        f"actions can only target actuator or hybrid entities",
                        **get_location(action),
                    )
                )
    if _errors:
        raise TextXSemanticError("\n".join(str(e) for e in _errors))


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


def verify_const_names(model):
    """Validate that constant names are unique."""
    _ids = []
    for c in model.constants or []:
        if c.name in _ids:
            raise TextXSemanticError(
                f"Constant with name '{c.name}' already defined",
                **get_location(c),
            )
        _ids.append(c.name)


def _resolve_condition_consts(cond, const_dict):
    """Walk condition tree and replace ConstRef operands with literal values."""
    if cond is None:
        return
    cls_name = cond.__class__.__name__
    if cls_name == "ConditionGroup":
        _resolve_condition_consts(cond.r1, const_dict)
        _resolve_condition_consts(cond.r2, const_dict)
        return
    if hasattr(cond, "operand2") and isinstance(cond.operand2, ConstRef):
        name = cond.operand2.name
        if name not in const_dict:
            raise TextXSemanticError(
                f"Undefined constant '{name}' in condition",
                **get_location(cond),
            )
        cond.operand2 = const_dict[name]
    if cls_name == "InRangeCondition":
        if isinstance(cond.min, ConstRef):
            if cond.min.name not in const_dict:
                raise TextXSemanticError(
                    f"Undefined constant '{cond.min.name}' in range bound",
                    **get_location(cond),
                )
            cond.min = const_dict[cond.min.name]
        if isinstance(cond.max, ConstRef):
            if cond.max.name not in const_dict:
                raise TextXSemanticError(
                    f"Undefined constant '{cond.max.name}' in range bound",
                    **get_location(cond),
                )
            cond.max = const_dict[cond.max.name]


def resolve_constants(model):
    """Resolve all ConstRef objects to their literal values."""
    const_dict = {c.name: c.value for c in (model.constants or [])}
    for auto in get_children_of_type("Automation", model):
        _resolve_condition_consts(auto.condition, const_dict)
        all_actions = list(auto.actions or []) + list(auto.elseActions or [])
        for action in all_actions:
            if isinstance(action, ConstSetAction):
                name = action.value.name
                if name not in const_dict:
                    raise TextXSemanticError(
                        f"Undefined constant '{name}' in action",
                        **get_location(action),
                    )
                action.value = const_dict[name]


def verify_scene_names(model):
    _ids = []
    _errors = []
    for s in model.scenes or []:
        if s.name in _ids:
            _errors.append(
                TextXSemanticError(
                    f"Scene with name '{s.name}' already defined",
                    **get_location(s),
                )
            )
        _ids.append(s.name)
    if _errors:
        raise TextXSemanticError("\n".join(str(e) for e in _errors))


def verify_group_names(model):
    _ids = []
    _errors = []
    for g in model.groups or []:
        if g.name in _ids:
            _errors.append(
                TextXSemanticError(
                    f"Group with name '{g.name}' already defined",
                    **get_location(g),
                )
            )
        _ids.append(g.name)
    if _errors:
        raise TextXSemanticError("\n".join(str(e) for e in _errors))


def expand_groups(model):
    """Expand GroupSetAction into individual SetActions for each entity in the group."""
    for auto in get_children_of_type("Automation", model):
        auto.actions = _expand_group_actions(auto.actions)
        if auto.elseActions:
            auto.elseActions = _expand_group_actions(auto.elseActions)


def _expand_group_actions(actions):
    expanded = []
    for action in actions or []:
        if isinstance(action, GroupSetAction):
            group = action.group
            for entity in group.members:
                attr = entity.attributes_dict.get(action.attr)
                if attr is None:
                    raise TextXSemanticError(
                        f"Entity '{entity.name}' in group '{group.name}' "
                        f"has no attribute '{action.attr}'",
                        **get_location(action),
                    )
                # Create typed SetAction based on value type
                val = action.value
                if isinstance(val, bool):
                    new_action = BoolSetAction(action.parent, attr, val)
                elif isinstance(val, float):
                    new_action = FloatSetAction(action.parent, attr, val)
                elif isinstance(val, int):
                    new_action = IntSetAction(action.parent, attr, val)
                elif isinstance(val, str):
                    new_action = StringSetAction(action.parent, attr, val)
                else:
                    new_action = SetAction(action.parent, attr, val)
                expanded.append(new_action)
        else:
            expanded.append(action)
    return expanded


def expand_scenes(model):
    scene_dict = {s.name: s for s in (model.scenes or [])}
    for auto in get_children_of_type("Automation", model):
        auto.actions = _expand_action_list(auto.actions, scene_dict)
        if auto.elseActions:
            auto.elseActions = _expand_action_list(auto.elseActions, scene_dict)


def _expand_action_list(actions, scene_dict):
    expanded = []
    for action in actions or []:
        if isinstance(action, ApplySceneAction):
            if action.name not in scene_dict:
                raise TextXSemanticError(
                    f"Undefined scene '{action.name}'",
                    **get_location(action),
                )
            expanded.extend(scene_dict[action.name].actions)
        else:
            expanded.append(action)
    return expanded


def model_proc(model, metamodel):
    errors = []
    _collect_errors(errors, process_time_class, model)
    _collect_errors(errors, verify_entity_names, model)
    _collect_errors(errors, verify_automation_names, model)
    _collect_errors(errors, verify_source_names, model)
    _collect_errors(errors, verify_const_names, model)
    _collect_errors(errors, verify_entity_semantics, model)
    _collect_errors(errors, verify_action_targets, model)
    _collect_errors(errors, verify_automation_status_refs, model)
    _collect_errors(errors, verify_scene_names, model)
    _collect_errors(errors, verify_group_names, model)
    verify_entity_sources_for_codegen(model)
    if errors:
        msg = f"Found {len(errors)} validation error(s):\n"
        msg += "\n".join(f"  - {e}" for e in errors)
        raise TextXSemanticError(msg)
    expand_scenes(model)
    expand_groups(model)
    resolve_constants(model)


def _collect_errors(errors, func, model):
    try:
        func(model)
    except TextXSemanticError as e:
        errors.append(str(e))
        return
    except Exception as e:
        errors.append(str(e))
        return


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
