"""Infrastructure compatibility checker for scaffold generator."""

import re
import subprocess


class InfrastructureChecker:
    """Handles infrastructure compatibility checks."""

    def __init__(self) -> None:
        self.infrastructure_tables = {
            "alembic_version",
            "procrastinate_jobs",
            "procrastinate_job",  # Alternative naming
            "procrastinate_events",
            "procrastinate_periodic_defers",
            "procrastinate_periodic_defer",  # Alternative naming
            "procrastinate_locks",
            "procrastinate_workers",
        }

        self.reserved_names = {
            "alembic_version",
            "alembic_versions",
            "procrastinate_jobs",
            "procrastinate_job",
            "procrastinate_events",
            "procrastinate_event",
            "procrastinate_periodic_defers",
            "procrastinate_periodic_defer",
            "procrastinate_workers",
            "procrastinate_worker",
            "procrastinate_locks",
            "procrastinate_lock",
            "migrations",
            "migration",
            "users",
            "user",  # Common conflicts
        }

    def check_compatibility(self) -> bool:
        """Check if the database infrastructure is compatible with scaffold generation."""
        try:
            # Check if Alembic is working
            result = subprocess.run(
                ["alembic", "current"], capture_output=True, text=True, check=False,
            )

            if result.returncode != 0:
                return False


            # Check if we can run a dry-run migration check
            result = subprocess.run(
                ["alembic", "check"], capture_output=True, text=True, check=False,
            )

            if result.returncode == 0:
                pass
            else:
                pass

            # Test infrastructure table filtering

            return True

        except FileNotFoundError:
            return False
        except Exception:
            return False

    def validate_table_name_compatibility(self, model_name: str) -> bool:
        """Validate that the model name won't conflict with infrastructure tables."""
        snake_name = re.sub(r"(?<!^)(?=[A-Z])", "_", model_name).lower()
        table_name = f"{snake_name}s"

        return not (table_name in self.reserved_names or snake_name in self.reserved_names)

    def get_infrastructure_tables(self) -> set[str]:
        """Get the set of infrastructure table names."""
        return self.infrastructure_tables.copy()

    def is_infrastructure_table(self, table_name: str) -> bool:
        """Check if a table name is an infrastructure table."""
        return table_name in self.infrastructure_tables

    def check_alembic_state(self) -> tuple[bool, str]:
        """Check the current Alembic migration state."""
        try:
            result = subprocess.run(
                ["alembic", "current"], capture_output=True, text=True, check=False,
            )

            if result.returncode == 0:
                current_revision = result.stdout.strip()
                return True, current_revision
            return False, result.stderr

        except Exception as e:
            return False, str(e)
