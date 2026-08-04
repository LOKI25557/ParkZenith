# --- Stage 1: Build dependencies ---
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Stage 2: Runtime image ---
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

# Copy AI service codebase under the ai_service/ prefix to match absolute imports
COPY . ./ai_service

# Create directories and set permissions for non-root user
RUN mkdir -p /app/ai_service/data && \
    addgroup --system appgroup && \
    adduser --system --group appuser && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8001

ENV ENVIRONMENT=production
ENV PORT=8001

CMD ["uvicorn", "ai_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
