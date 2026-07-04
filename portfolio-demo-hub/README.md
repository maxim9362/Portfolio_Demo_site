# Portfolio Demo Hub

Portfolio Demo Hub - монорепозиторий для сайта-портфолио с живыми demo-проектами, PostgreSQL, закрытой админкой, аналитикой, контактной формой и nginx.

Главная идея проекта: показать партнёрам и клиентам не абстрактные описания, а работающие AI/automation-решения, которые можно открыть, протестировать и адаптировать под реальный бизнес.

## 1. Описание проекта

Сайт помогает презентовать AI-решения и backend-автоматизацию для сайтов, лендингов, SEO-проектов, рекламных кампаний и клиентских digital-проектов.

В текущей версии доступны:

- публичный сайт Portfolio Hub;
- страницы партнёрского позиционирования;
- каталог живых демо;
- отдельные продающие страницы проектов;
- demo wrapper с переключением между демо и админкой;
- контактная форма;
- закрытая админка Portfolio Hub;
- сбор analytics events;
- хранение заявок и demo sessions в PostgreSQL.

## 2. Для кого

Проект ориентирован на:

- веб-дизайнеров;
- WordPress-разработчиков и специалистов по конструкторам сайтов;
- SEO-специалистов;
- маркетологов;
- небольшие digital-агентства;
- локальный бизнес, которому нужны AI и автоматизация без большой внутренней разработки.

Цель - быть техническим партнёром, который добавляет к сайтам клиентов AI, backend-логику, формы, интеграции и автоматизацию.

## 3. Основные возможности

- Portfolio Hub на FastAPI.
- PostgreSQL для заявок, посетителей, аналитики и demo sessions.
- Basic Auth для админки.
- Project Loader, который читает `project.json` из папок проектов.
- nginx routes для основного сайта, demo-проектов и project assets.
- Отдельные контейнеры и базы для demo-проектов.
- Локальный запуск одной командой через Docker Compose.
- Production compose с `restart: unless-stopped` и env-файлами.
- SEO-фундамент: robots, sitemap, meta-теги и страницы решений.

## 4. Структура проекта

```text
portfolio-demo-hub/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
├── README.md
├── hub_app/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── db/
│       ├── routes/
│       ├── services/
│       ├── templates/
│       └── static/
├── nginx/
│   └── nginx.conf
├── postgres/
│   └── init/
└── projects/
    ├── ai_site_consultant/
    └── smart_lead_form/
```

## 5. Demo-проекты

### AI Site Consultant

AI-чат для сайта. Он отвечает посетителю, задаёт уточняющие вопросы, собирает имя, телефон, город, проблему и удобное время связи, а затем показывает заявку в админке.

Подходит для адаптации под сервисные бизнесы, клиники, юристов, салоны красоты, риелторов, страховых агентов и локальные услуги.

### Smart Lead Form

Умная форма заявки. Вместо простого имени и телефона клиент отвечает на нужные бизнес-вопросы: услуга, язык документа, количество страниц, город, срочность и удобное время связи.

Такой формат помогает получать не просто контакты, а понятные и структурированные заявки.

WhatsApp-боты и отдельные мессенджер-боты сейчас не считаются готовой услугой в этом проекте. Их можно развивать отдельно позже.

## 6. Локальный запуск

```bash
cp .env.example .env
docker compose up --build
```

Проверить контейнеры:

```bash
docker compose ps
```

Остановить:

```bash
docker compose down
```

Остановить и удалить локальные volumes:

```bash
docker compose down -v
```

## 7. Production-запуск

1. Создайте production `.env`:

```bash
cp .env.example .env
```

2. Замените все пароли, домен и контактные данные на реальные значения.

3. Создайте env-файлы demo-проектов, если они требуются:

```bash
cp projects/ai_site_consultant/.env.example projects/ai_site_consultant/.env
cp projects/smart_lead_form/.env.example projects/smart_lead_form/.env
```

4. Запустите production compose:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Production compose использует `restart: unless-stopped`, отдельные persistent volumes и env-переменные для основных сервисов.

## 8. Переменные окружения

Безопасный пример находится в `.env.example`.

Основные переменные:

```text
DATABASE_URL=postgresql+psycopg://portfolio:portfolio@postgres:5432/portfolio
POSTGRES_DB=portfolio
POSTGRES_USER=portfolio
POSTGRES_PASSWORD=portfolio

ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_me

PROJECTS_ROOT=/projects
DEMO_INTERNAL_BASE_URL=http://nginx

APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000

SITE_NAME=Maxim AI Automation
SITE_URL=http://localhost
CONTACT_TELEGRAM=your_telegram
CONTACT_EMAIL=you@example.com
CONTACT_WHATSAPP=972500000000
CONTACT_FACEBOOK=https://www.facebook.com/your-profile
CONTACT_PHOTO_URL=/static/img/maxim-profile.jpg
```

Для production обязательно замените `ADMIN_PASSWORD`, `POSTGRES_PASSWORD`, контакты и домен.

## 9. Основные URL

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

Прямые demo routes:

```text
http://localhost/demo/ai-site-consultant/
http://localhost/admin-demo/ai-site-consultant/
http://localhost/demo/smart-lead-form/
http://localhost/admin-demo/smart-lead-form/
```

## 10. SEO

В проекте уже есть базовый SEO-фундамент:

- мета-теги на основных страницах;
- sitemap;
- robots;
- страницы решений;
- страницы проектов;
- человекочитаемые URL.

На этом этапе намеренно не добавлены pSEO-страницы, городские страницы, блог и ивритская локализация.

## 11. Как добавить новый demo-проект

1. Создайте папку в `projects/`, например:

```text
projects/new_project/
```

2. Добавьте внутри реальный проект:

```text
Dockerfile
requirements.txt
app/
project.json
```

3. В `project.json` укажите уникальный `id`, `folder`, `demo_path`, `admin_path`, `title`, `short_description` и `is_active`.

4. Добавьте новый сервис в `docker-compose.yml` и `docker-compose.prod.yml`.

5. Добавьте nginx routes для demo и admin-demo.

6. Перезапустите проект:

```bash
docker compose up --build
```

Project Loader автоматически покажет активный проект, если `is_active` равен `true` и `project.json` валидный.

## 12. Безопасность

- Реальные `.env` не должны попадать в git.
- В git хранится только `.env.example`.
- API keys, production-пароли и личные контакты не должны храниться в публичном репозитории.
- Portfolio Hub admin защищён Basic Auth.
- Данные demo-проектов разделены по контейнерам и базам.
- `.idea` и `.vscode` игнорируются, но физически не удаляются из рабочей папки.

Если `.idea` уже была добавлена в git раньше, её нужно убрать из индекса без удаления локальной папки:

```bash
git rm -r --cached .idea
```

## 13. Что не входит в текущую версию

- Email-уведомления.
- Alembic migrations.
- Готовая продажа WhatsApp-ботов как отдельной услуги.
- pSEO и городские страницы.
- Ивритская версия.
- Блог.

## GitHub packaging

Recommended repository settings:

```text
Description: AI automation portfolio hub with live demos, admin views and analytics.
Homepage: https://your-domain.com
Topics: fastapi, postgresql, docker, nginx, ai-chatbot, automation, portfolio, lead-generation, jinja2
```

Перед публикацией проверьте:

```bash
docker compose config --quiet
docker compose up --build
```
