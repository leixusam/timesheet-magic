# 🏠 Local Development Setup Guide

## **Overview: Environment-Based Configuration**

This project follows **industry best practices** with environment-specific configurations:

### **Local Development:**
```
Frontend (localhost:3000) → Backend (localhost:8000) → Database (SQLite local)
```

### **Production:**
```
Frontend (Vercel/deployed) → Backend (fly.dev) → Database (Supabase)
```

---

## **🚀 Quick Setup**

### **Option 1: Automated Setup**
```bash
./setup_local_dev.sh
```

### **Option 2: Manual Setup**

#### **1. Frontend Environment**
Create `frontend/.env.local`:
```env
BACKEND_URL=http://localhost:8000
NODE_ENV=development
NEXT_PUBLIC_APP_ENV=local
```

#### **2. Backend Environment**  
Create `backend/.env.local`:
```env
# Local Development Database
DATABASE_URL=sqlite:///./timesheet_magic_local.db

# Optional: Add your API keys for LLM features
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here

# Development settings
DEBUG=True
LOG_LEVEL=DEBUG
```

#### **3. Install Dependencies**
```bash
# Backend
cd backend
python -m venv venv_local
source venv_local/bin/activate  # On Windows: venv_local\Scripts\activate
pip install -r ../requirements.txt

# Frontend
cd ../frontend
npm install
```

---

## **🏃‍♂️ Running Locally**

### **Start Backend** (Terminal 1)
```bash
cd backend
source venv_local/bin/activate
uvicorn app.main:app --reload --port 8000
```

### **Start Frontend** (Terminal 2)
```bash
cd frontend
npm run dev
```

### **Access Your App**
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs

---

## **🔄 Environment Switching**

The system **automatically** detects which environment you're in:

| Environment | Frontend Calls | Backend Uses | Database |
|-------------|----------------|--------------|----------|
| **Local**   | `localhost:8000` | SQLite local | `timesheet_magic_local.db` |
| **Production** | `fly.dev` | Supabase | Production DB |

### **How It Works:**
1. **Frontend:** Reads `BACKEND_URL` from `.env.local` or defaults to production
2. **Backend:** Reads `DATABASE_URL` from `.env.local` or defaults to Supabase
3. **No code changes needed** - just different environment files!

---

## **📁 File Structure**
```
timesheet-magic/
├── frontend/
│   ├── .env.local          # 👈 Local frontend config
│   ├── .env.production     # 👈 Production frontend config
│   └── src/app/api/        # Auto-detects environment
├── backend/
│   ├── .env.local          # 👈 Local backend config  
│   ├── .env.production     # 👈 Production backend config
│   └── app/                # Auto-detects environment
└── setup_local_dev.sh      # 👈 Automated setup
```

---

## **✅ Benefits**

### **For Development:**
- **Fast iteration** with local database
- **No production interference** during testing
- **Offline development** capability
- **Quick debugging** with local logs

### **For Production:**
- **Secure production data** isolation
- **Scalable cloud infrastructure**
- **Professional deployment** pipeline
- **Zero downtime** deployments

---

## **🔧 Troubleshooting**

### **Backend Not Starting?**
```bash
# Check if port 8000 is free
lsof -i :8000

# Kill any process on port 8000
pkill -f "uvicorn"
```

### **Frontend API Errors?**
```bash
# Verify environment file
cat frontend/.env.local

# Check backend is running
curl http://localhost:8000/docs
```

### **Database Issues?**
```bash
# Check database file
ls -la backend/timesheet_magic_local.db

# Reset local database
rm backend/timesheet_magic_local.db
# Restart backend to recreate tables
```

---

## **🚀 Deployment**

### **Production Deployment** (Already Set Up)
```bash
# Deploy backend
cd backend && flyctl deploy

# Deploy frontend (if using Vercel)
cd frontend && vercel deploy --prod
```

The production deployment automatically uses production environment variables and connects all services together.

---

This setup gives you the **best of both worlds**: fast local development with production-grade deployment! 🎉 