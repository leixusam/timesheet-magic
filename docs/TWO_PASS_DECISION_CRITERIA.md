# Two-Pass vs Single-Pass Decision Criteria

This document explains the intelligent decision engine that determines when to use two-pass processing versus single-pass processing for timesheet analysis.

## Overview

The Time Sheet Magic system uses an intelligent decision engine to automatically choose the optimal processing approach based on file characteristics and complexity factors. This ensures the most efficient and reliable processing for each timesheet file.

## Processing Approaches

### Single-Pass Processing
- **Description**: Processes the entire file in one LLM call
- **Best for**: Small, simple files with few employees
- **Advantages**: Faster for simple files, lower API costs, simpler workflow
- **Limitations**: Token limits, reduced accuracy for complex files

### Two-Pass Processing  
- **Description**: Employee discovery followed by parallel per-employee parsing
- **Best for**: Large files, many employees, complex timesheets
- **Advantages**: Handles token limits, better accuracy, parallel processing
- **Overhead**: Additional API calls, more complex workflow

## Decision Engine Algorithm

The decision engine calculates a **complexity score** based on multiple factors and compares it against a configurable threshold.

### Complexity Scoring Factors

#### 1. File Size Scoring
Based on character count:
- **Small files** (< 3KB): +1 point
- **Medium files** (3-6KB): +2 points  
- **Large files** (≥ 6KB): +3 points

#### 2. Employee Count Scoring
Estimated employee count with multiplier:
- **1-3 employees**: +1 point × multiplier
- **4-8 employees**: +2 points × multiplier
- **9-15 employees**: +3 points × multiplier
- **16+ employees**: +4 points × multiplier

*Default multiplier: 1.0 (configurable)*

#### 3. Content Complexity Bonuses
Additional points for complex content:
- **Break punches detected**: +1 point
- **Many columns** (>3 per row): +1 point

### Decision Logic

```
if complexity_score >= complexity_threshold:
    use two-pass processing
else:
    use single-pass processing
```

**Default complexity threshold**: 1 (conservative - most files use two-pass)

## Configuration

The decision engine is controlled by settings in `backend/config.json`:

```json
{
  "two_pass": {
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

## Decision Examples

### Example 1: Small Simple File → Single-Pass
- **File**: 2KB, 5 employees, no breaks
- **Calculation**: 1 (small file) + 2×1.0 (employees) = 3 points
- **Decision**: 3 ≥ 1 → **Two-Pass** (conservative threshold)

### Example 2: Large Complex File → Two-Pass  
- **File**: 8KB, 20 employees, break punches
- **Calculation**: 3 (large) + 4×1.0 (many employees) + 1 (breaks) = 8 points
- **Decision**: 8 ≥ 1 → **Two-Pass**

### Example 3: With Higher Threshold
- **Configuration**: `complexity_threshold: 5`
- **File**: 2KB, 5 employees, no breaks
- **Calculation**: 1 + 2×1.0 = 3 points  
- **Decision**: 3 < 5 → **Single-Pass**

## Tuning Guidelines

### Conservative (Default)
- **Threshold**: 1
- **Result**: Most files use two-pass
- **Benefits**: Maximum reliability, handles edge cases
- **Tradeoffs**: Higher API costs for simple files

### Balanced
- **Threshold**: 3-4
- **Result**: Medium/large files use two-pass
- **Benefits**: Good balance of efficiency and reliability
- **Tradeoffs**: Some complex small files may fail

### Aggressive
- **Threshold**: 6+
- **Result**: Only very large/complex files use two-pass
- **Benefits**: Lower costs, faster simple processing
- **Tradeoffs**: Higher failure rate for medium complexity

## Override Options

### Force Two-Pass
```python
result = await parse_file_to_structured_data_two_pass(
    file_content=content,
    original_filename=filename,
    force_two_pass=True
)
```

### Disable Two-Pass
```python
result = await parse_file_to_structured_data_two_pass(
    file_content=content,
    original_filename=filename,
    enable_two_pass=False
)
```

## Monitoring Decision Quality

The decision engine logs detailed information for monitoring:

```
DECISION_ENGINE - File: 'timesheet.csv' | 
Complexity: 4.0/3 | Size: 5,234 chars (medium) | 
Est. employees: 12 | Recommendation: Two-pass
```

Monitor decision accuracy through:
- Success rates by complexity score
- Performance differences between approaches
- Files that exceed token limits
- Quality score variations

## Best Practices

1. **Start Conservative**: Use low threshold initially
2. **Monitor Performance**: Track success rates and costs
3. **Adjust Gradually**: Increase threshold based on data
4. **Document Changes**: Record threshold adjustments and rationale
5. **Test Edge Cases**: Verify complex files are handled properly

## Troubleshooting

### High Failure Rate
- **Symptom**: Many files failing processing
- **Solution**: Lower complexity threshold
- **Check**: File size distribution, employee counts

### High Costs
- **Symptom**: Excessive API usage
- **Solution**: Raise complexity threshold carefully
- **Monitor**: Success rate doesn't drop significantly

### Inconsistent Results
- **Symptom**: Similar files processed differently
- **Solution**: Review decision factors, consider file content variations
- **Action**: Fine-tune complexity scoring parameters

## Future Enhancements

Planned improvements to the decision engine:
- Machine learning-based complexity assessment
- Historical performance-based adjustments
- File type-specific thresholds
- User feedback integration
- Advanced content analysis (OCR quality, table structure) 