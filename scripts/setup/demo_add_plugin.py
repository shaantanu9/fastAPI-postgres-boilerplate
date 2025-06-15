#!/usr/bin/env python3
"""🚀 FastAPI Enterprise Plugin System - Demo Script.

This script demonstrates how to:
1. Add a new model using the plugin generator
2. Run database migrations
3. Start the application
4. Verify the routes appear in Swagger UI

Usage:
    python demo_add_plugin.py

The script will:
- Generate a new Product plugin with sample fields
- Apply database migrations
- Show you how to start the server
- Provide links to test the new API endpoints
"""

import contextlib
import subprocess
import sys
from pathlib import Path


def run_command(command, description) -> bool:
    """Run a command and display the result."""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, cwd=Path.cwd(), check=False,
        )

        if result.stdout:
            pass

        if result.stderr:
            pass

        if result.returncode == 0:
            pass
        else:
            return False

    except Exception:
        return False

    return True


def main() -> None:
    """Main demo function."""
    # Step 1: Generate a sample plugin
    success = run_command(
        "python scaffold_plugin_generator_v2.py add Product "
        "title:str:max_length=200 "
        "price:float:gt=0 "
        "description:text "
        "category:str:indexed "
        "sku:str:unique "
        "is_active:bool:default=True "
        "--with-tasks --with-bulk",
        "Generating Product plugin with full features",
    )

    if not success:
        return

    # Step 2: List generated plugins
    run_command(
        "python scaffold_plugin_generator_v2.py list", "Showing all generated plugins",
    )

    # Step 3: Run health check
    run_command(
        "python scaffold_plugin_generator_v2.py health-check",
        "Checking plugin system health",
    )

    # Step 4: Show the generated plugin file
    plugin_file = Path("app/plugins/product_plugin.py")
    if plugin_file.exists():
        pass
    else:
        pass

    # Instructions for running the server

    # Auto-start option

    response = input("Would you like to start the server now? (y/N): ")
    if response.lower() in ["y", "yes"]:

        with contextlib.suppress(KeyboardInterrupt):
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--reload",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    "8000",
                ], check=False,
            )



if __name__ == "__main__":
    main()
