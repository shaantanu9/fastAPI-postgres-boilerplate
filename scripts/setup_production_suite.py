#!/usr/bin/env python3
"""Production Suite Setup Script.

Integrates and configures all production features:
- Error aggregation and dashboard
- Load testing infrastructure
- Security audit automation
- Integration with existing monitoring
"""

import json
import logging
import subprocess
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ProductionSuiteSetup:
    """Setup and configure production suite features."""

    def __init__(self, project_root: str = ".") -> None:
        self.project_root = Path(project_root)
        self.config = {}

    def setup_all(self) -> None:
        """Setup all production features."""
        logger.info("🚀 Setting up production suite...")

        # Install dependencies
        self.install_dependencies()

        # Setup error aggregation
        self.setup_error_aggregation()

        # Setup load testing
        self.setup_load_testing()

        # Setup security audit
        self.setup_security_audit()

        # Update main application
        self.integrate_with_main_app()

        # Create configuration files
        self.create_config_files()

        # Setup automation scripts
        self.setup_automation()

        logger.info("✅ Production suite setup completed!")
        self.print_usage_instructions()

    def install_dependencies(self) -> None:
        """Install required dependencies."""
        logger.info("📦 Installing production dependencies...")

        dependencies = [
            "locust>=2.0.0",  # Load testing
            "bandit[toml]>=1.7.0",  # Security scanning
            "safety>=2.0.0",  # Vulnerability scanning
            "semgrep>=1.0.0",  # Security patterns
            "aiohttp>=3.8.0",  # Async HTTP for security checks
            "psutil>=5.8.0",  # System monitoring
        ]

        for dep in dependencies:
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", dep],
                    check=True,
                    capture_output=True,
                )
                logger.info(f"✅ Installed {dep}")
            except subprocess.CalledProcessError as e:
                logger.warning(f"⚠️ Failed to install {dep}: {e}")

    def setup_error_aggregation(self) -> None:
        """Setup error aggregation system."""
        logger.info("🔧 Setting up error aggregation...")

        # Update main.py to include error aggregation
        main_py_path = self.project_root / "app" / "main.py"

        if main_py_path.exists():
            with Path(main_py_path).open("r") as f:
                content = f.read()

            # Add error aggregation import and setup
            error_setup_code = """
# Error aggregation setup
try:
    from app.core.error_aggregator import setup_error_aggregation
    setup_error_aggregation()
    logger.info("✅ Error aggregation system initialized")
except ImportError as e:
    logger.warning(f"⚠️ Error aggregation not available: {e}")
"""

            if "setup_error_aggregation" not in content:
                # Find a good place to insert (after other imports)
                lines = content.split("\n")
                insert_index = -1

                for i, line in enumerate(lines):
                    if line.startswith("# --- Logging and settings initialization ---"):
                        insert_index = i + 3
                        break

                if insert_index > 0:
                    lines.insert(insert_index, error_setup_code)

                    with Path(main_py_path).open("w") as f:
                        f.write("\n".join(lines))

                    logger.info("✅ Error aggregation integrated into main.py")

        # Add error dashboard routes to API
        self.add_error_dashboard_routes()

    def add_error_dashboard_routes(self) -> None:
        """Add error dashboard routes to API router."""
        api_router_path = self.project_root / "app" / "api" / "v1" / "api.py"

        if api_router_path.exists():
            with Path(api_router_path).open("r") as f:
                content = f.read()

            # Add error dashboard import and route
            if "error_dashboard" not in content:
                # Add import
                import_line = "from app.api.v1.endpoints.error_dashboard import router as error_dashboard_router"

                # Add route inclusion
                route_line = 'api_router.include_router(error_dashboard_router, tags=["Error Dashboard"])'

                lines = content.split("\n")

                # Find import section
                for i, line in enumerate(lines):
                    if line.startswith("from app.api.v1.endpoints"):
                        lines.insert(i + 1, import_line)
                        break

                # Find router inclusion section
                for i, line in enumerate(lines):
                    if "include_router" in line and "tags=" in line:
                        lines.insert(i + 1, route_line)
                        break

                with Path(api_router_path).open("w") as f:
                    f.write("\n".join(lines))

                logger.info("✅ Error dashboard routes added to API")

    def setup_load_testing(self) -> None:
        """Setup load testing infrastructure."""
        logger.info("🔧 Setting up load testing...")

        # Create load testing directory
        load_test_dir = self.project_root / "tests" / "load_testing"
        load_test_dir.mkdir(parents=True, exist_ok=True)

        # Create load testing scripts
        scripts = {
            "run_load_test.sh": self.create_load_test_script(),
            "performance_benchmark.py": self.create_benchmark_script(),
            "load_test_scenarios.json": self.create_scenario_config(),
        }

        for script_name, content in scripts.items():
            script_path = load_test_dir / script_name
            with Path(script_path).open("w") as f:
                f.write(content)

            if script_name.endswith(".sh"):
                Path(script_path).chmod(0o755)

        logger.info("✅ Load testing infrastructure created")

    def create_load_test_script(self) -> str:
        """Create load testing shell script."""
        return """#!/bin/bash
# Load Testing Runner Script

set -e

echo "🚀 Starting Load Testing Suite..."

# Configuration
HOST=${HOST:-"http://localhost:8000"}
USERS=${USERS:-50}
SPAWN_RATE=${SPAWN_RATE:-5}
RUN_TIME=${RUN_TIME:-"10m"}
OUTPUT_DIR="load_test_results"

# Create output directory
mkdir -p $OUTPUT_DIR
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "📋 Test Configuration:"
echo "  Host: $HOST"
echo "  Users: $USERS"
echo "  Spawn Rate: $SPAWN_RATE/sec"
echo "  Duration: $RUN_TIME"

# Run the load test
echo "🔄 Running load test..."
locust -f locust_config.py \\
    --host=$HOST \\
    --users=$USERS \\
    --spawn-rate=$SPAWN_RATE \\
    --run-time=$RUN_TIME \\
    --headless \\
    --html=$OUTPUT_DIR/report_$TIMESTAMP.html \\
    --csv=$OUTPUT_DIR/results_$TIMESTAMP

echo "✅ Load test completed!"
echo "📊 Results saved to: $OUTPUT_DIR/"
"""

    def create_benchmark_script(self) -> str:
        """Create performance benchmark script."""
        return '''#!/usr/bin/env python3
"""
Performance Benchmark Runner

Automated performance testing with different scenarios.
"""

import os
import sys
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path

class PerformanceBenchmark:
    def __init__(self):
        self.results_dir = Path("performance_results")
        self.results_dir.mkdir(exist_ok=True)

    def run_all_scenarios(self):
        """Run all performance scenarios"""
        scenarios = [
            {"name": "baseline", "users": 10, "time": "2m"},
            {"name": "normal_load", "users": 50, "time": "5m"},
            {"name": "peak_load", "users": 100, "time": "5m"},
            {"name": "stress_test", "users": 200, "time": "3m"}
        ]

        results = {}

        for scenario in scenarios:
            print(f"🔄 Running {scenario['name']} scenario...")
            result = self.run_scenario(scenario)
            results[scenario['name']] = result

            # Wait between tests
            time.sleep(30)

        # Save consolidated results
        self.save_results(results)
        print("✅ All benchmarks completed!")

    def run_scenario(self, scenario):
        """Run a single performance scenario"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.results_dir / f"{scenario['name']}_{timestamp}"

        cmd = [
            "locust", "-f", "locust_config.py",
            "--host=http://localhost:8000",
            f"--users={scenario['users']}",
            "--spawn-rate=5",
            f"--run-time={scenario['time']}",
            "--headless",
            f"--html={output_file}.html",
            f"--csv={output_file}"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "html_report": f"{output_file}.html"
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Test timed out"}

    def save_results(self, results):
        """Save benchmark results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.results_dir / f"benchmark_results_{timestamp}.json"

        with Path(results_file).open("w") as f:
            json.dump(results, f, indent=2)

if __name__ == "__main__":
    benchmark = PerformanceBenchmark()
    benchmark.run_all_scenarios()
'''

    def create_scenario_config(self) -> str:
        """Create load testing scenario configuration."""
        config = {
            "scenarios": {
                "development": {
                    "host": "http://localhost:8000",
                    "users": 10,
                    "spawn_rate": 2,
                    "run_time": "2m",
                },
                "staging": {
                    "host": "https://staging.example.com",
                    "users": 50,
                    "spawn_rate": 5,
                    "run_time": "5m",
                },
                "production_baseline": {
                    "host": "https://api.example.com",
                    "users": 100,
                    "spawn_rate": 10,
                    "run_time": "10m",
                },
                "stress_test": {
                    "host": "http://localhost:8000",
                    "users": 500,
                    "spawn_rate": 25,
                    "run_time": "5m",
                },
            },
            "thresholds": {
                "avg_response_time_ms": 500,
                "p95_response_time_ms": 1000,
                "p99_response_time_ms": 2000,
                "max_failure_rate_percent": 1.0,
                "min_requests_per_second": 10,
            },
        }

        return json.dumps(config, indent=2)

    def setup_security_audit(self) -> None:
        """Setup security audit automation."""
        logger.info("🔧 Setting up security audit...")

        # Make security audit script executable
        security_script = self.project_root / "scripts" / "security_audit.py"
        if security_script.exists():
            Path(security_script).chmod(0o755)

        # Create security automation scripts
        self.create_security_automation()

        logger.info("✅ Security audit automation configured")

    def create_security_automation(self) -> None:
        """Create security automation scripts."""
        scripts_dir = self.project_root / "scripts"

        # Daily security scan script
        daily_scan_script = scripts_dir / "daily_security_scan.sh"
        with Path(daily_scan_script).open("w") as f:
            f.write("""#!/bin/bash
# Daily Security Scan Script

set -e

echo "🔒 Starting daily security scan..."

# Run security audit
python3 scripts/security_audit.py --project-root=. --output-dir=security_reports

# Check for critical issues
CRITICAL_COUNT=$(grep -c '"severity": "critical"' security_reports/security_audit_*.json | tail -1 | cut -d: -f2)

if [ "$CRITICAL_COUNT" -gt 0 ]; then
    echo "🚨 CRITICAL: Found $CRITICAL_COUNT critical security issues!"
    echo "Please review the security report immediately."
    exit 1
else
    echo "✅ No critical security issues found."
fi

echo "📊 Security scan completed. Check security_reports/ for details."
""")

        Path(daily_scan_script).chmod(0o755)

        # CI/CD integration script
        ci_security_script = scripts_dir / "ci_security_check.sh"
        with Path(ci_security_script).open("w") as f:
            f.write("""#!/bin/bash
# CI/CD Security Check Script

set -e

echo "🔒 Running security checks for CI/CD..."

# Quick security scan (limited scope for CI speed)
python3 -m bandit -r app/ -f json -o security_check_results.json || true

# Check for critical issues
if [ -f security_check_results.json ]; then
    CRITICAL_COUNT=$(grep -c '"issue_severity": "HIGH"' security_check_results.json || echo "0")

    if [ "$CRITICAL_COUNT" -gt 0 ]; then
        echo "🚨 BLOCKING: Found $CRITICAL_COUNT high-severity security issues!"
        echo "Security issues must be fixed before deployment."
        exit 1
    fi
fi

echo "✅ Security check passed."
""")

        Path(ci_security_script).chmod(0o755)

    def integrate_with_main_app(self) -> None:
        """Integrate production features with main application."""
        logger.info("🔧 Integrating with main application...")

        # Update requirements.txt
        self.update_requirements()

        # Update API documentation
        self.update_api_docs()

        logger.info("✅ Integration completed")

    def update_requirements(self) -> None:
        """Update requirements.txt with new dependencies."""
        req_file = self.project_root / "requirements.txt"

        new_deps = [
            "# Production monitoring and testing",
            "locust>=2.0.0  # Load testing",
            "bandit[toml]>=1.7.0  # Security scanning",
            "safety>=2.0.0  # Vulnerability scanning",
        ]

        if req_file.exists():
            with Path(req_file).open("r") as f:
                content = f.read()

            # Add new dependencies if not already present
            for dep in new_deps:
                if dep.split(">=")[0].split("#")[0].strip() not in content:
                    content += f"\n{dep}"

            with Path(req_file).open("w") as f:
                f.write(content)

            logger.info("✅ Requirements.txt updated")

    def update_api_docs(self) -> None:
        """Update API documentation with new endpoints."""
        # This could update OpenAPI documentation or README files
        # For now, we'll create a documentation update
        docs_update = {
            "new_endpoints": [
                "GET /api/v1/errors/dashboard - Error dashboard data",
                "GET /api/v1/errors/summary - Error summary statistics",
                "GET /api/v1/errors/groups/{fingerprint} - Error group details",
                "GET /api/v1/errors/alerts - Recent error alerts",
                "GET /api/v1/errors/dashboard/ui - Error dashboard UI",
            ],
            "production_features": [
                "Centralized error aggregation and tracking",
                "Performance load testing with Locust",
                "Automated security scanning and auditing",
                "Enhanced monitoring and alerting",
            ],
        }

        docs_file = self.project_root / "docs" / "production_features.md"
        docs_file.parent.mkdir(exist_ok=True)

        with Path(docs_file).open("w") as f:
            f.write(f"""# Production Features

## New API Endpoints

{chr(10).join("- " + endpoint for endpoint in docs_update["new_endpoints"])}

## Production Features

{chr(10).join("- " + feature for feature in docs_update["production_features"])}

## Usage

### Error Dashboard
Access the error dashboard at: `http://localhost:8000/api/v1/errors/dashboard/ui`

### Load Testing
```bash
cd tests/load_testing
./run_load_test.sh
```

### Security Audit
```bash
python3 scripts/security_audit.py
```

## Automation

### Daily Security Scan
```bash
./scripts/daily_security_scan.sh
```

### CI/CD Security Check
```bash
./scripts/ci_security_check.sh
```
""")

        logger.info("✅ Documentation updated")

    def create_config_files(self) -> None:
        """Create configuration files for production features."""
        logger.info("🔧 Creating configuration files...")

        # GitHub Actions workflow for security scanning
        github_dir = self.project_root / ".github" / "workflows"
        github_dir.mkdir(parents=True, exist_ok=True)

        security_workflow = github_dir / "security-scan.yml"
        with Path(security_workflow).open("w") as f:
            f.write("""name: Security Scan

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  security-scan:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install bandit[toml] safety

    - name: Run Bandit security scan
      run: |
        bandit -r app/ -f json -o bandit-results.json || true

    - name: Run Safety vulnerability scan
      run: |
        safety check --json --output safety-results.json || true

    - name: Upload security results
      uses: actions/upload-artifact@v3
      with:
        name: security-scan-results
        path: |
          bandit-results.json
          safety-results.json
""")

        logger.info("✅ GitHub Actions workflow created")

    def setup_automation(self) -> None:
        """Setup automation and monitoring."""
        logger.info("🔧 Setting up automation...")

        # Create monitoring integration
        monitoring_config = {
            "error_dashboard": {
                "enabled": True,
                "retention_days": 30,
                "alert_thresholds": {
                    "critical_errors_per_minute": 10,
                    "new_error_types_per_hour": 5,
                },
            },
            "load_testing": {
                "enabled": True,
                "schedule": "0 2 * * 0",  # Weekly on Sunday at 2 AM
                "scenarios": ["normal_load", "peak_load"],
            },
            "security_audit": {
                "enabled": True,
                "schedule": "0 3 * * *",  # Daily at 3 AM
                "tools": ["bandit", "safety", "semgrep"],
            },
        }

        config_file = self.project_root / "production_config.json"
        with Path(config_file).open("w") as f:
            json.dump(monitoring_config, f, indent=2)

        logger.info("✅ Automation configuration created")

    def print_usage_instructions(self) -> None:
        """Print usage instructions."""
        print("\n" + "=" * 60)
        print("🎉 PRODUCTION SUITE SETUP COMPLETED!")
        print("=" * 60)
        print("\n📋 Available Features:")
        print("  1. Error Dashboard: http://localhost:8000/api/v1/errors/dashboard/ui")
        print("  2. Load Testing: tests/load_testing/run_load_test.sh")
        print("  3. Security Audit: scripts/security_audit.py")
        print("\n🚀 Quick Start Commands:")
        print("  # Start the application with error tracking")
        print("  python -m uvicorn app.main:app --reload")
        print()
        print("  # Run load test")
        print("  cd tests/load_testing && ./run_load_test.sh")
        print()
        print("  # Run security audit")
        print("  python3 scripts/security_audit.py")
        print()
        print("  # View error dashboard")
        print("  curl http://localhost:8000/api/v1/errors/dashboard")
        print("\n🔄 Automation:")
        print("  - Daily security scans: ./scripts/daily_security_scan.sh")
        print("  - CI/CD integration: ./scripts/ci_security_check.sh")
        print("  - GitHub Actions workflow: .github/workflows/security-scan.yml")
        print("\n📚 Documentation: docs/production_features.md")
        print("=" * 60)


def main() -> None:
    """Main setup function."""
    import argparse

    parser = argparse.ArgumentParser(description="Setup Production Suite")
    parser.add_argument("--project-root", default=".", help="Project root directory")

    args = parser.parse_args()

    setup = ProductionSuiteSetup(args.project_root)
    setup.setup_all()


if __name__ == "__main__":
    main()
