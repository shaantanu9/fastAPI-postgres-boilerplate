#!/bin/bash
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
