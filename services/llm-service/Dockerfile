FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY llm-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY shared/ /app/shared/

# Copy provider config
COPY llm-service/config/ /app/config/

# Copy application code
COPY llm-service/app/ /app/app/

# Ensure shared imports resolve
ENV PYTHONPATH=/app

EXPOSE 5000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
