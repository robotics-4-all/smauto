#!/usr/bin/env python3
"""
Script to migrate automations to new action syntax:
1. Remove starts/stops from WITH block
2. Add SET prefix to attribute assignments
3. Convert starts/stops to START/STOP actions in DO block
"""

import os
import re
from pathlib import Path


def migrate_automation(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # Pattern to match automation blocks
    # AUTO name WITH ... ON condition DO ... ;
    pattern = re.compile(
        r"AUTO\s+(\w+)\s*\n"  # AUTO name
        r"(?:WITH\s*\n(.*?)\n)?"  # Optional WITH block
        r"ON\s+(.+?)\s*\n"  # ON condition
        r"DO\s*\n"  # DO
        r"(.*?)\n"  # Actions
        r"\s*;",  # End
        re.DOTALL | re.MULTILINE,
    )

    def replace_auto(match):
        name = match.group(1)
        with_block = match.group(2) if match.group(2) else ""
        condition = match.group(3).strip()
        actions_block = match.group(4)

        # Parse WITH block to extract starts/stops
        starts = []
        stops = []
        new_with_lines = []

        if with_block:
            for line in with_block.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("starts:"):
                    # Extract automation names
                    starts_str = line.replace("starts:", "").strip()
                    starts = [s.strip() for s in starts_str.split(",")]
                elif line.startswith("stops:"):
                    stops_str = line.replace("stops:", "").strip()
                    stops = [s.strip() for s in stops_str.split(",")]
                else:
                    new_with_lines.append("    " + line)

        # Process actions block - add SET prefix to attribute assignments
        new_actions = []
        for line in actions_block.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Check if it's an attribute assignment (contains entity.attribute: value)
            if ":" in line and "." in line:
                # Add SET prefix
                new_actions.append("    SET " + line)
            else:
                new_actions.append("    " + line)

        # Add START actions for each starts automation
        for auto in starts:
            new_actions.append(f"    START {auto}")

        # Add STOP actions for each stops automation
        for auto in stops:
            new_actions.append(f"    STOP {auto}")

        # Build new automation
        result = f"AUTO {name}\n"
        if new_with_lines:
            result += "WITH\n"
            result += "\n".join(new_with_lines) + "\n"
        result += f"ON {condition}\n"
        result += "DO\n"
        result += "\n".join(new_actions) + "\n"
        result += ";"

        return result

    new_content = pattern.sub(replace_auto, content)

    if new_content != content:
        print(f"Migrating {filepath}")
        with open(filepath, "w") as f:
            f.write(new_content)
        return True
    return False


def main():
    root_dir = Path(__file__).parent.parent / "examples"
    count = 0
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".auto"):
                if migrate_automation(os.path.join(root, file)):
                    count += 1
    print(f"Migrated {count} files.")


if __name__ == "__main__":
    main()
