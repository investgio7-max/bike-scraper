FROM python:3.11

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium && \
    playwright install-deps

RUN chmod +x start.sh

EXPOSE 8000
CMD ["bash", "start.sh"]
