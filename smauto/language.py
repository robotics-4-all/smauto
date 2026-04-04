from os.path import join
import types as python_types

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
    BoolSetAction,
    FloatSetAction,
    IntSetAction,
    StringSetAction,
    SetAction,
    ExprSetAction as _ExprSetAction,
)
from smauto.lib.entity import Entity, TimeAttribute
from smauto.lib.broker import MQTTBroker
from smauto.lib.types import List, Dict, Time, Date, ConstDef, ConstRef
from smauto.lib.condition import (
    Condition as _Condition,
    InRangeCondition as _InRangeCondition,
    TimeRangeCondition as _TimeRangeCondition,
)


def _value_type_class_provider(name):
    """Provide lib classes for simple value types so they retain their methods."""
    _value_classes = {
        "List": List,
        "Dict": Dict,
        "Time": Time,
        "Date": Date,
        "ConstDef": ConstDef,
        "ConstRef": ConstRef,
    }
    return _value_classes.get(name)


CURRENT_FPATH = pathlib.Path(__file__).parent.resolve()


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


# ---------------------------------------------------------------------------
# obj_processors
# ---------------------------------------------------------------------------


def _entity_obj_processor(obj):
    # Unwrap EntitySource → actual broker/endpoint
    if hasattr(obj, "source") and obj.source is not None and hasattr(obj.source, "ref"):
        obj.source = obj.source.ref
    # Default freq
    obj.freq = 1 if obj.freq in (None, 0) else obj.freq
    # Build derived attributes (used by templates and condition evaluation)
    obj.attributes_dict = {attr.name: attr for attr in obj.attributes}
    obj.attributes_buff = {attr.name: None for attr in obj.attributes}
    obj.attr_buffs = []
    obj.state = {}
    # CamelCase name (used by templates for class names)
    obj.camel_name = "".join(x.capitalize() for x in obj.name.lower().split("_"))
    # Build items_dict for DictAttributes
    for attr in obj.attributes:
        if attr.__class__.__name__ == "DictAttribute":
            attr.items_dict = {item.name: item for item in (attr.items or [])}
    # Bind lib Entity methods needed at runtime
    obj.init_attr_buffer = python_types.MethodType(Entity.init_attr_buffer, obj)
    obj.get_buffer = python_types.MethodType(Entity.get_buffer, obj)
    obj.update_state = python_types.MethodType(Entity.update_state, obj)
    obj.update_attributes = Entity.update_attributes  # static method
    obj.update_buffers = Entity.update_buffers  # static method


def _init_condition(cond):
    """Recursively initialize condition objects with required attributes and bound methods."""
    if cond is None:
        return
    # Initialize condition state fields
    cond.cond_lambda = None
    cond.cond_raw = None
    cond._compiled = None
    cond.cond_deactivate = None
    cond._compiled_deactivate = None
    cond._hysteresis_active = False
    cond.forDuration = getattr(cond, "forDuration", None) or 0
    cond._duration_start = None
    # Bind lib Condition methods to textX auto-object
    cond.build = python_types.MethodType(_Condition.build, cond)
    cond.evaluate = python_types.MethodType(_Condition.evaluate, cond)
    cond._eval_expr = python_types.MethodType(_Condition._eval_expr, cond)
    cond._apply_duration_gate = python_types.MethodType(_Condition._apply_duration_gate, cond)
    # Bind subclass-specific methods
    cls_name = cond.__class__.__name__
    if cls_name == "InRangeCondition":
        cond.process_node_condition = python_types.MethodType(
            _InRangeCondition.process_node_condition, cond
        )
    elif cls_name == "TimeRangeCondition":
        cond.process_node_condition = python_types.MethodType(
            _TimeRangeCondition.process_node_condition, cond
        )
    # Recurse into ConditionGroup children
    if cls_name == "ConditionGroup":
        _init_condition(getattr(cond, "r1", None))
        _init_condition(getattr(cond, "r2", None))


def _automation_obj_processor(obj):
    # Unwrap OptBool wrappers — None means absent (use True default)
    obj.enabled = True if obj.enabled is None else obj.enabled.val
    obj.continuous = True if obj.continuous is None else obj.continuous.val
    # Normalize numeric defaults
    obj.freq = 1 if obj.freq in (None, 0) else obj.freq
    obj.delay = 0.0 if obj.delay is None else obj.delay
    obj.cooldown = 0.0 if obj.cooldown is None else obj.cooldown
    obj.checkOnce = False if obj.checkOnce is None else obj.checkOnce
    obj.description = obj.description or ""
    obj.actions = obj.actions or []
    obj.elseActions = obj.elseActions or []
    obj.triggers = obj.triggers or []
    obj.terminates = obj.terminates or []
    obj.status = "IDLE"
    # Initialize condition (textX doesn't call obj_processors for imported-namespace classes)
    _init_condition(obj.condition)


def _int_attr_obj_processor(obj):
    obj.type = "int"
    if obj.default is None:
        obj.value = 0
    else:
        obj.value = obj.default


def _float_attr_obj_processor(obj):
    obj.type = "float"
    if obj.default is None:
        obj.value = 0.0
    else:
        obj.value = obj.default


def _string_attr_obj_processor(obj):
    obj.type = "str"
    obj.value = obj.default if obj.default is not None else ""


def _bool_attr_obj_processor(obj):
    obj.type = "bool"
    obj.value = obj.default if obj.default is not None else False


def _list_attr_obj_processor(obj):
    obj.type = "list"
    obj.value = obj.default if obj.default else []


def _time_attr_obj_processor(obj):
    obj.type = "time"
    if obj.default is None:
        t = Time(obj, 0, 0, 0)
        obj.value = t
    else:
        obj.value = obj.default


def _dict_attr_obj_processor(obj):
    obj.type = "dict"
    if obj.items:
        obj.value = {item.name: item for item in obj.items}
    else:
        obj.value = {}


def _condition_obj_processor(obj):
    obj.cond_lambda = None
    obj.cond_raw = None
    obj._compiled = None
    obj.cond_deactivate = None
    obj._compiled_deactivate = None
    obj._hysteresis_active = False
    obj.forDuration = getattr(obj, "forDuration", None) or 0
    obj._duration_start = None
    # Bind lib Condition methods to textX auto-object
    obj.build = python_types.MethodType(_Condition.build, obj)
    obj.evaluate = python_types.MethodType(_Condition.evaluate, obj)
    obj._eval_expr = python_types.MethodType(_Condition._eval_expr, obj)
    obj._apply_duration_gate = python_types.MethodType(_Condition._apply_duration_gate, obj)


def _mqtt_broker_obj_processor(obj):
    obj.ssl = False if obj.ssl is None else obj.ssl
    obj.basePath = obj.basePath or ""
    obj.webPath = obj.webPath or "/mqtt"
    obj.webPort = obj.webPort or 8883


def _amqp_broker_obj_processor(obj):
    obj.ssl = False if obj.ssl is None else obj.ssl
    obj.topicExchange = obj.topicE or "amq.topic"
    obj.rpcExchange = obj.rpcE or "DEFAULT"


def _redis_broker_obj_processor(obj):
    obj.ssl = False if obj.ssl is None else obj.ssl
    obj.db = obj.db or 0


def _log_action_obj_processor(obj):
    if not obj.level:
        obj.level = "INFO"


def _http_action_obj_processor(obj):
    if not obj.method:
        obj.method = "GET"
    if obj.timeout in (None, 0):
        obj.timeout = 10
    if obj.headers is None:
        obj.headers = []
    if obj.body is None:
        obj.body = ""


def _expr_set_action_obj_processor(obj):
    obj._expr_str = None
    obj.value = None
    # _build_node and _build_op_list are static — attach so bound methods can call via self
    obj._build_node = _ExprSetAction._build_node
    obj._build_op_list = _ExprSetAction._build_op_list

    def _build_expr(self):
        self._expr_str = self._build_node(self.expr)
        self.value = self._expr_str
        return self._expr_str

    obj.build_expr = python_types.MethodType(_build_expr, obj)


def _get_obj_processors():
    return {
        "Entity": _entity_obj_processor,
        "Automation": _automation_obj_processor,
        "IntAttribute": _int_attr_obj_processor,
        "FloatAttribute": _float_attr_obj_processor,
        "StringAttribute": _string_attr_obj_processor,
        "BoolAttribute": _bool_attr_obj_processor,
        "ListAttribute": _list_attr_obj_processor,
        "TimeAttribute": _time_attr_obj_processor,
        "DictAttribute": _dict_attr_obj_processor,
        "ConditionGroup": _condition_obj_processor,
        "NumericCondition": _condition_obj_processor,
        "BoolCondition": _condition_obj_processor,
        "StringCondition": _condition_obj_processor,
        "ListCondition": _condition_obj_processor,
        "DictCondition": _condition_obj_processor,
        "TimeCondition": _condition_obj_processor,
        "InRangeCondition": _condition_obj_processor,
        "TimeRangeCondition": _condition_obj_processor,
        "ConstRefCondition": _condition_obj_processor,
        "AutomationStatusCondition": _condition_obj_processor,
        "MQTTBroker": _mqtt_broker_obj_processor,
        "AMQPBroker": _amqp_broker_obj_processor,
        "RedisBroker": _redis_broker_obj_processor,
        "LogAction": _log_action_obj_processor,
        "HttpAction": _http_action_obj_processor,
        "ExprSetAction": _expr_set_action_obj_processor,
    }


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
            if action.__class__.__name__ in (
                "WaitAction",
                "LogAction",
                "ApplySceneAction",
                "GroupSetAction",
                "HttpAction",
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
    if (
        hasattr(cond, "operand2")
        and hasattr(cond.operand2, "__class__")
        and cond.operand2.__class__.__name__ == "ConstRef"
    ):
        name = cond.operand2.name
        if name not in const_dict:
            raise TextXSemanticError(
                f"Undefined constant '{name}' in condition",
                **get_location(cond),
            )
        cond.operand2 = const_dict[name]
    if cls_name == "InRangeCondition":
        if hasattr(cond.min, "__class__") and cond.min.__class__.__name__ == "ConstRef":
            if cond.min.name not in const_dict:
                raise TextXSemanticError(
                    f"Undefined constant '{cond.min.name}' in range bound",
                    **get_location(cond),
                )
            cond.min = const_dict[cond.min.name]
        if hasattr(cond.max, "__class__") and cond.max.__class__.__name__ == "ConstRef":
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
            if action.__class__.__name__ == "ConstSetAction":
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
        if action.__class__.__name__ == "GroupSetAction":
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
        if action.__class__.__name__ == "ApplySceneAction":
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
    # Build derived model-level dicts used by Condition.evaluate() at runtime
    model.entities_dict = {e.name: e for e in model.entities}
    model.automations_dict = {a.name: a for a in model.automations}


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
        classes=_value_type_class_provider,
        auto_init_attributes=True,
        textx_tools_support=True,
        # global_repository=GLOBAL_REPO,
        global_repository=global_repo,
        debug=debug,
    )

    metamodel.register_obj_processors(_get_obj_processors())
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
