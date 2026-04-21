FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app
COPY tests/ ./tests

# Set environment variables
ENV FLASK_DEBUG=false
ENV LOW_STOCK_THRESHOLD=10
ENV EXPIRY_WARNING_DAYS=30

# Expose port
EXPOSE 5000

# Run app
CMD ["python", "app/app.py"]
