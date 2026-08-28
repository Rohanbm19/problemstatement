FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for build
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

EXPOSE 8000

ENV PORT=8000
ENV HOST=0.0.0.0

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
