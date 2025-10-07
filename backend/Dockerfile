FROM python:3.11-slim
WORKDIR /app

# Install system deps for pdfplumber/openpyxl
RUN apt-get update && apt-get install -y build-essential libjpeg-dev zlib1g-dev poppler-utils && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
