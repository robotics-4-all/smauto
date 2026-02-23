#!/usr/bin/env python3
"""
Script to reorder automation components: move WITH before ON
From: AUTO name ON condition... WITH ... DO ... ;
To:   AUTO name WITH ... ON condition... DO ... ;
"""
import os
import re
from pathlib import Path

def reorder_automation(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Match automation blocks with the pattern:
    # AUTO name ON condition (multiline possible)
    # WITH
    # ... properties ...
    # DO
    # ... actions ...
    # ;
    
    def replace_auto(match):
        name = match.group(1)
        on_condition = match.group(2).strip()
        with_block = match.group(3) if match.group(3) else ""
        do_block = match.group(4)
        
        # Build new structure: AUTO name WITH ... ON condition DO ...
        if with_block:
            return f"AUTO {name}\nWITH\n{with_block}\nON {on_condition}\nDO\n{do_block}\n;"
        else:
            return f"AUTO {name}\nON {on_condition}\nDO\n{do_block}\n;"
    
    # Pattern explanation:
    # AUTO (\w+) - capture automation name
    # ON (.+?) - capture condition (non-greedy until WITH or DO)
    # (?:WITH\n(.*?))? - optionally capture WITH block
    # DO\n(.+?) - capture DO block (actions)
    # ; - end marker
    pattern = re.compile(
        r'AUTO\s+(\w+)\s+ON\s+(.+?)\s*(?:WITH\s*\n(.*?)\s*)?DO\s*\n(.*?)\n\s*;',
        re.DOTALL | re.MULTILINE
    )
    
    new_content = pattern.sub(replace_auto, content)
    
    if new_content != content:
        print(f"Reordering {filepath}")
        with open(filepath, 'w') as f:
            f.write(new_content)
        return True
    return False

def main():
    root_dir = Path(__file__).parent.parent / "examples"
    count = 0
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".auto"):
                if reorder_automation(os.path.join(root, file)):
                    count += 1
    print(f"Reordered {count} files.")

if __name__ == "__main__":
    main()
