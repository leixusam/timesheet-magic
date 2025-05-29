# Test Suite Documentation

This directory contains various test scripts for the Time Sheet Magic application. Each test validates different aspects of the system and integration points.

## Test Categories

### 🔍 Unit Tests
Located in `backend/app/tests/` - these are formal unit tests using pytest:
- `backend/app/tests/core/test_reporting.py` - Tests for KPI calculation functions
- `backend/app/tests/core/test_llm_processing.py` - Tests for LLM processing
- `backend/app/tests/core/test_compliance_rules.py` - Tests for compliance logic

### 🔗 Integration Tests
Located in this directory - these test end-to-end workflows:

#### Core Pipeline Tests
- **`test_end_to_end.py`** - Complete pipeline test (LLM → Compliance → Costs)
  - Tests the full workflow from CSV file to compliance analysis
  - Uses real data from `8.05-short.csv`
  - Validates LLM extraction and compliance detection
  - **Run this first** to generate baseline data

- **`test_compliance_only.py`** - Isolated compliance testing
  - Tests compliance rules with manually created punch events
  - Validates meal break, overtime, and duplicate detection logic
  - Independent of LLM processing

#### Specific Component Tests
- **`test_kpi_calculation.py`** - KPI calculation validation (Task 3.5.1)
  - Tests the new reporting module KPI functions
  - Uses existing processed data to avoid API calls
  - Validates labor hour breakdowns and cost calculations

- **`test_real_excel.py`** - Excel file processing test
  - Tests with real Excel timesheet files
  - Validates Excel parsing and data extraction

#### Diagnostic Tests
- **`test_final.py`** - Timeout diagnostic test
  - Tests API timeout handling and stability
  - Compares stable vs preview model performance
  - Used to diagnose LLM API hanging issues

- **`test_simple.py`** - Basic functionality test
  - Simple test with minimal data
  - Good for quick validation and debugging

## Test Data

All tests use real timesheet data from the `backend/app/tests/core/` directory:
- `8.05-short.csv` - Sample CSV timesheet data
- `8.05-short.xlsx` - Sample Excel timesheet data

## Debug Output

All tests save debug information to the `debug_runs/` directory:
- LLM processing outputs
- Compliance analysis results
- Cost calculations
- Function call traces

## Running Tests

### Prerequisites
```bash
# Activate virtual environment
source venv/bin/activate

# Ensure you have environment variables set
# Check for GOOGLE_API_KEY in .env file
```

### Individual Test Execution
```bash
# Run the main end-to-end test (run this first)
python tests/test_end_to_end.py

# Test KPI calculations (requires end-to-end data)
python tests/test_kpi_calculation.py

# Test compliance rules only
python tests/test_compliance_only.py

# Test Excel processing
python tests/test_real_excel.py

# Quick basic test
python tests/test_simple.py

# Diagnostic test for API issues
python tests/test_final.py
```

### Unit Test Execution
```bash
# Run backend unit tests
cd backend && python -m pytest app/tests/ -v

# Run specific test module
cd backend && python -m pytest app/tests/core/test_reporting.py -v
```

## Test Dependencies

- **Order matters**: Run `test_end_to_end.py` first to generate processed data
- **API Dependencies**: Some tests require Google Gemini API access
- **Data Dependencies**: Tests use shared debug output from previous runs

## Test Coverage

Current test coverage includes:
- ✅ LLM processing and file parsing
- ✅ Compliance rule detection (all types)
- ✅ Cost calculations and wage determination
- ✅ KPI calculation and reporting (Task 3.5.1)
- ✅ Excel and CSV file handling
- ✅ Error handling and retries
- ✅ Duplicate employee detection
- 🔄 Integration with frontend (planned)
- 🔄 Database logging (planned)

## Known Issues

- **API Timeouts**: Gemini API occasionally hangs; `test_final.py` helps diagnose
- **Model Reliability**: Preview models (`gemini-2.5-flash-preview-05-20`) are unstable
- **Data Variation**: Real timesheet formats may vary; add new test cases as needed

## Adding New Tests

When adding new test files:
1. Use descriptive names (e.g., `test_feature_name.py`)
2. Include docstrings explaining the test purpose
3. Save debug output to `debug_runs/`
4. Update this README with test description
5. Consider adding corresponding unit tests in `backend/app/tests/` 