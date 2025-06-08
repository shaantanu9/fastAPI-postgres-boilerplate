# Ruff Integration Guide

## Overview

Ruff is now integrated into this FastAPI project as a fast Python linter and formatter. This guide covers setup, configuration, and usage patterns.

## What is Ruff?

Ruff is an extremely fast Python linter and code formatter written in Rust. It can replace multiple tools:

- **Flake8** (linting)
- **Black** (formatting)
- **isort** (import sorting)
- **pyupgrade** (Python version upgrades)
- **And many more...**

## Installation & Setup

Ruff is already installed as a development dependency:

```bash
# Check Ruff version
uv run ruff --version

# View all available commands
uv run ruff --help
```

## Configuration

Ruff is configured in `pyproject.toml` with project-specific settings:

```toml
[tool.ruff]
line-length = 88                    # Black's default
target-version = "py313"            # Python version
exclude = [
    "alembic/versions/*.py",        # Auto-generated files
    ".venv", "__pycache__",
]

[tool.ruff.lint]
select = [
    "E", "W",    # pycodestyle
    "F",         # pyflakes
    "I",         # isort
    "B",         # flake8-bugbear
    "SIM",       # flake8-simplify
    # ... and more
]

ignore = [
    "E501",      # Line too long (handled by formatter)
    "B008",      # Function calls in defaults (FastAPI)
    "T201",      # Print statements (allowed throughout project)
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["T201", "S101"]  # Allow prints and asserts
"scripts/**/*.py" = ["T201"]        # Allow prints
```

## Usage

### Command Line

```bash
# Basic linting
uv run ruff check .

# Auto-fix issues
uv run ruff check . --fix

# Format code
uv run ruff format .

# Show statistics
uv run ruff check . --statistics
```

### Using the Lint Script

We've provided a convenient script:

```bash
# Basic check
./scripts/lint.sh

# Auto-fix issues
./scripts/lint.sh --fix

# Format code
./scripts/lint.sh --format

# Check only (no changes)
./scripts/lint.sh --check
```

### Pre-commit Integration

Install pre-commit hooks to run Ruff automatically:

```bash
# Install pre-commit (if not already installed)
uv add --dev pre-commit

# Install hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

## Rule Categories

### Enabled Rule Sets

| Code | Name               | Description                   |
| ---- | ------------------ | ----------------------------- |
| E, W | pycodestyle        | Style guide enforcement       |
| F    | pyflakes           | Logic errors, undefined names |
| I    | isort              | Import sorting                |
| B    | flake8-bugbear     | Bug-prone patterns            |
| N    | pep8-naming        | Naming conventions            |
| SIM  | flake8-simplify    | Code simplification           |
| UP   | pyupgrade          | Python version upgrades       |
| PTH  | flake8-use-pathlib | Use pathlib over os.path      |

### Ignored Rules (Project-Specific)

- **E501**: Line too long (handled by formatter)
- **B008**: Function calls in defaults (common in FastAPI dependency injection)
- **A003**: Class attribute shadows builtin (common in SQLAlchemy models)
- **T201**: Print statements (allowed throughout the entire project)

## File-Specific Ignores

### Test Files (`tests/**/*.py`)

- **T201**: Print statements allowed
- **S101**: Assert statements allowed
- **ARG**: Unused function arguments allowed

### Scripts (`scripts/**/*.py`)

- **T201**: Print statements allowed

### Alembic Migrations (`alembic/**/*.py`)

- **F401**: Unused imports allowed (auto-generated)
- **E402**: Module-level imports allowed

## Current Status

After initial setup and fixes:

- **15,418 total issues** found initially
- **10,692 issues** automatically fixed
- **2,126 remaining issues** (with T201 print statements now ignored globally)

### Remaining Issues Breakdown

- 742 blank lines with whitespace (W293) - auto-fixable
- 200 builtin-open usage (PTH123) - minor pathlib improvements
- 191 raise-without-from-inside-except (B904) - optional exception chaining
- Various unused variables and arguments - non-critical cleanup opportunities

## Editor Integration

### VS Code

Install the Ruff extension:

1. Search for "Ruff" in extensions
2. Install "Ruff" by Astral Software
3. Add to `settings.json`:

```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": true
    }
  }
}
```

### Other Editors

Ruff has official plugins for:

- **Neovim** (nvim-lspconfig)
- **Emacs** (eglot/lsp-mode)
- **Sublime Text** (LSP-ruff)
- **IntelliJ/PyCharm** (Ruff plugin)

## Best Practices

### 1. Regular Linting

```bash
# Before committing
./scripts/lint.sh --fix

# Format code
./scripts/lint.sh --format
```

### 2. CI/CD Integration

```yaml
# GitHub Actions example
- name: Lint with Ruff
  run: |
    uv run ruff check .
    uv run ruff format --check .
```

### 3. Incremental Adoption

- Fix auto-fixable issues first: `ruff check . --fix`
- Address critical issues (F, E7xx, W6xx)
- Gradually tackle style improvements

### 4. Team Consistency

- Use pre-commit hooks for automatic formatting
- Document project-specific ignores
- Regular team training on Ruff usage

## Comparison with Other Tools

| Tool   | Speed     | Features          | Replace With Ruff  |
| ------ | --------- | ----------------- | ------------------ |
| Black  | Medium    | Formatting        | ✅ `ruff format`   |
| isort  | Fast      | Import sorting    | ✅ Built-in        |
| Flake8 | Slow      | Basic linting     | ✅ Much faster     |
| pylint | Very slow | Advanced analysis | ⚠️ Partial overlap |
| mypy   | Medium    | Type checking     | ❌ Use alongside   |

## Troubleshooting

### Common Issues

**1. "Command not found: ruff"**

```bash
# Use uv to run ruff
uv run ruff check .
```

**2. "Too many errors"**

```bash
# Fix incrementally
uv run ruff check . --fix
uv run ruff format .
```

**3. "Rule conflicts with project needs"**

```toml
# Add to pyproject.toml [tool.ruff.lint] ignore list
ignore = ["E501", "T201"]
```

### Performance Tips

- Ruff is extremely fast (10-100x faster than alternatives)
- Use `--fix` for auto-fixable issues
- Run `ruff format` separately for consistent formatting
- Consider using `--unsafe-fixes` for advanced fixes

## Migration Strategy

If migrating from other tools:

1. **From Black**: Replace with `ruff format`
2. **From isort**: Enable `I` rules in Ruff
3. **From Flake8**: Gradually adopt Ruff's rule sets
4. **Keep mypy**: Ruff doesn't replace type checking

## Resources

- [Official Documentation](https://docs.astral.sh/ruff/)
- [Rule Reference](https://docs.astral.sh/ruff/rules/)
- [Configuration Guide](https://docs.astral.sh/ruff/configuration/)
- [Editor Integrations](https://docs.astral.sh/ruff/editors/)

## Project-Specific Notes

- **FastAPI**: B008 ignored for dependency injection patterns
- **SQLAlchemy**: A003 ignored for model attributes
- **Alembic**: Migrations excluded from strict linting
- **Tests**: Print statements and asserts allowed
- **Scripts**: Print statements allowed for user feedback
