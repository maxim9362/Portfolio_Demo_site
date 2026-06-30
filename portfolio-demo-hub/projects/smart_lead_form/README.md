# Smart Lead Form / Cost Estimator

## Что это

Универсальный backend + frontend widget для умной пошаговой формы заявки. Первый demo-сценарий — нотариальные услуги.

Проект сделан как reusable-template: Python-код остается общим, а вопросы, тексты интерфейса и правила предварительной оценки лежат в JSON-конфигах клиента.

## Для чего

- собрать качественную заявку;
- предварительно классифицировать обращение;
- показать ориентировочную стоимость или сообщение, что цену нужно уточнить;
- сохранить лид в PostgreSQL;
- подготовить уведомление владельцу бизнеса через stub в логах.

## Demo niche

`notary_demo` — форма заявки для нотариуса.

Конфиги находятся в:

- `app/clients/notary_demo/form_config.json`
- `app/clients/notary_demo/pricing_rules.json`
- `app/clients/notary_demo/ui_texts.json`

## Что умеет MVP

- пошаговая форма;
- условные вопросы `show_if` / `show_if_any`;
- предварительная оценка стоимости по JSON rules;
- сохранение заявок;
- защита от повторной новой заявки в течение 24 часов;
- редактирование уже созданной заявки из виджета;
- валидация израильского телефона;
- проверка удобного времени связи с учетом рабочих часов и Шабата;
- email notification stub в лог;
- embeddable widget через `script`;
- CORS через `.env`;
- раздача widget-файлов через backend.
- визуальная admin page с логином/паролем, списком заявок, статусами и удалением.

## Что не входит в MVP

- AI;
- юридическая консультация;
- загрузка документов;
- онлайн-оплата;
- настоящая SMTP-отправка;
- WordPress-плагин.

## Stack

- Python 3.12
- FastAPI
- PostgreSQL
- SQLAlchemy
- Pydantic
- Vanilla JS
- Docker Compose

## Структура проекта

- `app/api` — HTTP endpoints: health, form API, leads API, admin auth API.
- `app/models` — SQLAlchemy модели `Lead`, `FormSession`, `AdminUser`.
- `app/services` — reusable-сервисы: form engine, pricing engine, lead service, phone validation, admin auth, email stub.
- `app/clients/notary_demo` — JSON-конфиги первого demo-клиента.
- `app/core` — настройки, database session, init_db, security-заглушка.
- `app/schemas` — Pydantic-схемы API.
- `widget` — demo site, embeddable frontend widget и admin page на vanilla HTML/CSS/JS.
- `migrations` — зарезервировано для будущих миграций.

## Быстрый запуск

Скопируйте пример окружения:

```bash
cp .env.example .env
```

Запустите PostgreSQL отдельно в Docker Desktop. Нужны параметры:

```text
POSTGRES_DB=smart_lead_form
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
PORT=5432
```

Compose в этом проекте запускает только FastAPI app. Контейнер приложения подключается к вашей отдельно запущенной БД через:

```env
DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:5432/smart_lead_form
```

Запустите приложение:

```bash
docker compose up --build
```

Приложение будет доступно на:

```text
http://localhost:8000
```

## Startup links

После запуска:

```bash
docker compose up --build
```

В консоли будут показаны полезные ссылки:

- demo page;
- admin page.

Базовый URL задается в `.env`:

```env
PUBLIC_BASE_URL=http://localhost:8000
```

## Проверка backend

Health check:

```text
GET http://localhost:8000/api/health
```

Database health check:

```text
GET http://localhost:8000/api/health/db
```

Ожидаемый ответ для базы:

```json
{
  "status": "ok",
  "database": "connected"
}
```

## Проверка формы

Откройте:

```text
http://localhost:8000/widget/index.html
```

Сценарий:

- выбрать `Нотариальный перевод`;
- выбрать `Русский → Иврит`;
- выбрать `1 страница`;
- заполнить контакты;
- указать удобное время, например `завтра в 12:30`;
- получить оценку `150–250 ₪`;
- отправить заявку.

После успешной отправки в этом же браузере новая заявка блокируется на 24 часа. Пользователь увидит сообщение, что заявка уже создана, и сможет изменить существующую заявку.

Время связи:

- можно писать `завтра в 12:30`;
- `12%33` не пройдет как неправильный формат;
- `22:55` не пройдет как нерабочее время;
- в Шабат форма сообщает, что офис закрыт.

## Проверка API

Получить конфиг формы:

```bash
curl "http://localhost:8000/api/form/config?client_id=notary_demo"
```

Рассчитать стоимость:

```bash
curl -X POST "http://localhost:8000/api/form/calculate" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "notary_demo",
    "scenario_key": "notary_request",
    "answers": {
      "service_type": "notary_translation",
      "page_count": "1"
    }
  }'
```

Создать заявку:

```bash
curl -X POST "http://localhost:8000/api/leads" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "notary_demo",
    "scenario_key": "notary_request",
    "service_type": "notary_translation",
    "language_pair": "ru_he",
    "page_count": "1",
    "urgency": "1_2_days",
    "meeting_format": "phone",
    "city": "ashdod",
    "documents_ready": "scan",
    "name": "Максим",
    "phone": "0541234567",
    "email": null,
    "preferred_contact_time": "завтра в 12:30",
    "comment": "Нужен перевод свидетельства",
    "estimated_price_min": 150,
    "estimated_price_max": 250,
    "currency": "₪",
    "estimate_message": "Ориентировочная стоимость нотариального перевода одной страницы.",
    "disclaimer": "Стоимость является ориентировочной. Точная цена определяется нотариусом после проверки документов и уточнения деталей.",
    "answers": {
      "service_type": "notary_translation",
      "language_pair": "ru_he",
      "page_count": "1",
      "urgency": "1_2_days",
      "meeting_format": "phone",
      "city": "ashdod",
      "documents_ready": "scan"
    }
  }'
```

Войти в админку:

```bash
curl -X POST "http://localhost:8000/api/admin/login" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "notary_demo",
    "username": "admin",
    "password": "admin123"
  }'
```

Получить заявки через Bearer token из ответа login:

```bash
curl "http://localhost:8000/api/leads?client_id=notary_demo" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Подключение виджета на сайт

```html
<link rel="stylesheet" href="https://your-domain.com/widget/smart-form.css">

<script>
  window.SmartLeadFormConfig = {
    apiBaseUrl: "https://your-domain.com",
    clientId: "notary_demo"
  };
</script>

<script src="https://your-domain.com/widget/smart-form.js"></script>
```

Widget-файлы раздаются backend-ом:

- `http://localhost:8000/widget/index.html`
- `http://localhost:8000/widget/smart-form.js`
- `http://localhost:8000/widget/smart-form.css`

## Настройка CORS

В `.env`:

```env
ALLOWED_ORIGINS=https://client-site.com,https://www.client-site.com
```

Для локального теста:

```env
ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

## Admin

Визуальная админка:

```text
http://localhost:8000/widget/admin.html
```

Локальные demo-доступы из `.env.example`:

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

Визуальная админка сейчас предназначена для работы с заявками: просмотр, статусы и удаление. Блок настроек доступа внизу страницы не показывается.

Смена логина и пароля доступна через API `PUT /api/admin/credentials` после входа. Новые данные сохраняются в PostgreSQL.

`GET /api/leads` защищен Bearer token из `/api/admin/login`.

Legacy fallback `X-Admin-Api-Key` пока оставлен для локальных API-проверок, но основной способ входа — логин/пароль через admin page.

В `.env`:

```env
ADMIN_API_KEY=your-strong-secret-key
```

Для локального запуска из `.env.example` используется:

```env
ADMIN_API_KEY=change-me-admin-key
```

Проверка:

```bash
curl -X POST "http://localhost:8000/api/admin/login" \
  -H "Content-Type: application/json" \
  -d '{"client_id":"notary_demo","username":"admin","password":"admin123"}'
```

Важно: `POST /api/leads` остается публичным для виджета. Не храните admin credentials или `ADMIN_API_KEY` во frontend-коде и не публикуйте `.env` в GitHub.

## Как адаптировать под нового клиента

Создайте новую папку:

```text
app/clients/client_name/
```

Добавьте туда:

```text
form_config.json
pricing_rules.json
ui_texts.json
```

Затем подключайте виджет с:

```js
clientId: "client_name"
```

Python-код менять не нужно, если сценарий помещается в существующую логику `steps`, `show_if`, `show_if_any` и pricing `rules`.

## Production notes

- заменить `ADMIN_API_KEY` на длинный случайный ключ;
- заменить demo admin username/password;
- не хранить admin credentials во frontend;
- не публиковать `.env` в GitHub;
- заменить email stub на SMTP или другой approved email provider;
- настроить HTTPS;
- ограничить CORS доменами клиента;
- добавить rate limiting;
- добавить нормальные миграции вместо `Base.metadata.create_all`;
- не хранить документы на MVP.
