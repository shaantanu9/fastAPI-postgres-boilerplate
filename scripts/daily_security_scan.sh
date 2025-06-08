#!/bin/bash
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
