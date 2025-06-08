"""Migration management for scaffold generator."""

import re
import subprocess


class MigrationManager:
    """Handles Alembic migration operations."""

    def __init__(self, infrastructure_checker=None) -> None:
        self.infrastructure_checker = infrastructure_checker
        self.infrastructure_tables = [
            "alembic_version",
            "procrastinate_jobs",
            "procrastinate_job",
            "procrastinate_events",
            "procrastinate_periodic_defers",
            "procrastinate_periodic_defer",
            "procrastinate_workers",
        ]

    def generate_migration(self, model_name: str) -> bool:
        """Generate Alembic migration for the model."""
        try:
            re.sub(r"(?<!^)(?=[A-Z])", "_", model_name).lower()


            # Check Alembic status first
            status_result = subprocess.run(
                ["alembic", "current"], capture_output=True, text=True, check=False,
            )

            if status_result.returncode != 0:
                pass
            else:
                status_result.stdout.strip()

            # Check for infrastructure tables in the database

            # Generate migration with enhanced output
            result = subprocess.run(
                [
                    "alembic",
                    "revision",
                    "--autogenerate",
                    "-m",
                    f"Add {model_name} model",
                ],
                capture_output=True,
                text=True, check=False,
            )

            if result.returncode == 0:

                # Check if any infrastructure tables were detected in the output
                if any(table in result.stdout for table in self.infrastructure_tables):
                    pass

                # Apply migration with better error handling
                apply_result = subprocess.run(
                    ["alembic", "upgrade", "head"], capture_output=True, text=True, check=False,
                )

                if apply_result.returncode == 0:

                    # Verify the table was created
                    return True
                self._handle_migration_errors(apply_result.stderr)
                return False
            self._handle_generation_errors(result.stderr)
            return False

        except Exception:
            return False

    def _handle_migration_errors(self, error_message: str) -> None:
        """Handle migration application errors."""
        if "duplicate key value" in error_message or "relation already exists" in error_message:
            pass
        else:
            pass

    def _handle_generation_errors(self, error_message: str) -> None:
        """Handle migration generation errors."""
        if "Can't locate revision" in error_message or "could not assemble any primary key columns" in error_message or "No changes in schema detected" in error_message:
            pass

    def downgrade_migration(self, revision: str) -> bool:
        """Downgrade to a specific migration revision."""
        try:
            result = subprocess.run(
                ["alembic", "downgrade", revision], capture_output=True, text=True, check=False,
            )

            return result.returncode == 0

        except Exception:
            return False

    def get_migration_history(self) -> list[str]:
        """Get the migration history."""
        try:
            result = subprocess.run(
                ["alembic", "history", "--verbose"], capture_output=True, text=True, check=False,
            )

            if result.returncode == 0:
                return result.stdout.split("\n")
            return []

        except Exception:
            return []

    def stamp_head(self) -> bool:
        """Stamp the database to the current head revision."""
        try:
            result = subprocess.run(
                ["alembic", "stamp", "head"], capture_output=True, text=True, check=False,
            )

            return result.returncode == 0

        except Exception:
            return False

    def fix_alembic_state(self) -> bool | None:
        """Fix corrupted Alembic state by resetting to latest valid revision."""
        try:

            # Get the latest revision from history
            result = subprocess.run(
                ["alembic", "history"], capture_output=True, text=True, check=False,
            )
            if result.returncode != 0:
                return False

            # Parse the history to find the head revision
            lines = result.stdout.strip().split("\n")
            head_revision = None
            for line in lines:
                if "(head)" in line:
                    # Extract revision ID from line like "6aa199c2e923 -> 4231a548294e (head), ..."
                    parts = line.split(" -> ")
                    if len(parts) > 1:
                        head_revision = parts[1].split(" ")[0]
                        break

            if not head_revision:
                return False


            # Stamp the database with the head revision
            result = subprocess.run(
                ["alembic", "stamp", head_revision], capture_output=True, text=True, check=False,
            )
            return result.returncode == 0

        except Exception:
            return False
