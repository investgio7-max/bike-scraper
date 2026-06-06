FROM python:3.11

WORKDIR /app

# Install system dependencies for CloakBrowser
RUN apt-get update && apt-get install -y \
    libnspr4 \
    libnss3 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxkbcommon0 \
    libasound2 \
    fonts-liberation \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install -r requirements.txt

# Pre-download CloakBrowser
RUN python -c "from cloakbrowser import launch; print('CloakBrowser ready')" || true

RUN chmod +x start.sh

EXPOSE 8000
CMD ["bash", "start.sh"]
