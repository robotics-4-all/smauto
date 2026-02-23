# SmAuto DSL — Project Knowledge Base

**Generated:** 2026-02-23
**Commit:** 5760888
**Branch:** devel

## OVERVIEW

SmAuto is a Domain-Specific Language for programming IoT automation scenarios in smart environments. Built with Python + textX, it parses `.auto` model files into a metamodel and generates executable Python code via Jinja2 M2T transformations.

## STRUCTURE

```
smauto/                  # Main Python package
├── grammar/             # textX grammar files (.tx) — the language definition
├── lib/                 # Domain model classes (Automation, Entity, Broker, Condition)
├── transformations/     # M2T code generators (model → Python)
├── templates/           # Jinja2 templates for generated code
├── cli/                 # Click-based CLI (`smauto` command)
├── api/                 # FastAPI REST API for remote compilation
├── builtin_models/      # Built-in .br/.ent models (fake_broker, system_clock)
├── utils.py             # Shared utilities (select_clock_broker, make_executable)
└── definitions.py       # Path constants (TEMPLATES_PATH, BUILTIN_MODELS)
examples/                # Sample .auto models (6 progressive real-world IoT scenarios)
scripts/                 # Validation scripts (model, entity gen, automations gen)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Change DSL syntax | `smauto/grammar/*.tx` | Modular textX grammars, `smauto.tx` is root |
| Add/modify domain concept | `smauto/lib/*.py` | Must also register in `language.py` CUSTOM_CLASSES |
| Change generated output | `smauto/templates/*.jinja` | Jinja2 templates for Python codegen |
| Change codegen pipeline | `smauto/transformations/` | M2T logic, model traversal |
| Add CLI command | `smauto/cli/cli.py` | Click group, calls `build_model()` + transformations |
| Add API endpoint | `smauto/api/api.py` | FastAPI, API key auth via `X-API-Key` header |
| Add built-in model | `smauto/builtin_models/` | `.br` (broker) and `.ent` (entity) files |
| Validate all examples | `bash scripts/run_all_validations.sh` | Or individual `python3 scripts/validate_*.py` |
| Test with a model | `examples/01_smart_light/model.auto` | Best starting point |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `get_metamodel()` | function | `language.py` | Creates textX metamodel from grammar, registers classes + scoping |
| `build_model()` | function | `language.py` | Parses `.auto` file → model object |
| `smauto_m2t()` | function | `transformations/smauto_m2t.py` | Model → executable Python (automations) |
| `model_to_vnodes()` | function | `transformations/entity_to_code.py` | Model → virtual entity code (per-entity) |
| `model_to_vent()` | function | `transformations/ventities_merged.py` | Model → merged virtual entities file |
| `CUSTOM_CLASSES` | list | `language.py` | All domain classes registered with textX |
| `model_proc()` | function | `language.py` | Post-parse validation (unique names, time range checks) |
| `class_provider()` | function | `language.py` | textX class lookup for custom class mapping |

## CONVENTIONS

- **Grammar modularization**: Each DSL concept has its own `.tx` file imported by `smauto.tx`
- **Custom classes pattern**: Every grammar rule with behavior has a Python class in `smauto/lib/`, registered in `CUSTOM_CLASSES` in `language.py`
- **Scoping**: Uses `FQNImportURI` for imports + `FQNGlobalRepo` for built-in broker/entity models
- **No logging**: Project uses `print()` via `rich` library throughout — no `logging` module
- **No custom exceptions**: Relies on built-in exceptions + textX's `TextXSemanticError`
- **Pre-commit**: ruff linter + ruff formatter (v0.1.6)
- **Model file extension**: `.auto` for user models, `.br` for broker builtins, `.ent` for entity builtins

## ANTI-PATTERNS (THIS PROJECT)

- Do NOT add grammar rules without corresponding Python classes in `smauto/lib/` and registration in `CUSTOM_CLASSES`
- Do NOT use `/` in topic strings — use `.` notation (e.g., `bedroom.lamp` not `bedroom/lamp`)
- Do NOT apply Value/Noise generators to actuator entities — only `sensor` and `robot` types
- Do NOT define actions targeting sensor-only attributes — actions target `actuator`/`robot` entities
- Do NOT set `freq` on actuator entities — only for `sensor`/`robot`
- `select_clock_broker()` and `make_executable()` live in `smauto/utils.py` — single source of truth

## UNIQUE STYLES

- **Condition evaluation via `eval()`**: Conditions are built as Python expression strings at parse time, then evaluated at runtime with `eval()` and an entity dict context
- **Automation grammar uses ECA (Event-Condition-Action) syntax**: `Automation name when condition then actions config properties depends on ... triggers ... terminates ... end`
- **Action assignment uses `<-` operator**: `entity.attr <- value` (formal notation matching $x.a \leftarrow e$)
- **textX `parent` parameter**: All custom classes take `parent` as first arg (textX convention for tree navigation)
- **`auto_init_attributes=False`**: Metamodel disables auto-init — classes must handle all initialization

## COMMANDS

```bash
pip install .                                    # Install package
pip install -e .                                 # Dev install
smauto validate model.auto                       # Validate a model
smauto gen model.auto                            # Compile automations → Python
smauto genv model.auto                           # Generate virtual entities (per-entity)
smauto genv -m model.auto                        # Generate virtual entities (merged)
bash scripts/run_all_validations.sh              # Run all validation scripts
docker build -t smauto . && docker run -p 8080:8080 smauto  # Docker deployment
```

## NOTES

- **No tests exist** — `pytest` is in `setup.cfg[test]` extras but no test files or `tests/` dir
- CI pipeline is **deploy-only** (SSH + Docker on push to `main`) — no test step
- The `system_clock` entity is a built-in injected at codegen time, its broker is swapped to the first real broker in the model
- `commlib-py` is required at **runtime** by generated code, but NOT in `requirements.txt` (it's a generated-code dependency)
- The `graph` CLI command referenced in README is not implemented in `cli.py`
- `ventities_merged.py` references `KafkaBroker` but no Kafka support exists in the grammar or broker classes
- Some example READMEs reference old syntax (YAML-like) that no longer matches current grammar
