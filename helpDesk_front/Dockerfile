# Stage 1: Build the React application
# Prefer Node for maximum Docker compatibility; Bun image can fail on some hosts/architectures.
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files (npm works with package.json only; use npm ci if package-lock.json is present)
COPY package.json ./
RUN npm install

COPY . .

# Build arguments for environment variables
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=$VITE_API_URL
ARG VITE_BNPZID_ENABLED=false
ENV VITE_BNPZID_ENABLED=$VITE_BNPZID_ENABLED

# Build the application
RUN npm run build

# Stage 2: One-off copy runner (used by docker-compose to fill frontend_static volume)
# Does not depend on nginx paths; avoids "container doesn't start" issues.
FROM alpine:3.19 AS runner
COPY --from=builder /app/dist /output
RUN chmod -R a+rX /output
CMD ["sh", "-c", "mkdir -p /app/dist && cp -ra /output/. /app/dist/ && echo 'Frontend static files ready'"]

# Stage 3: Serve with Nginx (standalone run or other use)
FROM nginx:alpine AS production

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config for SPA (main proxy config is in nginx service; this is for standalone run)
COPY nginx-default.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
