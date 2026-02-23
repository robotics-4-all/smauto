#!/usr/bin/env python3
"""
Script to validate all SMAuto model examples.

This script discovers all .auto files in the examples/ directory
and validates them using the SMAuto language parser.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

# Add the parent directory to the path to import smauto
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from smauto.language import build_model


console = Console()


def find_auto_files(examples_dir: Path) -> List[Path]:
    """Find all .auto files in the examples directory."""
    auto_files = list(examples_dir.rglob("*.auto"))
    return sorted(auto_files)


def validate_model(model_path: Path) -> Tuple[bool, str]:
    """
    Validate a single SMAuto model.
    
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    try:
        model = build_model(str(model_path))
        return True, ""
    except Exception as e:
        return False, str(e)


def main():
    """Main validation function."""
    examples_dir = PROJECT_ROOT / "examples"
    
    if not examples_dir.exists():
        console.print(f"[red]Error: Examples directory not found: {examples_dir}[/red]")
        return 1
    
    console.print("[bold cyan]SMAuto Model Validation[/bold cyan]")
    console.print(f"Searching for .auto files in: {examples_dir}\n")
    
    # Find all .auto files
    auto_files = find_auto_files(examples_dir)
    
    if not auto_files:
        console.print("[yellow]No .auto files found in examples directory[/yellow]")
        return 0
    
    console.print(f"Found {len(auto_files)} model(s) to validate\n")
    
    # Validate each model
    results = []
    with Progress(console=console) as progress:
        task = progress.add_task("[cyan]Validating models...", total=len(auto_files))
        
        for auto_file in auto_files:
            relative_path = auto_file.relative_to(PROJECT_ROOT)
            success, error = validate_model(auto_file)
            results.append((relative_path, success, error))
            progress.update(task, advance=1)
    
    # Display results
    console.print("\n[bold]Validation Results:[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Model", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Error", style="red")
    
    passed = 0
    failed = 0
    
    for model_path, success, error in results:
        if success:
            table.add_row(str(model_path), "[green]✓ PASS[/green]", "")
            passed += 1
        else:
            table.add_row(str(model_path), "[red]✗ FAIL[/red]", error)
            failed += 1
    
    console.print(table)
    
    # Summary
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  Total:  {len(results)}")
    console.print(f"  [green]Passed: {passed}[/green]")
    console.print(f"  [red]Failed: {failed}[/red]")
    
    if failed > 0:
        console.print(f"\n[red]Validation failed with {failed} error(s)[/red]")
        return 1
    else:
        console.print(f"\n[green]All models validated successfully! ✓[/green]")
        return 0


if __name__ == "__main__":
    sys.exit(main())
