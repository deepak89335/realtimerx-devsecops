# Use minimal & secure base image
FROM python:3.11-slim-bookworm

# Prevent Python from writing .pyc files & enable logs immediately
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies (minimal) + security updates
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip + critical packages (fix vulnerabilities)
RUN pip install --upgrade pip wheel setuptools

# Copy only requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies securely
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app
COPY tests/ ./tests

# Create non-root user (SECURITY BEST PRACTICE)
RUN useradd -m appuser
USER appuser

# Environment variables
ENV FLASK_DEBUG=false
ENV LOW_STOCK_THRESHOLD=10
ENV EXPIRY_WARNING_DAYS=30

# Expose port
EXPOSE 5000

# Run app
CMD ["python", "app/app.py"]
