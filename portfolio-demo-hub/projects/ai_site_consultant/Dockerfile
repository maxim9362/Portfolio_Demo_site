# Этот файл собирает production-контейнер FastAPI-приложения на Python 3.12.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY app ./app
COPY knowledge ./knowledge
COPY scripts ./scripts

RUN chmod +x /app/scripts/start.sh \
    && mkdir -p /app/chroma_data

EXPOSE 8000

CMD ["/app/scripts/start.sh"]
