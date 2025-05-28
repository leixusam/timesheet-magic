# Stage 1: Build the Next.js application
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json (or yarn.lock)
COPY package.json package-lock.json ./
# If you were using yarn, it would be:
# COPY package.json yarn.lock ./

# Install dependencies
RUN npm install
# If you were using yarn:
# RUN yarn install --frozen-lockfile

# Copy the rest of the application code
COPY . .

# Set build-time arguments for Next.js public environment variables
# These NEXT_PUBLIC_ variables need to be available at build time if they affect static generation
# For variables only needed at runtime, they can be passed when running the container
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}

# Build the Next.js application
RUN npm run build

# Stage 2: Serve the application from a lean image
FROM node:18-alpine

WORKDIR /app

# Copy only necessary files from the builder stage
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/next.config.mjs ./next.config.mjs
# If you have a custom server.js, copy that too:
# COPY --from=builder /app/server.js ./server.js

# Expose port 3000 (default for Next.js)
EXPOSE 3000

# Set environment variable for port (Next.js uses PORT)
ENV PORT 3000

# Command to run the Next.js application
# This will use the .next/standalone output if you configure output: 'standalone' in next.config.mjs for an optimized production server.
# Otherwise, it starts the regular Next.js server.
# For a typical setup without standalone: 
CMD ["npm", "start"]

# If you configure `output: 'standalone'` in next.config.mjs (recommended for smaller images):
# WORKDIR /app
# COPY --from=builder /app/.next/standalone ./ 
# COPY --from=builder /app/.next/static ./.next/static 
# COPY --from=builder /app/public ./public 
# CMD ["node", "server.js"] 