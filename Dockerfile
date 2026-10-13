FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-tam && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python scripts/make_samples.py
# train the ML intelligence layer at build time (≈10 min on 2 cores; set BANKIQ_SKIP_TRAIN=1 to skip and mount models/ instead)
ARG BANKIQ_SKIP_TRAIN=0
RUN if [ "$BANKIQ_SKIP_TRAIN" = "0" ]; then python -m bankiq.experiments.run_all; fi
ENV VASOOL_DB=/data/vasool.db
VOLUME ["/data"]
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
