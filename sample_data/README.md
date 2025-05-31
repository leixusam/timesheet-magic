# Sample Data Files

This directory contains all sample timesheet files for testing and development purposes.

## Files

### Excel Files
- **`8.05 - Time Clock Detail.xlsx`** - Full comprehensive timesheet sample (812KB)
  - Contains complete employee data with complex punch patterns
  - **Primary file for backend unit tests** - comprehensive testing scenarios
  - Use for thorough integration testing and edge cases

- **`8.05-short.xlsx`** - Shortened Excel version (777KB)
  - Subset of the full data for faster processing
  - Good balance between comprehensiveness and speed
  - Use for moderate testing scenarios

- **`8.05 - Time Clock Detail 1sheet.xlsx`** - Single sheet version (42KB)
  - Simplified version with essential data only
  - Good for quick testing and demos
  - Use for lightweight integration testing

### CSV Files  
- **`8.05-short.csv`** - Shortened CSV version (5.2KB)
  - **Primary file for backend unit tests** - fast processing
  - Contains essential punch event data
  - Use for CSV parsing tests and quick validation

- **`test_deploy.csv`** - Basic deployment test file (83B)
  - Minimal format with minimal data
  - Good for quick deployment verification
  
- **`test_upload.csv`** - Upload test file (66B)
  - Minimal test data for upload functionality
  - Use for basic upload/parsing tests

## Usage

### In Backend Unit Tests
The backend unit tests reference these files:
```python
# In backend/app/tests/core/
sample_csv = "../../sample_data/8.05-short.csv"
sample_xlsx = "../../sample_data/8.05-short.xlsx"
full_excel = "../../sample_data/8.05 - Time Clock Detail.xlsx"
```

### In Integration Tests
Reference these files from integration tests:
```python
# From tests/ directory
sample_file = "sample_data/8.05 - Time Clock Detail.xlsx"
quick_test = "sample_data/8.05-short.csv"
```

### API Testing
Use these files for manual API testing:
```bash
# Quick test with minimal data
curl -X POST "http://localhost:8000/api/analyze" \
  -F "file=@sample_data/test_deploy.csv" \
  -F "lead_data={\"manager_name\":\"Test Manager\"}"

# Comprehensive test with full data
curl -X POST "http://localhost:8000/api/analyze" \
  -F "file=@sample_data/8.05 - Time Clock Detail.xlsx" \
  -F "lead_data={\"manager_name\":\"Test Manager\"}"
```

## File Relationships

```
8.05 Data Family:
├── 8.05 - Time Clock Detail.xlsx     # Full original (used by unit tests)
├── 8.05-short.xlsx                   # Shortened Excel version  
├── 8.05-short.csv                    # Shortened CSV (used by unit tests)
└── 8.05 - Time Clock Detail 1sheet.xlsx  # Single sheet version

Basic Test Files:
├── test_deploy.csv                   # Deployment validation
└── test_upload.csv                   # Upload functionality
```

## Testing Strategy

### Unit Tests (Fast)
- Use `8.05-short.csv` for CSV parsing tests
- Use `8.05-short.xlsx` for Excel processing tests  
- These are optimized for speed in the test suite

### Integration Tests (Comprehensive)
- Use `8.05 - Time Clock Detail.xlsx` for full pipeline testing
- Use `8.05 - Time Clock Detail 1sheet.xlsx` for moderate testing
- These test complete functionality with realistic data

### Quick Validation
- Use `test_deploy.csv` or `test_upload.csv` for basic functionality
- Use for deployment checks and simple API validation

## Adding New Sample Files

When adding new sample data:
1. Use descriptive filenames indicating purpose and size
2. Add documentation here with file size and use case
3. Keep files reasonably sized (< 50MB)
4. Include variety of formats and edge cases
5. Update tests that reference the files
6. Consider if it belongs to an existing "family" of related files 