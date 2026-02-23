# grammar/ — textX Grammar Definition

## OVERVIEW

Modular textX grammar files defining SmAuto's concrete syntax. `smauto.tx` is the root; others are imported.

## STRUCTURE

| File | DSL Concept | Key Rules |
|------|-------------|-----------|
| `smauto.tx` | Root model | `SmAutoModel`, `Metadata`, `RTMonitor` |
| `entity.tx` | Entities + Attributes | `Entity`, `*Attribute`, `*ValueGen`, `Noise` |
| `automation.tx` | Automations + Actions | `Automation`, `*SetAction`, `StartAction`, `StopAction` |
| `condition.tx` | Conditions + Operators | `Condition`, `ConditionGroup`, `*Condition` variants, all operators |
| `communication.tx` | Brokers + Auth | `MQTTBroker`, `AMQPBroker`, `RedisBroker`, `Auth*` |
| `types.tx` | Primitive types | `Time`, `Date`, `List`, `Dict` |
| `utils.tx` | Shared rules | `FQN`, `Import`, `Comment` |

## CONVENTIONS

- **Keyword-block syntax**: `Keyword name ... end` for Broker/Entity/Metadata; `AUTO name ... ;` for Automation
- **Ordered assignments with `#`**: Rules use `(...)#` — textX ordered assignment groups
- **Cross-references via FQN**: Attributes referenced as `[TypeName:FQN|+m:scope]` (e.g., `[IntAttribute:FQN|+m:entities.attributes]`)
- **Optional fields**: `(?` suffix on grammar lines — most Entity/Automation fields are optional
- **Import chain**: `smauto.tx` → `automation.tx` → `entity.tx` → `communication.tx` → `utils.tx`; `types.tx` imported by multiple files

## ANTI-PATTERNS

- Never add a grammar rule for a new concept without a corresponding Python class in `lib/` AND registration in `CUSTOM_CLASSES`
- Never define `FQN` in multiple files — it's in both `condition.tx` (line 175) and `utils.tx` (line 2); `condition.tx` version takes precedence
- The `NID` rule is defined in both `types.tx` and `utils.tx` — textX resolves by import order
- `MathExpression` in `condition.tx` uses recursive `op` assignment — unusual textX pattern, handle carefully
- `EntityType` only supports `sensor | actuator | hybrid` — `hybrid` has no codegen support yet

## NOTES

- Grammar comments use `//` and `/* */` (defined in `utils.tx`)
- The `#` in `(...)#` is textX syntax for "unordered group" — allows properties in any order
- Automation syntax changed from `Automation name ... end` to `AUTO name WITH ... ON ... DO ... ;` (migration scripts exist in `scripts/`)
