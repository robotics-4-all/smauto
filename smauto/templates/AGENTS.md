# templates/ — Jinja2 Code Generation Templates

## OVERVIEW

Jinja2 templates rendered by `transformations/` to produce executable Python code. Generated code uses `commlib-py` for broker communication.

## WHERE TO LOOK

| Template | Used By | Generates |
|----------|---------|-----------|
| `smauto.py.jinja` | `smauto_m2t.py` | Full automation executor (~640 lines): entities, conditions, actions, threading |
| `sensor.py.jinja` | `entity_to_code.py` | Standalone virtual sensor with value generators + noise |
| `actuator.py.jinja` | `entity_to_code.py` | Standalone virtual actuator (subscriber only) |
| `clock.py.jinja` | both entity codegen files | System clock entity |
| `ventity_merged.py.jinja` | `ventities_merged.py` | All virtual entities in one file |

## CONVENTIONS

- Templates emit `#!/usr/bin/env python` — generated files are directly executable
- All generated code imports from `commlib.node.Node`, `commlib.msg.PubSubMessage`
- Broker type determines `commlib.transports.{mqtt|amqp|redis}.ConnectionParameters`
- Entity names are CamelCased via `entity.camel_name` for class names (e.g., `weather_station` → `WeatherStationMsg`)
- Entity source/URI accessed as `entity.source.name`, `entity.source.host`, `entity.uri` (NOT `entity.broker` or `entity.topic`)
- RTMonitor source accessed as `rt_monitor.source.name` (NOT `rt_monitor.broker`)
- Condition expressions are inlined as strings: `{{ auto.condition.cond_lambda.replace('.value', '') }}`

## ANTI-PATTERNS

- `smauto.py.jinja` contains a `KafkaBroker` branch (line ~449) — no Kafka support exists; dead code
- Template logic uses `__class__.__name__` checks (e.g., `attr.generator.__class__.__name__ == 'GaussianFun'`) — fragile
- `smauto.py.jinja` redefines `Entity`, `Automation`, `Condition` etc. inline — these are NOT the same classes as in `smauto/lib/`; they're self-contained runtime classes for the generated code
