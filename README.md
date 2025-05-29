# Time Sheet Magic - AI-Powered Timesheet Analysis

AI-powered timesheet analysis application that extracts structured data from timesheet files and performs comprehensive compliance checking for labor law violations.

## Project Overview

Time Sheet Magic processes various timesheet formats (CSV, Excel, PDF, images) using multimodal LLMs and analyzes them for:
- Meal break violations
- Rest break violations  
- Daily and weekly overtime violations
- Cost calculations for violations
- Compliance risk assessment
- Employee hour breakdowns

## Project Structure

```
.
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/endpoints/      # API endpoints
│   │   │   ├── core/               # Core business logic
│   │   │   │   ├── llm_processing.py      # LLM integration
│   │   │   │   ├── compliance_rules.py    # Labor compliance logic
│   │   │   │   └── reporting.py           # KPI and report generation
│   │   │   ├── models/schemas.py   # Pydantic data models
│   │   │   └── tests/              # Unit tests (pytest)
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── frontend/                   # Next.js frontend
│   │   ├── src/
│   │   │   ├── app/               # Next.js app router
│   │   │   ├── components/        # React components
│   │   │   └── hooks/             # Custom React hooks
│   │   ├── package.json
│   │   └── Dockerfile
│   ├── tests/                      # Integration tests
│   │   ├── README.md              # Test documentation
│   │   ├── run_tests.py           # Test runner
│   │   ├── test_end_to_end.py     # Full pipeline test
│   │   ├── test_compliance_only.py # Isolated compliance test
│   │   ├── test_kpi_calculation.py # KPI validation (Task 3.5.1)
│   │   └── [other test files]
│   ├── llm_utils/                  # LLM utility functions
│   ├── tasks/                      # Project task documentation
│   └── debug_runs/                 # Test output and debug data
└── venv/                       # Python virtual environment
```

## Features

### ✅ Completed Features
- **LLM Processing**: Multi-format file parsing (CSV, Excel, PDF, images)
- **Compliance Analysis**: Comprehensive labor law violation detection
- **Cost Calculations**: Violation costs and overtime premiums
- **KPI Generation**: Labor hour breakdowns and compliance metrics
- **Duplicate Detection**: Employee consolidation across multiple roles
- **Wage Determination**: Parse wages from data or use defaults

### 🔄 In Progress
- **Reporting Module**: Staffing density heat-maps, violation summaries
- **Frontend Integration**: Report display and user interface
- **Database Logging**: Supabase integration for leads and analytics

## Testing

The project includes comprehensive testing with organized test files in the `tests/` directory.

### Test Categories

**🔍 Unit Tests** (in `backend/app/tests/`):
- `test_reporting.py` - KPI calculation functions
- `test_llm_processing.py` - LLM processing logic
- `test_compliance_rules.py` - Compliance detection

**🔗 Integration Tests** (in `tests/`):
- `test_end_to_end.py` - Complete pipeline (LLM → Compliance → Costs)
- `test_compliance_only.py` - Isolated compliance testing
- `test_kpi_calculation.py` - KPI validation (Task 3.5.1)
- `test_real_excel.py` - Excel file processing
- `test_simple.py` - Basic functionality
- `test_final.py` - API timeout diagnostics

### Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests with the test runner
python tests/run_tests.py all

# Run core pipeline tests
python tests/run_tests.py core

# Run specific test
python tests/run_tests.py end_to_end
python tests/run_tests.py kpi_calculation

# Run unit tests
cd backend && python -m pytest app/tests/ -v
```

### Test Dependencies

⚠️ **Important**: Run `test_end_to_end.py` first to generate baseline data that other tests depend on.

## Setup

### Prerequisites
- Python 3.13+
- Node.js 18+ (for frontend)
- Virtual environment

### Backend Setup

1. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create `.env` file in the root directory:
   ```env
   GOOGLE_API_KEY="your_google_api_key_here"
   OPENAI_API_KEY="your_openai_api_key_here"  # Optional
   ```
   Get your Google API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

4. **Run backend server:**
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload
   ```

### Frontend Setup

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Run development server:**
   ```bash
   npm run dev
   ```

## API Usage

### Process Timesheet File

```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -F "file=@timesheet.csv" \
  -F "lead_data={\"manager_name\":\"John Doe\",\"email\":\"john@example.com\",\"store_name\":\"Store 1\",\"store_address\":\"123 Main St\"}"
```

Response includes:
- KPI tiles data (labor hours, costs, violation counts)
- Compliance violations summary
- Employee-specific reports
- Risk assessments

## Data Models

### Key Schemas
- `LLMParsedPunchEvent` - Individual timesheet entries
- `ReportKPIs` - KPI tiles data structure
- `ViolationInstance` - Compliance violation details
- `FinalAnalysisReport` - Complete analysis output

## Development Status

### Task Progress (from `tasks/tasks-prd-timesheet-magic-mvp.md`)
- [x] 1.0 Project Structure and Dependencies
- [x] 2.0 Frontend: File Upload and Lead Capture UI
- [x] 3.0 Backend: Timesheet Processing and Analysis Logic
  - [x] 3.3 LLM Processing
  - [x] 3.4 Compliance Rules
  - [x] 3.5.1 KPI Calculation ✨ **Latest completion**
  - [ ] 3.5.2-3.5.5 Additional reporting functions
  - [ ] 3.6 Integration with analysis endpoint
- [ ] 4.0 Frontend: Report Display
- [ ] 5.0 Backend: Logging and Error Handling
- [ ] 6.0 End-to-End Integration and Testing

## Known Issues

- **LLM API Timeouts**: Gemini API occasionally hangs; use stable models instead of preview versions
- **Model Reliability**: Preview models are unstable; test suite includes diagnostics
- **Data Variations**: Real timesheet formats vary; test with different file types

## Contributing

1. Check task status in `tasks/tasks-prd-timesheet-magic-mvp.md`
2. Run existing tests before making changes: `python tests/run_tests.py core`
3. Add unit tests for new functions in `backend/app/tests/`
4. Add integration tests in `tests/` for new workflows
5. Update documentation and task status

## License

MIT License - see LICENSE file for details. 