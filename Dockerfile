# Use Python 3.11 slim base image (provides native StrEnum support)
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies (Pandoc is required for DOCX compilation via subprocess)
RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser and its system-level OS dependencies
RUN apt-get update && playwright install --with-deps chromium && rm -rf /var/lib/apt/lists/*

# Copy the rest of the application code
COPY core/ /app/core/
COPY server/ /app/server/

# Create output directory for caching generated papers
RUN mkdir -p /app/outputs

# Expose FastAPI port
EXPOSE 8000

# Start Uvicorn server (dynamically binds to PORT for environments like Railway)
CMD ["sh", "-c", "uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8000} --timeout-keep-alive 120"]

