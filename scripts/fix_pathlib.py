#!/usr/bin/env python3
"""
Script to automatically fix common pathlib modernization issues in Python files.
Converts os.path operations to pathlib.Path equivalents.
"""

import re
from pathlib import Path


def fix_file_content(content: str) -> tuple[str, list[str]]:
    """Fix pathlib issues in file content and return (fixed_content, list_of_fixes)"""
    fixes = []
    original_content = content

    # Fix os.path.exists() -> Path().exists()
    pattern = r'os\.path\.exists\(([^)]+)\)'
    if re.search(pattern, content):
        content = re.sub(pattern, r'Path(\1).exists()', content)
        fixes.append("os.path.exists() -> Path().exists()")

    # Fix os.path.dirname() -> Path().parent
    pattern = r'os\.path\.dirname\(([^)]+)\)'
    if re.search(pattern, content):
        content = re.sub(pattern, r'Path(\1).parent', content)
        fixes.append("os.path.dirname() -> Path().parent")

    # Fix os.path.join() -> Path() / operator (simple cases)
    pattern = r'os\.path\.join\(([^,)]+),\s*([^)]+)\)'
    if re.search(pattern, content):
        content = re.sub(pattern, r'Path(\1) / \2', content)
        fixes.append("os.path.join() -> Path() / operator")

    # Fix os.remove() -> Path().unlink()
    pattern = r'os\.remove\(([^)]+)\)'
    if re.search(pattern, content):
        content = re.sub(pattern, r'Path(\1).unlink()', content)
        fixes.append("os.remove() -> Path().unlink()")

    # Fix os.makedirs() -> Path().mkdir(parents=True)
    pattern = r'os\.makedirs\(([^,)]+)(?:,\s*exist_ok=True)?\)'
    if re.search(pattern, content):
        content = re.sub(pattern, r'Path(\1).mkdir(parents=True, exist_ok=True)', content)
        fixes.append("os.makedirs() -> Path().mkdir()")

    # Fix os.chmod() -> Path().chmod()
    pattern = r'os\.chmod\(([^,)]+),\s*([^)]+)\)'
    if re.search(pattern, content):
        content = re.sub(pattern, r'Path(\1).chmod(\2)', content)
        fixes.append("os.chmod() -> Path().chmod()")

    # Fix open() -> Path().open() (simple cases)
    pattern = r'with open\(([^,)]+)(?:,\s*["\']([rw])["\'])?\) as'
    if re.search(pattern, content):
        def replace_open(match):
            filepath = match.group(1)
            mode = match.group(2) if match.group(2) else "r"
            return f'with Path({filepath}).open("{mode}") as'
        content = re.sub(pattern, replace_open, content)
        fixes.append("open() -> Path().open()")

    # Add necessary imports if we made changes
    if fixes and content != original_content:
        if 'from pathlib import Path' not in content and 'import pathlib' not in content:
            # Find a good place to add the import
            lines = content.split('\n')
            import_line = 0

            # Find the last import line
            for i, line in enumerate(lines):
                if line.strip().startswith(('import ', 'from ')) and 'pathlib' not in line:
                    import_line = i + 1
                elif line.strip() and not line.strip().startswith('#'):
                    break

            # Insert the pathlib import
            lines.insert(import_line, 'from pathlib import Path')
            content = '\n'.join(lines)
            fixes.append("Added pathlib import")

    return content, fixes


def fix_pathlib_issues():
    """Fix pathlib issues in common Python files"""
    target_files = [
        "scaffold_plugin_generator.py",
        "scaffold_plugin_generator_v2.py",
        "scaffold_plugin_generator_v3.py",
        "scaffold_model_updated.py",
        "scripts/security_audit.py",
        "scripts/setup_production_suite.py",
        "setup_observability.py"
    ]

    for file_path in target_files:
        path = Path(file_path)
        if not path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue

        try:
            # Read original content
            with path.open('r') as f:
                original_content = f.read()

            # Fix issues
            fixed_content, fixes = fix_file_content(original_content)

            # Write back if changes were made
            if fixes:
                with path.open('w') as f:
                    f.write(fixed_content)
                print(f"✅ Fixed {path.name}: {', '.join(fixes[:3])}{'...' if len(fixes) > 3 else ''}")
            else:
                print(f"✅ {path.name}: No pathlib issues found")

        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")


if __name__ == "__main__":
    print("🔧 Fixing pathlib modernization issues...")
    fix_pathlib_issues()
    print("✅ Pathlib fixes complete!")
