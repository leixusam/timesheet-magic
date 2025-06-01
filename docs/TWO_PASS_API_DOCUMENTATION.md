# Two-Pass Processing API Documentation

This document provides comprehensive API documentation for all two-pass processing endpoints, parameters, and response formats.

## Table of Contents

1. [Processing Endpoints](#processing-endpoints)
2. [Monitoring Endpoints](#monitoring-endpoints)
3. [Configuration Parameters](#configuration-parameters)
4. [Response Formats](#response-formats)
5. [Error Handling](#error-handling)
6. [Code Examples](#code-examples)

## Processing Endpoints

### POST /api/analyze (Enhanced with Two-Pass Support)

**Description**: Process timesheet files with intelligent two-pass/single-pass selection

**URL**: `POST /api/analyze`

**Headers**:
```
Content-Type: multipart/form-data
Authorization: Bearer <token>  # If authentication enabled
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file` | File | Yes | - | Timesheet file to process (CSV, Excel, PDF) |
| `processing_mode` | String | No | `"auto"` | Processing mode: `"auto"`, `"two_pass"`, `"single_pass"` |
| `force_two_pass` | Boolean | No | `false` | Force two-pass processing regardless of decision engine |
| `enable_two_pass` | Boolean | No | `true` | Enable two-pass processing capability |
| `batch_size` | Integer | No | `50` | Number of employees to process in parallel (two-pass only) |
| `timeout_per_employee` | Float | No | `120.0` | Timeout per employee in seconds (two-pass only) |
| `max_retries` | Integer | No | `3` | Maximum retry attempts for failed operations |
| `enable_deduplication` | Boolean | No | `true` | Enable duplicate punch event removal |
| `strict_validation` | Boolean | No | `true` | Enable strict validation rules |
| `fallback_to_single_pass` | Boolean | No | `true` | Enable fallback to single-pass on two-pass failure |

**Request Example**:
```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@timesheet.csv" \
  -F "processing_mode=auto" \
  -F "batch_size=30" \
  -F "timeout_per_employee=180.0"
```

**Response Structure**:
```json
{
  "success": true,
  "data": {
    "punch_events": [...],
    "processing_metadata": {
      "original_filename": "timesheet.csv",
      "processing_mode": "two_pass",
      "workflow_version": "2.0",
      "decision_factors": {...},
      "performance_metrics": {...},
      "workflow_stages": {...}
    },
    "parsing_issues": [],
    "workflow_success": true
  },
  "request_id": "req_123456789",
  "processing_time_seconds": 45.7
}
```

### POST /api/start-analysis (Enhanced)

**Description**: Start asynchronous timesheet analysis with two-pass support

**URL**: `POST /api/start-analysis`

**Parameters**: Same as `/api/analyze` endpoint

**Response**:
```json
{
  "success": true,
  "request_id": "req_123456789",
  "estimated_completion_time": "2025-01-16T15:30:00Z",
  "processing_mode": "two_pass",
  "status_url": "/api/reports/req_123456789"
}
```

## Monitoring Endpoints

### GET /metrics/health

**Description**: Get current health status of two-pass processing

**URL**: `GET /metrics/health`

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `hours` | Integer | No | `24` | Number of hours to analyze (1-168) |

**Request Example**:
```bash
curl "http://localhost:8000/metrics/health?hours=24"
```

**Response**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "overall_score": 95.2,
    "summary": "Two-pass processing is operating normally with 98.5% success rate",
    "recommendations": [],
    "timestamp": "2025-01-16T14:30:00Z",
    "analysis_period_hours": 24,
    "alerts": []
  }
}
```

### GET /metrics/performance

**Description**: Get detailed performance analysis for two-pass processing

**URL**: `GET /metrics/performance`

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `hours` | Integer | No | `24` | Number of hours to analyze (1-168) |

**Response**:
```json
{
  "success": true,
  "data": {
    "period_hours": 24,
    "total_requests": 156,
    "successful_requests": 152,
    "failed_requests": 4,
    "success_rate_percentage": 97.4,
    "processing_time_stats": {
      "avg_seconds": 67.3,
      "median_seconds": 45.2,
      "min_seconds": 12.1,
      "max_seconds": 298.7,
      "std_dev_seconds": 34.5
    },
    "quality_stats": {
      "avg_quality_score": 89.2,
      "median_quality_score": 92.1,
      "min_quality_score": 65.3,
      "max_quality_score": 100.0
    },
    "throughput_stats": {
      "avg_employees_per_second": 0.34,
      "median_employees_per_second": 0.28,
      "max_employees_per_second": 1.23
    }
  }
}
```

### GET /metrics/trends

**Description**: Get performance trends over multiple days

**URL**: `GET /metrics/trends`

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `days` | Integer | No | `7` | Number of days to analyze (1-30) |

**Response**:
```json
{
  "success": true,
  "data": {
    "period_days": 7,
    "daily_breakdown": {
      "2025-01-16": {
        "total_requests": 45,
        "success_rate_percentage": 97.8,
        "avg_processing_time_seconds": 62.3,
        "avg_quality_score": 91.2
      },
      "2025-01-15": {
        "total_requests": 38,
        "success_rate_percentage": 94.7,
        "avg_processing_time_seconds": 71.8,
        "avg_quality_score": 87.6
      }
    }
  }
}
```

### GET /metrics/summary

**Description**: Get concise metrics summary with key performance indicators

**URL**: `GET /metrics/summary`

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `hours` | Integer | No | `24` | Number of hours to analyze (1-168) |

**Response**:
```json
{
  "success": true,
  "data": {
    "analysis_period_hours": 24,
    "timestamp": "2025-01-16T14:30:00Z",
    "health": {
      "status": "healthy",
      "overall_score": 95.2,
      "alert_count": 0,
      "critical_alerts": 0,
      "error_alerts": 0
    },
    "performance": {
      "total_requests": 156,
      "success_rate_percentage": 97.4,
      "avg_processing_time_seconds": 67.3,
      "avg_quality_score": 89.2,
      "avg_throughput_employees_per_second": 0.34
    },
    "recommendations": []
  }
}
```

### GET /metrics/dashboard

**Description**: Get comprehensive dashboard data for monitoring displays

**URL**: `GET /metrics/dashboard`

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `hours` | Integer | No | `24` | Hours for health/performance analysis |
| `trend_days` | Integer | No | `7` | Days for trend analysis |

**Response**: Combines health, performance, and trend data for dashboards.

## Configuration Parameters

### Two-Pass Processing Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `processing_mode` | String | `"auto"` | `"auto"`, `"two_pass"`, `"single_pass"` |
| `force_two_pass` | Boolean | `false` | Force two-pass regardless of decision |
| `enable_two_pass` | Boolean | `true` | Enable two-pass capability |
| `batch_size` | Integer | `50` | Parallel processing batch size |
| `timeout_per_employee` | Float | `120.0` | Timeout per employee (seconds) |
| `max_retries` | Integer | `3` | Maximum retry attempts |
| `enable_deduplication` | Boolean | `true` | Enable duplicate removal |
| `strict_validation` | Boolean | `true` | Enable strict validation |
| `fallback_to_single_pass` | Boolean | `true` | Enable fallback mechanism |

### Decision Engine Parameters

Configuration in `backend/config.json`:

```json
{
  "two_pass": {
    "default_batch_size": 50,
    "timeout_per_employee": 120.0,
    "max_retries": 3,
    "decision_engine": {
      "complexity_threshold": 1,
      "file_size_thresholds": {
        "small_file_kb": 3,
        "medium_file_kb": 6
      },
      "complexity_scoring": {
        "small_file_points": 1,
        "medium_file_points": 2,
        "large_file_points": 3,
        "employee_count_multiplier": 1.0
      }
    }
  }
}
```

## Response Formats

### Punch Event Structure

```json
{
  "employee_identifier_in_file": "John Doe",
  "timestamp": "2025-01-16T09:00:00Z",
  "punch_type": "Clock In",
  "location": "Main Office",
  "notes": "",
  "raw_text_context": "09:00 AM - Clock In - Main Office"
}
```

### Processing Metadata Structure

```json
{
  "original_filename": "timesheet.csv",
  "file_size_chars": 15420,
  "processing_mode": "two_pass",
  "workflow_version": "2.0",
  "timestamp": "2025-01-16T14:30:00Z",
  "decision_factors": {
    "should_use_two_pass": true,
    "complexity_score": 4.5,
    "complexity_threshold": 3,
    "file_size_category": "medium",
    "estimated_employees": 12,
    "reason": "Two-pass recommended due to moderate file size and employee count"
  },
  "workflow_stages": {
    "discovery": {
      "duration_seconds": 12.3,
      "employees_found": 12,
      "total_estimated_punches": 156,
      "success": true
    },
    "parallel_processing": {
      "duration_seconds": 28.7,
      "employees_processed": 12,
      "success_rate": 100.0,
      "total_actual_punches": 152,
      "success": true
    },
    "stitching": {
      "duration_seconds": 4.2,
      "final_punch_events": 152,
      "duplicates_removed": 0,
      "quality_score": 92.3,
      "success": true
    }
  },
  "performance_metrics": {
    "total_workflow_duration_seconds": 45.7,
    "throughput_employees_per_second": 0.26,
    "throughput_punches_per_second": 3.32,
    "monitoring_summary": {
      "processing_mode": "two_pass_success",
      "quality_grade": "A",
      "overall_efficiency_score": 85.2
    }
  }
}
```

### Alert Structure

```json
{
  "severity": "warning",
  "metric_name": "processing_time",
  "message": "Average processing time is 185.3s, above threshold of 120s",
  "value": 185.3,
  "threshold": 120.0,
  "timestamp": "2025-01-16T14:30:00Z",
  "recommendation": "Consider optimizing batch sizes or timeouts"
}
```

## Error Handling

### Error Response Format

```json
{
  "success": false,
  "error": {
    "type": "TwoPassDiscoveryError",
    "message": "Failed to discover employees in timesheet",
    "details": {
      "original_filename": "problematic.csv",
      "file_size": 25000,
      "discovery_issues": ["Invalid file format detected"]
    },
    "request_id": "req_123456789",
    "timestamp": "2025-01-16T14:30:00Z"
  },
  "fallback_attempted": true,
  "fallback_result": null
}
```

### HTTP Status Codes

| Status Code | Description | Example Scenario |
|-------------|-------------|------------------|
| `200` | Success | Successful processing |
| `400` | Bad Request | Invalid parameters or file format |
| `413` | Payload Too Large | File exceeds size limits |
| `422` | Unprocessable Entity | Valid request but processing failed |
| `429` | Too Many Requests | Rate limiting exceeded |
| `500` | Internal Server Error | Unexpected server error |
| `503` | Service Unavailable | LLM service temporarily unavailable |

### Error Types

| Error Type | Description | Resolution |
|------------|-------------|------------|
| `TwoPassDiscoveryError` | Employee discovery failed | Check file format, try single-pass |
| `TwoPassEmployeeParsingError` | Employee parsing failed | Reduce batch size, increase timeouts |
| `TwoPassPartialSuccessError` | Some employees failed processing | Review failed employees, retry |
| `LLMComplexityError` | File too complex for processing | Simplify file or use different approach |
| `LLMServiceError` | LLM service error | Check service status, retry later |
| `ParsingError` | General parsing error | Review file format and content |

## Code Examples

### Python Client Example

```python
import requests
import json

def process_timesheet_two_pass(
    file_path: str,
    processing_mode: str = "auto",
    batch_size: int = 50,
    timeout_per_employee: float = 120.0
):
    """Process timesheet with two-pass options"""
    
    url = "http://localhost:8000/api/analyze"
    
    files = {
        'file': open(file_path, 'rb')
    }
    
    data = {
        'processing_mode': processing_mode,
        'batch_size': batch_size,
        'timeout_per_employee': timeout_per_employee,
        'enable_deduplication': True,
        'strict_validation': True
    }
    
    try:
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()
        
        result = response.json()
        
        if result['success']:
            print(f"✅ Processing successful!")
            print(f"Processing mode: {result['data']['processing_metadata']['processing_mode']}")
            print(f"Punch events found: {len(result['data']['punch_events'])}")
            print(f"Processing time: {result['processing_time_seconds']:.1f}s")
            
            return result['data']
        else:
            print(f"❌ Processing failed: {result['error']['message']}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")
        return None
    finally:
        files['file'].close()

# Usage
result = process_timesheet_two_pass(
    file_path="timesheet.csv",
    processing_mode="two_pass",
    batch_size=30,
    timeout_per_employee=180.0
)
```

### JavaScript/Node.js Example

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

async function processTimesheetTwoPass(filePath, options = {}) {
    const form = new FormData();
    
    // Add file
    form.append('file', fs.createReadStream(filePath));
    
    // Add processing options
    form.append('processing_mode', options.processingMode || 'auto');
    form.append('batch_size', options.batchSize || 50);
    form.append('timeout_per_employee', options.timeoutPerEmployee || 120.0);
    form.append('enable_deduplication', options.enableDeduplication !== false);
    form.append('strict_validation', options.strictValidation !== false);
    
    try {
        const response = await axios.post(
            'http://localhost:8000/api/analyze',
            form,
            {
                headers: {
                    ...form.getHeaders(),
                },
                timeout: 300000 // 5 minutes
            }
        );
        
        if (response.data.success) {
            console.log('✅ Processing successful!');
            console.log(`Processing mode: ${response.data.data.processing_metadata.processing_mode}`);
            console.log(`Punch events found: ${response.data.data.punch_events.length}`);
            console.log(`Processing time: ${response.data.processing_time_seconds.toFixed(1)}s`);
            
            return response.data.data;
        } else {
            console.log(`❌ Processing failed: ${response.data.error.message}`);
            return null;
        }
        
    } catch (error) {
        console.log(`❌ Request failed: ${error.message}`);
        return null;
    }
}

// Usage
processTimesheetTwoPass('timesheet.csv', {
    processingMode: 'two_pass',
    batchSize: 30,
    timeoutPerEmployee: 180.0
});
```

### cURL Examples

**Basic Two-Pass Processing**:
```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@timesheet.csv" \
  -F "processing_mode=two_pass"
```

**Advanced Configuration**:
```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@large_timesheet.xlsx" \
  -F "processing_mode=auto" \
  -F "batch_size=25" \
  -F "timeout_per_employee=240.0" \
  -F "max_retries=5" \
  -F "strict_validation=false"
```

**Force Single-Pass**:
```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@simple_timesheet.csv" \
  -F "processing_mode=single_pass"
```

**Health Check**:
```bash
curl "http://localhost:8000/metrics/health?hours=48"
```

**Performance Analysis**:
```bash
curl "http://localhost:8000/metrics/performance?hours=24" | jq '.data.success_rate_percentage'
```

## Migration Guide

### Upgrading from Single-Pass Only

If you're upgrading from a single-pass only system:

1. **No Breaking Changes**: Existing API calls will continue to work
2. **Auto Mode**: Set `processing_mode=auto` for intelligent selection
3. **Gradual Rollout**: Start with `enable_two_pass=false` then enable gradually
4. **Monitor Performance**: Use metrics endpoints to track improvements

### API Compatibility

- All existing `/api/analyze` parameters remain supported
- New parameters have sensible defaults
- Response format is backward compatible with additional metadata
- Error handling is enhanced but maintains compatibility

## Best Practices

### Performance Optimization

1. **Batch Size Tuning**:
   - Start with default (50)
   - Reduce for complex files or resource constraints
   - Increase for simple files with many employees

2. **Timeout Configuration**:
   - Monitor average processing times
   - Set timeouts 2-3x average time
   - Consider file complexity in timeout calculation

3. **Decision Engine Tuning**:
   - Monitor decision accuracy
   - Adjust complexity threshold based on results
   - Consider cost vs. quality tradeoffs

### Error Handling

1. **Implement Retry Logic**: For transient failures
2. **Fallback Strategy**: Use single-pass as fallback
3. **Monitor Health**: Regular health checks in production
4. **Log Analysis**: Regular review of error patterns

### Security Considerations

1. **File Size Limits**: Implement reasonable file size limits
2. **Input Validation**: Validate file formats and parameters
3. **Rate Limiting**: Implement rate limiting for API calls
4. **Authentication**: Use appropriate authentication for production 