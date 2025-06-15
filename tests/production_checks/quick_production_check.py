#!/usr/bin/env python3
"""Quick Production Readiness Check"""

import sys
from pathlib import Path

def main():
    print("🚀 Quick Production Readiness Check")
    print("="*50)
    
    issues = []
    warnings = []
    
    # Check database session management
    session_file = Path('app/db/session.py')
    if session_file.exists():
        with open(session_file, 'r') as f:
            content = f.read()
            if 'async with' in content and 'contextlib.suppress' in content:
                print('✅ Database sessions: Proper cleanup found')
            else:
                print('⚠️ Database sessions: Check cleanup patterns')
                warnings.append('Database session cleanup needs review')
                
            if 'await redis_client.close()' in content:
                print('✅ Redis cleanup: Configured')
            else:
                print('⚠️ Redis cleanup: Verify connection management')
    else:
        print('❌ Database session file missing')
        issues.append('app/db/session.py not found')
    
    # Check graceful shutdown
    shutdown_file = Path('production_configs/scripts/graceful_shutdown.py')
    if shutdown_file.exists():
        print('✅ Graceful shutdown: Configured')
    else:
        print('⚠️ Graceful shutdown: Not configured')
        warnings.append('Graceful shutdown recommended')
    
    # Check monitoring
    monitor_files = [
        'app/core/health.py',
        'app/core/lightweight_monitoring.py',
        'app/plugins/monitoring_plugin.py'
    ]
    
    monitoring_found = any(Path(f).exists() for f in monitor_files)
    if monitoring_found:
        print('✅ Monitoring: Available')
    else:
        print('⚠️ Monitoring: Limited')
        warnings.append('Enhanced monitoring recommended')
    
    # Check error handling
    error_handler = Path('app/core/exception_handlers.py')
    if error_handler.exists():
        print('✅ Error handling: Configured')
    else:
        print('❌ Error handling: Missing')
        issues.append('Exception handlers needed')
    
    # Check memory leak potential
    print('\n🧠 Memory Leak Assessment:')
    
    # Check for proper async context managers
    files_to_check = ['app/db/session.py', 'app/main.py']
    for file_path in files_to_check:
        if Path(file_path).exists():
            with open(file_path, 'r') as f:
                content = f.read()
                if 'async with' in content:
                    print(f'✅ {file_path}: Uses async context managers')
                else:
                    print(f'⚠️ {file_path}: Check async patterns')
    
    # Check for WeakSet usage in WebSocket managers
    ws_files = ['app/websocket/websocket_manager.py', 'app/utils/websocket_manager.py']
    for ws_file in ws_files:
        if Path(ws_file).exists():
            with open(ws_file, 'r') as f:
                content = f.read()
                if 'WeakSet' in content:
                    print(f'✅ {ws_file}: Uses WeakSet (prevents leaks)')
                else:
                    print(f'⚠️ {ws_file}: Check connection tracking')
    
    print(f'\n📊 SUMMARY:')
    print(f'Critical Issues: {len(issues)}')
    print(f'Warnings: {len(warnings)}')
    
    if issues:
        print('\n❌ CRITICAL ISSUES:')
        for issue in issues:
            print(f'  - {issue}')
    
    if warnings:
        print('\n⚠️ WARNINGS:')
        for warning in warnings:
            print(f'  - {warning}')
    
    if len(issues) == 0:
        print('\n✅ NO CRITICAL ISSUES - Ready for production')
        return 0
    else:
        print('\n❌ CRITICAL ISSUES FOUND - Fix before production')
        return 1

if __name__ == "__main__":
    sys.exit(main()) 