# syntax=docker/dockerfile:1

# ==============================================================================
# Stage 1: Frontend Build Environment (Node.js 22 LTS Alpine)
# ==============================================================================
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Frontend Production Runner (Node.js 22 LTS Alpine)
# ==============================================================================
FROM node:22-alpine AS console
WORKDIR /app/frontend

ENV NODE_ENV=production
ENV PORT=3000

COPY --from=frontend-builder /app/frontend/package.json ./
COPY --from=frontend-builder /app/frontend/package-lock.json* ./
COPY --from=frontend-builder /app/frontend/.next ./.next
COPY --from=frontend-builder /app/frontend/public ./public
COPY --from=frontend-builder /app/frontend/node_modules ./node_modules

EXPOSE 3000
CMD ["npm", "start"]

# ==============================================================================
# Stage 3: Python 3.12 LTS Base & System Dependencies
# ==============================================================================
FROM python:3.12-slim AS python-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgomp1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY lexis_ops/ ./lexis_ops/
COPY tests/ ./tests/
COPY specs/ ./specs/
COPY Court_Administration_Agent_PRD.md ./

# ==============================================================================
# Stage 4: Production Temporal Worker & Health Gateway Runner
# ==============================================================================
FROM python-base AS worker

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/ready || exit 1

ENTRYPOINT ["python", "-m", "lexis_ops.entrypoint"]

# ==============================================================================
# Stage 5: Continuous Verification & Automated Test Runner
# ==============================================================================
FROM python-base AS test-runner

ENTRYPOINT ["pytest", "-v", "--disable-warnings"]
