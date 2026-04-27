FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip wheel setuptools

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app
COPY tests/ ./tests

# Create non-root user AND fix instance directory permissions
RUN useradd -m appuser && \
    mkdir -p /app/instance && \
    chown -R appuser:appuser /app

USER appuser

ENV FLASK_DEBUG=false
ENV LOW_STOCK_THRESHOLD=10
ENV EXPIRY_WARNING_DAYS=30

EXPOSE 5000

CMD ["python", "app/app.py"]
