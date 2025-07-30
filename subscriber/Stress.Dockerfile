# Dockerfile for subscriber
FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the new stress test script
COPY subscriber_stress.py .

# Use the stress test script as the default command
CMD ["python", "-u", "subscriber_stress.py"]