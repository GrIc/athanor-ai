FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY digest.py .
COPY templates/ templates/

RUN useradd -r -u 1001 -s /sbin/nologin appuser
USER 1001

CMD ["python", "digest.py"]
