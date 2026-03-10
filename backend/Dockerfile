FROM python:3.12-slim

# Do not write .pyc files inside the container image
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Create and switch to a non-root user for security
RUN useradd --no-create-home --shell /bin/false appuser && \
    mkdir -p /data && chown appuser /data
USER appuser

# --reload is for development only; remove it for production deployments
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
