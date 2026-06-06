FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything else
COPY . .

# Make start.sh executable
RUN chmod +x start.sh

EXPOSE 8000

CMD ["bash", "./start.sh"]
