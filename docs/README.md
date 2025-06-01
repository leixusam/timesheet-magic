# Documentation

This directory contains comprehensive documentation for the TimeSheet Magic project.

## Setup and Deployment
- **[Local Development Setup](LOCAL_DEV_SETUP.md)** - Complete guide for setting up local development environment
- **[Supabase Setup](SUPABASE_SETUP.md)** - Database and authentication configuration
- **[Frontend Deployment](FRONTEND_DEPLOYMENT.md)** - Guide for deploying the frontend to production

## Two-Pass Processing System
- **[Decision Criteria](TWO_PASS_DECISION_CRITERIA.md)** - When to use two-pass vs single-pass processing
- **[Developer Guide](TWO_PASS_DEVELOPER_GUIDE.md)** - Extending and modifying two-pass functionality
- **[Troubleshooting Guide](TWO_PASS_TROUBLESHOOTING.md)** - Operational troubleshooting and monitoring
- **[API Documentation](TWO_PASS_API_DOCUMENTATION.md)** - Complete API reference for two-pass processing

## Development
- **[Repository Cleanup Summary](CLEANUP_SUMMARY.md)** - Documentation of repository organization and cleanup

## Quick Links

### Development Setup
```bash
# Quick local setup
source docs/LOCAL_DEV_SETUP.md

# Backend setup
cd backend && source venv_local/bin/activate
uvicorn app.main:app --reload

# Frontend setup  
cd frontend && npm run dev
```

### Two-Pass Processing
```bash
# Check system health
curl http://localhost:8000/metrics/health

# Process with two-pass
curl -X POST http://localhost:8000/api/analyze \
  -F "file=@timesheet.csv" \
  -F "processing_mode=two_pass"

# Monitor performance
curl http://localhost:8000/metrics/performance?hours=24
```

### Testing
```bash
# Run all tests
python run_tests.py

# See tests documentation
cat tests/README.md
```

### Sample Data
```bash
# Use sample files for testing
ls sample_data/

# See sample data documentation
cat sample_data/README.md
```

## Project Structure
```
time-sheet-magic/
├── docs/                      # 📚 Documentation (you are here)
├── sample_data/               # 📊 Test data files
├── tests/                     # 🧪 Integration tests
├── backend/                   # ⚙️ FastAPI backend
├── frontend/                  # 🌐 Next.js frontend
└── run_tests.py              # 🚀 Unified test runner
``` 