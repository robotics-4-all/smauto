#!/usr/bin/env python3
import os
import re
from pathlib import Path


def migrate_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # Regex to find Automation blocks
    # We assume 'end' is on a separate line
    pattern = re.compile(r"Automation\s+(\w+)(.*?)^\s*end", re.DOTALL | re.MULTILINE)

    def replace_automation(match):
        name = match.group(1)
        body = match.group(2)

        # Extract properties
        props = {}
        actions = []

        lines = body.split("\n")
        iterator = iter(lines)

        current_key = None
        current_value = []

        for line in iterator:
            stripped = line.strip()
            if not stripped:
                continue

            # Check for keys
            key_match = re.match(r"^\s*(\w+):(.*)", line)
            if key_match and not line.strip().startswith("-"):
                # New key found
                if current_key:
                    props[current_key] = "\n".join(current_value).strip()

                current_key = key_match.group(1)
                val = key_match.group(2).strip()
                current_value = [val] if val else []

                if current_key == "actions":
                    # Actions block started
                    pass
            elif current_key == "actions":
                # Inside actions
                if stripped.startswith("-"):
                    actions.append(stripped[1:].strip())
            elif current_key:
                # Continuation of previous key (e.g. multiline condition)
                current_value.append(stripped)

        # Save last prop
        if current_key:
            props[current_key] = "\n".join(current_value).strip()

        # Construct new syntax
        new_block = f"AUTO {name}"

        if "condition" in props:
            new_block += f" ON {props['condition']}"
            del props["condition"]

        new_block += "\n"

        # Handle other props
        for k, v in props.items():
            if k == "actions":
                continue

            # Handle lists (starts, stops, after)
            if k in ["starts", "stops", "after"]:
                # Convert "- item" lines to comma separated
                items = [item.strip("- ").strip() for item in v.split("\n") if item.strip()]
                v = ", ".join(items)
                new_block += f"    {k}: {v}\n"
            else:
                new_block += f"    {k}: {v}\n"

        new_block += "DO\n"
        for action in actions:
            new_block += f"    {action}\n"

        new_block += ";"

        return new_block

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
