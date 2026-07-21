FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1

# All configuration is loaded from environment variables (.env / env_file)
# See .env.example for the full list of supported variables.
# At minimum, BOT_TOKEN must be provided.

CMD ["python", "main.py"]
