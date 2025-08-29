FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install build dependencies and requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Create non-root user
RUN useradd --create-home appuser || true

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11

# Copy only needed source files (avoid copying .env or .venv)
COPY ./manage.py ./requirements.txt ./safeballot ./elections ./templates ./static ./scripts /app/

# Ensure entrypoint or start script will run collectstatic at container start
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["gunicorn", "safeballot.wsgi:application", "--bind", "0.0.0.0:8000"]
