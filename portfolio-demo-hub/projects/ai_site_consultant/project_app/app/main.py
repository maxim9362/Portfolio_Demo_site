from collections import defaultdict
from datetime import datetime
from html import escape
from typing import Any

from fastapi import FastAPI, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI(title="Universal AI Site Consultant")

demo_storage: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
    lambda: {"messages": [], "leads": []}
)

KNOWLEDGE_SNIPPETS = {
    "цена": "Стоимость зависит от ниши, объёма базы знаний и интеграций. Обычно сначала согласуют сценарий и список услуг.",
    "заявка": "Я могу собрать имя, телефон, email, город, интересующую услугу и удобное время для связи.",
    "wordpress": "Виджет можно встроить на WordPress, Tilda, Wix или обычный сайт через небольшой script-код.",
    "услуги": "Демо показывает консультацию по услугам, сбор заявки и просмотр истории в demo admin.",
}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def answer_for(message: str) -> str:
    lowered = message.lower()
    for keyword, answer in KNOWLEDGE_SNIPPETS.items():
        if keyword in lowered:
            return answer
    return (
        "AI-консультант отвечает по базе знаний компании, уточняет задачу и помогает оставить заявку. "
        "Для демо попробуйте спросить про цену, заявку, WordPress или услуги."
    )


def shell(title: str, body: str) -> str:
    return f"""
    <!doctype html>
    <html lang="ru">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>{escape(title)}</title>
      <style>
        :root {{ --bg:#f5f7fb; --ink:#14212f; --muted:#68778a; --line:#dce4ee; --primary:#0f7a6c; }}
        * {{ box-sizing: border-box; }}
        body {{ margin:0; background:var(--bg); color:var(--ink); font-family:Inter,ui-sans-serif,system-ui,"Segoe UI",sans-serif; }}
        main {{ margin:0 auto; max-width:1040px; padding:28px 18px; }}
        .layout {{ display:grid; grid-template-columns:minmax(0,1.1fr) minmax(280px,.9fr); gap:18px; }}
        .panel {{ background:#fff; border:1px solid var(--line); border-radius:8px; padding:20px; box-shadow:0 10px 28px rgba(31,48,69,.06); }}
        h1,h2 {{ margin:0 0 10px; line-height:1.1; }}
        p {{ color:var(--muted); }}
        label {{ display:grid; gap:6px; font-weight:800; margin-top:12px; }}
        input,select,textarea {{ border:1px solid var(--line); border-radius:8px; font:inherit; padding:11px 12px; width:100%; }}
        button {{ background:var(--primary); border:0; border-radius:8px; color:#fff; cursor:pointer; font:inherit; font-weight:850; margin-top:14px; padding:11px 16px; }}
        .messages {{ display:grid; gap:10px; max-height:430px; overflow:auto; padding-right:4px; }}
        .msg {{ border-radius:8px; padding:12px; }}
        .user {{ background:#eef3f8; }}
        .assistant {{ background:#e8f5f2; }}
        .meta {{ color:var(--muted); font-size:.82rem; margin-top:6px; }}
        table {{ border-collapse:collapse; width:100%; min-width:720px; }}
        th,td {{ border-bottom:1px solid var(--line); padding:9px; text-align:left; vertical-align:top; }}
        .table-wrap {{ overflow:auto; }}
        @media (max-width:760px) {{ .layout {{ grid-template-columns:1fr; }} }}
      </style>
    </head>
    <body><main>{body}</main></body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
def demo(demo_session_id: str = Query(default="default"), session_id: str | None = None) -> HTMLResponse:
    session = demo_storage[demo_session_id]
    messages = "".join(
        f"<div class='msg {escape(item['role'])}'><strong>{escape(item['label'])}</strong><p>{escape(item['text'])}</p><div class='meta'>{escape(item['created_at'])}</div></div>"
        for item in session["messages"]
    )
    body = f"""
    <h1>Universal AI Site Consultant</h1>
    <p>Demo session: {escape(demo_session_id)}</p>
    <div class="layout">
      <section class="panel">
        <h2>AI-чат</h2>
        <div class="messages">{messages or "<p>Напишите первое сообщение AI-консультанту.</p>"}</div>
        <form method="post" action="/demo/ai-site-consultant/message?demo_session_id={escape(demo_session_id)}&session_id={escape(session_id or '')}">
          <label>Ваш вопрос
            <textarea name="message" rows="4" required placeholder="Например: сколько стоит внедрение?"></textarea>
          </label>
          <button type="submit">Отправить вопрос</button>
        </form>
      </section>
      <aside class="panel">
        <h2>Оставить заявку</h2>
        <form method="post" action="/demo/ai-site-consultant/lead?demo_session_id={escape(demo_session_id)}&session_id={escape(session_id or '')}">
          <label>Имя<input name="name" required></label>
          <label>Телефон<input name="phone" required></label>
          <label>Email<input name="email" type="email"></label>
          <label>Город<input name="city"></label>
          <label>Интересующая услуга
            <select name="service">
              <option>AI-консультант для сайта</option>
              <option>Интеграция с WhatsApp</option>
              <option>Demo admin и аналитика</option>
            </select>
          </label>
          <label>Удобное время<input name="preferred_time" placeholder="Например: завтра после 14:00"></label>
          <button type="submit">Сохранить заявку</button>
        </form>
      </aside>
    </div>
    """
    return HTMLResponse(shell("Universal AI Site Consultant", body))


@app.post("/message", response_class=HTMLResponse)
def add_message(
    demo_session_id: str = Query(default="default"),
    session_id: str | None = None,
    message: str = Form(...),
) -> RedirectResponse:
    session = demo_storage[demo_session_id]
    session["messages"].append({"role": "user", "label": "Посетитель", "text": message, "created_at": now()})
    session["messages"].append({"role": "assistant", "label": "AI-консультант", "text": answer_for(message), "created_at": now()})
    return RedirectResponse(f"/demo/ai-site-consultant/?demo_session_id={demo_session_id}&session_id={session_id or ''}", status_code=303)


@app.post("/lead", response_class=HTMLResponse)
def add_lead(
    demo_session_id: str = Query(default="default"),
    session_id: str | None = None,
    name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(default=""),
    city: str = Form(default=""),
    service: str = Form(default=""),
    preferred_time: str = Form(default=""),
) -> RedirectResponse:
    demo_storage[demo_session_id]["leads"].append(
        {
            "name": name,
            "phone": phone,
            "email": email,
            "city": city,
            "service": service,
            "preferred_time": preferred_time,
            "session_id": session_id or "",
            "created_at": now(),
        }
    )
    return RedirectResponse(f"/demo/ai-site-consultant/?demo_session_id={demo_session_id}&session_id={session_id or ''}", status_code=303)


@app.get("/admin", response_class=HTMLResponse)
def admin(demo_session_id: str = Query(default="default"), session_id: str | None = None) -> HTMLResponse:
    session = demo_storage[demo_session_id]
    message_rows = "".join(
        f"<tr><td>{escape(item['created_at'])}</td><td>{escape(item['label'])}</td><td>{escape(item['text'])}</td></tr>"
        for item in session["messages"]
    )
    lead_rows = "".join(
        f"<tr><td>{escape(item['created_at'])}</td><td>{escape(item['name'])}</td><td>{escape(item['phone'])}</td><td>{escape(item['email'])}</td><td>{escape(item['city'])}</td><td>{escape(item['service'])}</td><td>{escape(item['preferred_time'])}</td></tr>"
        for item in session["leads"]
    )
    body = f"""
    <h1>Demo admin: AI Site Consultant</h1>
    <p>Данные только для demo_session_id: {escape(demo_session_id)}</p>
    <section class="panel">
      <h2>Заявки</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Дата</th><th>Имя</th><th>Телефон</th><th>Email</th><th>Город</th><th>Услуга</th><th>Время</th></tr></thead>
        <tbody>{lead_rows or "<tr><td colspan='7'>Заявок пока нет.</td></tr>"}</tbody>
      </table></div>
    </section>
    <section class="panel" style="margin-top:18px">
      <h2>История диалога</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Дата</th><th>Автор</th><th>Сообщение</th></tr></thead>
        <tbody>{message_rows or "<tr><td colspan='3'>Сообщений пока нет.</td></tr>"}</tbody>
      </table></div>
    </section>
    """
    return HTMLResponse(shell("AI Site Consultant Admin", body))


@app.delete("/demo-session/{demo_session_id}")
def delete_demo_session(demo_session_id: str) -> dict[str, bool]:
    demo_storage.pop(demo_session_id, None)
    return {"success": True}
