#!/usr/bin/env python3
"""
Script to validate entity generator on all SMAuto model examples.

This script discovers all .auto files in the examples/ directory,
runs the entity generator on each one (both merged and individual modes),
and validates the generated Python code using syntax and compilation checks.
"""

import os
import sys
import ast
import py_compile
import tempfile
from pathlib import Path
from typing import List, Tuple
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

# Add the parent directory to the path to import smauto
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from smauto.transformations import model_to_vnodes, model_to_vent


console = Console()


def find_auto_files(examples_dir: Path) -> List[Path]:
    """Find all .auto files in the examples directory."""
    auto_files = list(examples_dir.rglob("*.auto"))
    return sorted(auto_files)


def validate_python_code(code: str, filename: str = "generated.py") -> Tuple[bool, str]:
    """
    Validate Python code using AST parser and compilation.

    Returns:
        Tuple of (success: bool, error_message: str)
    """
    # First, try to parse the code
    try:
        ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    # Then, try to compile it
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        py_compile.compile(tmp_path, doraise=True)
        return True, ""
    except py_compile.PyCompileError as e:
        return False, f"Compilation error: {e}"
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def generate_and_validate_merged(model_path: Path) -> Tuple[bool, str]:
    """
    Generate merged virtual entities and validate the code.

    Returns:
        Tuple of (success: bool, error_message: str)
    """
    try:
        # Generate merged virtual entities
        vent_code = model_to_vent(str(model_path))

        # Validate the generated code
        success, error = validate_python_code(vent_code, "merged_entities.py")
        return success, error
    except Exception as e:
        return False, f"Generation error: {e}"


def generate_and_validate_individual(model_path: Path) -> Tuple[bool, str, int]:
    """
    Generate individual virtual entities and validate the code.

    Returns:
        Tuple of (success: bool, error_message: str, count: int)
    """
    try:
        # Generate individual virtual entities
        vnodes = model_to_vnodes(str(model_path))

        if not vnodes:
            return True, "No sensor entities to generate", 0

        # Validate each generated entity
        for vnode, code in vnodes:
            success, error = validate_python_code(code, f"{vnode.name}.py")
            if not success:
                return False, f"Entity '{vnode.name}': {error}", len(vnodes)

        return True, "", len(vnodes)
    except Exception as e:
        return False, f"Generation error: {e}", 0


def main():
    """Main validation function."""
    examples_dir = PROJECT_ROOT / "examples"

    if not examples_dir.exists():
        console.print(f"[red]Error: Examples directory not found: {examples_dir}[/red]")
        return 1

    console.print("[bold cyan]SMAuto Entity Generator Validation[/bold cyan]")
    console.print(f"Searching for .auto files in: {examples_dir}\n")

    # Find all .auto files
    auto_files = find_auto_files(examples_dir)

    if not auto_files:
        console.print("[yellow]No .auto files found in examples directory[/yellow]")
        return 0

    console.print(f"Found {len(auto_files)} model(s) to test\n")

    # Test each model
    results_merged = []
    results_individual = []

    with Progress(console=console) as progress:
        task = progress.add_task(
            "[cyan]Testing entity generation...",
            total=len(auto_files) * 2,
        )

        for auto_file in auto_files:
            relative_path = auto_file.relative_to(PROJECT_ROOT)

            # Test merged mode
            success, error = generate_and_validate_merged(auto_file)
            results_merged.append((relative_path, success, error))
            progress.update(task, advance=1)

            # Test individual mode
            success, error, count = generate_and_validate_individual(auto_file)
            results_individual.append((relative_path, success, error, count))
            progress.update(task, advance=1)

    # Display results for merged mode
    console.print("\n[bold]Merged Entity Generation Results:[/bold]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Model", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Error", style="red")

    passed_merged = 0
    failed_merged = 0

    for model_path, success, error in results_merged:
        if success:
            table.add_row(str(model_path), "[green]✓ PASS[/green]", "")
            passed_merged += 1
        else:
            table.add_row(str(model_path), "[red]✗ FAIL[/red]", error)
            failed_merged += 1

    console.print(table)

    # Display results for individual mode
    console.print("\n[bold]Individual Entity Generation Results:[/bold]\n")

    table2 = Table(show_header=True, header_style="bold magenta")
    table2.add_column("Model", style="cyan")
    table2.add_column("Status", justify="center")
    table2.add_column("Entities", justify="center")
    table2.add_column("Error", style="red")

    passed_individual = 0
    failed_individual = 0

    for model_path, success, error, count in results_individual:
        if success:
            table2.add_row(str(model_path), "[green]✓ PASS[/green]", str(count), "")
            passed_individual += 1
        else:
            table2.add_row(str(model_path), "[red]✗ FAIL[/red]", str(count), error)
            failed_individual += 1

    console.print(table2)

    # Summary
    console.print("\n[bold]Summary:[/bold]")
    console.print("  Merged Mode:")
    console.print(f"    Total:  {len(results_merged)}")
    console.print(f"    [green]Passed: {passed_merged}[/green]")
    console.print(f"    [red]Failed: {failed_merged}[/red]")
    console.print("\n  Individual Mode:")
    console.print(f"    Total:  {len(results_individual)}")
    console.print(f"    [green]Passed: {passed_individual}[/green]")
    console.print(f"    [red]Failed: {failed_individual}[/red]")

    total_failed = failed_merged + failed_individual

    if total_failed > 0:
        console.print(
            f"\n[red]Entity generation validation"
            f" failed with {total_failed} error(s)[/red]"
        )
        return 1
    else:
        console.print(
            "\n[green]All entity generators validated successfully! ✓[/green]"
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
