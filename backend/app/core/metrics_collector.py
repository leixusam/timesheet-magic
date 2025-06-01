"""
Two-Pass Processing Metrics Collection and Analysis

This module provides utilities for collecting, analyzing, and monitoring 
two-pass processing performance metrics. It includes functions for:
- Metrics aggregation and analysis
- Performance monitoring and alerting 
- Operational insights and reporting
- Health check assessments

Created for Task 11.3 - Add monitoring and metrics for two-pass processing performance
"""

import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import statistics
from dataclasses import dataclass
from enum import Enum

from app.core.logging_config import get_logger

logger = get_logger("metrics")


class MetricSeverity(Enum):
    """Severity levels for metric alerts"""
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricAlert:
    """Alert generated from metric analysis"""
    severity: MetricSeverity
    metric_name: str
    message: str
    value: float
    threshold: float
    timestamp: datetime
    recommendation: Optional[str] = None


@dataclass
class ProcessingHealthStatus:
    """Overall health status of two-pass processing"""
    status: str  # "healthy", "degraded", "unhealthy"
    overall_score: float  # 0-100
    alerts: List[MetricAlert]
    summary: str
    recommendations: List[str]
    timestamp: datetime


class TwoPassMetricsCollector:
    """Collector and analyzer for two-pass processing metrics"""
    
    def __init__(self):
        self.metrics_history: List[Dict[str, Any]] = []
        self.performance_thresholds = {
            'max_processing_time_seconds': 300,  # 5 minutes
            'min_success_rate_percentage': 90,
            'min_quality_score': 75,
            'max_failure_rate_percentage': 10,
            'min_throughput_employees_per_second': 0.1,
            'max_average_time_per_employee': 30
        }
    
    def collect_metrics(self, processing_result: Dict[str, Any]) -> None:
        """
        Collect metrics from a two-pass processing result
        
        Args:
            processing_result: Result dictionary from two-pass processing
        """
        try:
            metadata = processing_result.get('processing_metadata', {})
            performance_metrics = metadata.get('performance_metrics', {})
            
            if not performance_metrics:
                logger.warning("No performance metrics found in processing result")
                return
            
            # Extract and normalize metrics
            metric_entry = {
                'timestamp': datetime.now(),
                'request_id': metadata.get('request_id', 'unknown'),
                'filename': metadata.get('original_filename', 'unknown'),
                'processing_mode': performance_metrics.get('monitoring_summary', {}).get('processing_mode', 'unknown'),
                'workflow_success': performance_metrics.get('workflow_success', False),
                'metrics': performance_metrics
            }
            
            self.metrics_history.append(metric_entry)
            
            # Keep only last 1000 entries for memory management
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]
            
            logger.debug(f"Collected metrics for {metric_entry['filename']} - Success: {metric_entry['workflow_success']}")
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {str(e)}")
    
    def analyze_recent_performance(self, hours: int = 24) -> Dict[str, Any]:
        """
        Analyze performance metrics from the last N hours
        
        Args:
            hours: Number of hours to analyze (default: 24)
            
        Returns:
            Dictionary containing performance analysis
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in self.metrics_history if m['timestamp'] >= cutoff_time]
        
        if not recent_metrics:
            return {
                'period_hours': hours,
                'total_requests': 0,
                'analysis': 'No data available for the specified period'
            }
        
        # Basic statistics
        total_requests = len(recent_metrics)
        successful_requests = len([m for m in recent_metrics if m['workflow_success']])
        failed_requests = total_requests - successful_requests
        success_rate = (successful_requests / total_requests) * 100
        
        # Processing time analysis
        processing_times = []
        quality_scores = []
        throughput_values = []
        
        for metric in recent_metrics:
            perf = metric['metrics']
            processing_times.append(perf.get('total_workflow_duration_seconds', 0))
            
            quality_metrics = perf.get('quality_and_accuracy_metrics', {})
            if quality_metrics:
                quality_scores.append(quality_metrics.get('final_quality_score', 0))
            
            throughput = perf.get('throughput_employees_per_second', 0)
            if throughput > 0:
                throughput_values.append(throughput)
        
        # Calculate statistics
        analysis = {
            'period_hours': hours,
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate_percentage': success_rate,
            
            'processing_time_stats': {
                'avg_seconds': statistics.mean(processing_times) if processing_times else 0,
                'median_seconds': statistics.median(processing_times) if processing_times else 0,
                'min_seconds': min(processing_times) if processing_times else 0,
                'max_seconds': max(processing_times) if processing_times else 0,
                'std_dev_seconds': statistics.stdev(processing_times) if len(processing_times) > 1 else 0
            },
            
            'quality_stats': {
                'avg_quality_score': statistics.mean(quality_scores) if quality_scores else 0,
                'median_quality_score': statistics.median(quality_scores) if quality_scores else 0,
                'min_quality_score': min(quality_scores) if quality_scores else 0,
                'max_quality_score': max(quality_scores) if quality_scores else 0
            },
            
            'throughput_stats': {
                'avg_employees_per_second': statistics.mean(throughput_values) if throughput_values else 0,
                'median_employees_per_second': statistics.median(throughput_values) if throughput_values else 0,
                'max_employees_per_second': max(throughput_values) if throughput_values else 0
            }
        }
        
        return analysis
    
    def generate_alerts(self, analysis: Dict[str, Any]) -> List[MetricAlert]:
        """
        Generate alerts based on performance analysis
        
        Args:
            analysis: Performance analysis from analyze_recent_performance
            
        Returns:
            List of metric alerts
        """
        alerts = []
        timestamp = datetime.now()
        
        # Success rate alert
        success_rate = analysis.get('success_rate_percentage', 0)
        if success_rate < self.performance_thresholds['min_success_rate_percentage']:
            severity = MetricSeverity.CRITICAL if success_rate < 80 else MetricSeverity.ERROR
            alerts.append(MetricAlert(
                severity=severity,
                metric_name='success_rate',
                message=f"Success rate is {success_rate:.1f}%, below threshold of {self.performance_thresholds['min_success_rate_percentage']}%",
                value=success_rate,
                threshold=self.performance_thresholds['min_success_rate_percentage'],
                timestamp=timestamp,
                recommendation="Check error logs and consider adjusting complexity thresholds"
            ))
        
        # Processing time alert
        avg_time = analysis.get('processing_time_stats', {}).get('avg_seconds', 0)
        if avg_time > self.performance_thresholds['max_processing_time_seconds']:
            severity = MetricSeverity.WARNING if avg_time < 600 else MetricSeverity.ERROR
            alerts.append(MetricAlert(
                severity=severity,
                metric_name='processing_time',
                message=f"Average processing time is {avg_time:.1f}s, above threshold of {self.performance_thresholds['max_processing_time_seconds']}s",
                value=avg_time,
                threshold=self.performance_thresholds['max_processing_time_seconds'],
                timestamp=timestamp,
                recommendation="Consider optimizing batch sizes or timeouts"
            ))
        
        # Quality score alert
        avg_quality = analysis.get('quality_stats', {}).get('avg_quality_score', 0)
        if avg_quality < self.performance_thresholds['min_quality_score']:
            severity = MetricSeverity.WARNING if avg_quality > 60 else MetricSeverity.ERROR
            alerts.append(MetricAlert(
                severity=severity,
                metric_name='quality_score',
                message=f"Average quality score is {avg_quality:.1f}%, below threshold of {self.performance_thresholds['min_quality_score']}%",
                value=avg_quality,
                threshold=self.performance_thresholds['min_quality_score'],
                timestamp=timestamp,
                recommendation="Review validation logic and consider model improvements"
            ))
        
        # Throughput alert
        avg_throughput = analysis.get('throughput_stats', {}).get('avg_employees_per_second', 0)
        if avg_throughput < self.performance_thresholds['min_throughput_employees_per_second']:
            alerts.append(MetricAlert(
                severity=MetricSeverity.WARNING,
                metric_name='throughput',
                message=f"Average throughput is {avg_throughput:.3f} employees/second, below threshold of {self.performance_thresholds['min_throughput_employees_per_second']}",
                value=avg_throughput,
                threshold=self.performance_thresholds['min_throughput_employees_per_second'],
                timestamp=timestamp,
                recommendation="Consider increasing batch sizes or optimizing parallel processing"
            ))
        
        return alerts
    
    def assess_health_status(self, hours: int = 24) -> ProcessingHealthStatus:
        """
        Assess overall health status of two-pass processing
        
        Args:
            hours: Number of hours to analyze for health assessment
            
        Returns:
            ProcessingHealthStatus with overall assessment
        """
        analysis = self.analyze_recent_performance(hours)
        alerts = self.generate_alerts(analysis)
        
        # Calculate overall health score
        score_factors = []
        
        # Success rate factor (40% weight)
        success_rate = analysis.get('success_rate_percentage', 0)
        score_factors.append(min(100, success_rate) * 0.4)
        
        # Quality factor (30% weight)
        avg_quality = analysis.get('quality_stats', {}).get('avg_quality_score', 0)
        score_factors.append(min(100, avg_quality) * 0.3)
        
        # Performance factor (20% weight)
        avg_time = analysis.get('processing_time_stats', {}).get('avg_seconds', 0)
        time_score = max(0, min(100, 100 - (avg_time / 300) * 50))  # Penalize if > 5 minutes
        score_factors.append(time_score * 0.2)
        
        # Error factor (10% weight)
        error_count = len([a for a in alerts if a.severity in [MetricSeverity.ERROR, MetricSeverity.CRITICAL]])
        error_score = max(0, 100 - (error_count * 25))  # -25 points per error/critical alert
        score_factors.append(error_score * 0.1)
        
        overall_score = sum(score_factors)
        
        # Determine status
        if overall_score >= 90 and not any(a.severity == MetricSeverity.CRITICAL for a in alerts):
            status = "healthy"
            summary = f"Two-pass processing is operating normally with {success_rate:.1f}% success rate"
        elif overall_score >= 70:
            status = "degraded"
            summary = f"Two-pass processing is operating with reduced performance - {len(alerts)} alerts"
        else:
            status = "unhealthy"
            summary = f"Two-pass processing requires attention - {len(alerts)} alerts including critical issues"
        
        # Generate recommendations
        recommendations = []
        if success_rate < 90:
            recommendations.append("Monitor error patterns and consider adjusting complexity thresholds")
        if avg_time > 180:
            recommendations.append("Optimize batch sizes and timeout configurations")
        if avg_quality < 80:
            recommendations.append("Review data quality and validation logic")
        if error_count > 0:
            recommendations.append("Address critical and error-level alerts immediately")
        
        return ProcessingHealthStatus(
            status=status,
            overall_score=overall_score,
            alerts=alerts,
            summary=summary,
            recommendations=recommendations,
            timestamp=datetime.now()
        )
    
    def get_performance_trends(self, days: int = 7) -> Dict[str, Any]:
        """
        Analyze performance trends over multiple days
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary containing trend analysis
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        metrics = [m for m in self.metrics_history if m['timestamp'] >= cutoff_time]
        
        if not metrics:
            return {'error': 'No data available for trend analysis'}
        
        # Group by day
        daily_stats = {}
        for metric in metrics:
            day_key = metric['timestamp'].date()
            if day_key not in daily_stats:
                daily_stats[day_key] = {
                    'total': 0,
                    'successful': 0,
                    'processing_times': [],
                    'quality_scores': []
                }
            
            daily_stats[day_key]['total'] += 1
            if metric['workflow_success']:
                daily_stats[day_key]['successful'] += 1
            
            perf = metric['metrics']
            daily_stats[day_key]['processing_times'].append(
                perf.get('total_workflow_duration_seconds', 0)
            )
            
            quality_metrics = perf.get('quality_and_accuracy_metrics', {})
            if quality_metrics:
                daily_stats[day_key]['quality_scores'].append(
                    quality_metrics.get('final_quality_score', 0)
                )
        
        # Calculate trends
        trends = {
            'period_days': days,
            'daily_breakdown': {},
            'trend_analysis': {}
        }
        
        for day, stats in daily_stats.items():
            success_rate = (stats['successful'] / stats['total']) * 100
            avg_time = statistics.mean(stats['processing_times'])
            avg_quality = statistics.mean(stats['quality_scores']) if stats['quality_scores'] else 0
            
            trends['daily_breakdown'][str(day)] = {
                'total_requests': stats['total'],
                'success_rate_percentage': success_rate,
                'avg_processing_time_seconds': avg_time,
                'avg_quality_score': avg_quality
            }
        
        return trends


# Global metrics collector instance
metrics_collector = TwoPassMetricsCollector()


def collect_two_pass_metrics(processing_result: Dict[str, Any]) -> None:
    """
    Convenience function to collect metrics from a two-pass processing result
    
    Args:
        processing_result: Result dictionary from two-pass processing
    """
    metrics_collector.collect_metrics(processing_result)


def get_health_status(hours: int = 24) -> ProcessingHealthStatus:
    """
    Get current health status of two-pass processing
    
    Args:
        hours: Number of hours to analyze (default: 24)
        
    Returns:
        ProcessingHealthStatus with current system health
    """
    return metrics_collector.assess_health_status(hours)


def get_performance_analysis(hours: int = 24) -> Dict[str, Any]:
    """
    Get performance analysis for the specified time period
    
    Args:
        hours: Number of hours to analyze (default: 24)
        
    Returns:
        Dictionary containing performance analysis
    """
    return metrics_collector.analyze_recent_performance(hours)


def get_performance_trends(days: int = 7) -> Dict[str, Any]:
    """
    Get performance trends over multiple days
    
    Args:
        days: Number of days to analyze (default: 7)
        
    Returns:
        Dictionary containing trend analysis
    """
    return metrics_collector.get_performance_trends(days) 