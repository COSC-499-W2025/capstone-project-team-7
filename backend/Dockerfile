FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ffmpeg \
    libsndfile1 \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt

COPY src ./src

CMD ["python", "-m", "src.cli.textual_app"]