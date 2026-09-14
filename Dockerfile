FROM --platform=linux/arm64 python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt requirements-strands.txt requirements-agentcore.txt ./
RUN pip install --no-cache-dir \
    -r requirements.txt \
    -r requirements-strands.txt \
    -r requirements-agentcore.txt

COPY flylab ./flylab
COPY agentcore ./agentcore
COPY data/mb_summary.json ./data/mb_summary.json

EXPOSE 8080

CMD ["uvicorn", "agentcore.main:app", "--host", "0.0.0.0", "--port", "8080"]
