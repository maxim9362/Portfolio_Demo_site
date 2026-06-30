# Portfolio Demo Hub

Монорепозиторий для портфолио с живыми demo projects, PostgreSQL, админкой, аналитикой, контактной формой и nginx.

## Как запустить

```bash
cp .env.example .env
docker compose up --build
```

После запуска nginx публикует сайт на `http://localhost/`.

## Как открыть сайт

- http://localhost/
- http://localhost/projects
- http://localhost/projects/ai-site-consultant
- http://localhost/launch/ai-site-consultant
- http://localhost/contact
- http://localhost/for-partners
- http://localhost/health

## Страницы сайта

- `/` - главная страница с описанием AI-automation услуг, проектами, аудиторией, шагами работы и CTA.
- `/projects` - каталог demo projects с карточками, нишами, статусами и быстрым запуском демо.
- `/projects/{project_id}` - продающая страница проекта: описание, видео/placeholder, польза, функции, ниши, технологии и CTA.
- `/launch/{project_id}` - demo wrapper с фиксированной панелью, переключением demo/admin iframe и завершением demo session.
- `/contact` - контактная форма для заявки на адаптацию проекта.
- `/for-partners` - страница для веб-дизайнеров, SEO-специалистов, маркетологов, WordPress-разработчиков и небольших агентств.

## Как открыть админку

Админка доступна по адресу:

- http://localhost/admin

Basic Auth берёт логин и пароль из `.env`.

Данные по умолчанию:

```text
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_me
```

## Улучшенная админка

Разделы:

- `Dashboard` - карточки статистики и последние 10 analytics events.
- `Заявки` - таблица лидов и действия `Viewed` / `Archive`.
- `Аналитика` - последние события с session/demo/project данными.
- `Демо-сессии` - статусы запусков демо, длительность, opened_demo/opened_admin.
- `Проекты` - проекты, загруженные из `projects/*/project.json`.

## Analytics events

Базовые события:

- `page_view`
- `project_view`
- `contact_open`
- `contact_submit`
- `demo_launch`
- `demo_tab_open`
- `admin_tab_open`
- `demo_finish`
- `heartbeat`
- `session_end`

События для новых CTA и страниц:

- `cta_click`
- `partner_page_view`
- `project_demo_button_click`
- `contact_button_click`

## Как добавить новый проект

1. Создайте папку внутри `projects/`, например `projects/my_project`.
2. Добавьте `project.json` с уникальным `id`, `folder`, `order`, описанием, `demo_path` и `admin_path`.
3. Если проект имеет собственное демо-приложение, добавьте его `Dockerfile` и сервис в `docker-compose.yml`.
4. Добавьте nginx-маршруты для demo/admin iframe.
5. Перезапустите стек: `docker compose up --build`.

## Как скрыть проект

В `project.json` установите:

```json
"is_active": false
```

Project Loader игнорирует такие проекты и не показывает их на сайте и в админском списке активных проектов.

## Как удалить проект

1. Остановите стек: `docker compose down`.
2. Удалите папку проекта из `projects/`.
3. Удалите его сервис из `docker-compose.yml`, если он был добавлен.
4. Удалите связанные location-блоки из `nginx/nginx.conf`.
5. Запустите стек снова: `docker compose up --build`.

## Как проверить demo/admin iframe

Подключены два реальных demo project:

- AI Site Consultant: `projects/ai_site_consultant`
- Smart Lead Form / Cost Calculator: `projects/smart_lead_form`

Для AI Site Consultant доступны:

- http://localhost/demo/ai-site-consultant/
- http://localhost/admin-demo/ai-site-consultant/
- http://localhost/demo/ai-site-consultant/health

Для Smart Lead Form доступны:

- http://localhost/demo/smart-lead-form/
- http://localhost/admin-demo/smart-lead-form/
- http://localhost/demo/smart-lead-form/health

Launch wrapper сам передаёт в iframe параметры `demo_session_id` и `session_id`:

```text
?demo_session_id=...&session_id=...
```

На странице `http://localhost/launch/ai-site-consultant` проверьте кнопки `Демо`, `Админка` и `Завершить демо`.

Для второго проекта используйте:

- http://localhost/projects/smart-lead-form
- http://localhost/launch/smart-lead-form

При завершении демо Portfolio Hub завершает свою `DemoSession` и отправляет `DELETE /demo-session/{demo_session_id}` в соответствующий demo project, чтобы очистить временные данные текущей demo session.

## Как подключены реальные проекты

Каждый проект лежит внутри `projects/` как отдельное Docker-приложение со своими файлами:

```text
Dockerfile
requirements.txt
.env.example
.env
project.json
preview.png
video.mp4
app/
```

`project.json` читает Project Loader в `hub_app`. `docker-compose.yml` собирает проекты как отдельные сервисы, а `nginx/nginx.conf` проксирует demo/admin пути в нужный контейнер.

Чтобы добавить следующий проект:

1. Создайте папку `projects/new_project`.
2. Добавьте `Dockerfile`, `requirements.txt`, `.env.example`, `.env`, `app/` и `project.json`.
3. Укажите уникальный `id`, например `new-project`.
4. Добавьте сервис в `docker-compose.yml`.
5. Добавьте nginx routes `/demo/new-project/` и `/admin-demo/new-project/`.
6. Запустите `docker compose up --build`.

## Что намеренно не добавлено

- Email-уведомления
- Alembic
## Real Demo Projects

Portfolio Demo Hub запускает реальные проекты, а не тестовые формы-заглушки:

- `projects/ai_site_consultant` - реальный проект `AI_Chat_Web` / Universal AI Site Consultant.
- `projects/smart_lead_form` - реальный проект Smart Lead Form / Cost Calculator.

Каждый demo project запускается как отдельное Docker-приложение. Основные файлы проектов лежат в корне их папок:

```text
app/
knowledge/ или widget/
scripts/
Dockerfile
requirements.txt
.env.example
README.md
project.json
```

Проверка после `docker compose up --build`:

- `http://localhost/demo/ai-site-consultant/`
- `http://localhost/launch/ai-site-consultant`
- `http://localhost/demo/smart-lead-form/`
- `http://localhost/launch/smart-lead-form`

AI demo должно показывать реальный лендинг AI_Chat_Web с подключенным AI-чатом, а не страницу `Demo session` с простой формой. Smart demo должно показывать реальный Smart Lead Form с `SmartLeadFormConfig`, а не тестовую форму.

Базы PostgreSQL разделены:

- `portfolio` - таблицы Portfolio Hub.
- `ai_consultant` - таблицы AI_Chat_Web.
- `smart_lead_form` - таблицы Smart Lead Form.
