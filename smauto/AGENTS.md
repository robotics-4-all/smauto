# smauto/ — Main Package

## OVERVIEW

Root Python package. `language.py` is the central orchestrator — everything flows through it.

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| Metamodel creation | `language.py:get_metamodel()` | Loads grammar, registers custom classes, sets up scoping |
| Parse a model file | `language.py:build_model()` | Returns populated model object |
| Post-parse validation | `language.py:model_proc()` | Unique names, time range checks |
| Add a custom class | `language.py:CUSTOM_CLASSES` | List of all registered domain classes |
| Path constants | `definitions.py` | `TEMPLATES_PATH`, `BUILTIN_MODELS`, `MODEL_REPO_PATH` |
| Shared utilities | `utils.py` | `select_clock_broker()`, `make_executable()` |

## CODE MAP

| Symbol | Role |
|--------|------|
| `get_metamodel(debug, global_repo)` | Factory — creates textX metamodel from `grammar/smauto.tx` |
| `build_model(model_path)` | Convenience — calls `get_metamodel()` then `model_from_file()` |
| `class_provider(name)` | Lookup function passed to textX for custom class resolution |
| `get_scope_providers()` | Configures `FQNImportURI` + `FQNGlobalRepo` for built-in models |
| `ENTITY_BUILTINS` | Hardcoded `system_clock` entity (also loaded via `.ent` file) |
| `smauto_language()` | textX `@language` decorator — registers SmAuto as a textX language |

## CONVENTIONS

- All custom classes take `parent` as first constructor arg (textX requirement)
- `auto_init_attributes=False` — every class must explicitly handle its own init
- `MODEL_REPO_PATH` env var (`SMAUTO_MODEL_REPO`) allows external model repositories
- CLI entry point: `smauto.cli.cli:main` (registered in `setup.cfg`)
- API entry point: `smauto.api:api` (uvicorn target in Dockerfile)

## ANTI-PATTERNS

- Never call `metamodel_from_file()` directly — always use `get_metamodel()` to ensure classes + scoping are registered
- Never modify `ENTITY_BUILTINS` at runtime — the `system_clock` is also loaded from `builtin_models/entity/system_clock.ent`
