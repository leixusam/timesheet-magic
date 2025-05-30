# Frontend Deployment Guide

## 🚀 Deployment Options for Time Sheet Magic Frontend

Your Next.js frontend is ready for deployment! Here are several deployment options from easiest to most advanced:

## Prerequisites

Before deploying, you'll need to set up environment variables:

### Required Environment Variables

Create a `.env.local` file in the `frontend/` directory with:

```bash
# Google Maps API Key (for location autocomplete)
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your-google-maps-api-key-here

# Backend API URL (adjust based on your deployment)
BACKEND_URL=http://localhost:8000

# Supabase Configuration (if using Supabase)
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url-here
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key-here
```

## Option 1: Vercel (Recommended - Easiest)

Vercel is the company behind Next.js and offers the best integration:

### Steps:
1. Push your code to GitHub/GitLab/Bitbucket
2. Go to [vercel.com](https://vercel.com) and sign up
3. Import your repository
4. Set environment variables in Vercel dashboard:
   - `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`
   - `BACKEND_URL` (your backend deployment URL)
   - `NEXT_PUBLIC_SUPABASE_URL` (if using)
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` (if using)
5. Deploy!

### Advantages:
- Zero configuration
- Automatic deployments on git push
- Global CDN
- Free tier available
- Perfect Next.js integration

## Option 2: Netlify

Another excellent option for static sites:

### Steps:
1. Push code to Git repository
2. Go to [netlify.com](https://netlify.com)
3. Connect your repository
4. Build settings:
   - Build command: `npm run build`
   - Publish directory: `.next`
5. Set environment variables in Netlify dashboard
6. Deploy!

## Option 3: Docker Deployment

Use the included Dockerfile for containerized deployment:

### Build the Docker image:
```bash
cd frontend
docker build -t timesheet-frontend .
```

### Run the container:
```bash
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your-key \
  -e BACKEND_URL=http://your-backend-url \
  timesheet-frontend
```

### For production with docker-compose:
Create a `docker-compose.yml`:

```yaml
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY}
      - BACKEND_URL=${BACKEND_URL}
    depends_on:
      - backend
```

## Option 4: Traditional VPS/Server

Deploy on any Linux server:

### Steps:
1. Install Node.js 18+ on your server
2. Clone your repository
3. Install dependencies: `npm install`
4. Create `.env.local` with your environment variables
5. Build the application: `npm run build`
6. Start with PM2 for process management:

```bash
# Install PM2 globally
npm install -g pm2

# Start the application
pm2 start npm --name "timesheet-frontend" -- start

# Save PM2 configuration
pm2 save
pm2 startup
```

### Nginx Configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## Option 5: AWS/GCP/Azure

### AWS (using Amplify):
1. Go to AWS Amplify console
2. Connect your Git repository
3. Configure build settings:
   - Build command: `npm run build`
   - Output directory: `.next`
4. Set environment variables
5. Deploy

### Google Cloud Platform:
1. Use Google Cloud Run for containerized deployment
2. Build and push Docker image to Google Container Registry
3. Deploy to Cloud Run

### Azure:
1. Use Azure Static Web Apps
2. Connect your GitHub repository
3. Configure build pipeline

## Environment Variables by Deployment Type

### For Static Deployments (Vercel, Netlify):
- All `NEXT_PUBLIC_*` variables must be set at build time
- `BACKEND_URL` should point to your deployed backend

### For Server Deployments (Docker, VPS):
- Can use both build-time and runtime environment variables
- More flexible configuration options

## Testing Your Deployment

After deployment, test these features:
1. File upload functionality
2. Google Maps autocomplete (if API key is configured)
3. Backend API communication
4. Report generation and viewing

## Troubleshooting

### Common Issues:

1. **Environment variables not working:**
   - Ensure `NEXT_PUBLIC_*` variables are set at build time
   - Check variable names match exactly

2. **API calls failing:**
   - Verify `BACKEND_URL` points to correct backend
   - Check CORS configuration on backend

3. **Google Maps not working:**
   - Verify `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` is set
   - Check API key has Places API enabled

4. **Build failures:**
   - Run `npm run build` locally first
   - Check for TypeScript errors
   - Ensure all dependencies are installed

## Performance Optimization

For production deployments:

1. **Enable compression** in your web server
2. **Set up CDN** for static assets
3. **Configure caching headers**
4. **Monitor performance** with tools like Lighthouse

## Security Considerations

1. **Never expose sensitive keys** in `NEXT_PUBLIC_*` variables
2. **Use HTTPS** in production
3. **Configure CSP headers** for security
4. **Regularly update dependencies**

## Monitoring

Set up monitoring for:
- Application uptime
- Error tracking (Sentry, LogRocket)
- Performance metrics
- User analytics

---

## Quick Start Commands

```bash
# Local development
cd frontend
npm install
npm run dev

# Production build
npm run build
npm start

# Docker deployment
docker build -t timesheet-frontend .
docker run -p 3000:3000 timesheet-frontend
```

Choose the deployment option that best fits your infrastructure and requirements! 