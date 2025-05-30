#!/bin/bash

echo "🚀 Setting up Local Development Environment for TimeSheet Magic"

# 1. Create frontend environment file
echo "📁 Creating frontend .env.local..."
cat > frontend/.env.local << 'EOF'
# Local Development Environment
BACKEND_URL=http://localhost:8000
NODE_ENV=development
NEXT_PUBLIC_APP_ENV=local
EOF

# 2. Create backend environment file  
echo "📁 Creating backend .env.local..."
cat > backend/.env.local << 'EOF'
# Local Development Database
DATABASE_URL=sqlite:///./timesheet_magic_local.db

# Optional: Local LLM settings
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here

# Development settings
DEBUG=True
LOG_LEVEL=DEBUG
EOF

# 3. Install dependencies
echo "📦 Installing backend dependencies..."
cd backend
python -m venv venv_local
source venv_local/bin/activate
pip install -r ../requirements.txt

echo "📦 Installing frontend dependencies..."
cd ../frontend
npm install

echo "✅ Local development environment setup complete!"
echo ""
echo "🏃‍♂️ To start local development:"
echo "   1. Backend:  cd backend && source venv_local/bin/activate && uvicorn app.main:app --reload --port 8000"
echo "   2. Frontend: cd frontend && npm run dev"
echo ""
echo "🌐 Your app will be available at:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs" 