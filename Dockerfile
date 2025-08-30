# ---------- base image ----------
    FROM python:3.11-slim AS app

    ENV PYTHONDONTWRITEBYTECODE=1 \
        PYTHONUNBUFFERED=1
    
    WORKDIR /app
    
    # System deps for psycopg / builds
    RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev \
     && rm -rf /var/lib/apt/lists/*
    
    # Install Python deps
    COPY requirements.txt .
    RUN pip install --no-cache-dir --upgrade pip \
     && pip install --no-cache-dir -r requirements.txt
    
    # Copy source
    COPY app ./app
    # (Optional but useful if you run alembic in the container)
    COPY alembic.ini ./alembic.ini
    COPY migrations ./migrations
    
    # Expose & run
    EXPOSE 8080
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    