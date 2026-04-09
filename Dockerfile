FROM python:3.11-slim

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .
COPY tests/ ./tests/

ENV FLASK_DEBUG=false
ENV LOW_STOCK_THRESHOLD=10
ENV EXPIRY_WARNING_DAYS=30

EXPOSE 5000

CMD ["python", "app.py"]
