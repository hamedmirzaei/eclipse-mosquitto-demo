# Dockerfile for publisher
FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY publisher.py .

CMD ["python", "-u", "publisher.py"]