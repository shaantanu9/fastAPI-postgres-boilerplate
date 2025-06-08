#!/usr/bin/env python3
"""
Comprehensive Procrastinate Job Scheduling Test

This script tests all aspects of the Procrastinate job scheduling system:
1. Task queuing and execution
2. Job status monitoring 
3. Scheduled tasks
4. Different task types and priorities
5. Queue statistics
6. Health checks
7. Error handling and retries
"""

import asyncio
import httpx
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"

async def test_procrastinate_comprehensive():
    """Run comprehensive tests of all Procrastinate features"""
    
    print("🧪 PROCRASTINATE COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        # Test 1: Health Check
        print("\n1️⃣ TESTING PROCRASTINATE HEALTH")
        await test_procrastinate_health(client)
        
        # Test 2: Queue Statistics  
        print("\n2️⃣ TESTING QUEUE STATISTICS")
        await test_queue_statistics(client)
        
        # Test 3: User Processing Task
        print("\n3️⃣ TESTING USER PROCESSING TASK")
        job_id_1 = await test_user_processing_task(client)
        
        # Test 4: Bulk Processing Task
        print("\n4️⃣ TESTING BULK PROCESSING TASK") 
        job_id_2 = await test_bulk_processing_task(client)
        
        # Test 5: Notification Task
        print("\n5️⃣ TESTING NOTIFICATION TASK")
        job_id_3 = await test_notification_task(client)
        
        # Test 6: File Processing Task
        print("\n6️⃣ TESTING FILE PROCESSING TASK")
        job_id_4 = await test_file_processing_task(client)
        
        # Test 7: Analytics Report Task  
        print("\n7️⃣ TESTING ANALYTICS REPORT TASK")
        job_id_5 = await test_analytics_report_task(client)
        
        # Test 8: Scheduled Tasks
        print("\n8️⃣ TESTING SCHEDULED TASKS")
        cleanup_job_id = await test_scheduled_cleanup_task(client)
        health_check_job_id = await test_scheduled_health_check(client)
        
        # Test 9: Job Status Monitoring
        print("\n9️⃣ TESTING JOB STATUS MONITORING")
        all_job_ids = [job_id_1, job_id_2, job_id_3, job_id_4, job_id_5, cleanup_job_id, health_check_job_id]
        await test_job_status_monitoring(client, all_job_ids)
        
        # Test 10: Error Handling
        print("\n🔟 TESTING ERROR HANDLING")
        await test_error_handling(client)
        
        print("\n✅ COMPREHENSIVE PROCRASTINATE TESTS COMPLETED!")
        print("=" * 60)


async def test_procrastinate_health(client: httpx.AsyncClient):
    """Test Procrastinate health check endpoint"""
    try:
        response = await client.get(f"{BASE_URL}/api/v1/procrastinate/health")
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Health Status: {data}")
        else:
            print(f"  ❌ Health check failed: {response.text}")
    except Exception as e:
        print(f"  ❌ Health check error: {e}")


async def test_queue_statistics(client: httpx.AsyncClient):
    """Test queue statistics endpoint"""
    try:
        response = await client.get(f"{BASE_URL}/api/v1/procrastinate/queue/stats")
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Queue Stats: {json.dumps(data, indent=2)}")
        else:
            print(f"  ❌ Queue stats failed: {response.text}")
    except Exception as e:
        print(f"  ❌ Queue stats error: {e}")


async def test_user_processing_task(client: httpx.AsyncClient) -> str:
    """Test user processing task creation"""
    try:
        payload = {
            "user_id": 12345,
            "operation": "profile_update",
            "priority": "high",
            "additional_data": {
                "fields": ["email", "name", "preferences"],
                "notify_user": True,
                "audit_log": True
            }
        }
        
        response = await client.post(f"{BASE_URL}/api/v1/procrastinate/user-processing", json=payload)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            job_id = data.get("job_id")
            print(f"  ✅ User Processing Task Created")
            print(f"     Job ID: {job_id}")
            print(f"     Status: {data.get('status')}")
            print(f"     Message: {data.get('message')}")
            return job_id
        else:
            print(f"  ❌ User processing failed: {response.text}")
            return None
    except Exception as e:
        print(f"  ❌ User processing error: {e}")
        return None


async def test_bulk_processing_task(client: httpx.AsyncClient) -> str:
    """Test bulk processing task creation"""
    try:
        payload = {
            "data_items": [
                {"id": 1, "action": "process", "type": "data"},
                {"id": 2, "action": "validate", "type": "data"},
                {"id": 3, "action": "transform", "type": "data"},
                {"id": 4, "action": "export", "type": "data"},
                {"id": 5, "action": "archive", "type": "data"}
            ],
            "task_type": "parallel",
            "batch_size": 2,
            "priority": "normal"
        }
        
        response = await client.post(f"{BASE_URL}/api/v1/procrastinate/bulk-processing", json=payload)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            job_id = data.get("job_id")
            print(f"  ✅ Bulk Processing Task Created")
            print(f"     Job ID: {job_id}")
            print(f"     Status: {data.get('status')}")
            print(f"     Message: {data.get('message')}")
            return job_id
        else:
            print(f"  ❌ Bulk processing failed: {response.text}")
            return None
    except Exception as e:
        print(f"  ❌ Bulk processing error: {e}")
        return None


async def test_notification_task(client: httpx.AsyncClient) -> str:
    """Test notification task creation"""
    try:
        payload = {
            "notification_type": "email",
            "recipient": "user@example.com",
            "message": "Your account has been updated successfully!",
            "priority": "high",
            "metadata": {
                "template": "account_update",
                "language": "en",
                "retry_count": 3,
                "category": "account"
            }
        }
        
        response = await client.post(f"{BASE_URL}/api/v1/procrastinate/notifications", json=payload)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            job_id = data.get("job_id")
            print(f"  ✅ Notification Task Created")
            print(f"     Job ID: {job_id}")
            print(f"     Status: {data.get('status')}")
            print(f"     Message: {data.get('message')}")
            return job_id
        else:
            print(f"  ❌ Notification failed: {response.text}")
            return None
    except Exception as e:
        print(f"  ❌ Notification error: {e}")
        return None


async def test_file_processing_task(client: httpx.AsyncClient) -> str:
    """Test file processing task creation"""
    try:
        payload = {
            "file_path": "/uploads/documents/report_2024.pdf",
            "operation": "extract_text",
            "file_size": 2048576,  # 2MB
            "priority": "normal",
            "metadata": {
                "format": "pdf",
                "pages": 25,
                "language": "en",
                "extract_tables": True,
                "generate_summary": True
            }
        }
        
        response = await client.post(f"{BASE_URL}/api/v1/procrastinate/file-processing", json=payload)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            job_id = data.get("job_id")
            print(f"  ✅ File Processing Task Created")
            print(f"     Job ID: {job_id}")
            print(f"     Status: {data.get('status')}")
            print(f"     Message: {data.get('message')}")
            return job_id
        else:
            print(f"  ❌ File processing failed: {response.text}")
            return None
    except Exception as e:
        print(f"  ❌ File processing error: {e}")
        return None


async def test_analytics_report_task(client: httpx.AsyncClient) -> str:
    """Test analytics report task creation"""
    try:
        payload = {
            "report_type": "user_engagement",
            "date_range": {
                "start": "2024-01-01",
                "end": "2024-12-31"
            },
            "priority": "high",
            "parameters": {
                "include_charts": True,
                "format": "pdf",
                "email_recipients": ["admin@example.com"],
                "breakdown_by": ["month", "region", "device_type"]
            }
        }
        
        response = await client.post(f"{BASE_URL}/api/v1/procrastinate/analytics-reports", json=payload)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            job_id = data.get("job_id")
            print(f"  ✅ Analytics Report Task Created")
            print(f"     Job ID: {job_id}")
            print(f"     Status: {data.get('status')}")
            print(f"     Message: {data.get('message')}")
            return job_id
        else:
            print(f"  ❌ Analytics report failed: {response.text}")
            return None
    except Exception as e:
        print(f"  ❌ Analytics report error: {e}")
        return None


async def test_scheduled_cleanup_task(client: httpx.AsyncClient) -> str:
    """Test scheduled cleanup task"""
    try:
        # Schedule cleanup for 2 minutes from now
        schedule_time = datetime.now() + timedelta(minutes=2)
        
        payload = {
            "task_type": "cleanup",
            "parameters": {
                "days_old": 90,
                "tables": ["logs", "temp_files", "expired_sessions"],
                "dry_run": True
            },
            "schedule_at": schedule_time.isoformat()
        }
        
        response = await client.post(f"{BASE_URL}/api/v1/procrastinate/scheduled/cleanup", json=payload)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            job_id = data.get("job_id")
            print(f"  ✅ Scheduled Cleanup Task Created")
            print(f"     Job ID: {job_id}")
            print(f"     Status: {data.get('status')}")
            print(f"     Scheduled for: {schedule_time}")
            print(f"     Message: {data.get('message')}")
            return job_id
        else:
            print(f"  ❌ Scheduled cleanup failed: {response.text}")
            return None
    except Exception as e:
        print(f"  ❌ Scheduled cleanup error: {e}")
        return None


async def test_scheduled_health_check(client: httpx.AsyncClient) -> str:
    """Test scheduled health check task"""
    try:
        # Schedule health check for 1 minute from now
        schedule_time = datetime.now() + timedelta(minutes=1)
        
        payload = {
            "task_type": "health_check",
            "parameters": {
                "check_database": True,
                "check_redis": True,
                "check_external_apis": True,
                "notification_threshold": "warning"
            },
            "schedule_at": schedule_time.isoformat()
        }
        
        response = await client.post(f"{BASE_URL}/api/v1/procrastinate/scheduled/health-check", json=payload)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            job_id = data.get("job_id")
            print(f"  ✅ Scheduled Health Check Created")
            print(f"     Job ID: {job_id}")
            print(f"     Status: {data.get('status')}")
            print(f"     Scheduled for: {schedule_time}")
            print(f"     Message: {data.get('message')}")
            return job_id
        else:
            print(f"  ❌ Scheduled health check failed: {response.text}")
            return None
    except Exception as e:
        print(f"  ❌ Scheduled health check error: {e}")
        return None


async def test_job_status_monitoring(client: httpx.AsyncClient, job_ids: List[str]):
    """Test job status monitoring for all created jobs"""
    print("  📊 Monitoring job statuses...")
    
    valid_job_ids = [job_id for job_id in job_ids if job_id is not None]
    
    for i, job_id in enumerate(valid_job_ids, 1):
        try:
            response = await client.get(f"{BASE_URL}/api/v1/procrastinate/jobs/{job_id}/status")
            print(f"    Job {i} ({job_id[:8]}...): Status {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"      ✅ Status: {data.get('status', 'unknown')}")
                if data.get('result'):
                    print(f"      📄 Result: {data.get('result')}")
                if data.get('error'):
                    print(f"      ❌ Error: {data.get('error')}")
            else:
                print(f"      ⚠️ Could not get status: {response.text}")
                
        except Exception as e:
            print(f"      ❌ Status check error: {e}")
        
        # Small delay between checks
        await asyncio.sleep(0.5)


async def test_error_handling(client: httpx.AsyncClient):
    """Test error handling and validation"""
    
    # Test 1: Invalid user ID
    try:
        payload = {
            "user_id": "invalid_id",  # Should be integer
            "operation": "test",
            "priority": "normal"
        }
        
        response = await client.post(f"{BASE_URL}/api/v1/procrastinate/user-processing", json=payload)
        print(f"  Invalid user ID test: {response.status_code}")
        if response.status_code == 422:
            print("  ✅ Validation error handled correctly")
        else:
            print(f"  ⚠️ Unexpected response: {response.text}")
    except Exception as e:
        print(f"  ❌ Invalid user ID test error: {e}")
    
    # Test 2: Missing required fields
    try:
        payload = {
            "priority": "normal"
            # Missing user_id and operation
        }
        
        response = await client.post(f"{BASE_URL}/api/v1/procrastinate/user-processing", json=payload)
        print(f"  Missing fields test: {response.status_code}")
        if response.status_code == 422:
            print("  ✅ Missing fields validation handled correctly")
        else:
            print(f"  ⚠️ Unexpected response: {response.text}")
    except Exception as e:
        print(f"  ❌ Missing fields test error: {e}")
    
    # Test 3: Empty bulk data
    try:
        payload = {
            "data_items": [],  # Empty list
            "task_type": "parallel",
            "priority": "normal"
        }
        
        response = await client.post(f"{BASE_URL}/api/v1/procrastinate/bulk-processing", json=payload)
        print(f"  Empty bulk data test: {response.status_code}")
        if response.status_code == 400:
            print("  ✅ Empty data validation handled correctly")
        else:
            print(f"  ⚠️ Unexpected response: {response.text}")
    except Exception as e:
        print(f"  ❌ Empty bulk data test error: {e}")


if __name__ == "__main__":
    print("🚀 Starting Procrastinate Comprehensive Test...")
    print("📋 Make sure the FastAPI server is running on http://localhost:8000")
    print("⚠️  Make sure Procrastinate workers are running for full testing")
    print()
    
    try:
        asyncio.run(test_procrastinate_comprehensive())
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc() 