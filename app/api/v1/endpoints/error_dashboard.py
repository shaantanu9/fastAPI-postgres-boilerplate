"""
Error Dashboard API Endpoints

Provides REST API for accessing centralized error aggregation data.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.core.error_aggregator import error_aggregator

router = APIRouter()

class ErrorSummaryResponse(BaseModel):
    """Error summary response model"""
    total_events: int
    total_groups: int
    events_by_level: Dict[str, int]
    top_error_groups: List[Dict[str, Any]]
    error_timeline: List[Dict[str, Any]]
    affected_users: int
    affected_paths: int

class ErrorDetailsResponse(BaseModel):
    """Error details response model"""
    group: Dict[str, Any]
    recent_events: List[Dict[str, Any]]
    occurrence_timeline: List[Dict[str, Any]]

@router.get("/errors/dashboard", response_model=Dict[str, Any], tags=["Error Dashboard"])
async def get_error_dashboard(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back (max 1 week)"),
    request: Request = None
):
    """
    Get comprehensive error dashboard data.
    
    Returns error statistics, trends, and top error groups for the specified time period.
    Includes error timeline, affected users/paths, and recent alerts.
    
    Args:
        hours (int): Time period to look back (1-168 hours).
        request (Request): Optional request object for correlation ID.
    
    Returns:
        Dict[str, Any]: Error dashboard data including statistics, trends, and top error groups.
        
    Raises:
        HTTPException: If retrieval fails.
    """
    try:
        dashboard_data = error_aggregator.get_dashboard_data(hours=hours)
        
        # Add metadata
        dashboard_data['metadata'] = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'time_range_hours': hours,
            'request_id': getattr(request.state, 'correlation_id', None) if request else None
        }
        
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve dashboard data: {str(e)}"
        )

@router.get("/errors/summary", response_model=ErrorSummaryResponse, tags=["Error Dashboard"])
async def get_error_summary(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back")
):
    """
    Get error summary statistics for the specified time period.
    """
    try:
        dashboard_data = error_aggregator.get_dashboard_data(hours=hours)
        return ErrorSummaryResponse(**dashboard_data['summary'])
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve error summary: {str(e)}"
        )

@router.get("/errors/groups/{fingerprint}", response_model=ErrorDetailsResponse, tags=["Error Dashboard"])
async def get_error_group_details(
    fingerprint: str,
    limit: int = Query(50, ge=1, le=500, description="Max events to return")
):
    """
    Get detailed information about a specific error group.
    
    Retrieves comprehensive details about an error group identified by its fingerprint,
    including recent occurrences, stack traces, and occurrence timeline.
    
    Args:
        fingerprint (str): The unique fingerprint/identifier of the error group.
        limit (int): Maximum number of recent events to return (1-500).
    
    Returns:
        ErrorDetailsResponse: Detailed information about the error group including
                             recent events and occurrence timeline.
                             
    Raises:
        HTTPException: If the error group is not found or if retrieval fails.
    """
    try:
        error_details = error_aggregator.get_error_details(fingerprint)
        
        if not error_details:
            raise HTTPException(
                status_code=404,
                detail=f"Error group with fingerprint '{fingerprint}' not found"
            )
        
        # Limit recent events
        error_details['recent_events'] = error_details['recent_events'][:limit]
        
        return ErrorDetailsResponse(**error_details)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve error details: {str(e)}"
        )

@router.get("/errors/alerts", tags=["Error Dashboard"])
async def get_error_alerts(
    limit: int = Query(50, ge=1, le=500, description="Max alerts to return"),
    severity: Optional[str] = Query(None, regex="^(critical|warning|info)$", description="Filter by severity")
):
    """
    Get recent error alerts with optional severity filtering.
    
    Retrieves the most recent error alerts from the system, with options to filter by
    severity level and limit the number of results. Useful for monitoring dashboards
    and alert systems.
    
    Args:
        limit (int): Maximum number of alerts to return (1-500).
        severity (Optional[str]): Filter alerts by severity level (critical, warning, or info).
    
    Returns:
        Dict[str, Any]: List of error alerts with their details including timestamp,
                             message, severity, and context.
                             
    Raises:
        HTTPException: If retrieval fails.
    """
    try:
        alerts = list(error_aggregator.alerts)
        
        # Filter by severity if specified
        if severity:
            alerts = [alert for alert in alerts if alert.get('severity') == severity]
        
        # Sort by timestamp (newest first) and limit
        alerts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        alerts = alerts[:limit]
        
        return {
            'alerts': alerts,
            'total_count': len(list(error_aggregator.alerts)),
            'filtered_count': len(alerts),
            'severity_filter': severity,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve alerts: {str(e)}"
        )

@router.get("/errors/stats", tags=["Error Dashboard"])
async def get_error_stats():
    """
    Get overall error statistics and configuration.
    
    Provides aggregate statistics about the error monitoring system, including
    total errors tracked, system configuration, retention policies, and
    current system status.
    
    Returns:
        Dict[str, Any]: Error statistics and system configuration information.
        
    Raises:
        HTTPException: If retrieval fails.
    """
    try:
        stats = error_aggregator.stats.copy()
        
        # Add system information
        stats['system_info'] = {
            'max_events': error_aggregator.max_events,
            'retention_days': error_aggregator.retention_days,
            'current_events_count': len(error_aggregator.events),
            'current_groups_count': len(error_aggregator.groups),
            'alerts_count': len(error_aggregator.alerts)
        }
        
        # Add configuration
        stats['configuration'] = {
            'alert_thresholds': error_aggregator.stats['alert_thresholds']
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve error statistics: {str(e)}"
        )

@router.post("/errors/simulate", tags=["Error Dashboard"], include_in_schema=False)
async def simulate_error(
    error_type: str = Query("test_error", description="Type of error to simulate"),
    message: str = Query("This is a test error", description="Error message"),
    level: str = Query("ERROR", regex="^(ERROR|CRITICAL|WARNING)$", description="Error level")
):
    """
    Simulate an error for testing the error aggregation system.
    
    Creates a test error event in the error aggregation system to verify monitoring,
    alerting, and dashboard functionality. This endpoint is hidden from API documentation
    and should only be available in development/testing environments.
    
    Args:
        error_type (str): Type/category of error to simulate.
        message (str): Error message to include.
        level (str): Error severity level (ERROR, CRITICAL, or WARNING).
    
    Returns:
        Dict[str, Any]: Details of the simulated error including its ID and timestamp.
        
    Raises:
        HTTPException: If the error simulation fails.
    """
    try:
        # Add simulated error
        event_id = error_aggregator.add_error(
            level=level,
            message=message,
            exception_type=error_type,
            exception_message=f"Simulated {error_type} for testing",
            traceback=f"Simulated traceback for {error_type}",
            request_path="/errors/simulate",
            request_method="POST",
            context={"simulated": True, "test_type": error_type}
        )
        
        return {
            'success': True,
            'event_id': event_id,
            'message': f"Simulated {level} error: {message}",
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to simulate error: {str(e)}"
        )

@router.get("/errors/dashboard/ui", response_class=HTMLResponse, include_in_schema=False)
async def error_dashboard_ui():
    """
    Simple HTML dashboard for viewing errors (development/internal use).
    
    Provides a basic web interface for viewing error data without requiring a separate
    frontend application. This is intended for development and internal debugging use only.
    The endpoint is hidden from API documentation.
    
    Returns:
        HTMLResponse: HTML page containing the error dashboard interface.
        
    Raises:
        HTTPException: If the dashboard generation fails.
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Error Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .card { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .header { text-align: center; color: #333; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
            .stat-box { background: #007bff; color: white; padding: 15px; border-radius: 6px; text-align: center; }
            .stat-box.error { background: #dc3545; }
            .stat-box.warning { background: #ffc107; color: #333; }
            .stat-box.success { background: #28a745; }
            .error-group { border-left: 4px solid #dc3545; padding: 10px; margin: 10px 0; background: #f8f9fa; }
            .error-group h4 { margin: 0 0 5px 0; color: #dc3545; }
            .error-meta { font-size: 0.9em; color: #666; }
            .refresh-btn { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
            .refresh-btn:hover { background: #0056b3; }
            .timeline { display: flex; gap: 2px; height: 30px; align-items: end; margin: 10px 0; }
            .timeline-bar { background: #dc3545; min-width: 2px; opacity: 0.7; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h1 class="header">🚨 Error Dashboard</h1>
                <button class="refresh-btn" onclick="loadData()">🔄 Refresh Data</button>
            </div>
            
            <div class="card">
                <h2>📊 Statistics (Last 24 Hours)</h2>
                <div class="stats" id="stats-container">
                    <div class="stat-box">
                        <h3 id="total-events">-</h3>
                        <p>Total Events</p>
                    </div>
                    <div class="stat-box warning">
                        <h3 id="total-groups">-</h3>
                        <p>Error Groups</p>
                    </div>
                    <div class="stat-box error">
                        <h3 id="critical-errors">-</h3>
                        <p>Critical Errors</p>
                    </div>
                    <div class="stat-box success">
                        <h3 id="affected-users">-</h3>
                        <p>Affected Users</p>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>🔥 Top Error Groups</h2>
                <div id="error-groups-container">
                    <p>Loading...</p>
                </div>
            </div>
            
            <div class="card">
                <h2>⚠️ Recent Alerts</h2>
                <div id="alerts-container">
                    <p>Loading...</p>
                </div>
            </div>
        </div>
        
        <script>
            async function loadData() {
                try {
                    // Load dashboard data
                    const response = await fetch('/api/v1/errors/dashboard?hours=24');
                    const data = await response.json();
                    
                    // Update statistics
                    document.getElementById('total-events').textContent = data.summary.total_events;
                    document.getElementById('total-groups').textContent = data.summary.total_groups;
                    document.getElementById('critical-errors').textContent = data.summary.events_by_level.CRITICAL || 0;
                    document.getElementById('affected-users').textContent = data.summary.affected_users;
                    
                    // Update error groups
                    const groupsContainer = document.getElementById('error-groups-container');
                    if (data.summary.top_error_groups.length === 0) {
                        groupsContainer.innerHTML = '<p>🎉 No errors in the last 24 hours!</p>';
                    } else {
                        groupsContainer.innerHTML = data.summary.top_error_groups.map(group => `
                            <div class="error-group">
                                <h4>${group.exception_type || 'Unknown'}: ${group.message}</h4>
                                <div class="error-meta">
                                    Count: ${group.count} | Rate: ${group.rate_per_hour}/hour | 
                                    Fingerprint: ${group.fingerprint}
                                </div>
                            </div>
                        `).join('');
                    }
                    
                    // Update alerts
                    const alertsContainer = document.getElementById('alerts-container');
                    if (data.recent_alerts.length === 0) {
                        alertsContainer.innerHTML = '<p>✅ No recent alerts</p>';
                    } else {
                        alertsContainer.innerHTML = data.recent_alerts.map(alert => `
                            <div class="error-group">
                                <h4>${alert.type}: ${alert.message}</h4>
                                <div class="error-meta">
                                    Severity: ${alert.severity} | Time: ${new Date(alert.timestamp).toLocaleString()}
                                </div>
                            </div>
                        `).join('');
                    }
                    
                } catch (error) {
                    console.error('Failed to load dashboard data:', error);
                    document.getElementById('error-groups-container').innerHTML = 
                        '<p style="color: red;">❌ Failed to load data. Check console for details.</p>';
                }
            }
            
            // Load data on page load
            loadData();
            
            // Auto-refresh every 30 seconds
            setInterval(loadData, 30000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@router.get("/errors/health", tags=["Error Dashboard"])
async def error_system_health():
    """
    Health check for the error aggregation system.
    """
    try:
        current_time = datetime.utcnow()
        
        # Check if system is processing errors
        recent_events = [
            e for e in error_aggregator.events
            if (current_time - e.timestamp).total_seconds() < 300  # Last 5 minutes
        ]
        
        health_status = {
            'status': 'healthy',
            'timestamp': current_time.isoformat() + 'Z',
            'metrics': {
                'total_events_stored': len(error_aggregator.events),
                'total_groups': len(error_aggregator.groups),
                'recent_events_5min': len(recent_events),
                'alerts_count': len(error_aggregator.alerts),
                'retention_days': error_aggregator.retention_days,
                'max_events': error_aggregator.max_events
            },
            'last_event_time': error_aggregator.events[-1].timestamp.isoformat() + 'Z' if error_aggregator.events else None
        }
        
        # Determine health status
        if len(error_aggregator.events) >= error_aggregator.max_events * 0.9:
            health_status['status'] = 'warning'
            health_status['warning'] = 'Near storage capacity'
        
        return health_status
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        } 