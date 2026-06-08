# Dockerfile for Railway Deployment

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
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

# Set environment
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO
ENV PORT=8000

# Expose port for Railway
EXPOSE 8000

# Health check (disabled - Railway handles health checks via API endpoints)
# HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
#     CMD curl -f http://localhost:${PORT}/health || exit 1

# Run FastAPI with Telegram bot
# CMD removed - using railway.toml startCommand only
# CMD ["python3", "-u", "run_api.py"]
