# Integration Tests

This directory contains integration tests that validate end-to-end workflows and cross-component functionality.

## Quick Start

**Use the unified test runner from the project root:**

```bash
# Run all tests (unit + integration)
python run_tests.py

# Run only integration tests
python run_tests.py --type integration

# Run only unit tests  
python run_tests.py --type unit

# Run quick validation tests
python run_tests.py --type quick
```

## Test Files

### Core Integration Tests
- **`test_end_to_end.py`** - Complete pipeline validation (🚀 **Run this first**)
- **`test_compliance_only.py`** - Compliance rules validation  
- **`test_kpi_calculation.py`** - KPI calculation validation
- **`test_real_excel.py`** - Excel file processing test
- **`test_immediate_flow.py`** - API workflow and immediate lead submission test

### Development/Debug Tests
- **`test_simple.py`** - Basic functionality test
- **`test_final.py`** - API timeout diagnostics

## Test Data

Tests use sample data from multiple sources:
- `../sample_data/` - Root-level sample files for general testing
- `backend/app/tests/core/` - Backend-specific test data
- `8.05-short.csv` - Sample CSV timesheet  
- `8.05-short.xlsx` - Sample Excel timesheet

## Notes

- **Order matters**: Run `test_end_to_end.py` first to generate baseline data
- **API Dependencies**: Some tests require Google Gemini API key in `.env`
- **Debug Output**: Tests save debug info to `debug_runs/` (gitignored)
- **Backend Server**: API tests require backend running on localhost:8000

## Backend Unit Tests

Unit tests are located in `backend/app/tests/` and use pytest:
- `backend/app/tests/core/test_reporting.py` - KPI functions
- `backend/app/tests/core/test_llm_processing.py` - LLM processing  
- `backend/app/tests/core/test_error_handlers.py` - Error handling

Run with: `cd backend && python -m pytest app/tests/ -v` 