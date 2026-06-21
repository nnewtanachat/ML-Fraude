FROM python:3.12-slim

WORKDIR /app

# ติดตั้ง dependencies ก่อน (cache layer) — retry loop ถ้า fail
COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && \
    for i in 1 2 3 4 5; do \
      pip install --no-cache-dir -r requirements.txt && break; \
      echo "Attempt $i failed, retrying..."; \
      sleep 5; \
    done

# copy code + model
COPY src/ ./src/
COPY model/ ./model/

# รัน API
CMD ["uvicorn", "src.serve.main:app", "--host", "0.0.0.0", "--port", "8000"]
