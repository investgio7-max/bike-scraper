FROM python:3.11

WORKDIR /app

# Install system dependencies for python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Make executable
RUN chmod +x start.sh

EXPOSE 8000

CMD ["bash", "start.sh"]
