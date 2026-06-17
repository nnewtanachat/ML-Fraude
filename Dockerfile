FROM python:3.12-slim

WORKDIR /app

# ติดตั้ง dependencies ก่อน (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy code + model
COPY src/ ./src/
COPY model/ ./model/

# รัน API
CMD ["uvicorn", "src.serve.main:app", "--host", "0.0.0.0", "--port", "8000"]
