# Smart Lead Form / Cost Estimator

## Инструкция по запуску, VPS, домену, WordPress, админке и ценам

Актуальный guide для проекта Smart Lead Form. Проект состоит из FastAPI backend, PostgreSQL, demo-сайта, frontend widget и визуальной админки заявок.

Python/FastAPI не запускается внутри WordPress. WordPress подключает только внешний CSS/JS-виджет, а backend работает отдельно на VPS или локально через Docker.

## 1. Общая схема работы

```text
WordPress-сайт клиента или demo-сайт
↓
smart-form.css + smart-form.js
↓
https://forms.mydomain.com
↓
Nginx
↓
FastAPI backend на http://127.0.0.1:8000
↓
PostgreSQL + админка заявок
```

Что где работает:

- WordPress остается обычным сайтом.
- FastAPI, API, виджет и админка работают на сервере.
- PostgreSQL хранит заявки и данные администратора.
- Cloudflare направляет домен или поддомен на IP VPS.
- Nginx принимает HTTP/HTTPS и проксирует запросы в FastAPI.

## 2. Локальный запуск

Скопировать переменные окружения:

```bash
cp .env.example .env
```

Запустить PostgreSQL отдельно через Docker Desktop или другой удобный способ.

Параметры базы:

```text
POSTGRES_DB=smart_lead_form
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
PORT=5432
```

В `.env` для локального запуска:

```env
DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:5432/smart_lead_form
```

Запустить приложение:

```bash
docker compose up --build
```

Открыть:

- Demo page: `http://localhost:8000/widget/index.html`
- Admin page: `http://localhost:8000/widget/admin.html`
- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/health`
- Database health: `http://localhost:8000/api/health/db`

## 3. Основные переменные `.env`

```env
APP_NAME=Smart Lead Form
APP_ENV=development
DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:5432/smart_lead_form
DEFAULT_CLIENT_ID=notary_demo
OWNER_EMAIL=test@example.com
ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
ADMIN_API_KEY=change-me-admin-key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
PUBLIC_BASE_URL=http://localhost:8000
```

Важно:

- `PUBLIC_BASE_URL` используется для ссылок в startup logs.
- `ALLOWED_ORIGINS` должен включать домены, где установлен виджет.
- `ADMIN_USERNAME` и `ADMIN_PASSWORD` создают первого администратора.
- `ADMIN_API_KEY` оставлен как legacy fallback для API-проверок.
- Основной вход в админку: логин и пароль.
- Настоящий `.env` нельзя публиковать в GitHub.

## 4. Запуск на VPS

Подключиться к серверу:

```bash
ssh root@IP_ТВОЕГО_VPS
```

Установить Docker, Docker Compose plugin и Git:

```bash
sudo apt update
sudo apt install docker.io docker-compose-plugin git -y
```

Скачать проект:

```bash
cd /opt
git clone https://github.com/maxim9362/Smart-Lead-Form.git
cd Smart-Lead-Form
cp .env.example .env
nano .env
```

Запустить:

```bash
docker compose up -d --build
docker compose logs -f app
```

Проверить backend на VPS:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/health/db
```

Если PostgreSQL не запущен внутри compose, нужно запустить базу отдельно или добавить `db`-сервис в `docker-compose.yml`.

## 5. Домен и Cloudflare DNS

Рекомендуемый вариант: отдельный поддомен для форм.

Примеры:

| Вариант | Когда использовать | Пример |
|---|---|---|
| IP VPS | Только временная проверка | `http://123.123.123.123:8000` |
| Основной домен | Если домен свободен | `https://mydomain.com` |
| Поддомен | Лучший вариант | `https://forms.mydomain.com` |
| Поддомен клиента | Белый брендинг | `https://form.client-site.co.il` |

В Cloudflare:

```text
DNS → Records → Add record
Type: A
Name: forms
IPv4 address: IP_ТВОЕГО_VPS
TTL: Auto
Proxy status: DNS only для первого запуска
```

Сначала лучше использовать `DNS only`. После настройки HTTPS можно включить `Proxied`.

## 6. Nginx

Установить Nginx:

```bash
sudo apt install nginx -y
sudo systemctl status nginx
```

Создать конфиг:

```bash
sudo nano /etc/nginx/sites-available/forms.mydomain.com
```

Пример конфига:

```nginx
server {
    listen 80;
    server_name forms.mydomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Включить конфиг:

```bash
sudo ln -s /etc/nginx/sites-available/forms.mydomain.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Проверить:

```text
http://forms.mydomain.com/api/health
```

## 7. HTTPS

Установить Certbot:

```bash
sudo apt install certbot python3-certbot-nginx -y
```

Выпустить сертификат:

```bash
sudo certbot --nginx -d forms.mydomain.com
```

Проверить:

- `https://forms.mydomain.com/api/health`
- `https://forms.mydomain.com/widget/index.html`
- `https://forms.mydomain.com/widget/admin.html`
- `https://forms.mydomain.com/docs`

## 8. `.env` для VPS

Пример:

```env
APP_NAME=Smart Lead Form
APP_ENV=production
DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:5432/smart_lead_form
DEFAULT_CLIENT_ID=notary_demo
OWNER_EMAIL=test@example.com
ALLOWED_ORIGINS=https://forms.mydomain.com,https://client-site.com,https://www.client-site.com
ADMIN_API_KEY=change-me-admin-key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=strong-temporary-password
PUBLIC_BASE_URL=https://forms.mydomain.com
```

После изменения `.env`:

```bash
docker compose down
docker compose up -d --build
docker compose logs -f app
```

## 9. Подключение к WordPress

FastAPI не устанавливается в WordPress. WordPress подключает внешний виджет с VPS.

Можно использовать:

- WPCode
- Insert Headers and Footers
- Header Footer Code Manager
- HTML-блок на странице

## 9.1 Плавающая форма

Код вставить в Footer:

```html
<link rel="stylesheet" href="https://forms.mydomain.com/widget/smart-form.css">

<script>
window.SmartLeadFormConfig = {
  apiBaseUrl: "https://forms.mydomain.com",
  clientId: "notary_demo",
  mode: "floating"
};
</script>

<script src="https://forms.mydomain.com/widget/smart-form.js"></script>
```

## 9.2 Встроенная форма

На нужной странице WordPress добавить HTML-блок:

```html
<div id="smart-lead-form"></div>
```

В Footer вставить:

```html
<link rel="stylesheet" href="https://forms.mydomain.com/widget/smart-form.css">

<script>
window.SmartLeadFormConfig = {
  apiBaseUrl: "https://forms.mydomain.com",
  clientId: "notary_demo",
  mode: "embedded",
  containerId: "smart-lead-form"
};
</script>

<script src="https://forms.mydomain.com/widget/smart-form.js"></script>
```

## 10. Админка заявок

Админка:

```text
https://forms.mydomain.com/widget/admin.html
```

Что умеет:

- вход по логину и паролю;
- просмотр заявок;
- просмотр деталей заявки;
- телефон и WhatsApp-ссылка;
- смена статуса;
- удаление заявки.

Статусы:

```text
new
in_progress
done
cancelled
```

Что передать клиенту:

| Что | Пример |
|---|---|
| Ссылка на админку | `https://forms.mydomain.com/widget/admin.html` |
| Логин | `admin` или клиентский логин |
| Временный пароль | `strong-temporary-password` |
| Инструкция | Сохранить доступы в безопасном месте |

Блок настроек доступа внизу страницы сейчас не показывается. Смена логина и пароля доступна через API `PUT /api/admin/credentials`.

## 11. Как заполнять цены

Цены находятся здесь:

```text
app/clients/notary_demo/pricing_rules.json
```

Python-код менять не нужно.

Пример правила:

```json
{
  "id": "notary_translation_2_3_pages",
  "priority": 90,
  "when": {
    "service_type": "notary_translation",
    "page_count": "2_3"
  },
  "price_min": 300,
  "price_max": 700,
  "estimate_message": "Ориентировочная стоимость перевода 2-3 страниц."
}
```

Как заполнять:

- Если цена точная, `price_min` и `price_max` можно сделать одинаковыми.
- Если цена `от 250`, поставить `price_min: 250`, `price_max: null`.
- Если цену нужно уточнить, поставить `price_min: null`, `price_max: null`.
- Значения в `when` должны совпадать с `value` из `form_config.json`.

Пример:

```json
{
  "when": {
    "service_type": "power_of_attorney"
  },
  "price_min": 250,
  "price_max": null
}
```

## 12. Текущие правила формы

- Email из формы убран.
- В API поле `email` остается nullable для совместимости.
- Время связи вводится текстом, например `завтра в 12:30`.
- `12%33` не проходит как неправильный формат.
- `22:55` не проходит как нерабочее время.
- В Шабат форма сообщает, что офис закрыт.
- После успешной отправки новая заявка в этом браузере блокируется на 24 часа.
- Пользователь может изменить уже созданную заявку.

## 13. Финальная проверка после установки

Проверить:

- `https://forms.mydomain.com/api/health`
- `https://forms.mydomain.com/api/health/db`
- `https://forms.mydomain.com/widget/index.html`
- `https://forms.mydomain.com/widget/admin.html`
- WordPress-сайт, где установлен виджет.
- Создание тестовой заявки.
- Появление заявки в админке.
- Смену статуса.
- Телефон и WhatsApp-ссылку.
- Удаление тестовой заявки.

## 14. Если что-то не работает

| Проблема | Что проверить |
|---|---|
| Домен не открывается | DNS A-запись, IP VPS, порты 80/443 |
| Открывается Nginx default page | `server_name`, sites-enabled config |
| 502 Bad Gateway | FastAPI не запущен или Nginx проксирует не туда |
| HTTPS не выпускается | Сначала должен работать HTTP, DNS должен вести на VPS |
| Форма на WordPress не появилась | JS/CSS ссылки, кэш WordPress/CDN, режим инкогнито |
| Форма появилась, но не отправляет | `ALLOWED_ORIGINS`, HTTPS, `apiBaseUrl`, backend logs |
| Браузер блокирует запросы | Нельзя подключать HTTP backend на HTTPS-сайт |
| Заявка не видна в админке | PostgreSQL, `/api/health/db`, правильный `clientId` |
| Цена не показывается | `pricing_rules.json`, `price_min`, `price_max`, совпадение `value` |

## 15. Что не нужно делать

- Не загружать FastAPI/Python-код в WordPress.
- Не запускать backend на Cloudflare Pages.
- Не вставлять backend-код в WordPress theme files.
- Не подключать HTTP-виджет на HTTPS-сайте.
- Не ставить `ALLOWED_ORIGINS=*` на production.
- Не публиковать `.env` и админские пароли в GitHub.
- Не зашивать клиентские цены и нотариальную логику в Python.

