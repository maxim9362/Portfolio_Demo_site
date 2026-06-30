<!-- Этот файл содержит актуальную инструкцию по запуску, настройке и адаптации AI-консультанта под клиентов. -->

# Universal AI Site Consultant

Universal AI Site Consultant - это AI-чат для сайта бизнеса. Он консультирует посетителя по базе знаний клиента, помогает собрать заявку и сохраняет ее в админке.

Проект сейчас настроен как пример для сервиса по ремонту и установке кондиционеров в Израиле. Для нового клиента код менять обычно не нужно: меняется база знаний, email получателя заявок и, при необходимости, тексты/стили виджета.

## Что уже есть

- FastAPI backend.
- Чат с потоковым ответом через SSE.
- RAG по локальным Markdown-файлам из `knowledge`.
- ChromaDB для поиска по базе знаний.
- Локальные embeddings через `sentence-transformers`.
- Gemini как LLM-провайдер.
- PostgreSQL для сессий, сообщений, заявок и админки.
- Админка заявок: `/admin`.
- Встраиваемый виджет для WordPress и других сайтов: `/widget/chat-widget.js`.
- Email-уведомления о новых заявках.
- Автоматическое удаление заявок и связанных диалогов через 14 дней.
- Docker Compose запуск одной командой.

## Быстрый запуск через Docker

Нужны Docker Desktop и Gemini API key.

1. Создайте `.env` из примера:

```powershell
Copy-Item .env.example .env
```

2. Откройте `.env` и заполните минимум:

```dotenv
GEMINI_API_KEY=ваш_gemini_api_key
ADMIN_SESSION_SECRET=длинная_случайная_строка
```

3. Запустите проект:

```powershell
docker compose up --build
```

При запуске приложение автоматически:

- дождется PostgreSQL;
- создаст таблицы;
- создаст первого администратора;
- создаст индекс ChromaDB, если его еще нет;
- запустит FastAPI на порту `8000`.

Адреса:

- Чат / демо-страница: `http://localhost:8000`
- Админка: `http://localhost:8000/admin`
- Health check: `http://localhost:8000/health`
- JS-виджет: `http://localhost:8000/widget/chat-widget.js`

Остановка:

```powershell
docker compose down
```

Данные PostgreSQL и ChromaDB сохраняются в Docker volumes `postgres_data` и `chroma_data`.

## Локальный запуск без Docker

Нужны Python 3.12 и запущенный PostgreSQL.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/init_db.py
python scripts/ingest_knowledge.py
uvicorn app.main:app --reload
```

После запуска:

- чат: `http://127.0.0.1:8000`
- админка: `http://127.0.0.1:8000/admin`

## Настройка `.env`

Основные переменные:

```dotenv
APP_NAME=Universal AI Site Consultant
DEBUG=false
UVICORN_WORKERS=1

DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/ai_consultant

GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash
GEMINI_FALLBACK_MODEL=gemini-2.5-flash

EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
KNOWLEDGE_DIR=knowledge
CHROMA_PATH=chroma_data
CHROMA_COLLECTION=business_knowledge
RAG_MAX_DISTANCE=0.78
ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_me
ADMIN_SESSION_SECRET=change_me_long_random_string
ADMIN_COOKIE_SECURE=false

LEAD_RETENTION_DAYS=14

SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_USE_TLS=true
EMAIL_FROM=
EMAIL_TO=
```

Для подключения нового клиента обычно меняется только:

- `EMAIL_TO` - почта клиента, куда приходят заявки;
- файлы в `knowledge` - база знаний клиента;
- при необходимости `ALLOWED_ORIGINS` - домены сайтов, где будет стоять виджет.

## Email-уведомления

`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` и `EMAIL_FROM` - это техническая почта владельца системы. Эти данные один раз настраивает владелец проекта.

`EMAIL_TO` - почта клиента, куда должны приходить новые заявки.

Клиенту не нужны SMTP-доступы. Для подключения клиента нужно изменить только `EMAIL_TO`.

Если SMTP не настроен, приложение не падает: заявка сохраняется в PostgreSQL, а ошибка отправки письма пишется в лог.

Проверка email:

```powershell
python scripts/check_email.py
```

В Docker:

```powershell
docker compose exec app python scripts/check_email.py
```

## Админка

Админка доступна по адресу:

```text
http://localhost:8000/admin
```

При первом запуске логин и пароль берутся из `.env`:

```dotenv
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_me
```

После первого создания администратора данные хранятся в PostgreSQL. Если потом поменять `ADMIN_USERNAME` или `ADMIN_PASSWORD` в `.env`, существующий логин в базе не перезапишется.

После первого входа откройте:

```text
/admin/settings
```

и смените стандартный логин/пароль.

В `/admin/leads` можно:

- смотреть новые заявки;
- открывать карточку заявки;
- видеть последние сообщения диалога;
- менять статус заявки;
- звонить или писать в WhatsApp;
- удалять заявку из базы.

Удаление заявки из админки удаляет ее из PostgreSQL вместе с сообщениями и сессией этого диалога.

Заявки также удаляются автоматически через `LEAD_RETENTION_DAYS`, по умолчанию через 14 дней.

## База знаний

База знаний лежит в папке `knowledge`.

Сейчас там пример для сервиса кондиционеров:

- `knowledge/services/air_conditioner_services.md`
- `knowledge/prices/air_conditioner_prices.md`
- `knowledge/faq/air_conditioner_faq.md`
- `knowledge/contacts/company_contacts.md`
- `knowledge/policies/lead_rules.md`

После изменения Markdown-файлов нужно переиндексировать базу знаний:

```powershell
python scripts/ingest_knowledge.py
```

В Docker:

```powershell
docker compose exec app python scripts/ingest_knowledge.py
```

Если нужно полностью пересоздать ChromaDB volume:

```powershell
docker compose down
docker volume rm ai_chat_web_chroma_data
docker compose up --build
```

Точное имя volume можно посмотреть командой:

```powershell
docker volume ls
```

## Как адаптировать проект под другого клиента

Для адвоката, парикмахера, клиники, риелтора или другого бизнеса в первую очередь меняются не Python-файлы, а база знаний.

Что нужно заменить:

1. `knowledge/services/...md`
   Услуги клиента: что делает компания, какие направления есть, что входит в услугу.

2. `knowledge/prices/...md`
   Цены или диапазоны цен. Лучше писать диапазоны и условия: от чего зависит точная стоимость.

3. `knowledge/faq/...md`
   Частые вопросы клиентов и короткие понятные ответы.

4. `knowledge/contacts/...md`
   Города, адрес, телефон, email, часы работы, зона обслуживания.

5. `knowledge/policies/...md`
   Правила поведения AI: что можно обещать, что нельзя, когда собирать заявку, какие данные нужны.

6. `.env`
   Для клиента поменять `EMAIL_TO`.

7. `app/widget/chat-widget.js`
   Менять только если нужен другой текст кнопки, цвет, приветствие или внешний вид виджета.

8. `app/static/index.html`, `app/static/style.css`, `app/static/chat.js`
   Это демо-страница проекта. Для реального сайта клиента эти файлы обычно не нужны, если используется только виджет.

После изменения базы знаний обязательно выполнить:

```powershell
python scripts/ingest_knowledge.py
```

или в Docker:

```powershell
docker compose exec app python scripts/ingest_knowledge.py
```

## Пример адаптации под адвоката

Изменить файлы в `knowledge`:

- услуги: консультации, подготовка документов, сопровождение сделки, семейные споры, трудовые споры;
- цены: диапазоны или формат расчета, без обещания точной суммы до консультации;
- FAQ: какие документы нужны, как проходит консультация, сроки рассмотрения;
- контакты: город, офис, часы работы, формат онлайн/офлайн;
- правила: AI не дает юридических гарантий и не заменяет адвоката, а помогает записаться на консультацию.

В `.env`:

```dotenv
EMAIL_TO=client-lawyer@example.com
```

## Пример адаптации под парикмахера

Изменить файлы в `knowledge`:

- услуги: стрижки, окрашивание, укладка, уход, детские стрижки;
- цены: примерные диапазоны по длине волос и сложности;
- FAQ: сколько длится процедура, нужна ли запись, какие материалы используются;
- контакты: адрес салона, часы работы, районы обслуживания;
- правила: AI помогает выбрать услугу и записаться, но не обещает точный результат без консультации мастера.

В `.env`:

```dotenv
EMAIL_TO=client-salon@example.com
```

## Как встроить виджет на сайт

Backend должен быть доступен по HTTPS на отдельном домене или поддомене, например:

```text
https://ai.example.com
```

На сайт клиента нужно вставить одну строку перед закрывающим тегом `</body>`:

```html
<script src="https://ai.example.com/widget/chat-widget.js"></script>
```

Для WordPress это можно сделать через WPCode, Insert Headers and Footers или похожий плагин.

Виджет сам определяет адрес backend по своему `src` и отправляет сообщения на:

```text
https://ai.example.com/api/chat
```

Если виджет ставится на внешний домен, добавьте домен клиента в `.env`:

```dotenv
ALLOWED_ORIGINS=https://site-clienta.com,https://www.site-clienta.com
```

## Как удалить демо-сайт и оставить только виджет

В проекте есть простая демо-страница чата по адресу `/`. Она нужна для разработки и показа. На реальном сайте клиента обычно нужен только виджет.

Чтобы оставить только виджет:

1. Удалите или не публикуйте демо-страницу:

```text
app/static/index.html
app/static/style.css
app/static/chat.js
app/static/site.js
app/static/widget-demo.html
app/static/assets/
```

2. В `app/main.py` удалите маршрут главной страницы:

```python
@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
```

3. Если папка `app/static` больше не нужна, удалите подключение:

```python
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
```

4. Не удаляйте эти файлы и маршруты:

```text
app/widget/chat-widget.js
app/widget/router.py
app/api/chat.py
app/admin/router.py
```

Они нужны для работы виджета, API чата и админки.

После этого у проекта останутся основные адреса:

- `/widget/chat-widget.js` - скрипт виджета;
- `/api/chat` - API чата;
- `/admin` - админка заявок;
- `/health` - проверка работоспособности.

## API

Основные маршруты:

- `GET /health` - проверка приложения, возвращает `{"status": "ok"}`.
- `POST /api/chat` - потоковый чат через SSE.
- `GET /api/leads` - список заявок.
- `POST /api/ingest` - переиндексация базы знаний.
- `GET /admin` - админка.
- `GET /widget/chat-widget.js` - встраиваемый виджет.

## Проверки

Проверить импорты и тесты:

```powershell
python -m unittest discover -s tests
```

Проверить запуск:

```powershell
uvicorn app.main:app --reload
```

Проверить Docker:

```powershell
docker compose up --build
```

## Важные правила эксплуатации

- Не храните реальные ключи и пароли в репозитории.
- Для production используйте `DEBUG=false`.
- Для production укажите длинный `ADMIN_SESSION_SECRET`.
- Для production по HTTPS установите `ADMIN_COOKIE_SECURE=true`.
- После каждого изменения `knowledge` запускайте переиндексацию.
- Для нового клиента обычно меняйте только `knowledge` и `EMAIL_TO`.
