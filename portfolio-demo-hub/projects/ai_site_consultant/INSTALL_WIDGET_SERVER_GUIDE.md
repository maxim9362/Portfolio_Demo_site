<!-- Этот файл объясняет, как развернуть AI-консультанта на сервере и подключить виджет к сайту клиента. -->

# Установка AI-чата и подключение виджета

Эта инструкция нужна, чтобы развернуть Universal AI Site Consultant на сервере и подключить чат к сайту клиента через одну строку JavaScript.

Главная идея простая: AI-чат не устанавливается внутрь WordPress, Tilda, Cloudflare Pages или обычного HTML-сайта. Он работает на отдельном FastAPI-сервере, а на сайт клиента вставляется только виджет.

## Общая схема

```text
Сайт клиента
    ↓
<script src="https://ai-client-domain.com/widget/chat-widget.js"></script>
    ↓
FastAPI backend: https://ai-client-domain.com
    ↓
PostgreSQL + ChromaDB + Gemini + админка /admin
```

Клиенту обычно передаются две вещи:

- ссылка на админку: `https://ai-client-domain.com/admin`;
- логин и временный пароль от админки.

На сайт клиента вставляется одна строка:

```html
<script src="https://ai-client-domain.com/widget/chat-widget.js"></script>
```

## Что должно быть готово

Перед подключением виджета нужно проверить:

- backend запускается без ошибок;
- `/health` возвращает `{"status": "ok"}`;
- админка открывается по адресу `/admin`;
- виджет открывается по адресу `/widget/chat-widget.js`;
- в `.env` указан `GEMINI_API_KEY`;
- в `.env` указан домен сайта клиента в `ALLOWED_ORIGINS`;
- backend работает по HTTPS, если сайт клиента тоже HTTPS;
- создан временный логин и пароль для админки.

## 1. Подготовка сервера

Подойдет обычный VPS на Ubuntu 22.04 или Ubuntu 24.04.

Минимально рекомендуется:

- 2 CPU;
- 4 GB RAM;
- 30 GB SSD;
- публичный IP;
- домен или поддомен для backend, например `ai.client-site.com`.

Подключитесь к серверу по SSH:

```bash
ssh root@SERVER_IP
```

Обновите систему:

```bash
apt update
apt upgrade -y
```

Установите базовые пакеты:

```bash
apt install -y ca-certificates curl gnupg git ufw
```

## 2. Установка Docker на сервер

Добавьте официальный Docker repository:

```bash
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
```

```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
```

Установите Docker и Docker Compose plugin:

```bash
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Проверьте установку:

```bash
docker --version
docker compose version
```

Включите автозапуск Docker:

```bash
systemctl enable docker
systemctl start docker
```

## 3. Настройка firewall

Откройте SSH, HTTP и HTTPS:

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

Порт `8000` наружу обычно открывать не нужно, если перед приложением стоит Nginx или Caddy.

## 4. Загрузка проекта на сервер

Перейдите в папку для проектов:

```bash
mkdir -p /opt/ai-chat
cd /opt/ai-chat
```

Скопируйте проект на сервер любым удобным способом.

Вариант через Git:

```bash
git clone YOUR_REPOSITORY_URL .
```

Вариант через архив:

```bash
# На локальном компьютере
scp ai-chat-project.zip root@SERVER_IP:/opt/ai-chat/

# На сервере
cd /opt/ai-chat
unzip ai-chat-project.zip
```

## 5. Настройка `.env`

Создайте `.env`:

```bash
cp .env.example .env
```

Откройте файл:

```bash
nano .env
```

Минимальные настройки:

```dotenv
APP_NAME=Universal AI Site Consultant
DEBUG=false
UVICORN_WORKERS=1

DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/ai_consultant

GEMINI_API_KEY=ваш_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash
GEMINI_FALLBACK_MODEL=gemini-2.5-flash

EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
KNOWLEDGE_DIR=knowledge
CHROMA_PATH=chroma_data
CHROMA_COLLECTION=business_knowledge
RAG_MAX_DISTANCE=0.78

ALLOWED_ORIGINS=https://client-site.com,https://www.client-site.com

ADMIN_USERNAME=admin
ADMIN_PASSWORD=временный_сложный_пароль
ADMIN_SESSION_SECRET=длинная_случайная_строка_минимум_32_символа
ADMIN_COOKIE_SECURE=true

LEAD_RETENTION_DAYS=14

SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_USE_TLS=true
EMAIL_FROM=
EMAIL_TO=client@example.com
```

Важно:

- `GEMINI_API_KEY` обязателен для ответов AI.
- `ALLOWED_ORIGINS` должен содержать домен сайта клиента.
- `EMAIL_TO` - почта клиента, куда приходят заявки.
- `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM` можно оставить пустыми, если email-уведомления пока не настроены.
- Если SMTP не настроен, заявки все равно сохраняются в админке.

В Docker Compose приложение само переопределяет `DATABASE_URL` на внутренний адрес PostgreSQL:

```text
postgresql+psycopg://postgres:postgres@postgres:5432/ai_consultant
```

Поэтому в `.env` можно оставить локальный `DATABASE_URL` из примера.

## 6. Настройка базы знаний клиента

Для нового клиента измените Markdown-файлы в папке `knowledge`.

Обычно нужно заменить:

```text
knowledge/services/...
knowledge/prices/...
knowledge/faq/...
knowledge/contacts/...
knowledge/policies/...
```

Примеры:

- для адвоката: услуги, консультации, документы, цены, ограничения юридических обещаний;
- для парикмахера: услуги, стрижки, окрашивание, цены, часы работы;
- для клиники: направления, врачи, запись, цены, правила медицинских ответов.

После изменения базы знаний нужно переиндексировать ChromaDB.

Если приложение еще не запущено, индексация произойдет автоматически при первом запуске.

Если приложение уже запущено:

```bash
docker compose exec app python scripts/ingest_knowledge.py
```

## 7. Запуск проекта

Из папки проекта выполните:

```bash
docker compose up -d --build
```

Проверить контейнеры:

```bash
docker compose ps
```

Посмотреть логи:

```bash
docker compose logs -f app
```

Проверить локально на сервере:

```bash
curl http://127.0.0.1:8000/health
```

Ожидаемый ответ:

```json
{"status":"ok"}
```

## 8. Подключение домена и HTTPS

Для реального клиента лучше использовать отдельный поддомен:

```text
ai.client-site.com
```

В DNS нужно создать `A` record:

```text
ai.client-site.com -> SERVER_IP
```

Дальше нужен reverse proxy с HTTPS. Можно использовать Nginx или Caddy.

## 9. Вариант с Nginx и Certbot

Установите Nginx и Certbot:

```bash
apt install -y nginx certbot python3-certbot-nginx
```

Создайте конфиг:

```bash
nano /etc/nginx/sites-available/ai-chat
```

Пример конфига:

```nginx
server {
    listen 80;
    server_name ai.client-site.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_buffering off;
        proxy_cache off;
    }
}
```

Активируйте сайт:

```bash
ln -s /etc/nginx/sites-available/ai-chat /etc/nginx/sites-enabled/ai-chat
nginx -t
systemctl reload nginx
```

Выпустите SSL-сертификат:

```bash
certbot --nginx -d ai.client-site.com
```

Проверьте:

```text
https://ai.client-site.com/health
https://ai.client-site.com/admin
https://ai.client-site.com/widget/chat-widget.js
```

## 10. Вариант с Caddy

Caddy проще, потому что сам выпускает HTTPS-сертификаты.

Установка:

```bash
apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
apt update
apt install -y caddy
```

Откройте Caddyfile:

```bash
nano /etc/caddy/Caddyfile
```

Пример:

```caddyfile
ai.client-site.com {
    reverse_proxy 127.0.0.1:8000
}
```

Перезапустите Caddy:

```bash
systemctl reload caddy
```

Проверьте:

```text
https://ai.client-site.com/health
https://ai.client-site.com/admin
https://ai.client-site.com/widget/chat-widget.js
```

## 11. Подключение виджета к WordPress

1. Откройте админку WordPress:

```text
https://client-site.com/wp-admin
```

2. Установите плагин для вставки кода, например WPCode или Insert Headers and Footers.

3. Откройте раздел для вставки кода в Footer.

4. Вставьте:

```html
<script src="https://ai.client-site.com/widget/chat-widget.js"></script>
```

5. Сохраните изменения.

6. Откройте сайт в новой вкладке или в режиме инкогнито.

7. Проверьте, что кнопка чата появилась в правом нижнем углу.

## 12. Подключение виджета к обычному HTML-сайту

Откройте `index.html` сайта клиента и вставьте script перед закрывающим тегом `</body>`:

```html
<body>
    ...контент сайта...

    <script src="https://ai.client-site.com/widget/chat-widget.js"></script>
</body>
```

Если сайт хранится в Git:

```bash
git add index.html
git commit -m "Add AI chat widget"
git push
```

## 13. Подключение виджета к Cloudflare Pages

Cloudflare Pages не запускает Python/FastAPI backend. Там размещается только сайт клиента.

Правильная схема:

- FastAPI backend работает на VPS;
- Cloudflare Pages показывает сайт клиента;
- в HTML сайта вставлен script виджета с VPS.

Вставьте:

```html
<script src="https://ai.client-site.com/widget/chat-widget.js"></script>
```

В `.env` backend укажите домен Cloudflare Pages:

```dotenv
ALLOWED_ORIGINS=https://client-site.pages.dev,https://client-site.com,https://www.client-site.com
```

После изменения `.env` перезапустите приложение:

```bash
docker compose down
docker compose up -d --build
```

## 14. Что передать клиенту

Клиенту не нужно давать доступ к серверу, Docker, PostgreSQL или SMTP.

Передайте:

```text
Админка: https://ai.client-site.com/admin
Логин: admin
Пароль: временный_пароль
```

И инструкцию:

```text
После первого входа откройте /admin/settings и смените логин/пароль.
Новые заявки появляются в разделе /admin/leads.
```

## 15. Финальная проверка

После установки проверьте весь путь:

1. Открыть сайт клиента.
2. Открыть чат.
3. Написать тестовый вопрос.
4. Убедиться, что AI отвечает.
5. Оставить тестовую заявку.
6. Открыть `https://ai.client-site.com/admin`.
7. Проверить, что заявка появилась.
8. Открыть карточку заявки.
9. Поменять статус заявки.
10. Проверить кнопки звонка и WhatsApp.
11. Удалить тестовую заявку, если она не нужна.

## 16. Если чат не работает

| Проблема | Что проверить |
| --- | --- |
| Чат не появился на сайте | Открывается ли `/widget/chat-widget.js`, правильно ли вставлен script, очищен ли кэш сайта. |
| Чат появился, но AI не отвечает | Проверить `GEMINI_API_KEY`, `ALLOWED_ORIGINS`, HTTPS и логи backend. |
| Браузер блокирует запросы | Сайт и backend должны быть по HTTPS, домен сайта должен быть в `ALLOWED_ORIGINS`. |
| В WordPress не видно изменений | Очистить кэш WordPress, кэш плагина, CDN-кэш, открыть сайт в инкогнито. |
| Заявка не появляется в админке | Проверить PostgreSQL, логи backend, `/admin/leads`, корректность работы `/api/chat`. |
| Email не приходит | Проверить SMTP-настройки и `EMAIL_TO`. Если SMTP пустой, заявки все равно сохраняются в админке. |

Логи приложения:

```bash
docker compose logs -f app
```

Логи PostgreSQL:

```bash
docker compose logs -f postgres
```

## 17. Обновление проекта на сервере

Если проект обновляется через Git:

```bash
cd /opt/ai-chat
git pull
docker compose up -d --build
```

Если менялась база знаний:

```bash
docker compose exec app python scripts/ingest_knowledge.py
```

## 18. Резервная копия данных

Заявки хранятся в PostgreSQL volume.

Создать backup:

```bash
docker compose exec postgres pg_dump -U postgres ai_consultant > ai_consultant_backup.sql
```

Восстановить backup:

```bash
cat ai_consultant_backup.sql | docker compose exec -T postgres psql -U postgres ai_consultant
```

## 19. Что не нужно делать

- Не вставлять backend-код внутрь WordPress.
- Не запускать Python/FastAPI на Cloudflare Pages.
- Не использовать HTTP-виджет на HTTPS-сайте.
- Не отдавать клиенту SMTP-пароли.
- Не отдавать клиенту доступ к серверу без необходимости.
- Не ставить `ALLOWED_ORIGINS=*` на production без причины.
- Не удалять `app/widget/chat-widget.js`, если нужен виджет.

## 20. Короткая версия для партнера

1. Backend AI-чата запускается на отдельном сервере.
2. На сайт клиента вставляется одна строка script.
3. Посетитель общается с AI и оставляет заявку.
4. Заявка появляется в `/admin`.
5. Клиенту передается только ссылка на админку и временный пароль.
6. Для нового клиента обычно меняются только база знаний и `EMAIL_TO`.
