# Beep-Boop v2.0 Production Dockerfile
# Multi-stage build for optimized production container

# =============================================================================
# Build Stage
# =============================================================================
FROM node:18-alpine AS builder

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    make \
    g++ \
    && rm -rf /var/cache/apk/*

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./

# Install dependencies
RUN npm ci --only=production && npm cache clean --force

# Copy source code
COPY src/ ./src/

# Generate Prisma client
RUN npx prisma generate

# Build TypeScript application
RUN npm run build

# Build client application
COPY client/package*.json ./client/
RUN cd client && npm ci --only=production
COPY client/ ./client/
RUN npm run build:client

# =============================================================================
# Production Stage
# =============================================================================
FROM node:18-alpine AS production

# Install system dependencies
RUN apk add --no-cache \
    curl \
    bash \
    && rm -rf /var/cache/apk/*

# Create non-root user
RUN addgroup -g 1001 -S beepboop && \
    adduser -S beepboop -u 1001 -G beepboop

# Set working directory
WORKDIR /app

# Copy built application from builder stage
COPY --from=builder --chown=beepboop:beepboop /app/dist ./dist
COPY --from=builder --chown=beepboop:beepboop /app/node_modules ./node_modules
COPY --from=builder --chown=beepboop:beepboop /app/package*.json ./
COPY --from=builder --chown=beepboop:beepboop /app/client/dist ./client/dist

# Copy Prisma schema and generated client
COPY --from=builder --chown=beepboop:beepboop /app/node_modules/.prisma ./node_modules/.prisma

# Create logs directory
RUN mkdir -p logs && chown -R beepboop:beepboop logs

# Switch to non-root user
USER beepboop

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/health/live || exit 1

# Start application
CMD ["npm", "start"]