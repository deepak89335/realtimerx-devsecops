# Use latest slim image with fewer vulnerabilities
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps + force security upgrades on ALL packages
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip + packages
RUN pip install --upgrade pip wheel setuptools

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app
COPY tests/ ./tests

# Non-root user
RUN useradd -m appuser
USER appuser

ENV FLASK_DEBUG=false
ENV LOW_STOCK_THRESHOLD=10
ENV EXPIRY_WARNING_DAYS=30

EXPOSE 5000

CMD ["python", "app/app.py"]
