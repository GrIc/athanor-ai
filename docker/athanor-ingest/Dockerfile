FROM python:3.12-slim

# Install system dependencies: rclone and build essentials if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    rclone \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1001 appuser
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Make sure the appuser can write to /tmp for rclone.conf and downloads
RUN chown -R appuser:appuser /app /tmp

USER 1001

# The entrypoint will be the ingest script
CMD ["python", "ingest_job.py"]