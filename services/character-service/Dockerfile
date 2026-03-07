FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY character-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY shared/ /app/shared/

# Copy application code
COPY character-service/app/ /app/app/

# Copy generation config
COPY character-service/config/ /app/config/

# Ensure shared imports resolve
ENV PYTHONPATH=/app

EXPOSE 5002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5002"]
