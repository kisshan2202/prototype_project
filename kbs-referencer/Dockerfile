FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY referencer ./referencer
COPY guide/kaplan_harvard_rules.md ./guide/kaplan_harvard_rules.md
COPY web ./web
COPY server.py .
RUN useradd -m app
USER app
# Cloud Run sets PORT; Vertex AI is used when GOOGLE_GENAI_USE_VERTEXAI=TRUE
CMD ["python", "server.py"]
