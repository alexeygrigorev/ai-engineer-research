#!/usr/bin/env python3
"""Fix YAML files with unquoted colons in values."""
import re
from pathlib import Path

EXTRACTED_DIR = Path(__file__).parent / "extracted"


def fix_yaml_file(yaml_file):
    """Fix a single YAML file."""
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Clean ONLY the Unicode characters that break YAML parsing
        # Line/paragraph separators can break YAML scanners
        content = content.replace('\u2028', '\n')  # Line separator -> newline
        content = content.replace('\u2029', '\n')  # Paragraph separator -> newline
        # Zero-width space inside values can cause issues
        content = content.replace('\u200b', '')

        lines = content.split('\n')
        fixed_lines = []

        in_literal_block = False
        literal_block_indent = 0

        for line in lines:
            # Check if we're entering a literal block
            if re.match(r'^(\w+):\s*\|', line):
                in_literal_block = True
                fixed_lines.append(line)
                continue

            # Check if we're exiting a literal block (next top-level key)
            if in_literal_block:
                if line and not line.startswith(' ') and not line.startswith('\t') and not line.startswith('-'):
                    # Top-level key found, exit literal block
                    in_literal_block = False
                else:
                    # Still in literal block, don't modify
                    fixed_lines.append(line)
                    continue

            # Process non-literal-block lines
            # Match top-level key: value pairs
            match = re.match(r'^(\w+):\s*(.+)$', line)
            if match:
                key, value = match.groups()
                value = value.strip()

                # Don't quote if already quoted, special YAML, or safe values
                if (value.startswith('"') or value.startswith("'") or
                    value.startswith('|') or value.startswith('>') or
                    value.startswith('-') or value == '' or
                    re.match(r'^\d+$|^https?://|^[\d,]+K?\s*-\s*\d+K?$', value)):
                    fixed_lines.append(line)
                # Quote only if contains problematic colons (not at end)
                elif ':' in value and not value.endswith(':'):
                    quoted = value.replace('\\', '\\\\').replace('"', '\\"')
                    fixed_lines.append(f'{key}: "{quoted}"')
                else:
                    fixed_lines.append(line)
            else:
                # List items or other lines - fix if needed
                list_match = re.match(r'^(\s*-\s*)(.+)$', line)
                if list_match:
                    prefix, value = list_match.groups()
                    value = value.strip()
                    # Quote list values with colons (not at end)
                    if ':' in value and not value.endswith(':') and not (value.startswith('"') or value.startswith("'")):
                        quoted = value.replace('\\', '\\\\').replace('"', '\\"')
                        fixed_lines.append(f'{prefix}"{quoted}"')
                    else:
                        fixed_lines.append(line)
                else:
                    fixed_lines.append(line)

        fixed_content = '\n'.join(fixed_lines)

        with open(yaml_file, 'w', encoding='utf-8', newline='\n') as f:
            f.write(fixed_content)

        return True
    except Exception as e:
        print(f"  Error fixing {yaml_file.name}: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fix YAML files with unquoted colons')
    parser.add_argument('--all', action='store_true', help='Fix all YAML files')
    args = parser.parse_args()

    if not args.all:
        parser.print_help()
        return

    yaml_files = list(EXTRACTED_DIR.glob("*.yaml"))
    print(f"Fixing {len(yaml_files)} YAML files...\n")

    fixed = 0
    errors = 0

    for yaml_file in yaml_files:
        if fix_yaml_file(yaml_file):
            fixed += 1
        else:
            errors += 1

    print(f"\nFixed: {fixed}")
    print(f"Errors: {errors}")


if __name__ == '__main__':
    main()
