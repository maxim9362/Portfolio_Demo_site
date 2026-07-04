# Maxim AI Automation - Portfolio Demo Hub

Portfolio Demo Hub - сайт-портфолио с живыми демо AI-решений, админкой, аналитикой и контактной формой.

Проект показывает, как можно добавлять к сайтам клиентов AI, автоматизацию и backend-функционал: чат-консультант, умную форму заявки, демо-доступ, просмотр заявок и базовую аналитику поведения пользователей.

## Что внутри

Основной код находится в папке:

```text
portfolio-demo-hub/
```

Внутри:

- основной сайт на FastAPI, Jinja2 и PostgreSQL;
- закрытая админка Portfolio Hub;
- nginx reverse proxy;
- Docker Compose для локального и production-запуска;
- два demo-проекта: AI Site Consultant и Smart Lead Form;
- analytics events, demo sessions и contact leads.

## Быстрый запуск

```bash
cd portfolio-demo-hub
cp .env.example .env
docker compose up --build
```

После запуска:

```text
http://localhost/
http://localhost/for-partners
http://localhost/services
http://localhost/projects
http://localhost/projects/ai-site-consultant
http://localhost/projects/smart-lead-form
http://localhost/launch/ai-site-consultant
http://localhost/launch/smart-lead-form
http://localhost/contact
http://localhost/admin
http://localhost/robots.txt
http://localhost/sitemap.xml
http://localhost/health
```

## Demo-проекты

- AI Site Consultant - AI-чат для сайта, который консультирует посетителя и собирает заявку.
- Smart Lead Form - умная форма заявки, которая превращает обычный контакт в структурированный лид.

WhatsApp-боты и отдельные мессенджер-боты в текущей версии не продаются как готовая услуга. Они могут быть добавлены позже как отдельное направление.

## GitHub

Recommended repository settings:

```text
Description: AI automation portfolio hub with live demos, admin views and analytics.
Homepage: https://your-domain.com
Topics: fastapi, postgresql, docker, nginx, ai-chatbot, automation, portfolio, lead-generation, jinja2
```

## Security

Реальные `.env`, API keys, пароли и production-секреты не должны попадать в git. В репозитории хранится только `.env.example` с безопасными примерами.

Подробная документация находится в [portfolio-demo-hub/README.md](portfolio-demo-hub/README.md).
