#!/usr/bin/env python3
"""
Comprehensive Security Audit Script

Automated security scanning and vulnerability assessment for FastAPI application.
Integrates multiple security tools and generates consolidated reports.
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import asyncio
import aiohttp
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SecurityAudit:
    """Comprehensive security audit suite"""
    
    def __init__(self, project_root: str = ".", output_dir: str = "security_reports"):
        self.project_root = Path(project_root)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.audit_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_file = self.output_dir / f"security_audit_{self.audit_timestamp}.json"
        
        self.results = {
            "audit_info": {
                "timestamp": datetime.now().isoformat(),
                "project_root": str(self.project_root),
                "python_version": sys.version,
                "audit_version": "1.0.0"
            },
            "findings": [],
            "summary": {},
            "recommendations": []
        }
    
    async def run_full_audit(self):
        """Run complete security audit"""
        logger.info("🔒 Starting comprehensive security audit...")
        
        # Static code analysis
        await self.run_bandit_scan()
        await self.run_safety_scan()
        await self.run_semgrep_scan()
        
        # Dependency analysis
        await self.check_dependencies()
        await self.check_outdated_packages()
        
        # Configuration analysis
        await self.check_configuration_security()
        await self.check_secrets_exposure()
        
        # Application-specific checks
        await self.check_api_security()
        await self.check_authentication_security()
        await self.check_rate_limiting()
        
        # Infrastructure checks
        await self.check_docker_security()
        await self.check_environment_variables()
        
        # Generate report
        await self.generate_report()
        
        logger.info(f"✅ Security audit completed. Report saved to: {self.report_file}")
    
    async def run_bandit_scan(self):
        """Run Bandit static security analysis"""
        logger.info("🔍 Running Bandit security scan...")
        
        try:
            # Install bandit if not available
            subprocess.run([sys.executable, "-m", "pip", "install", "bandit[toml]"], 
                         capture_output=True, check=False)
            
            # Run bandit scan
            result = subprocess.run([
                "bandit", "-r", str(self.project_root),
                "-f", "json",
                "--exclude", "**/venv/**,**/node_modules/**,**/tests/**",
                "--skip", "B101,B601"  # Skip assert and shell injection for tests
            ], capture_output=True, text=True)
            
            if result.returncode == 0 or result.stdout:
                try:
                    bandit_data = json.loads(result.stdout)
                    
                    for issue in bandit_data.get("results", []):
                        self.add_finding(
                            tool="bandit",
                            severity=issue["issue_severity"].lower(),
                            category="static_analysis",
                            title=issue["test_name"],
                            description=issue["issue_text"],
                            file_path=issue["filename"],
                            line_number=issue["line_number"],
                            code_snippet=issue["code"],
                            cwe_id=issue.get("issue_cwe", {}).get("id"),
                            confidence=issue["issue_confidence"].lower()
                        )
                    
                    logger.info(f"Bandit found {len(bandit_data.get('results', []))} issues")
                    
                except json.JSONDecodeError:
                    logger.error("Failed to parse Bandit output")
            
        except Exception as e:
            logger.error(f"Bandit scan failed: {e}")
            self.add_finding(
                tool="bandit",
                severity="high",
                category="tool_error",
                title="Bandit scan failed",
                description=str(e)
            )
    
    async def run_safety_scan(self):
        """Run Safety vulnerability scan for dependencies"""
        logger.info("🔍 Running Safety vulnerability scan...")
        
        try:
            # Install safety if not available
            subprocess.run([sys.executable, "-m", "pip", "install", "safety"], 
                         capture_output=True, check=False)
            
            # Run safety check
            result = subprocess.run([
                "safety", "check", "--json", "--full-report"
            ], capture_output=True, text=True)
            
            if result.stdout:
                try:
                    safety_data = json.loads(result.stdout)
                    
                    for vuln in safety_data.get("vulnerabilities", []):
                        self.add_finding(
                            tool="safety",
                            severity="high",  # Safety reports are typically high severity
                            category="dependency_vulnerability",
                            title=f"Vulnerable dependency: {vuln['package_name']}",
                            description=vuln["vulnerability_description"],
                            package_name=vuln["package_name"],
                            installed_version=vuln["installed_version"],
                            vulnerable_spec=vuln["vulnerable_spec"],
                            cve_id=vuln.get("CVE"),
                            advisory_url=vuln.get("advisory")
                        )
                    
                    logger.info(f"Safety found {len(safety_data.get('vulnerabilities', []))} vulnerabilities")
                    
                except json.JSONDecodeError:
                    logger.error("Failed to parse Safety output")
        
        except Exception as e:
            logger.error(f"Safety scan failed: {e}")
    
    async def run_semgrep_scan(self):
        """Run Semgrep security patterns scan"""
        logger.info("🔍 Running Semgrep security scan...")
        
        try:
            # Install semgrep if not available
            subprocess.run([sys.executable, "-m", "pip", "install", "semgrep"], 
                         capture_output=True, check=False)
            
            # Run semgrep with security rules
            result = subprocess.run([
                "semgrep", "--config=auto", "--json", 
                "--exclude=**/venv/**", "--exclude=**/node_modules/**",
                str(self.project_root)
            ], capture_output=True, text=True)
            
            if result.stdout:
                try:
                    semgrep_data = json.loads(result.stdout)
                    
                    for finding in semgrep_data.get("results", []):
                        severity = finding.get("extra", {}).get("severity", "medium")
                        
                        self.add_finding(
                            tool="semgrep",
                            severity=severity.lower(),
                            category="security_pattern",
                            title=finding.get("check_id", "Unknown rule"),
                            description=finding.get("extra", {}).get("message", "Security pattern detected"),
                            file_path=finding["path"],
                            line_number=finding["start"]["line"],
                            rule_id=finding.get("check_id"),
                            metadata=finding.get("extra", {}).get("metadata", {})
                        )
                    
                    logger.info(f"Semgrep found {len(semgrep_data.get('results', []))} issues")
                    
                except json.JSONDecodeError:
                    logger.error("Failed to parse Semgrep output")
        
        except Exception as e:
            logger.error(f"Semgrep scan failed: {e}")
    
    async def check_dependencies(self):
        """Check for insecure dependencies"""
        logger.info("📦 Checking dependency security...")
        
        requirements_files = [
            "requirements.txt",
            "requirements-dev.txt",
            "pyproject.toml"
        ]
        
        for req_file in requirements_files:
            req_path = self.project_root / req_file
            if req_path.exists():
                await self._analyze_requirements_file(req_path)
    
    async def _analyze_requirements_file(self, file_path: Path):
        """Analyze specific requirements file"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check for unpinned dependencies
            unpinned = []
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    if '==' not in line and '>=' not in line and '~=' not in line:
                        unpinned.append(line)
            
            if unpinned:
                self.add_finding(
                    tool="dependency_check",
                    severity="medium",
                    category="dependency_management",
                    title="Unpinned dependencies detected",
                    description=f"Found {len(unpinned)} unpinned dependencies",
                    file_path=str(file_path),
                    affected_packages=unpinned
                )
            
            # Check for known insecure packages
            insecure_packages = [
                "urllib3<1.26.5",  # Example insecure versions
                "requests<2.25.0",
                "flask<2.0.0"
            ]
            
            for line in content.split('\n'):
                for insecure in insecure_packages:
                    if insecure.split('<')[0] in line:
                        self.add_finding(
                            tool="dependency_check",
                            severity="high",
                            category="insecure_dependency",
                            title=f"Potentially insecure package: {insecure}",
                            description=f"Package may be vulnerable: {line}",
                            file_path=str(file_path)
                        )
        
        except Exception as e:
            logger.error(f"Failed to analyze {file_path}: {e}")
    
    async def check_configuration_security(self):
        """Check configuration files for security issues"""
        logger.info("⚙️ Checking configuration security...")
        
        config_patterns = {
            "hardcoded_secrets": [
                r"password\s*=\s*['\"][^'\"]+['\"]",
                r"secret\s*=\s*['\"][^'\"]+['\"]",
                r"api_key\s*=\s*['\"][^'\"]+['\"]",
                r"token\s*=\s*['\"][^'\"]+['\"]"
            ],
            "debug_enabled": [
                r"debug\s*=\s*true",
                r"DEBUG\s*=\s*True"
            ],
            "insecure_defaults": [
                r"host\s*=\s*['\"]0\.0\.0\.0['\"]",
                r"ssl_verify\s*=\s*false"
            ]
        }
        
        config_files = [
            "*.py", "*.ini", "*.cfg", "*.yaml", "*.yml", "*.json", "*.env"
        ]
        
        for pattern in config_files:
            for file_path in self.project_root.glob(f"**/{pattern}"):
                if self._should_scan_file(file_path):
                    await self._scan_file_for_patterns(file_path, config_patterns)
    
    def _should_scan_file(self, file_path: Path) -> bool:
        """Check if file should be scanned"""
        exclude_dirs = ["venv", "node_modules", ".git", "__pycache__", ".pytest_cache"]
        return not any(part in exclude_dirs for part in file_path.parts)
    
    async def _scan_file_for_patterns(self, file_path: Path, patterns: Dict[str, List[str]]):
        """Scan file for security patterns"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            import re
            
            for category, pattern_list in patterns.items():
                for pattern in pattern_list:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        
                        severity = "high" if "secret" in category else "medium"
                        
                        self.add_finding(
                            tool="config_scanner",
                            severity=severity,
                            category=category,
                            title=f"Security issue in configuration: {category}",
                            description=f"Pattern '{pattern}' found",
                            file_path=str(file_path),
                            line_number=line_num,
                            matched_text=match.group()
                        )
        
        except Exception as e:
            logger.error(f"Failed to scan {file_path}: {e}")
    
    async def check_api_security(self):
        """Check API-specific security configurations"""
        logger.info("🌐 Checking API security...")
        
        # Check for CORS configuration
        cors_files = list(self.project_root.glob("**/main.py")) + \
                    list(self.project_root.glob("**/app.py"))
        
        for file_path in cors_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Check for overly permissive CORS
                if "allow_origins=[\"*\"]" in content or "allow_origins='*'" in content:
                    self.add_finding(
                        tool="api_security_check",
                        severity="high",
                        category="cors_misconfiguration",
                        title="Overly permissive CORS configuration",
                        description="CORS allows all origins (*) which can be dangerous in production",
                        file_path=str(file_path),
                        recommendation="Specify explicit origins instead of using '*'"
                    )
                
                # Check for missing security headers
                if "SecurityHeadersMiddleware" not in content:
                    self.add_finding(
                        tool="api_security_check",
                        severity="medium",
                        category="missing_security_headers",
                        title="Security headers middleware not found",
                        description="Application may be missing security headers",
                        file_path=str(file_path),
                        recommendation="Add security headers middleware"
                    )
            
            except Exception as e:
                logger.error(f"Failed to check API security in {file_path}: {e}")
    
    async def check_docker_security(self):
        """Check Docker configuration security"""
        logger.info("🐳 Checking Docker security...")
        
        dockerfile_path = self.project_root / "Dockerfile"
        if dockerfile_path.exists():
            try:
                with open(dockerfile_path, 'r') as f:
                    content = f.read()
                
                # Check for security issues
                issues = {
                    "USER root": "Running as root user",
                    "FROM .*:latest": "Using 'latest' tag is not recommended",
                    "COPY . .": "Copying entire context may include sensitive files",
                    "--privileged": "Privileged mode is dangerous"
                }
                
                import re
                for pattern, description in issues.items():
                    if re.search(pattern, content, re.IGNORECASE):
                        self.add_finding(
                            tool="docker_security_check",
                            severity="medium",
                            category="docker_security",
                            title="Docker security issue",
                            description=description,
                            file_path=str(dockerfile_path),
                            pattern=pattern
                        )
            
            except Exception as e:
                logger.error(f"Failed to check Docker security: {e}")
    
    async def check_secrets_exposure(self):
        """Check for exposed secrets and sensitive data"""
        logger.info("🔑 Checking for exposed secrets...")
        
        # Pattern for common secrets
        secret_patterns = [
            (r"sk-[a-zA-Z0-9]{48}", "OpenAI API Key"),
            (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
            (r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "UUID/API Key"),
            (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
            (r"xox[baprs]-[a-zA-Z0-9-]{10,48}", "Slack Token")
        ]
        
        for file_path in self.project_root.glob("**/*"):
            if file_path.is_file() and self._should_scan_file(file_path):
                await self._scan_for_secrets(file_path, secret_patterns)
    
    async def _scan_for_secrets(self, file_path: Path, patterns: List[tuple]):
        """Scan file for secret patterns"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            import re
            
            for pattern, secret_type in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    
                    self.add_finding(
                        tool="secret_scanner",
                        severity="critical",
                        category="exposed_secret",
                        title=f"Potential {secret_type} exposed",
                        description=f"Found pattern matching {secret_type}",
                        file_path=str(file_path),
                        line_number=line_num,
                        secret_type=secret_type
                    )
        
        except Exception as e:
            # Ignore binary files and encoding errors
            pass
    
    def add_finding(self, tool: str, severity: str, category: str, title: str, 
                   description: str, **kwargs):
        """Add a security finding to the report"""
        finding = {
            "id": f"{tool}_{len(self.results['findings'])}",
            "tool": tool,
            "severity": severity,
            "category": category,
            "title": title,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        
        self.results["findings"].append(finding)
    
    async def generate_report(self):
        """Generate comprehensive security report"""
        logger.info("📄 Generating security report...")
        
        # Calculate summary statistics
        findings = self.results["findings"]
        
        severity_counts = {}
        category_counts = {}
        tool_counts = {}
        
        for finding in findings:
            severity = finding["severity"]
            category = finding["category"]
            tool = finding["tool"]
            
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
        
        self.results["summary"] = {
            "total_findings": len(findings),
            "by_severity": severity_counts,
            "by_category": category_counts,
            "by_tool": tool_counts,
            "risk_score": self._calculate_risk_score(findings)
        }
        
        # Generate recommendations
        self.results["recommendations"] = self._generate_recommendations(findings)
        
        # Save JSON report
        with open(self.report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Generate HTML report
        await self._generate_html_report()
        
        # Print summary
        self._print_summary()
    
    def _calculate_risk_score(self, findings: List[Dict]) -> int:
        """Calculate overall risk score (0-100)"""
        severity_weights = {
            "critical": 10,
            "high": 7,
            "medium": 4,
            "low": 1
        }
        
        total_score = sum(severity_weights.get(f["severity"], 0) for f in findings)
        # Normalize to 0-100 scale
        return min(100, total_score)
    
    def _generate_recommendations(self, findings: List[Dict]) -> List[str]:
        """Generate security recommendations based on findings"""
        recommendations = []
        
        # Check for common issues and generate specific recommendations
        critical_count = len([f for f in findings if f["severity"] == "critical"])
        high_count = len([f for f in findings if f["severity"] == "high"])
        
        if critical_count > 0:
            recommendations.append("🚨 URGENT: Address critical security vulnerabilities immediately")
        
        if high_count > 0:
            recommendations.append("⚠️ HIGH PRIORITY: Fix high-severity security issues")
        
        # Category-specific recommendations
        categories = set(f["category"] for f in findings)
        
        if "exposed_secret" in categories:
            recommendations.append("🔑 Rotate any exposed secrets immediately")
            recommendations.append("🔒 Implement proper secret management (e.g., environment variables, vault)")
        
        if "dependency_vulnerability" in categories:
            recommendations.append("📦 Update vulnerable dependencies to latest secure versions")
        
        if "cors_misconfiguration" in categories:
            recommendations.append("🌐 Review and restrict CORS configuration")
        
        if "docker_security" in categories:
            recommendations.append("🐳 Review Docker configuration for security best practices")
        
        # General recommendations
        recommendations.extend([
            "✅ Set up automated security scanning in CI/CD pipeline",
            "📚 Conduct security training for development team",
            "🔄 Implement regular security audits",
            "📋 Create incident response plan for security breaches"
        ])
        
        return recommendations
    
    async def _generate_html_report(self):
        """Generate HTML report for better readability"""
        html_file = self.output_dir / f"security_audit_{self.audit_timestamp}.html"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Security Audit Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f44336; color: white; padding: 20px; border-radius: 5px; }}
                .summary {{ background: #fff3cd; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                .finding {{ border-left: 4px solid #ddd; padding: 10px; margin: 10px 0; }}
                .critical {{ border-left-color: #f44336; background: #ffebee; }}
                .high {{ border-left-color: #ff9800; background: #fff3e0; }}
                .medium {{ border-left-color: #ff5722; background: #fce4ec; }}
                .low {{ border-left-color: #4caf50; background: #e8f5e8; }}
                .recommendations {{ background: #e3f2fd; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔒 Security Audit Report</h1>
                <p>Generated: {self.results['audit_info']['timestamp']}</p>
            </div>
            
            <div class="summary">
                <h2>📊 Summary</h2>
                <p><strong>Total Findings:</strong> {self.results['summary']['total_findings']}</p>
                <p><strong>Risk Score:</strong> {self.results['summary']['risk_score']}/100</p>
                <p><strong>By Severity:</strong> {json.dumps(self.results['summary']['by_severity'], indent=2)}</p>
            </div>
            
            <div class="recommendations">
                <h2>💡 Recommendations</h2>
                <ul>
                    {''.join(f'<li>{rec}</li>' for rec in self.results['recommendations'])}
                </ul>
            </div>
            
            <h2>🔍 Detailed Findings</h2>
        """
        
        for finding in self.results["findings"]:
            severity_class = finding["severity"]
            html_content += f"""
            <div class="finding {severity_class}">
                <h3>{finding['title']} ({finding['severity'].upper()})</h3>
                <p><strong>Tool:</strong> {finding['tool']}</p>
                <p><strong>Category:</strong> {finding['category']}</p>
                <p><strong>Description:</strong> {finding['description']}</p>
                {f"<p><strong>File:</strong> {finding.get('file_path', 'N/A')}</p>" if finding.get('file_path') else ""}
                {f"<p><strong>Line:</strong> {finding.get('line_number', 'N/A')}</p>" if finding.get('line_number') else ""}
            </div>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        logger.info(f"HTML report saved to: {html_file}")
    
    def _print_summary(self):
        """Print audit summary to console"""
        summary = self.results["summary"]
        
        print("\n" + "="*60)
        print("🔒 SECURITY AUDIT SUMMARY")
        print("="*60)
        print(f"Total Findings: {summary['total_findings']}")
        print(f"Risk Score: {summary['risk_score']}/100")
        print("\nFindings by Severity:")
        for severity, count in summary['by_severity'].items():
            print(f"  {severity.upper()}: {count}")
        
        print("\nTop Recommendations:")
        for i, rec in enumerate(self.results["recommendations"][:5], 1):
            print(f"  {i}. {rec}")
        
        print(f"\nDetailed reports saved to:")
        print(f"  JSON: {self.report_file}")
        print(f"  HTML: {str(self.report_file).replace('.json', '.html')}")

async def main():
    """Main function to run security audit"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Comprehensive Security Audit")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--output-dir", default="security_reports", help="Output directory for reports")
    
    args = parser.parse_args()
    
    audit = SecurityAudit(args.project_root, args.output_dir)
    await audit.run_full_audit()

if __name__ == "__main__":
    asyncio.run(main()) 