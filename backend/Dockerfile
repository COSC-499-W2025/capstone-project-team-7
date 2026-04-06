FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ffmpeg \
    libsndfile1 \
    libmagic1 \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt

# Preserve backend.src.* import path expected by the codebase
COPY __init__.py ./backend/__init__.py
COPY src ./backend/src

ENV PYTHONPATH=/app

EXPOSE ${PORT:-8000}

CMD ["sh", "-c", "python -m uvicorn backend.src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]