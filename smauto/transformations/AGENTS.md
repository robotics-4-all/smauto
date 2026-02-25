# transformations/ — Code Generation (M2T)

## OVERVIEW

Model-to-Text transformations. Takes a parsed SmAuto model and generates executable Python code via Jinja2 templates.

## WHERE TO LOOK

| File | Function | Output |
|------|----------|--------|
| `smauto_m2t.py` | `smauto_m2t(model_path)` | Single Python file running all automations |
| `entity_to_code.py` | `model_to_vnodes(model_path)` | One Python file per entity (virtual entity simulator) |
| `ventities_merged.py` | `model_to_vent(model_path)` | Single Python file with all virtual entities merged |

## PIPELINE

1. `build_model(model_path)` → parsed model object
2. `select_clock_broker(model)` → picks first non-fake broker for system_clock
3. Inject `system_clock` entity from built-in model, swap its broker
4. For automations: call `auto.condition.build()` to generate expression strings
5. Render Jinja2 template with model context → Python source code string

## CONVENTIONS

- `select_clock_broker()` and `make_executable()` are imported from `smauto.utils` — single source of truth
- All three files create their own `jinja2.Environment` at module level (not shared)
- `build_model()` is called inside each transformation — they take `model_path: str`, not a model object
- Generated code depends on `commlib-py` at runtime (not a project dependency)
