#!/usr/bin/env python3
"""Performance Benchmark Runner.

Automated performance testing with different scenarios.
"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path


class PerformanceBenchmark:
    def __init__(self) -> None:
        self.results_dir = Path("performance_results")
        self.results_dir.mkdir(exist_ok=True)

    def run_all_scenarios(self) -> None:
        """Run all performance scenarios."""
        scenarios = [
            {"name": "baseline", "users": 10, "time": "2m"},
            {"name": "normal_load", "users": 50, "time": "5m"},
            {"name": "peak_load", "users": 100, "time": "5m"},
            {"name": "stress_test", "users": 200, "time": "3m"},
        ]

        results = {}

        for scenario in scenarios:
            print(f"🔄 Running {scenario['name']} scenario...")
            result = self.run_scenario(scenario)
            results[scenario["name"]] = result

            # Wait between tests
            time.sleep(30)

        # Save consolidated results
        self.save_results(results)
        print("✅ All benchmarks completed!")

    def run_scenario(self, scenario):
        """Run a single performance scenario."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.results_dir / f"{scenario['name']}_{timestamp}"

        cmd = [
            "locust",
            "-f",
            "locust_config.py",
            "--host=http://localhost:8000",
            f"--users={scenario['users']}",
            "--spawn-rate=5",
            f"--run-time={scenario['time']}",
            "--headless",
            f"--html={output_file}.html",
            f"--csv={output_file}",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=False)
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "html_report": f"{output_file}.html",
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Test timed out"}

    def save_results(self, results) -> None:
        """Save benchmark results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.results_dir / f"benchmark_results_{timestamp}.json"

        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)


if __name__ == "__main__":
    benchmark = PerformanceBenchmark()
    benchmark.run_all_scenarios()
