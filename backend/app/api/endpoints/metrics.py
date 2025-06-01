"""
Metrics API Endpoints

This module provides REST API endpoints for accessing two-pass processing
performance metrics, health status, and monitoring data.

Created for Task 11.3 - Add monitoring and metrics for two-pass processing performance
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.metrics_collector import (
    get_health_status,
    get_performance_analysis, 
    get_performance_trends,
    ProcessingHealthStatus,
    MetricAlert
)
from app.core.logging_config import get_logger

logger = get_logger("metrics_api")

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/health", 
            summary="Get Two-Pass Processing Health Status",
            description="Retrieve the current health status of two-pass processing including alerts and recommendations",
            response_model=Dict[str, Any])
async def get_processing_health(hours: int = Query(24, ge=1, le=168, description="Number of hours to analyze (1-168)")):
    """
    Get current health status of two-pass processing system
    
    Args:
        hours: Number of hours to analyze (default: 24, max: 168/1 week)
        
    Returns:
        Health status with overall score, alerts, and recommendations
    """
    try:
        health_status = get_health_status(hours)
        
        # Convert dataclass to dictionary for JSON response
        health_dict = {
            'status': health_status.status,
            'overall_score': health_status.overall_score,
            'summary': health_status.summary,
            'recommendations': health_status.recommendations,
            'timestamp': health_status.timestamp.isoformat(),
            'analysis_period_hours': hours,
            'alerts': [
                {
                    'severity': alert.severity.value,
                    'metric_name': alert.metric_name,
                    'message': alert.message,
                    'value': alert.value,
                    'threshold': alert.threshold,
                    'timestamp': alert.timestamp.isoformat(),
                    'recommendation': alert.recommendation
                }
                for alert in health_status.alerts
            ]
        }
        
        logger.info(f"Health status requested for {hours}h period - Status: {health_status.status}, Score: {health_status.overall_score:.1f}")
        
        return {
            'success': True,
            'data': health_dict
        }
        
    except Exception as e:
        logger.error(f"Failed to get health status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve health status: {str(e)}")


@router.get("/performance", 
            summary="Get Performance Analysis",
            description="Retrieve detailed performance analysis for two-pass processing over a specified time period",
            response_model=Dict[str, Any])
async def get_performance_metrics(hours: int = Query(24, ge=1, le=168, description="Number of hours to analyze (1-168)")):
    """
    Get detailed performance analysis for two-pass processing
    
    Args:
        hours: Number of hours to analyze (default: 24, max: 168/1 week)
        
    Returns:
        Detailed performance metrics including processing times, success rates, and throughput
    """
    try:
        analysis = get_performance_analysis(hours)
        
        logger.info(f"Performance analysis requested for {hours}h period - {analysis.get('total_requests', 0)} requests analyzed")
        
        return {
            'success': True,
            'data': analysis
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve performance metrics: {str(e)}")


@router.get("/trends", 
            summary="Get Performance Trends",
            description="Retrieve performance trends over multiple days showing daily breakdown and patterns",
            response_model=Dict[str, Any])
async def get_performance_trend_analysis(days: int = Query(7, ge=1, le=30, description="Number of days to analyze (1-30)")):
    """
    Get performance trends over multiple days
    
    Args:
        days: Number of days to analyze (default: 7, max: 30)
        
    Returns:
        Daily performance breakdown and trend analysis
    """
    try:
        trends = get_performance_trends(days)
        
        if 'error' in trends:
            return {
                'success': False,
                'error': trends['error'],
                'data': None
            }
        
        logger.info(f"Performance trends requested for {days} days - {len(trends.get('daily_breakdown', {}))} days analyzed")
        
        return {
            'success': True,
            'data': trends
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance trends: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve performance trends: {str(e)}")


@router.get("/summary", 
            summary="Get Metrics Summary",
            description="Get a concise summary of key performance indicators and system health",
            response_model=Dict[str, Any])
async def get_metrics_summary(hours: int = Query(24, ge=1, le=168, description="Number of hours to analyze (1-168)")):
    """
    Get concise metrics summary with key performance indicators
    
    Args:
        hours: Number of hours to analyze (default: 24, max: 168/1 week)
        
    Returns:
        Summary of key metrics and health indicators
    """
    try:
        # Get both health status and performance analysis
        health = get_health_status(hours)
        performance = get_performance_analysis(hours)
        
        # Create summary
        summary = {
            'analysis_period_hours': hours,
            'timestamp': datetime.now().isoformat(),
            'health': {
                'status': health.status,
                'overall_score': health.overall_score,
                'alert_count': len(health.alerts),
                'critical_alerts': len([a for a in health.alerts if a.severity.value == 'critical']),
                'error_alerts': len([a for a in health.alerts if a.severity.value == 'error'])
            },
            'performance': {
                'total_requests': performance.get('total_requests', 0),
                'success_rate_percentage': performance.get('success_rate_percentage', 0),
                'avg_processing_time_seconds': performance.get('processing_time_stats', {}).get('avg_seconds', 0),
                'avg_quality_score': performance.get('quality_stats', {}).get('avg_quality_score', 0),
                'avg_throughput_employees_per_second': performance.get('throughput_stats', {}).get('avg_employees_per_second', 0)
            },
            'recommendations': health.recommendations[:3] if health.recommendations else []  # Top 3 recommendations
        }
        
        logger.info(f"Metrics summary requested for {hours}h - {performance.get('total_requests', 0)} requests, {health.status} health")
        
        return {
            'success': True,
            'data': summary
        }
        
    except Exception as e:
        logger.error(f"Failed to get metrics summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve metrics summary: {str(e)}")


@router.get("/dashboard", 
            summary="Get Dashboard Data",
            description="Get comprehensive dashboard data combining health, performance, and trends for monitoring displays",
            response_model=Dict[str, Any])
async def get_dashboard_data(
    hours: int = Query(24, ge=1, le=168, description="Number of hours for health/performance analysis"),
    trend_days: int = Query(7, ge=1, le=30, description="Number of days for trend analysis")
):
    """
    Get comprehensive dashboard data for monitoring displays
    
    Args:
        hours: Number of hours to analyze for health/performance (default: 24, max: 168)
        trend_days: Number of days to analyze for trends (default: 7, max: 30)
        
    Returns:
        Comprehensive dashboard data including health, performance, and trends
    """
    try:
        # Get all data types
        health = get_health_status(hours)
        performance = get_performance_analysis(hours)
        trends = get_performance_trends(trend_days)
        
        dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'analysis_periods': {
                'health_performance_hours': hours,
                'trends_days': trend_days
            },
            'health_status': {
                'status': health.status,
                'overall_score': health.overall_score,
                'summary': health.summary,
                'alerts_summary': {
                    'total': len(health.alerts),
                    'critical': len([a for a in health.alerts if a.severity.value == 'critical']),
                    'error': len([a for a in health.alerts if a.severity.value == 'error']),
                    'warning': len([a for a in health.alerts if a.severity.value == 'warning'])
                },
                'top_recommendations': health.recommendations[:3]
            },
            'performance_summary': {
                'total_requests': performance.get('total_requests', 0),
                'success_rate_percentage': performance.get('success_rate_percentage', 0),
                'failed_requests': performance.get('failed_requests', 0),
                'avg_processing_time_seconds': performance.get('processing_time_stats', {}).get('avg_seconds', 0),
                'avg_quality_score': performance.get('quality_stats', {}).get('avg_quality_score', 0),
                'throughput_employees_per_second': performance.get('throughput_stats', {}).get('avg_employees_per_second', 0)
            },
            'trends_available': 'error' not in trends,
            'recent_alerts': [
                {
                    'severity': alert.severity.value,
                    'metric': alert.metric_name,
                    'message': alert.message,
                    'recommendation': alert.recommendation
                }
                for alert in health.alerts[:5]  # Most recent 5 alerts
            ]
        }
        
        # Add trends if available
        if 'error' not in trends:
            dashboard_data['trends_summary'] = {
                'days_analyzed': trends.get('period_days', 0),
                'daily_data_points': len(trends.get('daily_breakdown', {}))
            }
        
        logger.info(f"Dashboard data requested - Health: {health.status}, Requests: {performance.get('total_requests', 0)}")
        
        return {
            'success': True,
            'data': dashboard_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve dashboard data: {str(e)}") 