#!/usr/bin/env python3
"""
Script to add WITH keyword to automations in .auto files.
Transforms:
    AUTO name ON condition
        property: value
    DO

To:
    AUTO name ON condition
    WITH
        property: value
    DO
"""

import os
import re
from pathlib import Path


def add_with_keyword(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # Pattern: AUTO ... ON ... (multiline condition) then properties before DO
    # We need to find automations and insert WITH before the first property

    # Split into lines for easier processing
    lines = content.split("\n")
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        new_lines.append(line)

        # Check if this is an AUTO line
        if line.strip().startswith("AUTO "):
            # Look ahead to find DO
            j = i + 1
            found_do = False
            first_property_idx = None

            while j < len(lines):
                if lines[j].strip() == "DO":
                    found_do = True
                    break
                # Check if this is a property line
                # (starts with spaces, has key: value)
                prop_match = re.match(r"^\s+\w+:", lines[j])
                not_comment = not lines[j].strip().startswith("//")
                if prop_match and not_comment:
                    if first_property_idx is None:
                        first_property_idx = j
                j += 1

            # If we found properties before DO, insert WITH
            if found_do and first_property_idx is not None:
                # Insert WITH line before first property
                # Collect remaining lines up to first_property_idx
                for k in range(i + 1, first_property_idx):
                    new_lines.append(lines[k])

                # Insert WITH
                new_lines.append("WITH")

                # Add remaining lines including first property up to and including DO
                for k in range(first_property_idx, j + 1):
                    new_lines.append(lines[k])

                # Skip to after DO
                i = j + 1
                continue

        i += 1

    new_content = "\n".join(new_lines)

    if new_content != content:
        print(f"Adding WITH to {filepath}")
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
                if add_with_keyword(os.path.join(root, file)):
                    count += 1
    print(f"Updated {count} files.")


if __name__ == "__main__":
    main()
