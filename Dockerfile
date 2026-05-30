FROM python:3.11-slim

# Install system dependencies for Playwright + Chromium
RUN apt-get update && apt-get install -y \
    wget curl gnupg \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libgtk-3-0 libgbm1 \
    libasound2 libxss1 libxtst6 \
    fonts-liberation libappindicator3-1 \
    xdg-utils libxrandr2 libpangocairo-1.0-0 \
    libxcomposite1 libxdamage1 libxfixes3 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data generated_resumes logs

# Default command (overridden by docker-compose)
CMD ["python", "-m", "streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
