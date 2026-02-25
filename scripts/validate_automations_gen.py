#!/usr/bin/env python3
"""
Script to validate automations generator on all SMAuto model examples.

This script discovers all .auto files in the examples/ directory,
runs the automations generator on each one, and validates the generated
Python code using syntax and compilation checks.
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

from smauto.transformations import smauto_m2t


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


def generate_and_validate_automations(model_path: Path) -> Tuple[bool, str, str]:
    """
    Generate automations code and validate it.

    Returns:
        Tuple of (success: bool, error_message: str, status: str)
        status can be: "success", "no_automations", "error"
    """
    try:
        # Try to generate automations code
        auto_code = smauto_m2t(str(model_path))

        # Validate the generated code
        success, error = validate_python_code(auto_code, "automations.py")
        if success:
            return True, "", "success"
        else:
            return False, error, "error"

    except ValueError as e:
        # This is expected for models without automations
        if "does not include any Automations" in str(e):
            return True, "No automations defined", "no_automations"
        else:
            return False, f"Generation error: {e}", "error"
    except Exception as e:
        return False, f"Generation error: {e}", "error"


def main():
    """Main validation function."""
    examples_dir = PROJECT_ROOT / "examples"

    if not examples_dir.exists():
        console.print(f"[red]Error: Examples directory not found: {examples_dir}[/red]")
        return 1

    console.print("[bold cyan]SMAuto Automations Generator Validation[/bold cyan]")
    console.print(f"Searching for .auto files in: {examples_dir}\n")

    # Find all .auto files
    auto_files = find_auto_files(examples_dir)

    if not auto_files:
        console.print("[yellow]No .auto files found in examples directory[/yellow]")
        return 0

    console.print(f"Found {len(auto_files)} model(s) to test\n")

    # Test each model
    results = []

    with Progress(console=console) as progress:
        task = progress.add_task(
            "[cyan]Testing automations generation...",
            total=len(auto_files),
        )

        for auto_file in auto_files:
            relative_path = auto_file.relative_to(PROJECT_ROOT)
            success, error, status = generate_and_validate_automations(auto_file)
            results.append((relative_path, success, error, status))
            progress.update(task, advance=1)

    # Display results
    console.print("\n[bold]Automations Generation Results:[/bold]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Model", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Note", style="yellow")

    passed = 0
    failed = 0
    skipped = 0

    for model_path, success, error, status in results:
        if success:
            if status == "no_automations":
                table.add_row(
                    str(model_path), "[yellow]● SKIP[/yellow]", "No automations"
                )
                skipped += 1
            else:
                table.add_row(str(model_path), "[green]✓ PASS[/green]", "")
                passed += 1
        else:
            table.add_row(str(model_path), "[red]✗ FAIL[/red]", error)
            failed += 1

    console.print(table)

    # Summary
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Total:   {len(results)}")
    console.print(f"  [green]Passed:  {passed}[/green]")
    console.print(f"  [yellow]Skipped: {skipped}[/yellow]")
    console.print(f"  [red]Failed:  {failed}[/red]")

    if failed > 0:
        console.print(
            f"\n[red]Automations generation validation"
            f" failed with {failed} error(s)[/red]"
        )
        return 1
    else:
        console.print(
            "\n[green]All automations generators validated successfully! ✓[/green]"
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
