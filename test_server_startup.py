#!/usr/bin/env python3
"""
Test script to verify Gunicorn server starts correctly
"""

import subprocess
import time
import requests
import signal
import os

def test_server_startup():
    """Test that the server starts without errors"""
    print("🧪 Testing Gunicorn Server Startup")
    print("=" * 50)
    
    # Start the server in background
    print("🚀 Starting server...")
    env = os.environ.copy()
    env['ENVIRONMENT'] = 'development'
    
    process = subprocess.Popen([
        'gunicorn', 
        '--config', 'scripts/setup/gunicorn.conf.py',
        'app.main:app'
    ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        # Wait a bit for server to start
        print("⏳ Waiting for server to start...")
        time.sleep(8)
        
        # Check if process is still running (good sign)
        if process.poll() is None:
            print("✅ Server process is running!")
            
            # Try to make a request
            try:
                response = requests.get("http://localhost:8000/health", timeout=5)
                if response.status_code == 200:
                    print("✅ Server is responding to requests!")
                    print(f"📊 Health check status: {response.status_code}")
                else:
                    print(f"⚠️ Server responded with status: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"⚠️ Could not connect to server: {e}")
                print("   (This might be normal if server is still starting)")
        else:
            print("❌ Server process exited unexpectedly")
            stdout, stderr = process.communicate()
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            
    finally:
        # Clean up - stop the server
        print("🛑 Stopping server...")
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        print("✅ Server stopped")

if __name__ == "__main__":
    test_server_startup() 