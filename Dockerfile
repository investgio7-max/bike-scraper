# Dockerfile for Railway Deployment

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Chromium/CloakBrowser
# Use chromium-browser package to automatically pull all dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    build-essential \
    chromium-browser \
    && apt-get clean \
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
