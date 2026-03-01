FROM python:3.12-slim

# Install libmagic for python-magic MIME detection
RUN apt-get update && apt-get install -y --no-install-recommends libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY image-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utils and application code
COPY shared/ /app/shared/
COPY image-service/app/ /app/app/

ENV PYTHONPATH=/app

EXPOSE 5001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5001"]
