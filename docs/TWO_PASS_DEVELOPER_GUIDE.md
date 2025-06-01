# Two-Pass Processing Developer Guide

This guide provides developers with comprehensive information for extending, modifying, and working with the two-pass timesheet processing system.

## Architecture Overview

The two-pass system is designed with modularity and extensibility in mind:

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Orchestration                       │
│              parse_file_to_structured_data_two_pass()       │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
   ┌────────┐    ┌────────┐    ┌────────┐
   │ Pass 1 │    │ Pass 2 │    │ Pass 3 │
   │Discovery│    │Parallel│    │Stitching│
   │        │    │Parsing │    │        │
   └────────┘    └────────┘    └────────┘
```

## Core Components

### 1. Employee Discovery (Pass 1)
**File**: `backend/app/core/llm_processing_two_pass.py`
**Function**: `discover_employees_in_file()`

**Purpose**: Fast identification of all employees in the timesheet

**Key Extension Points**:
- Custom employee identification patterns
- Enhanced punch count estimation
- File format-specific discovery logic

### 2. Per-Employee Parsing (Pass 2)  
**Function**: `parse_employee_punches()`

**Purpose**: Detailed parsing for individual employees

**Key Extension Points**:
- Custom punch event types
- Enhanced validation rules
- Employee-specific processing logic

### 3. Parallel Processing Engine
**Function**: `process_employees_in_parallel()`

**Purpose**: Coordinate parallel processing with retry logic

**Key Extension Points**:
- Custom batch sizing strategies
- Advanced retry mechanisms
- Resource management

### 4. Result Stitching (Pass 3)
**Function**: `stitch_employee_results()`

**Purpose**: Combine and validate all results

**Key Extension Points**:
- Custom deduplication logic
- Enhanced validation rules
- Quality scoring algorithms

## Key Extension Patterns

### 1. Adding New Punch Event Types

To support new punch event types:

#### Step 1: Extend the Schema
```python
# In backend/app/models/schemas.py
class LLMParsedPunchEvent(BaseModel):
    # ... existing fields ...
    punch_type: str  # Add validation for new types
    custom_field: Optional[str] = None  # Add custom fields
```

#### Step 2: Update Discovery Prompts
```python
# In discover_employees_in_file()
discovery_prompt = f"""
...existing prompt...
- Custom Event Type (new)
- Any other time recording events
...
"""
```

#### Step 3: Update Parsing Prompts
```python
# In parse_employee_punches()
parsing_prompt = f"""
...existing types...
✅ Custom Event Type (if timestamped)
...
"""
```

### 2. Custom Validation Rules

Add custom validation in the stitching phase:

```python
def _perform_custom_validation(stitched_result: Dict[str, Any]) -> Dict[str, Any]:
    """Add your custom validation logic here"""
    issues = []
    
    # Example: Validate minimum break time
    for event in stitched_result['punch_events']:
        if event.get('punch_type') == 'Break Start':
            # Custom validation logic
            pass
    
    return {'issues': issues, 'quality_score': 100.0}

# Integrate in stitch_employee_results()
custom_validation = _perform_custom_validation(stitched_result)
stitched_result['processing_metadata']['custom_validation'] = custom_validation
```

### 3. Enhanced Decision Engine

Create custom decision factors:

```python
def _evaluate_custom_complexity(file_content: str) -> float:
    """Add custom complexity evaluation"""
    complexity_bonus = 0
    
    # Example: OCR quality assessment
    if has_poor_ocr_quality(file_content):
        complexity_bonus += 2
    
    # Example: Multiple time zones
    if multiple_time_zones_detected(file_content):
        complexity_bonus += 1
    
    return complexity_bonus

# Integrate in _evaluate_two_pass_suitability()
custom_complexity = _evaluate_custom_complexity(file_content)
complexity_score += custom_complexity
```

### 4. Custom Metrics Collection

Extend metrics collection for monitoring:

```python
def collect_custom_metrics(processing_result: Dict[str, Any]) -> None:
    """Collect additional custom metrics"""
    
    # Extract custom data
    custom_data = extract_custom_performance_data(processing_result)
    
    # Store in custom metrics store
    custom_metrics_store.add_entry(custom_data)
    
    # Generate custom alerts
    custom_alerts = evaluate_custom_thresholds(custom_data)
    
    # Log custom insights
    logger.info(f"CUSTOM_METRICS - {custom_data}")

# Call from parse_file_to_structured_data_two_pass()
collect_custom_metrics(workflow_result)
```

## Configuration Extensions

### Adding New Configuration Options

1. **Update config.json**:
```json
{
  "two_pass": {
    "custom_settings": {
      "enable_advanced_ocr": true,
      "timezone_detection": true,
      "custom_validation_threshold": 0.8
    }
  }
}
```

2. **Access in code**:
```python
custom_config = config.get("two_pass", {}).get("custom_settings", {})
enable_ocr = custom_config.get("enable_advanced_ocr", False)
```

## Testing Extensions

### Unit Tests for Custom Features

```python
# In backend/app/tests/core/test_llm_processing_two_pass.py

@pytest.mark.asyncio
async def test_custom_punch_type_discovery():
    """Test discovery of custom punch types"""
    file_content = """
    Employee: John Doe
    09:00 AM - Clock In
    10:30 AM - Training Start
    11:30 AM - Training End  
    05:00 PM - Clock Out
    """
    
    result = await discover_employees_in_file(file_content, "test.csv")
    
    # Verify custom punch types are counted
    assert len(result.employees) == 1
    assert result.employees[0].punch_count_estimate == 4  # Including training events

@pytest.mark.asyncio 
async def test_custom_validation_rules():
    """Test custom validation logic"""
    # Setup test data with edge cases
    # Run processing
    # Verify custom validation caught issues
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_end_to_end_custom_workflow():
    """Test complete workflow with custom extensions"""
    
    # Test file with custom scenarios
    test_file = load_test_file("custom_timesheet.csv")
    
    result = await parse_file_to_structured_data_two_pass(
        file_content=test_file,
        original_filename="custom_test.csv",
        # Custom parameters
        enable_custom_validation=True
    )
    
    # Verify custom features worked
    assert result['workflow_success']
    assert 'custom_validation' in result['processing_metadata']
```

## Error Handling Extensions

### Custom Exception Types

```python
# In backend/app/core/error_handlers.py

class CustomTwoPassError(Exception):
    """Base class for custom two-pass errors"""
    pass

class CustomValidationError(CustomTwoPassError):
    """Raised when custom validation fails"""
    def __init__(self, message: str, validation_details: Dict[str, Any]):
        super().__init__(message)
        self.validation_details = validation_details

class CustomComplexityError(CustomTwoPassError):
    """Raised when custom complexity assessment fails"""
    pass
```

### Error Recovery Strategies

```python
async def _handle_custom_failure(
    error: Exception,
    file_content: str, 
    original_filename: str
) -> Dict[str, Any]:
    """Custom error recovery logic"""
    
    if isinstance(error, CustomValidationError):
        # Attempt validation with relaxed rules
        return await _retry_with_relaxed_validation(file_content, original_filename)
    
    elif isinstance(error, CustomComplexityError):
        # Force specific processing mode
        return await _force_simple_processing(file_content, original_filename)
    
    else:
        # Delegate to standard error handling
        raise error
```

## Performance Optimization Extensions

### Custom Batch Sizing

```python
def calculate_optimal_batch_size(
    employees: List[EmployeeDiscoveryResult],
    file_characteristics: Dict[str, Any]
) -> int:
    """Calculate optimal batch size based on custom factors"""
    
    base_batch_size = 50
    
    # Adjust based on file complexity
    if file_characteristics.get('has_complex_schedules'):
        base_batch_size = min(20, base_batch_size)
    
    # Adjust based on employee punch counts
    avg_punches = sum(emp.punch_count_estimate for emp in employees) / len(employees)
    if avg_punches > 10:
        base_batch_size = min(30, base_batch_size)
    
    return max(5, base_batch_size)  # Minimum batch size
```

### Custom Timeout Strategies

```python
def calculate_employee_timeout(
    employee: EmployeeDiscoveryResult,
    file_characteristics: Dict[str, Any]
) -> float:
    """Calculate timeout per employee based on complexity"""
    
    base_timeout = 120.0  # 2 minutes
    
    # Adjust based on estimated punch count
    timeout_per_punch = 5.0  # 5 seconds per punch
    estimated_timeout = employee.punch_count_estimate * timeout_per_punch
    
    # Factor in file complexity
    complexity_multiplier = file_characteristics.get('complexity_multiplier', 1.0)
    
    return max(30.0, min(300.0, estimated_timeout * complexity_multiplier))
```

## API Extensions

### Custom Endpoints

```python
# In backend/app/api/endpoints/custom_two_pass.py

@router.post("/analyze-custom")
async def analyze_with_custom_options(
    file_content: str,
    custom_options: CustomProcessingOptions
):
    """Process timesheet with custom two-pass options"""
    
    result = await parse_file_to_structured_data_two_pass(
        file_content=file_content,
        original_filename=custom_options.filename,
        # Custom parameters
        enable_custom_validation=custom_options.enable_validation,
        custom_complexity_threshold=custom_options.complexity_threshold,
        custom_batch_strategy=custom_options.batch_strategy
    )
    
    return {"success": True, "data": result}
```

## Monitoring Extensions

### Custom Metrics

```python
# Custom metrics for specialized monitoring
class CustomMetricsCollector:
    def __init__(self):
        self.custom_metrics = []
    
    def collect_ocr_quality_metrics(self, processing_result: Dict[str, Any]):
        """Collect OCR quality metrics"""
        # Implementation for OCR-specific monitoring
        pass
    
    def collect_timezone_handling_metrics(self, processing_result: Dict[str, Any]):
        """Collect timezone processing metrics"""
        # Implementation for timezone-specific monitoring
        pass
```

## Best Practices for Extensions

### 1. Backward Compatibility
- Always provide default values for new parameters
- Use feature flags for experimental functionality
- Maintain existing API contracts

### 2. Configuration Management
- Add new settings to appropriate config sections
- Provide clear documentation for new options
- Use validation for configuration values

### 3. Error Handling
- Create specific exception types for new features
- Provide meaningful error messages
- Include recovery suggestions

### 4. Testing
- Write comprehensive unit tests for new features
- Include integration tests for end-to-end workflows
- Test edge cases and failure scenarios

### 5. Documentation
- Document all new parameters and options
- Provide examples of usage
- Update API documentation

### 6. Performance
- Monitor performance impact of extensions
- Use profiling to identify bottlenecks
- Implement caching where appropriate

## Common Extension Scenarios

### 1. New File Format Support
- Extend preprocessing in `llm_processing.py`
- Add format-specific discovery logic
- Update parsing prompts for format requirements

### 2. Industry-Specific Features
- Add domain-specific punch types
- Implement compliance-specific validation
- Create industry-specific decision criteria

### 3. Integration with External Systems
- Add hooks for external validation services
- Implement custom data transformation
- Create API extensions for system integration

### 4. Advanced Analytics
- Extend metrics collection
- Add custom performance indicators
- Implement predictive failure detection

## Getting Help

For questions about extending two-pass functionality:

1. **Review existing code**: Study similar implementations in the codebase
2. **Check tests**: Look at existing tests for patterns and examples
3. **Documentation**: Refer to API documentation and type hints
4. **Logging**: Use the logging system to debug and trace execution
5. **Metrics**: Monitor performance impact of changes

## Future Roadmap

Planned enhancements that may affect extensions:

- **Machine Learning Integration**: AI-powered complexity assessment
- **Multi-Language Support**: International timesheet formats
- **Real-time Processing**: Streaming/incremental processing
- **Advanced Validation**: ML-powered anomaly detection
- **Performance Optimization**: GPU acceleration for large files 