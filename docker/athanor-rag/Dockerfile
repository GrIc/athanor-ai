FROM python:3.12-slim

RUN useradd -m -u 1001 rag
USER 1001
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=rag:rag . .
COPY --chown=rag:rag ../../lib ./lib

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]