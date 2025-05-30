#!/bin/bash

# Local Frontend Deployment Script
# This script builds and starts the frontend in production mode

echo "🚀 Starting Frontend Deployment..."

# Check if we're in the frontend directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Please run this script from the frontend directory"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to install dependencies"
    exit 1
fi

# Build the application
echo "🔨 Building the application..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Error: Build failed"
    exit 1
fi

echo "✅ Build successful!"

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "⚠️  Warning: .env.local not found. Creating template..."
    cat > .env.local << EOF
# Google Maps API Key (for location autocomplete)
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your-google-maps-api-key-here

# Backend API URL (adjust based on your deployment)
BACKEND_URL=http://localhost:8000

# Supabase Configuration (if using Supabase)
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url-here
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key-here
EOF
    echo "📝 Please edit .env.local with your actual values"
fi

# Start the production server
echo "🌟 Starting production server..."
echo "Frontend will be available at: http://localhost:3000"
echo "Press Ctrl+C to stop the server"

npm start 