FROM python:3.11

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

# Install Playwright browsers and dependencies
RUN pip install playwright && \
    python -m playwright install chromium && \
    python -m playwright install-deps

RUN chmod +x start.sh

EXPOSE 8000
CMD ["bash", "start.sh"]
