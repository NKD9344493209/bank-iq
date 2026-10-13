FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-tam && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python scripts/make_samples.py
ENV VASOOL_DB=/app/data/vasool.db VASOOL_AUTH=off PORT=8000
EXPOSE 8000
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT}