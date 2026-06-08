# Dockerfile for Railway Deployment

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright/Chromium
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libglib2.0-0 \
    libglib2.0-dev \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxext6 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libdbus-1-3 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY bike_scraper/ ./bike_scraper/
COPY run_api.py .
COPY run_bot.py .
COPY minimal_app.py .
COPY production_scheduler.py .
COPY production_wrapper.py .
COPY monitoring_reporter.py .
COPY hybrid_priority_config.py .

# Set environment
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO
ENV PORT=8080
ENV PRODUCTION_MODE=true

# Expose port for Railway
EXPOSE 8080

# Health check (disabled - Railway handles health checks via API endpoints)
# HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
#     CMD curl -f http://localhost:${PORT}/health || exit 1

# Run in production mode (24/7 scheduler + API)
CMD ["python", "production_wrapper.py"]
