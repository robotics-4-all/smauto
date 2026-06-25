"""
smauto/_builtins.py
-------------------
Built-in model objects that are not parsed from .auto files.

The system_clock entity is special: it is also available as a built-in .ent
model (builtin_models/entity/system_clock.ent) loaded via FQNGlobalRepo at
parse time.  ENTITY_BUILTINS holds a manually-constructed counterpart that
tests and tooling can inspect without needing to load a full model.

lib/ imports are intentional here — this module creates lib class instances
directly, which is fine since it is NOT part of the textX parsing pipeline.
"""

from smauto.lib.entity import Entity, TimeAttribute
from smauto.lib.broker import MQTTBroker

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
