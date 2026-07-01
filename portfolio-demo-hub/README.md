# Portfolio Demo Hub

Portfolio Demo Hub — монорепозиторий с основным сайтом-портфолио, PostgreSQL, админкой, аналитикой, nginx и реальными demo projects:

- `projects/ai_site_consultant` — AI_Chat_Web / Universal AI Site Consultant.
- `projects/smart_lead_form` — Smart Lead Form / Cost Calculator.

## Локальный Запуск

```bash
cp .env.example .env
docker compose up --build
```

Откройте:

- http://localhost/
- http://localhost/projects
- http://localhost/projects/ai-site-consultant
- http://localhost/projects/smart-lead-form
- http://localhost/launch/ai-site-consultant
- http://localhost/launch/smart-lead-form
- http://localhost/contact
- http://localhost/for-partners
- http://localhost/admin
- http://localhost/health

Demo URLs:

- http://localhost/demo/ai-site-consultant/
- http://localhost/admin-demo/ai-site-consultant/
- http://localhost/demo/smart-lead-form/
- http://localhost/admin-demo/smart-lead-form/

## Production Запуск

1. Скопируйте env-файлы:

```bash
cp .env.example .env
cp projects/ai_site_consultant/.env.example projects/ai_site_consultant/.env
cp projects/smart_lead_form/.env.example projects/smart_lead_form/.env
```

2. Замените все `change_me...`, домен и API-ключи на серверные значения.

3. Запустите production compose:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Production compose использует `restart: unless-stopped`, `env_file`, persistent volumes для PostgreSQL и ChromaDB, не монтирует исходный код Hub как writable volume.

## Переменные Окружения

Корневой `.env`:

```text
DATABASE_URL=postgresql+psycopg://portfolio:portfolio@postgres:5432/portfolio
POSTGRES_DB=portfolio
POSTGRES_USER=portfolio
POSTGRES_PASSWORD=change_me
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_me_strong_password
PROJECTS_ROOT=/projects
DEMO_INTERNAL_BASE_URL=http://nginx
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
SITE_NAME=Maxim AI Automation
SITE_URL=https://your-domain.com
CONTACT_TELEGRAM=your_telegram
CONTACT_EMAIL=you@example.com
CONTACT_WHATSAPP=972503213621
CONTACT_FACEBOOK=https://www.facebook.com/profile.php?id=61584187357263&locale=ru_RU
CONTACT_PHOTO_URL=/static/img/maxim-profile.jpg
```

Реальные `.env` не должны попадать в git. В репозитории хранятся только `.env.example`.

## Как Подключить Домен

1. На сервере направьте DNS A-record домена на IP сервера.
2. В `.env` укажите `SITE_URL=https://your-domain.com`.
3. В env-файлах demo projects укажите production `ALLOWED_ORIGINS`.
4. Запустите `docker compose -f docker-compose.prod.yml up -d --build`.

Nginx уже проксирует:

```text
/                                      -> portfolio_hub
/demo/ai-site-consultant/              -> ai_site_consultant
/admin-demo/ai-site-consultant/        -> ai_site_consultant/admin
/demo/smart-lead-form/                 -> smart_lead_form
/admin-demo/smart-lead-form/           -> smart_lead_form/admin
/project-assets/                       -> static assets из /projects
```

## HTTPS

Вариант 1: HTTPS через Cloudflare

1. Подключите домен к Cloudflare.
2. В DNS включите proxy для A-record.
3. На сервере оставьте nginx на порту `80`.
4. В Cloudflare SSL/TLS используйте режим `Full` или `Full (strict)`, если добавлен origin certificate.

Вариант 2: HTTPS через certbot на сервере

1. Остановите внешний reverse proxy, если он занимает 80/443.
2. Выпустите сертификат certbot для домена.
3. Добавьте отдельный nginx server block на 443 с `ssl_certificate` и `ssl_certificate_key`.
4. Оставьте текущие `location` и `proxy_set_header` правила.

На этом этапе certbot не установлен в compose намеренно.

## Как Проверить Админку

Portfolio Hub admin закрыт Basic Auth:

```text
/admin
/admin/leads
/admin/analytics
/admin/sessions
/admin/demo-sessions
/admin/projects
```

Логин и пароль берутся только из `.env`:

```text
ADMIN_USERNAME
ADMIN_PASSWORD
```

Demo admin открывается через `/launch/{project_id}`. Если открыть `/admin-demo/...` без `demo_session_id`, приложение покажет безопасное сообщение и не отдаст чужие demo data.

## Backup PostgreSQL

Backup основной базы Hub:

```bash
docker compose exec postgres pg_dump -U portfolio portfolio > backup.sql
```

Restore:

```bash
cat backup.sql | docker compose exec -T postgres psql -U portfolio portfolio
```

Если в `.env` другой пользователь или имя базы, подставьте свои значения вместо `portfolio`.

## Логи

```bash
docker compose logs -f nginx
docker compose logs -f portfolio_hub
docker compose logs -f ai_site_consultant
docker compose logs -f smart_lead_form
```

Для production:

```bash
docker compose -f docker-compose.prod.yml logs -f nginx
docker compose -f docker-compose.prod.yml logs -f portfolio_hub
docker compose -f docker-compose.prod.yml logs -f ai_site_consultant
docker compose -f docker-compose.prod.yml logs -f smart_lead_form
```

## Health Checks

```text
http://localhost/health
http://localhost/demo/ai-site-consultant/health
http://localhost/demo/smart-lead-form/health
```

Каждый endpoint должен вернуть:

```json
{"status": "ok"}
```

## Контент Проекта

Каждый проект описывается файлом:

```text
projects/<project_folder>/project.json
```

Превью:

```text
projects/ai_site_consultant/preview.png
projects/smart_lead_form/preview.png
```

На сайте используется путь через nginx:

```text
/project-assets/ai_site_consultant/preview.png
```

Если `preview_image` пустой или файл не загрузился, сайт покажет заглушку.

Если `video_url` пустой, страница проекта покажет “Видео будет добавлено позже”. Скриншоты добавляются через `screenshots`; если массив пустой, блок скрывается.

## Как Добавить Новый Проект

1. Создайте папку в `projects/`, например `projects/new_project`.
2. Добавьте реальный проект с `Dockerfile`, `requirements.txt`, `app/` и файлами запуска.
3. Добавьте `project.json` с уникальным `id`, `demo_path`, `admin_path`, `cleanup_path`.
4. Добавьте сервис проекта и, если нужно, отдельный PostgreSQL в `docker-compose.yml` и `docker-compose.prod.yml`.
5. Добавьте nginx routes `/demo/new-project/` и `/admin-demo/new-project/`.
6. Запустите `docker compose up --build`.

## Как Скрыть Проект

В `project.json` установите:

```json
{
  "is_active": false
}
```

Проект останется в папке, но исчезнет из каталога.

## Как Удалить Проект

1. Остановите compose.
2. Удалите сервис проекта из `docker-compose.yml` и `docker-compose.prod.yml`.
3. Удалите nginx routes проекта.
4. Удалите папку проекта из `projects/`, если она больше не нужна.
5. Удалите связанные Docker volumes только если данные точно не нужны.

## Security

- Реальные `.env` игнорируются git.
- Nginx добавляет базовые security headers.
- `client_max_body_size` ограничен `10M`.
- `X-Frame-Options` установлен в `SAMEORIGIN`, чтобы iframe внутри Portfolio Hub продолжал работать.
- Portfolio Hub admin требует Basic Auth.
- Demo admin ограничен текущим `demo_session_id`.

## Не Добавлено Намеренно

- Email-уведомления в Portfolio Hub.
- Alembic для Hub.
- Заглушки вместо реальных demo projects.
