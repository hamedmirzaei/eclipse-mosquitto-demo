# Dockerfile for publisher
FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the new stress test script
COPY publisher_stress.py .

# Use the stress test script as the default command
CMD ["python", "-u", "publisher_stress.py"]