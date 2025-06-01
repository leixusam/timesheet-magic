# Two-Pass Processing Troubleshooting Guide

This guide provides operational teams with comprehensive troubleshooting information for diagnosing and resolving two-pass processing issues.

## Quick Reference

### Emergency Response
- **Service Down**: Check `/metrics/health` endpoint
- **High Failure Rate**: Review `/metrics/performance` for patterns
- **Timeout Issues**: Adjust `timeout_per_employee` configuration
- **Memory Issues**: Reduce `default_batch_size` configuration

### Common Issue Categories
1. [Processing Failures](#processing-failures) - Files failing to process
2. [Performance Issues](#performance-issues) - Slow or timeout problems
3. [Quality Issues](#quality-issues) - Poor parsing accuracy
4. [Configuration Problems](#configuration-problems) - Setup and tuning issues
5. [Resource Issues](#resource-issues) - Memory, CPU, API limits

## Diagnostic Tools

### 1. Health Check Endpoint
```bash
curl http://localhost:8000/metrics/health
```

**Response Analysis**:
- `status: "healthy"` - System operating normally
- `status: "degraded"` - Performance issues detected
- `status: "unhealthy"` - Critical issues requiring attention
- `overall_score` - Health percentage (0-100)

### 2. Performance Analysis
```bash
curl "http://localhost:8000/metrics/performance?hours=24"
```

**Key Metrics**:
- `success_rate_percentage` - Target: >90%
- `avg_processing_time_seconds` - Target: <300s
- `avg_quality_score` - Target: >75%

### 3. Log Analysis
Check backend logs for specific error patterns:

```bash
# Search for two-pass specific issues
grep "TWO_PASS" /path/to/logs/app.log

# Search for decision engine logs
grep "DECISION_ENGINE" /path/to/logs/app.log

# Search for performance issues
grep "TIMEOUT\|FAILURE\|ERROR" /path/to/logs/app.log
```

## Processing Failures

### Symptom: High Failure Rate
**Detection**: Success rate < 90% over 24 hours

**Common Causes**:
1. **LLM Service Issues**
2. **Token Limit Exceeded**
3. **Configuration Problems**
4. **File Format Issues**

#### Diagnostic Steps:

1. **Check Recent Failures**:
```bash
grep "❌.*failed" /path/to/logs/app.log | tail -20
```

2. **Analyze Error Patterns**:
```bash
# Check for specific error types
grep "TwoPassDiscoveryError" /path/to/logs/app.log
grep "TwoPassEmployeeParsingError" /path/to/logs/app.log
grep "LLMComplexityError" /path/to/logs/app.log
```

3. **Review Decision Engine**:
```bash
# Check if decisions are appropriate
grep "DECISION_ENGINE" /path/to/logs/app.log | tail -10
```

#### Resolution Strategies:

**A. Adjust Complexity Threshold** (if too many files use two-pass):
```json
{
  "two_pass": {
    "decision_engine": {
      "complexity_threshold": 3  // Increase from 1
    }
  }
}
```

**B. Increase Timeout Settings** (for timeout failures):
```json
{
  "two_pass": {
    "timeout_per_employee": 180.0,  // Increase from 120s
    "max_retries": 5  // Increase from 3
  }
}
```

**C. Reduce Batch Size** (for resource issues):
```json
{
  "two_pass": {
    "default_batch_size": 25  // Reduce from 50
  }
}
```

### Symptom: Employee Discovery Failures
**Detection**: `TwoPassDiscoveryError` in logs

**Common Causes**:
- File too complex for discovery
- Invalid file format
- OCR quality issues
- LLM service problems

#### Diagnostic Steps:

1. **Check Discovery Logs**:
```bash
grep "Employee discovery.*failed" /path/to/logs/app.log
```

2. **Analyze File Characteristics**:
```bash
# Look for file size/complexity patterns
grep "DECISION_ENGINE.*failed_file" /path/to/logs/app.log
```

#### Resolution:

**A. Force Single-Pass** (temporary workaround):
```python
# API call with fallback
result = await parse_file_to_structured_data_two_pass(
    file_content=content,
    original_filename=filename,
    enable_two_pass=False  # Force single-pass
)
```

**B. Adjust Discovery Settings**:
- Review and simplify discovery prompts
- Increase discovery timeout
- Enable more aggressive error handling

### Symptom: Employee Parsing Failures
**Detection**: `TwoPassEmployeeParsingError` in logs

**Common Causes**:
- Individual employee data too complex
- Parallel processing overload
- Network timeouts
- Resource exhaustion

#### Diagnostic Steps:

1. **Check Parallel Processing**:
```bash
grep "PARALLEL_PROCESSING_FAILURES" /path/to/logs/app.log
```

2. **Identify Problem Employees**:
```bash
grep "ERROR.*Employee.*failed" /path/to/logs/app.log
```

#### Resolution:

**A. Reduce Parallelism**:
```json
{
  "two_pass": {
    "default_batch_size": 10  // Reduce from 50
  }
}
```

**B. Increase Individual Timeouts**:
```json
{
  "two_pass": {
    "timeout_per_employee": 240.0  // Increase from 120s
  }
}
```

## Performance Issues

### Symptom: Slow Processing
**Detection**: Average processing time > 300 seconds

**Common Causes**:
- Large batch sizes
- Complex files
- LLM service latency
- Resource contention

#### Diagnostic Steps:

1. **Check Performance Metrics**:
```bash
curl "http://localhost:8000/metrics/performance?hours=6"
```

2. **Analyze Processing Times**:
```bash
grep "workflow completed.*in.*s" /path/to/logs/app.log | tail -20
```

3. **Check Resource Usage**:
```bash
# Monitor system resources
top -p $(pgrep -f "uvicorn")
```

#### Resolution:

**A. Optimize Batch Size**:
```json
{
  "two_pass": {
    "default_batch_size": 30  // Reduce for complex files
  }
}
```

**B. Adjust Timeouts**:
```json
{
  "two_pass": {
    "timeout_per_employee": 90.0  // Reduce for faster processing
  }
}
```

**C. Increase Complexity Threshold** (use single-pass more often):
```json
{
  "two_pass": {
    "decision_engine": {
      "complexity_threshold": 4  // Higher threshold
    }
  }
}
```

### Symptom: Timeout Errors
**Detection**: `TimeoutError` or `asyncio.TimeoutError` in logs

#### Diagnostic Steps:

1. **Check Timeout Patterns**:
```bash
grep "TIMEOUT" /path/to/logs/app.log | tail -10
```

2. **Analyze Timeout Distribution**:
```bash
# Check which employees are timing out
grep "exceeded.*timeout" /path/to/logs/app.log
```

#### Resolution:

**A. Increase Timeouts Gradually**:
```json
{
  "two_pass": {
    "timeout_per_employee": 180.0  // Start with 50% increase
  }
}
```

**B. Enable Aggressive Retries**:
```json
{
  "two_pass": {
    "max_retries": 5  // Increase from 3
  }
}
```

## Quality Issues

### Symptom: Low Quality Scores
**Detection**: Average quality score < 75%

**Common Causes**:
- Poor punch count estimation
- Validation rule mismatches
- File format inconsistencies
- LLM model issues

#### Diagnostic Steps:

1. **Check Quality Trends**:
```bash
curl "http://localhost:8000/metrics/trends?days=7"
```

2. **Analyze Punch Count Accuracy**:
```bash
grep "PUNCH_COUNT_MISMATCH" /path/to/logs/app.log
```

3. **Review Validation Issues**:
```bash
grep "FINAL_VALIDATION.*Poor" /path/to/logs/app.log
```

#### Resolution:

**A. Review Estimation Logic**:
- Check discovery prompts for accuracy
- Adjust punch counting rules
- Improve employee identification

**B. Tune Validation Rules**:
- Adjust quality score thresholds
- Review deduplication logic
- Update validation criteria

### Symptom: Punch Count Mismatches
**Detection**: `PUNCH_COUNT_MISMATCH` warnings in logs

#### Analysis:
```bash
# Check mismatch patterns
grep "PUNCH_COUNT_MISMATCH" /path/to/logs/app.log | \
  grep -o "Accuracy: [0-9.]*%" | sort | uniq -c
```

#### Resolution:

**A. Improve Discovery Accuracy**:
- Enhance employee discovery prompts
- Add file format-specific logic
- Improve punch counting heuristics

**B. Adjust Tolerance**:
- Lower accuracy threshold for warnings
- Accept higher variance for complex files

## Configuration Problems

### Symptom: Incorrect Processing Decisions
**Detection**: Files using wrong processing mode

#### Diagnostic Steps:

1. **Check Decision Logic**:
```bash
grep "DECISION_ENGINE" /path/to/logs/app.log | grep "Recommendation"
```

2. **Analyze File Characteristics**:
```bash
# Look for decision factors
grep "Complexity:.*Size:.*Est. employees:" /path/to/logs/app.log
```

#### Resolution:

**A. Tune Decision Thresholds**:
```json
{
  "two_pass": {
    "decision_engine": {
      "complexity_threshold": 2,  // Adjust based on analysis
      "file_size_thresholds": {
        "small_file_kb": 2,  // Lower for more two-pass
        "medium_file_kb": 5
      }
    }
  }
}
```

**B. Adjust Scoring Factors**:
```json
{
  "two_pass": {
    "decision_engine": {
      "complexity_scoring": {
        "employee_count_multiplier": 1.5  // Weight employees more
      }
    }
  }
}
```

### Symptom: Configuration Not Loading
**Detection**: Default values used instead of config

#### Diagnostic Steps:

1. **Verify Config File**:
```bash
cat backend/config.json | jq '.two_pass'
```

2. **Check Config Loading**:
```bash
grep "config.*loaded\|config.*error" /path/to/logs/app.log
```

#### Resolution:

**A. Validate JSON Syntax**:
```bash
python -m json.tool backend/config.json
```

**B. Check File Permissions**:
```bash
ls -la backend/config.json
```

**C. Restart Service**:
```bash
# Restart to reload configuration
sudo systemctl restart timesheet-backend
```

## Resource Issues

### Symptom: Memory Exhaustion
**Detection**: `MemoryError` or high memory usage

#### Diagnostic Steps:

1. **Monitor Memory Usage**:
```bash
# Check memory consumption
ps aux | grep uvicorn
free -h
```

2. **Check for Memory Leaks**:
```bash
grep "memory\|Memory" /path/to/logs/app.log
```

#### Resolution:

**A. Reduce Batch Size**:
```json
{
  "two_pass": {
    "default_batch_size": 15  // Significantly reduce
  }
}
```

**B. Enable Memory Management**:
- Implement garbage collection between batches
- Clear large variables after processing
- Use memory profiling tools

### Symptom: API Rate Limits
**Detection**: Rate limit errors from LLM service

#### Diagnostic Steps:

1. **Check API Usage**:
```bash
grep "rate.*limit\|quota.*exceeded" /path/to/logs/app.log
```

2. **Analyze Request Patterns**:
```bash
grep "API.*request" /path/to/logs/app.log | wc -l
```

#### Resolution:

**A. Reduce Request Rate**:
```json
{
  "two_pass": {
    "default_batch_size": 10,  // Fewer parallel requests
    "max_retries": 2  // Reduce retry attempts
  }
}
```

**B. Implement Backoff**:
- Add delays between batches
- Implement exponential backoff
- Use queue-based processing

## Monitoring and Alerts

### Setting Up Alerts

**A. Health Check Monitoring**:
```bash
# Add to cron for regular health checks
*/5 * * * * curl -s http://localhost:8000/metrics/health | \
  jq '.data.status' | grep -v "healthy" && \
  echo "ALERT: Two-pass processing unhealthy" | mail -s "Alert" admin@company.com
```

**B. Performance Monitoring**:
```bash
# Monitor success rate
*/15 * * * * curl -s "http://localhost:8000/metrics/performance?hours=1" | \
  jq '.data.success_rate_percentage' | \
  awk '$1 < 90 { print "ALERT: Success rate below 90%: " $1 "%" }' | \
  mail -s "Performance Alert" admin@company.com
```

### Log Analysis Tools

**A. Error Pattern Analysis**:
```bash
#!/bin/bash
# two_pass_error_analysis.sh

echo "=== Two-Pass Error Analysis ==="
echo "Date range: $(date -d '24 hours ago') to $(date)"
echo

echo "Error Count by Type:"
grep -E "(TwoPassDiscoveryError|TwoPassEmployeeParsingError|LLMComplexityError)" \
  /path/to/logs/app.log | \
  grep "$(date +%Y-%m-%d)" | \
  awk '{print $NF}' | sort | uniq -c | sort -nr

echo -e "\nRecent Decision Engine Logs:"
grep "DECISION_ENGINE" /path/to/logs/app.log | tail -5

echo -e "\nPerformance Summary:"
grep "workflow completed.*in.*s" /path/to/logs/app.log | \
  grep "$(date +%Y-%m-%d)" | \
  awk '{print $(NF-1)}' | \
  awk '{sum+=$1; count++} END {print "Average time: " sum/count "s, Count: " count}'
```

**B. Health Dashboard Script**:
```bash
#!/bin/bash
# two_pass_dashboard.sh

echo "=== Two-Pass Processing Dashboard ==="
echo "Timestamp: $(date)"
echo

# Get health status
HEALTH=$(curl -s http://localhost:8000/metrics/health | jq -r '.data.status')
SCORE=$(curl -s http://localhost:8000/metrics/health | jq -r '.data.overall_score')

echo "Health Status: $HEALTH ($SCORE%)"

# Get performance metrics
PERF=$(curl -s "http://localhost:8000/metrics/performance?hours=24")
SUCCESS_RATE=$(echo $PERF | jq -r '.data.success_rate_percentage')
AVG_TIME=$(echo $PERF | jq -r '.data.processing_time_stats.avg_seconds')
TOTAL_REQUESTS=$(echo $PERF | jq -r '.data.total_requests')

echo "24h Performance:"
echo "  - Success Rate: $SUCCESS_RATE%"
echo "  - Average Time: ${AVG_TIME}s"
echo "  - Total Requests: $TOTAL_REQUESTS"

# Check for alerts
ALERTS=$(curl -s http://localhost:8000/metrics/health | jq -r '.data.alerts | length')
if [ "$ALERTS" -gt 0 ]; then
    echo "⚠️  Active Alerts: $ALERTS"
    curl -s http://localhost:8000/metrics/health | \
      jq -r '.data.alerts[] | "  - " + .severity + ": " + .message'
fi
```

## Escalation Procedures

### Level 1: Operational Issues
- **Scope**: Individual file failures, minor performance degradation
- **Response**: Adjust configuration, restart service if needed
- **Escalate if**: Issues persist > 2 hours or affect > 20% of requests

### Level 2: Service Degradation
- **Scope**: High failure rates, significant performance impact
- **Response**: Emergency configuration changes, resource scaling
- **Escalate if**: Issues persist > 1 hour or affect > 50% of requests

### Level 3: Service Outage
- **Scope**: Complete processing failure, system unavailable
- **Response**: Immediate failover to single-pass, emergency support
- **Contact**: Development team, infrastructure team

## Emergency Procedures

### Emergency Disable Two-Pass
If two-pass processing is completely failing:

```bash
# Quick config update to disable two-pass
jq '.two_pass.decision_engine.complexity_threshold = 999' backend/config.json > temp.json
mv temp.json backend/config.json

# Restart service
sudo systemctl restart timesheet-backend
```

### Emergency Batch Size Reduction
For memory/performance issues:

```bash
# Reduce to minimal batch size
jq '.two_pass.default_batch_size = 5' backend/config.json > temp.json
mv temp.json backend/config.json

# Restart service
sudo systemctl restart timesheet-backend
```

### Force Single-Pass Mode
For critical processing needs:

```python
# In emergency processing script
result = await parse_file_to_structured_data_two_pass(
    file_content=content,
    original_filename=filename,
    enable_two_pass=False,  # Emergency: force single-pass
    fallback_to_single_pass=True
)
```

## Recovery Procedures

### Post-Incident Recovery

1. **Identify Root Cause**:
   - Analyze logs and metrics
   - Review configuration changes
   - Check external dependencies

2. **Implement Fix**:
   - Apply configuration corrections
   - Update code if necessary
   - Test with sample files

3. **Verify Recovery**:
   - Monitor health endpoint
   - Process test files
   - Check performance metrics

4. **Document Incident**:
   - Record timeline and actions
   - Update troubleshooting procedures
   - Implement preventive measures

### Performance Recovery

After performance issues:

1. **Gradual Scale-Up**:
   - Start with conservative settings
   - Gradually increase batch sizes
   - Monitor impact at each step

2. **Validation**:
   - Process sample files successfully
   - Verify quality scores
   - Check processing times

3. **Optimization**:
   - Fine-tune based on observed performance
   - Update monitoring thresholds
   - Document optimal settings

## Prevention

### Regular Maintenance

1. **Weekly Health Checks**:
   - Review performance trends
   - Check for configuration drift
   - Analyze error patterns

2. **Monthly Optimization**:
   - Tune decision thresholds
   - Update batch size settings
   - Review timeout configurations

3. **Quarterly Reviews**:
   - Analyze processing patterns
   - Update troubleshooting procedures
   - Plan capacity scaling

### Proactive Monitoring

1. **Set up automated alerts for**:
   - Success rate < 90%
   - Average processing time > 300s
   - Quality score < 75%
   - Memory usage > 80%

2. **Regular review of**:
   - Error log patterns
   - Performance trends
   - Resource utilization
   - Configuration effectiveness 