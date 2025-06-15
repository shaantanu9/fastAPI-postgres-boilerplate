import os
import re

MIGRATIONS_DIR = "alembic/versions"
FUNC_NAMES = ["upgrade", "downgrade"]

TEMPLATE_FUNC = """
def {func}() -> None:
    pass
"""

def fix_migration_file(filepath):
    with open(filepath, "r") as f:
        lines = f.readlines()

    changed = False
    warnings = []
    new_lines = []
    found_funcs = {name: False for name in FUNC_NAMES}
    func_lines = {name: [] for name in FUNC_NAMES}
    skip_lines = set()

    # First pass: find all function definitions and their line numbers
    for idx, line in enumerate(lines):
        func_match = re.match(r"^(\s*)def (upgrade|downgrade)\s*\(.*\):", line)
        if func_match:
            func_name = func_match.group(2)
            func_lines[func_name].append(idx)

    # Second pass: build new_lines, skipping duplicates and fixing bodies
    i = 0
    while i < len(lines):
        func_match = re.match(r"^(\s*)def (upgrade|downgrade)\s*\(.*\):", lines[i])
        if func_match:
            func_indent = len(func_match.group(1))
            func_name = func_match.group(2)
            # If this is not the first occurrence, skip this function
            if func_lines[func_name][0] != i:
                changed = True
                i += 1
                # Skip lines until next function or EOF
                while i < len(lines) and not re.match(r"^(\s*)def (upgrade|downgrade)\s*\(.*\):", lines[i]):
                    i += 1
                continue
            # This is the first occurrence, ensure it has a body
            new_lines.append(lines[i])
            j = i + 1
            body_found = False
            while j < len(lines):
                next_line = lines[j]
                if next_line.strip() == "" or next_line.strip().startswith("#"):
                    new_lines.append(next_line)
                    j += 1
                    continue
                # If next line is not indented or is another function/class, insert pass
                if len(next_line) - len(next_line.lstrip()) <= func_indent or next_line.strip().startswith("def "):
                    break
                body_found = True
                new_lines.append(next_line)
                j += 1
            if not body_found:
                new_lines.append(" " * (func_indent + 4) + "pass\n")
                changed = True
            i = j
            found_funcs[func_name] = True
            continue
        new_lines.append(lines[i])
        i += 1

    # Check for missing upgrade/downgrade and add stubs if needed
    for func in FUNC_NAMES:
        if not found_funcs[func]:
            warnings.append(f"⚠️ {func}() missing in {filepath}, adding stub.")
            new_lines.append(TEMPLATE_FUNC.format(func=func))
            changed = True

    # Fix indentation errors (basic check)
    for idx, line in enumerate(new_lines):
        if re.match(r"^def (upgrade|downgrade)\s*\(.*\):", line.strip()):
            # Next line must be indented
            if idx + 1 < len(new_lines) and new_lines[idx + 1].strip() != "" and not new_lines[idx + 1].startswith("    "):
                new_lines[idx + 1] = "    " + new_lines[idx + 1].lstrip()
                changed = True

    if changed:
        with open(filepath, "w") as f:
            f.writelines(new_lines)
        print(f"✅ Fixed: {filepath}")
    for w in warnings:
        print(w)
    return changed or bool(warnings)

def main():
    fixed = 0
    for fname in os.listdir(MIGRATIONS_DIR):
        if fname.endswith(".py"):
            path = os.path.join(MIGRATIONS_DIR, fname)
            if fix_migration_file(path):
                fixed += 1
    if fixed == 0:
        print("🎉 No migration issues found.")
    else:
        print(f"🔧 Fixed or warned on {fixed} migration file(s).\nAlways review changes before running migrations!")

if __name__ == "__main__":
    main() 