# SMAuto Validation Scripts

This directory contains validation scripts for the SMAuto DSL project. These scripts automatically test all examples and code generators to ensure they work correctly.

## Scripts Overview

### 1. `validate_examples.py`
Validates all SMAuto model files (`.auto`) in the `examples/` directory.

**What it does:**
- Discovers all `.auto` files recursively in `examples/`
- Validates each model using the SMAuto language parser
- Reports validation results with detailed error messages
- Returns exit code 0 on success, 1 on failure

**Usage:**
```bash
python3 scripts/validate_examples.py
```

### 2. `validate_entity_gen.py`
Tests the entity generator on all examples and validates the generated Python code.

**What it does:**
- Runs the entity generator in both **merged** and **individual** modes
- Validates generated Python code using AST parsing and compilation
- Reports results for each mode separately
- Returns exit code 0 on success, 1 on failure

**Validation checks:**
- Python syntax validation (`ast.parse()`)
- Python compilation (`py_compile.compile()`)

**Usage:**
```bash
python3 scripts/validate_entity_gen.py
```

### 3. `validate_automations_gen.py`
Tests the automations generator on all examples and validates the generated Python code.

**What it does:**
- Runs the automations generator on each example
- Validates generated Python code using AST parsing and compilation
- Gracefully handles models without automations (marked as SKIP)
- Returns exit code 0 on success, 1 on failure

**Validation checks:**
- Python syntax validation (`ast.parse()`)
- Python compilation (`py_compile.compile()`)

**Usage:**
```bash
python3 scripts/validate_automations_gen.py
```

### 4. `run_all_validations.sh`
Convenience script that runs all three validation scripts in sequence.

**What it does:**
- Runs model validation
- Runs entity generator validation
- Runs automations generator validation
- Provides overall summary of all tests
- Returns exit code 0 if all tests pass, 1 if any fail

**Usage:**
```bash
bash scripts/run_all_validations.sh
# or
chmod +x scripts/run_all_validations.sh
./scripts/run_all_validations.sh
```

## Requirements

All scripts require the following Python packages (installed with SMAuto):
- `textx` - For DSL parsing
- `rich` - For colored console output
- `jinja2` - For code generation templates

These are already included in the SMAuto `requirements.txt`.

## Example Output

### Successful validation:
```
SMAuto Model Validation
Searching for .auto files in: /path/to/examples

Found 13 model(s) to validate

Validation Results:

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━┓
┃ Model                        ┃ Status ┃ Error ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━┩
│ examples/simple/model.auto   │ ✓ PASS │       │
│ examples/advanced/model.auto │ ✓ PASS │       │
└──────────────────────────────┴────────┴───────┘

Summary:
  Total:  13
  Passed: 13
  Failed: 0

All models validated successfully! ✓
```

### Failed validation:
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Model                        ┃ Status ┃ Error                   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ examples/broken/model.auto   │ ✗ FAIL │ Syntax error at line 10 │
└──────────────────────────────┴────────┴─────────────────────────┘

Summary:
  Total:  1
  Passed: 0
  Failed: 1

Validation failed with 1 error(s)
```

## Integration with CI/CD

These scripts can be easily integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run SMAuto Validations
  run: |
    pip install -e .
    bash scripts/run_all_validations.sh
```

## Development

To add new validation checks:
1. Edit the relevant script (`validate_*.py`)
2. Add your validation logic
3. Update the results table to include new information
4. Test with `python3 scripts/validate_*.py`

## Troubleshooting

**Import errors:**
- Make sure SMAuto is installed: `pip install -e .`
- Scripts automatically add the project root to `sys.path`

**Permission denied:**
- Make scripts executable: `chmod +x scripts/*.sh scripts/*.py`

**No models found:**
- Ensure you're running from the project root directory
- Check that the `examples/` directory exists
