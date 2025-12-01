#!/bin/bash

# Script to run all SMAuto validation tests
# This script runs model validation, entity generator validation,
# and automations generator validation in sequence.

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "  SMAuto Validation Suite"
echo "========================================"
echo ""

# Run model validation
echo "[1/3] Running model validation..."
echo "----------------------------------------"
python3 "$SCRIPT_DIR/validate_examples.py"
RESULT_1=$?
echo ""

# Run entity generator validation
echo "[2/3] Running entity generator validation..."
echo "----------------------------------------"
python3 "$SCRIPT_DIR/validate_entity_gen.py"
RESULT_2=$?
echo ""

# Run automations generator validation
echo "[3/3] Running automations generator validation..."
echo "----------------------------------------"
python3 "$SCRIPT_DIR/validate_automations_gen.py"
RESULT_3=$?
echo ""

# Summary
echo "========================================"
echo "  Validation Suite Summary"
echo "========================================"
echo ""

if [ $RESULT_1 -eq 0 ]; then
    echo "✓ Model Validation:        PASSED"
else
    echo "✗ Model Validation:        FAILED"
fi

if [ $RESULT_2 -eq 0 ]; then
    echo "✓ Entity Generator:        PASSED"
else
    echo "✗ Entity Generator:        FAILED"
fi

if [ $RESULT_3 -eq 0 ]; then
    echo "✓ Automations Generator:   PASSED"
else
    echo "✗ Automations Generator:   FAILED"
fi

echo ""

# Overall result
TOTAL_FAILED=$((RESULT_1 + RESULT_2 + RESULT_3))

if [ $TOTAL_FAILED -eq 0 ]; then
    echo "========================================"
    echo "  All validations PASSED! ✓"
    echo "========================================"
    exit 0
else
    echo "========================================"
    echo "  Some validations FAILED! ✗"
    echo "========================================"
    exit 1
fi
