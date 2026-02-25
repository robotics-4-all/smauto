#!/usr/bin/env python3
"""
Migrate SmAuto models from imperative syntax (AUTO...WITH...ON...DO...;)
to ECA formalism (Automation...when...then...config...depends on...triggers...terminates...end).

Transformations:
  - AUTO name       -> Automation name
  - WITH block      -> config block (after: extracted to depends on)
  - ON condition    -> when condition
  - DO              -> then
  - SET attr: value -> attr <- value
  - START auto      -> triggers auto
  - STOP auto       -> terminates auto
  - ;               -> end
"""

import os
import re
from pathlib import Path


def migrate_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # Match automation blocks: AUTO name (WITH ...)? ON condition DO actions ;
    pattern = re.compile(
        r"AUTO\s+(\w+)\s*\n"  # AUTO name
        r"((?:WITH\s*\n(?:.*?\n))*?)?"  # Optional WITH block (non-greedy)
        r"ON\s+(.*?)\n"  # ON condition (may be multiline via lookahead)
        r"DO\s*\n"  # DO
        r"(.*?)"  # Actions block
        r"\s*;",  # Terminator
        re.DOTALL,
    )

    def replace_automation(match):
        name = match.group(1)
        with_block = match.group(2) or ""
        condition = match.group(3).strip()
        actions_block = match.group(4)

        # Parse WITH block — separate config properties from after:
        config_lines = []
        after_autos = []

        for line in with_block.split("\n"):
            stripped = line.strip()
            if not stripped or stripped == "WITH":
                continue
            if stripped.startswith("after:"):
                after_str = stripped.replace("after:", "").strip()
                after_autos = [a.strip() for a in after_str.split(",") if a.strip()]
            else:
                config_lines.append(stripped)

        # Parse actions — separate SET, START, STOP
        set_actions = []
        triggers = []
        terminates = []

        for line in actions_block.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("START "):
                triggers.append(stripped[6:].strip())
            elif stripped.startswith("STOP "):
                terminates.append(stripped[5:].strip())
            elif stripped.startswith("SET "):
                # SET entity.attr: value -> entity.attr <- value
                set_part = stripped[4:]  # Remove "SET "
                colon_idx = set_part.find(":")
                if colon_idx != -1:
                    attr = set_part[:colon_idx].strip()
                    value = set_part[colon_idx + 1 :].strip()
                    set_actions.append(f"{attr} <- {value}")
                else:
                    set_actions.append(set_part)
            else:
                set_actions.append(stripped)

        # Build new automation block
        lines = [f"Automation {name}"]

        # when section
        lines.append("    when")
        for cond_line in condition.split("\n"):
            lines.append(f"        {cond_line.strip()}")

        # then section
        if set_actions:
            lines.append("    then")
            for action in set_actions:
                lines.append(f"        {action}")

        # config section
        if config_lines:
            lines.append("    config")
            for cl in config_lines:
                lines.append(f"        {cl}")

        # depends on section
        if after_autos:
            lines.append("    depends on")
            lines.append(f"        {', '.join(after_autos)}")

        # triggers section
        if triggers:
            lines.append("    triggers")
            for t in triggers:
                lines.append(f"        {t}")

        # terminates section
        if terminates:
            lines.append("    terminates")
            for t in terminates:
                lines.append(f"        {t}")

        lines.append("end")
        return "\n".join(lines)

    new_content = pattern.sub(replace_automation, content)

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
                if migrate_file(os.path.join(root, file)):
                    count += 1
    print(f"Migrated {count} files.")


if __name__ == "__main__":
    main()
