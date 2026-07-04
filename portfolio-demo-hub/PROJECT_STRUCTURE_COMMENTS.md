# Project Structure Comments

This file is a readable map of the repository. It documents files that cannot
be safely commented inline, such as JSON configs, videos, images, and generated
assets.

## Root

- `docker-compose.yml` - local development stack: Hub, nginx, Hub PostgreSQL,
  and separate PostgreSQL/app containers for each demo project.
- `docker-compose.prod.yml` - production-oriented stack with restart policies,
  env files, and persistent volumes.
- `.env.example` - public example settings. Real `.env` files must stay local.
- `.gitignore` - keeps secrets, caches, local databases, and generated artifacts
  out of git.
- `README.md` - runbook for local launch, production launch, links, backup,
  logs, and adding projects.

## nginx

- `nginx/nginx.conf` - the public entrypoint on port 80. It routes the main
  site to `portfolio_hub`, demo URLs to isolated demo containers, admin-demo
  URLs to admin pages, and `/project-assets/` to project media files.

## hub_app

- `hub_app/Dockerfile` - builds the main Portfolio Hub FastAPI container.
- `hub_app/requirements.txt` - Python dependencies for the Hub only.
- `app/main.py` - creates the FastAPI app, mounts static assets, includes
  routers, creates tables on startup, and handles 404 responses.
- `app/config.py` - reads environment settings for database, admin auth,
  public contact links, site URL, project root, and internal demo cleanup URL.

## hub_app/app/db

- `database.py` - SQLAlchemy engine/session/base for the Hub database.
- `models.py` - Hub-owned tables: contact leads, visitor sessions, analytics
  events, and wrapper-level demo sessions.

## hub_app/app/routes

- `pages.py` - public pages: home, projects, project detail, launch wrapper,
  contact, partners, robots, and sitemap.
- `api.py` - JSON endpoints for contact leads, analytics, heartbeat, demo start,
  demo finish, and demo cleanup calls.
- `admin.py` - Basic Auth admin UI for dashboard, leads, analytics, visitor
  sessions, demo sessions, and loaded projects.

## hub_app/app/services

- `project_loader.py` - reads `projects/*/project.json`, skips broken/inactive
  projects, and returns active projects sorted by `order`.
- `analytics.py` - central event recorder that updates visitor timing,
  demo timing, and appends analytics events.

## hub_app/app/templates

- `base.html` - shared public layout: meta tags, header, footer, CSS, JS.
- `index.html` - main landing page.
- `projects.html` - catalog of active projects.
- `project_card.html` - reusable card partial.
- `project_detail.html` - sales/detail page for one project.
- `launch.html` - demo iframe wrapper with Demo/Admin/New Chat/Finish controls.
- `contact.html` - public lead form.
- `for_partners.html` - partner collaboration page.
- `admin/*.html` - protected admin screens.

## hub_app/app/static

- `css/styles.css` - shared visual system for public pages, admin, and launch.
- `js/analytics.js` - browser session id, page views, heartbeats, session end.
- `js/launch.js` - iframe tab switching, new demo session, finish cleanup.
- `js/premium.js` - decorative UI effects.
- `js/reveal.js` - scroll reveal behavior.
- `js/typing.js` - hero text animation.

## projects/ai_site_consultant

- `project.json` - Hub metadata: title, text, media, demo/admin paths, CTA.
- `Dockerfile`, `requirements.txt` - isolated AI Chat demo build.
- `.env.example` - example settings for this demo service.
- `preview.*`, `video.*` - media served through `/project-assets/`.
- `app/main.py` - AI Chat FastAPI application.
- `app/api/` - chat, leads, and knowledge ingestion endpoints.
- `app/admin/` - admin UI for collected leads.
- `app/database/` - separate database connection and initialization.
- `app/models/` - AI Chat database models.
- `app/rag/` - knowledge ingestion, embeddings, and retrieval.
- `app/llm/` - LLM client integration.
- `app/services/` - chat, lead extraction, dialogue, retention, notifications.
- `knowledge/` - source knowledge base for the demo scenario.

## projects/smart_lead_form

- `project.json` - Hub metadata: title, text, media, demo/admin paths, CTA.
- `Dockerfile`, `requirements.txt` - isolated Smart Lead Form demo build.
- `.env.example` - example settings for this demo service.
- `preview.*`, `video.*` - media served through `/project-assets/`.
- `app/main.py` - Smart Lead Form FastAPI application.
- `app/api/` - form config, lead submission, admin, health endpoints.
- `app/core/` - settings, database connection, security, DB initialization.
- `app/models/` - Smart Lead Form database models.
- `app/schemas/` - request/response schemas.
- `app/services/` - form engine, pricing, lead storage, phone validation, auth.
- `widget/` - browser demo and admin static UI.

## Adding New Projects

Each new project should live in its own folder under `projects/`, with its own
`project.json`, Dockerfile, application code, and optional database service in
`docker-compose.yml`. The Hub discovers the project through `project.json`,
while nginx decides which container receives `/demo/...` and `/admin-demo/...`.
