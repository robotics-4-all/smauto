# lib/ — Domain Model Classes

## OVERVIEW

Python classes mapped to textX grammar rules. These ARE the metamodel — textX instantiates them during parsing.

## WHERE TO LOOK

| File | Domain | Key Classes |
|------|--------|-------------|
| `automation.py` | Automation logic | `Automation`, `AutomationState`, `Action`, `SetAction` (+ typed variants), `StartAction`, `StopAction` |
| `entity.py` | Smart devices | `Entity`, `Attribute` (+ typed variants: `IntAttribute`, `FloatAttribute`, etc.) |
| `broker.py` | Communication | `Broker`, `MQTTBroker`, `AMQPBroker`, `RedisBroker`, `BrokerAuthPlain` |
| `condition.py` | Condition evaluation | `Condition`, `ConditionGroup`, `PrimitiveCondition`, `AdvancedCondition`, `InRangeCondition`, typed `*Condition` |
| `types.py` | Value types | `List`, `Dict`, `Time`, `Date` |

## CONVENTIONS

- **Constructor signature**: `(self, parent, ...grammar_fields)` — `parent` is always first (textX tree navigation)
- **Default handling**: Classes must set defaults manually since `auto_init_attributes=False` (e.g., `enabled = True if enabled is None else enabled`)
- **Inheritance maps to grammar alternatives**: `SetAction` → `IntSetAction | FloatSetAction | ...` mirrors `SetAction: IntSetAction | FloatSetAction | ...` in grammar
- **No ABC/Protocol**: Base classes are plain `object` subclasses, no abstract methods

## CRITICAL PATTERNS

- **Condition.build()**: Post-order tree traversal that builds Python expression strings. Called before evaluation. The `cond_lambda` attribute holds the generated expression string.
- **Condition.evaluate()**: Calls `eval(self.cond_lambda, {"entities": ...}, {...})` — the entity dict is the runtime context
- **Entity.update_state()**: Callback for `commlib-py` subscriber — updates attribute values from incoming messages
- **Entity.attributes_dict**: `{name: Attribute}` mapping built at init — used by condition evaluation at runtime
- **Automation.start()**: Blocking event loop — checks dependencies (`after`), evaluates conditions, triggers actions in a `while True` loop

## ANTI-PATTERNS

- Never add an Attribute subclass without also adding a corresponding `*SetAction` in `automation.py`
- The `transform_augmented_attr()` method in `condition.py` uses `__class__.__name__` string comparison — fragile; don't rename classes without updating these strings
- Do not add a `broker_index` or similar global registry — it was removed as dead code
