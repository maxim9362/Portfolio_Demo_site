#!/bin/sh
# Этот файл подготавливает базу данных и ChromaDB перед запуском FastAPI.

set -eu

python scripts/init_db.py

if [ ! -f "${CHROMA_PATH:-/app/chroma_data}/chroma.sqlite3" ]; then
    echo "Индекс ChromaDB не найден, запускается индексация базы знаний."
    python scripts/ingest_knowledge.py
else
    echo "Найден существующий индекс ChromaDB."
fi

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${UVICORN_WORKERS:-1}"
