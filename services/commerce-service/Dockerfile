FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY commerce-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY shared/ /app/shared/

# Copy application code
COPY commerce-service/app/ /app/app/

# Ensure shared imports resolve
ENV PYTHONPATH=/app

EXPOSE 3004

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3004"]
