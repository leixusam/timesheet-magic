# Documentation

This directory contains comprehensive documentation for the TimeSheet Magic project.

## Setup and Deployment
- **[Local Development Setup](LOCAL_DEV_SETUP.md)** - Complete guide for setting up local development environment
- **[Supabase Setup](SUPABASE_SETUP.md)** - Database and authentication configuration
- **[Frontend Deployment](FRONTEND_DEPLOYMENT.md)** - Guide for deploying the frontend to production

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