#!/usr/bin/env python3
"""
Script to fix all remaining Pydantic v1 @validator decorators to v2 @field_validator format.
"""

import re
from pathlib import Path


def fix_validators_in_file(file_path: Path) -> bool:
    """Fix validators in a single file."""
    try:
        with file_path.open("r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 1. Replace import of validator with field_validator
        content = re.sub(
            r'from pydantic import (.*?)validator(.*?)',
            r'from pydantic import \1field_validator\2',
            content
        )

        # 2. Fix @validator decorators
        # Pattern to match @validator("field_name", ...)
        validator_pattern = r'@validator\((.*?)\)(.*?)\n(\s*)def (\w+)\(self,(.*?)\):'

        def replace_validator(match):
            field_args = match.group(1)
            decorator_args = match.group(2) if match.group(2) else ""
            indent = match.group(3)
            func_name = match.group(4)
            func_args = match.group(5)

            # Convert decorator arguments
            new_decorator_args = ""
            if "pre=True" in decorator_args or "always=True" in decorator_args:
                new_decorator_args = ', mode="before"'

            # Build new method signature
            return f"@field_validator({field_args}{new_decorator_args})\n{indent}@classmethod\n{indent}def {func_name}(cls,{func_args}):"

        content = re.sub(validator_pattern, replace_validator, content, flags=re.MULTILINE | re.DOTALL)

        # 3. Fix function signatures that still use 'self' and 'values'
        # Replace 'self' with 'cls' and 'values' with 'info.data'
        content = re.sub(r'def (\w+)\(cls, v, values\):', r'def \1(cls, v, info):', content)
        content = re.sub(r'values\["(\w+)"\]', r'info.data["\1"]', content)
        content = re.sub(r'values\.get\("(\w+)"\)', r'info.data.get("\1")', content)
        content = re.sub(r'"(\w+)" in values', r'"\1" in info.data', content)

        # Add info.data guard where needed
        content = re.sub(r'info\.data\[', r'info.data and info.data[', content)

        # Write back if changed
        if content != original_content:
            with file_path.open("w", encoding="utf-8") as f:
                f.write(content)
            return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

    return False


def main():
    """Fix all validator issues in the project."""
    project_root = Path.cwd()

    # Find all Python files that might contain validators
    python_files = []

    # Search in app directory
    app_dir = project_root / "app"
    if app_dir.exists():
        python_files.extend(app_dir.rglob("*.py"))

    # Search in tests directory
    tests_dir = project_root / "tests"
    if tests_dir.exists():
        python_files.extend(tests_dir.rglob("*.py"))

    # Search for standalone files with validators
    for pattern in ["*validation*.py", "*model*.py", "*schema*.py"]:
        python_files.extend(project_root.glob(pattern))

    fixed_files = []

    for file_path in python_files:
        # Skip __pycache__ and .pyc files
        if "__pycache__" in str(file_path) or file_path.suffix == ".pyc":
            continue

        if fix_validators_in_file(file_path):
            fixed_files.append(file_path)
            print(f"✅ Fixed validators in: {file_path}")

    if fixed_files:
        print(f"\n🎉 Fixed validators in {len(fixed_files)} files!")
    else:
        print("✅ No additional validator fixes needed")


if __name__ == "__main__":
    main()
