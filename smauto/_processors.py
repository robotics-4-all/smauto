"""
smauto/_processors.py
---------------------
textX obj_processors for the SmAuto metamodel.

All lib imports live here — language.py stays free of lib dependencies.
These processors run after textX instantiates each grammar object and are
responsible for:
  - binding lib methods onto textX auto-class instances
  - setting default attribute values
  - patching value-type classes (__repr__, to_int) so parsed instances
    behave identically to their lib counterparts

No lib classes are registered with textX (classes= param is unused).
Everything is handled through obj_processors and method binding.
"""

from __future__ import annotations

import types as python_types

from smauto.lib.entity import Entity
from smauto.lib.types import Time
from smauto.lib.condition import (
    Condition as _Condition,
    InRangeCondition as _InRangeCondition,
    TimeRangeCondition as _TimeRangeCondition,
)
from smauto.lib.automation import ExprSetAction as _ExprSetAction


# ---------------------------------------------------------------------------
# Value-type processors (Time, List, Dict)
# Patch class-level __repr__ / bind to_int() so textX auto-instances behave
# exactly like the corresponding lib classes.
# ---------------------------------------------------------------------------


def _time_obj_processor(obj):
    """Bind to_int() to each parsed Time instance."""

    def _to_int(self):
        h = getattr(self, "hour", 0) or 0
        m = getattr(self, "minute", 0) or 0
        s = getattr(self, "second", 0) or 0
        return s + int(m << 8) + int(h << 16)

    obj.to_int = python_types.MethodType(_to_int, obj)


def _list_obj_processor(obj):
    """Patch List auto-class __repr__ to produce a proper Python list string."""
    cls = type(obj)
    if not getattr(cls, "_smauto_repr_patched", False):

        def _repr(self):
            def _item(x):
                if x.__class__.__name__ == "List":
                    return [_item(i) for i in (x.items or [])]
                return x

            return str([_item(x) for x in (self.items or [])])

        cls.__repr__ = _repr
        cls._smauto_repr_patched = True


def _dict_obj_processor(obj):
    """Patch Dict auto-class __repr__ to produce a proper Python dict string."""
    cls = type(obj)
    if not getattr(cls, "_smauto_repr_patched", False):

        def _repr(self):
            def _item_val(x):
                if x.__class__.__name__ == "List":
                    return [_item_val(i) for i in (x.items or [])]
                return x

            parts = [f"'{i.name}':{_item_val(i.value)}" for i in (self.items or [])]
            return "{" + ",".join(parts) + "}"

        cls.__repr__ = _repr
        cls._smauto_repr_patched = True


# ---------------------------------------------------------------------------
# Entity processor
# ---------------------------------------------------------------------------


def _entity_obj_processor(obj):
    # Unwrap EntitySource → actual broker/endpoint
    if hasattr(obj, "source") and obj.source is not None and hasattr(obj.source, "ref"):
        obj.source = obj.source.ref
    # Default freq
    obj.freq = 1 if obj.freq in (None, 0) else obj.freq
    # Build derived attribute mappings
    obj.attributes_dict = {attr.name: attr for attr in obj.attributes}
    obj.attributes_buff = {attr.name: None for attr in obj.attributes}
    obj.attr_buffs = []
    obj.state = {}
    # CamelCase name (used by templates for generated class names)
    obj.camel_name = "".join(x.capitalize() for x in obj.name.lower().split("_"))
    # Build items_dict for DictAttributes
    for attr in obj.attributes:
        if attr.__class__.__name__ == "DictAttribute":
            attr.items_dict = {item.name: item for item in (attr.items or [])}
    # Bind lib Entity runtime methods onto the textX auto-object
    obj.init_attr_buffer = python_types.MethodType(Entity.init_attr_buffer, obj)
    obj.get_buffer = python_types.MethodType(Entity.get_buffer, obj)
    obj.update_state = python_types.MethodType(Entity.update_state, obj)
    obj.update_attributes = Entity.update_attributes  # static
    obj.update_buffers = Entity.update_buffers  # static


# ---------------------------------------------------------------------------
# Condition processors
# ---------------------------------------------------------------------------


def _init_condition(cond):
    """Recursively initialise condition nodes with state fields and bound methods."""
    if cond is None:
        return
    cond.cond_lambda = None
    cond.cond_raw = None
    cond._compiled = None
    cond.cond_deactivate = None
    cond._compiled_deactivate = None
    cond._hysteresis_active = False
    cond.forDuration = getattr(cond, "forDuration", None) or 0
    cond._duration_start = None
    # Core Condition methods
    cond.build = python_types.MethodType(_Condition.build, cond)
    cond.evaluate = python_types.MethodType(_Condition.evaluate, cond)
    cond._eval_expr = python_types.MethodType(_Condition._eval_expr, cond)
    cond._apply_duration_gate = python_types.MethodType(_Condition._apply_duration_gate, cond)
    # Subclass-specific methods
    cls_name = cond.__class__.__name__
    if cls_name == "InRangeCondition":
        cond.process_node_condition = python_types.MethodType(
            _InRangeCondition.process_node_condition, cond
        )
    elif cls_name == "TimeRangeCondition":
        cond.process_node_condition = python_types.MethodType(
            _TimeRangeCondition.process_node_condition, cond
        )
    # Recurse for ConditionGroup children
    if cls_name == "ConditionGroup":
        _init_condition(getattr(cond, "r1", None))
        _init_condition(getattr(cond, "r2", None))


def _condition_obj_processor(obj):
    obj.cond_lambda = None
    obj.cond_raw = None
    obj._compiled = None
    obj.cond_deactivate = None
    obj._compiled_deactivate = None
    obj._hysteresis_active = False
    obj.forDuration = getattr(obj, "forDuration", None) or 0
    obj._duration_start = None
    obj.build = python_types.MethodType(_Condition.build, obj)
    obj.evaluate = python_types.MethodType(_Condition.evaluate, obj)
    obj._eval_expr = python_types.MethodType(_Condition._eval_expr, obj)
    obj._apply_duration_gate = python_types.MethodType(_Condition._apply_duration_gate, obj)


# ---------------------------------------------------------------------------
# Automation processor
# ---------------------------------------------------------------------------


def _automation_obj_processor(obj):
    # Unwrap OptBool wrappers — None means absent → default True
    obj.enabled = True if obj.enabled is None else obj.enabled.val
    obj.continuous = True if obj.continuous is None else obj.continuous.val
    # Numeric defaults
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
    # textX doesn't fire obj_processors for imported-namespace classes, so we
    # initialise condition nodes manually via the recursive helper.
    _init_condition(obj.condition)


# ---------------------------------------------------------------------------
# Attribute processors
# ---------------------------------------------------------------------------


def _int_attr_obj_processor(obj):
    obj.type = "int"
    obj.value = 0 if obj.default is None else obj.default


def _float_attr_obj_processor(obj):
    obj.type = "float"
    obj.value = 0.0 if obj.default is None else obj.default


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
        # Use the lib Time so the default value has to_int()
        t = Time(obj, 0, 0, 0)
        obj.value = t
    else:
        obj.value = obj.default


def _dict_attr_obj_processor(obj):
    obj.type = "dict"
    obj.value = {item.name: item for item in obj.items} if obj.items else {}


# ---------------------------------------------------------------------------
# Broker processors
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Action processors
# ---------------------------------------------------------------------------


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
    # Attach static methods so the bound build_expr can call them via self
    obj._build_node = _ExprSetAction._build_node
    obj._build_op_list = _ExprSetAction._build_op_list

    def _build_expr(self):
        self._expr_str = self._build_node(self.expr)
        self.value = self._expr_str
        return self._expr_str

    obj.build_expr = python_types.MethodType(_build_expr, obj)


# ---------------------------------------------------------------------------
# Public registry
# ---------------------------------------------------------------------------


def get_obj_processors() -> dict:
    """Return the full obj_processor map for textX registration."""
    return {
        # Value types
        "Time": _time_obj_processor,
        "List": _list_obj_processor,
        "Dict": _dict_obj_processor,
        # Entities
        "Entity": _entity_obj_processor,
        # Attributes
        "IntAttribute": _int_attr_obj_processor,
        "FloatAttribute": _float_attr_obj_processor,
        "StringAttribute": _string_attr_obj_processor,
        "BoolAttribute": _bool_attr_obj_processor,
        "ListAttribute": _list_attr_obj_processor,
        "TimeAttribute": _time_attr_obj_processor,
        "DictAttribute": _dict_attr_obj_processor,
        # Conditions
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
        # Automations
        "Automation": _automation_obj_processor,
        # Brokers
        "MQTTBroker": _mqtt_broker_obj_processor,
        "AMQPBroker": _amqp_broker_obj_processor,
        "RedisBroker": _redis_broker_obj_processor,
        # Actions
        "LogAction": _log_action_obj_processor,
        "HttpAction": _http_action_obj_processor,
        "ExprSetAction": _expr_set_action_obj_processor,
    }
