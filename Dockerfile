# Deployment image for Render, Railway or any container host.
#
# Python 3.12 is used here rather than 3.15 on purpose. Every wheel this
# project can use exists for 3.12, so the build is fast and reliable. The code
# runs on 3.10 and above, so nothing is lost.

FROM python:3.12-slim

# Tesseract is a system program, not a Python package. Without these three the
# app still runs, it just reports scanned pages as needing OCR.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Train at build time so the first request is not slowed by it.
RUN python run.py train || true

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD streamlit run bsp/ui/streamlit_app.py \
    --server.port=${PORT:-8501} \
    --server.address=0.0.0.0 \
    --server.headless=true
