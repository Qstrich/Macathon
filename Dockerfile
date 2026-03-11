FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# System dependencies for Playwright/Chromium and Node.js
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    fonts-liberation \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy project into image (inner Macathon contains backend/, frontend/, scraper/, etc.)
COPY Macathon /app

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Install Node dependencies for scraper.
# Playwright will download Chromium at runtime when the scraper runs.
WORKDIR /app/scraper
RUN npm install

# Runtime working dir: backend root
WORKDIR /app

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

