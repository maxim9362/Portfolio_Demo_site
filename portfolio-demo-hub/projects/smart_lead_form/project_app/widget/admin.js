// Visual admin page for login and lead management.

(function () {
  "use strict";

  var config = window.SmartLeadAdminConfig || {};
  var apiBaseUrl = config.apiBaseUrl || "http://localhost:8000";
  var sessionStorageKey = "smartLeadAdminSession";
  var statusLabels = {
    new: "Новая",
    in_progress: "В работе",
    done: "Готово",
    cancelled: "Отменена"
  };

  var labels = {
    service_type: {
      notary_translation: "Нотариальный перевод",
      signature_verification: "Заверение подписи",
      power_of_attorney: "Доверенность",
      affidavit: "Аффидевит / декларация",
      document_copy: "Копия документа",
      apostille: "Апостиль",
      consultation: "Консультация",
      other: "Другое"
    },
    language_pair: {
      ru_he: "Русский → Иврит",
      he_ru: "Иврит → Русский",
      en_he: "Английский → Иврит",
      he_en: "Иврит → Английский",
      other: "Другой вариант"
    },
    page_count: {
      "1": "1 страница",
      "2_3": "2–3 страницы",
      "4_10": "4–10 страниц",
      "10_plus": "Больше 10 страниц",
      unknown: "Пока не знаю"
    },
    urgency: {
      today: "Сегодня",
      "1_2_days": "В течение 1–2 дней",
      this_week: "На этой неделе",
      not_urgent: "Не срочно"
    },
    meeting_format: {
      office: "Прийти в офис",
      phone: "Сначала консультация по телефону",
      online: "Онлайн-консультация"
    },
    city: {
      ashdod: "Ашдод",
      ashkelon: "Ашкелон",
      tel_aviv: "Тель-Авив",
      rishon_lezion: "Ришон-ле-Цион",
      jerusalem: "Иерусалим",
      other: "Другой город"
    },
    documents_ready: {
      ready: "Да, документы на руках",
      scan: "Есть фото или скан",
      need_consultation: "Нет, нужна консультация",
      not_sure: "Не уверен"
    }
  };

  var fieldTitles = {
    service_type: "Услуга",
    language_pair: "Языковая пара",
    page_count: "Страницы",
    urgency: "Срочность",
    meeting_format: "Формат связи",
    city: "Город",
    documents_ready: "Документы",
    name: "Имя",
    phone: "Телефон",
    email: "Email",
    preferred_contact_time: "Удобное время",
    comment: "Комментарий",
    created_at: "Создано",
    estimated_price_min: "Стоимость"
  };

  var state = {
    token: "",
    clientId: config.clientId || "",
    username: "",
    leads: [],
    selectedId: null
  };

  var elements = {};

  function createElement(tagName, className, text) {
    var element = document.createElement(tagName);
    if (className) {
      element.className = className;
    }
    if (text !== undefined && text !== null) {
      element.textContent = text;
    }
    return element;
  }

  function apiUrl(path) {
    return apiBaseUrl.replace(/\/$/, "") + path;
  }

  function authHeaders() {
    return {
      Authorization: "Bearer " + state.token
    };
  }

  function requestJson(path, options) {
    return fetch(apiUrl(path), options).then(function (response) {
      return response.json().catch(function () {
        return {};
      }).then(function (data) {
        if (!response.ok) {
          throw new Error(data.detail || data.message || "Ошибка запроса");
        }
        return data;
      });
    });
  }

  function setStatus(message, type) {
    elements.status.textContent = message;
    elements.status.className = "notice";
    if (type === "success") {
      elements.status.classList.add("notice--success");
    } else if (type === "error") {
      elements.status.classList.add("notice--error");
    }
  }

  function saveSession() {
    try {
      window.sessionStorage.setItem(sessionStorageKey, JSON.stringify({
        token: state.token,
        clientId: state.clientId,
        username: state.username
      }));
    } catch (error) {
      // Session storage is optional; the current page can still keep working.
    }
  }

  function readSession() {
    try {
      return JSON.parse(window.sessionStorage.getItem(sessionStorageKey) || "{}");
    } catch (error) {
      return {};
    }
  }

  function clearSession() {
    state.token = "";
    state.username = "";
    state.leads = [];
    state.selectedId = null;
    try {
      window.sessionStorage.removeItem(sessionStorageKey);
    } catch (error) {
      // Ignore storage errors.
    }
  }

  function showLoggedIn() {
    elements.loginPanel.classList.add("is-hidden");
    elements.content.classList.remove("is-hidden");
    elements.logoutButton.classList.remove("is-hidden");
    elements.currentUser.textContent = state.username;
  }

  function showLoggedOut() {
    elements.loginPanel.classList.remove("is-hidden");
    elements.content.classList.add("is-hidden");
    elements.logoutButton.classList.add("is-hidden");
    elements.total.textContent = "0";
    elements.list.replaceChildren();
    elements.detail.replaceChildren();
  }

  function formatValue(group, value) {
    if (value === null || value === undefined || value === "") {
      return "—";
    }

    if (labels[group] && labels[group][value]) {
      return labels[group][value];
    }

    return String(value);
  }

  function formatDate(value) {
    if (!value) {
      return "—";
    }

    var date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return date.toLocaleString("ru-RU", {
      dateStyle: "short",
      timeStyle: "short"
    });
  }

  function formatPrice(lead) {
    if (lead.estimated_price_min !== null && lead.estimated_price_max !== null) {
      return lead.estimated_price_min + "–" + lead.estimated_price_max + " " + (lead.currency || "₪");
    }

    if (lead.estimated_price_min !== null) {
      return "от " + lead.estimated_price_min + " " + (lead.currency || "₪");
    }

    return "Уточнить";
  }

  function renderEmptyList(message) {
    var empty = createElement("section", "empty-state");
    empty.appendChild(createElement("h2", "", "Заявок пока нет"));
    empty.appendChild(createElement("p", "", message));
    elements.list.replaceChildren(empty);
    elements.detail.replaceChildren();
  }

  function createStatusBadge(status) {
    var safeStatus = statusLabels[status] ? status : "new";
    return createElement("span", "status status--" + safeStatus, statusLabels[safeStatus]);
  }

  function renderLeadRow(lead) {
    var row = createElement("tr");
    row.dataset.leadId = String(lead.id);

    if (state.selectedId === lead.id) {
      row.classList.add("is-selected");
    }

    function cell(label, content) {
      var tableCell = createElement("td");
      tableCell.setAttribute("data-label", label);
      if (typeof content === "string") {
        tableCell.textContent = content;
      } else {
        tableCell.appendChild(content);
      }
      return tableCell;
    }

    var clientCell = createElement("div");
    clientCell.appendChild(createElement("strong", "", lead.name || "Без имени"));
    clientCell.appendChild(createElement("span", "table-muted", lead.phone || "Телефон не указан"));
    if (lead.email) {
      clientCell.appendChild(createElement("span", "table-muted", lead.email));
    }

    var requestCell = createElement("div");
    requestCell.appendChild(createElement("strong", "", formatValue("service_type", lead.service_type)));
    requestCell.appendChild(createElement("span", "table-muted table-muted--wrap", formatPrice(lead)));

    var actions = createElement("div", "row-actions");
    var openButton = createElement("button", "icon-link", "Открыть");
    openButton.type = "button";
    openButton.addEventListener("click", function (event) {
      event.stopPropagation();
      state.selectedId = lead.id;
      renderList();
      renderDetails(lead);
    });
    actions.appendChild(openButton);

    if (lead.phone) {
      var phoneLink = createElement("a", "icon-link", "Позвонить");
      phoneLink.href = "tel:" + lead.phone;
      actions.appendChild(phoneLink);
    }

    row.appendChild(cell("ID", "#" + lead.id));
    row.appendChild(cell("Дата", formatDate(lead.created_at)));
    row.appendChild(cell("Клиент", clientCell));
    row.appendChild(cell("Город", formatValue("city", lead.city)));
    row.appendChild(cell("Услуга", requestCell));
    row.appendChild(cell("Время связи", formatValue("preferred_contact_time", lead.preferred_contact_time)));
    row.appendChild(cell("Статус", createStatusBadge(lead.status)));
    row.appendChild(cell("Действия", actions));

    row.addEventListener("click", function () {
      state.selectedId = lead.id;
      renderList();
      renderDetails(lead);
    });

    return row;
  }

  function renderList() {
    elements.total.textContent = String(state.leads.length);

    if (!state.leads.length) {
      renderEmptyList("Заявок пока нет.");
      return;
    }

    var table = createElement("table", "leads-table");
    var thead = createElement("thead");
    var headRow = createElement("tr");
    ["ID", "Дата", "Клиент", "Город", "Услуга", "Время связи", "Статус", "Действия"].forEach(function (label) {
      headRow.appendChild(createElement("th", "", label));
    });
    thead.appendChild(headRow);

    var tbody = createElement("tbody");
    state.leads.forEach(function (lead) {
      tbody.appendChild(renderLeadRow(lead));
    });
    table.appendChild(thead);
    table.appendChild(tbody);
    elements.list.replaceChildren(table);
  }

  function addDetailRow(container, key, value) {
    var row = createElement("div");
    row.appendChild(createElement("dt", "", fieldTitles[key] || key));
    row.appendChild(createElement("dd", "", value));
    container.appendChild(row);
  }

  function renderAnswers(container, answers) {
    if (!answers || !Object.keys(answers).length) {
      return;
    }

    var block = createElement("div", "conversation-list");
    container.appendChild(createElement("div", "section-heading"));
    container.querySelector(".section-heading").appendChild(createElement("h2", "", "Все ответы"));
    container.querySelector(".section-heading").appendChild(createElement("span", "", String(Object.keys(answers).length)));

    Object.keys(answers).forEach(function (key) {
      var message = createElement("article", "conversation-message conversation-message--user");
      var header = createElement("header");
      header.appendChild(createElement("strong", "", fieldTitles[key] || key));
      message.appendChild(header);
      message.appendChild(createElement("p", "", formatValue(key, answers[key])));
      block.appendChild(message);
    });

    container.appendChild(block);
  }

  function renderDetails(lead) {
    var fragment = document.createDocumentFragment();
    var heading = createElement("section", "page-heading page-heading--detail");
    var headingText = createElement("div");

    headingText.appendChild(createElement("button", "back-link", "↑ К списку заявок"));
    headingText.querySelector("button").type = "button";
    headingText.querySelector("button").addEventListener("click", function () {
      elements.list.scrollIntoView({ behavior: "smooth" });
    });
    headingText.appendChild(createElement("h1", "", "Заявка #" + lead.id));
    headingText.appendChild(createElement("p", "", "Создана " + formatDate(lead.created_at)));
    heading.appendChild(headingText);
    heading.appendChild(createStatusBadge(lead.status));
    fragment.appendChild(heading);

    var layout = createElement("div", "detail-layout");
    var mainSection = createElement("section", "detail-section");
    var actionsSection = createElement("aside", "detail-section detail-section--actions");

    mainSection.appendChild(createElement("h2", "", "Контакт и задача"));

    var summary = createElement("dl", "detail-grid");
    addDetailRow(summary, "phone", formatValue("phone", lead.phone));
    addDetailRow(summary, "email", formatValue("email", lead.email));
    addDetailRow(summary, "preferred_contact_time", formatValue("preferred_contact_time", lead.preferred_contact_time));
    addDetailRow(summary, "city", formatValue("city", lead.city));
    addDetailRow(summary, "urgency", formatValue("urgency", lead.urgency));
    addDetailRow(summary, "meeting_format", formatValue("meeting_format", lead.meeting_format));
    addDetailRow(summary, "language_pair", formatValue("language_pair", lead.language_pair));
    addDetailRow(summary, "page_count", formatValue("page_count", lead.page_count));
    addDetailRow(summary, "documents_ready", formatValue("documents_ready", lead.documents_ready));
    addDetailRow(summary, "created_at", formatDate(lead.created_at));
    addDetailRow(summary, "estimated_price_min", formatPrice(lead));
    addDetailRow(summary, "comment", formatValue("comment", lead.comment));
    mainSection.appendChild(summary);

    if (lead.estimate_message || lead.disclaimer) {
      var estimate = createElement("div", "notice notice--success");
      if (lead.estimate_message) {
        estimate.appendChild(createElement("p", "", lead.estimate_message));
      }
      if (lead.disclaimer) {
        estimate.appendChild(createElement("p", "", lead.disclaimer));
      }
      mainSection.appendChild(estimate);
    }

    var contactActions = createElement("div", "contact-actions");
    if (lead.phone) {
      var call = createElement("a", "button button--primary", "Позвонить");
      call.href = "tel:" + lead.phone;
      contactActions.appendChild(call);
    }
    if (lead.phone) {
      var whatsapp = createElement("a", "button button--secondary", "WhatsApp");
      whatsapp.href = "https://wa.me/" + lead.phone.replace(/\D/g, "");
      whatsapp.target = "_blank";
      whatsapp.rel = "noopener noreferrer";
      contactActions.appendChild(whatsapp);
    }
    mainSection.appendChild(contactActions);

    actionsSection.appendChild(createElement("h2", "", "Обработка"));
    var statusField = createElement("label", "field");
    statusField.appendChild(createElement("span", "", "Статус заявки"));
    var statusSelect = createElement("select");
    Object.keys(statusLabels).forEach(function (statusValue) {
      var option = createElement("option", "", statusLabels[statusValue]);
      option.value = statusValue;
      option.selected = lead.status === statusValue;
      statusSelect.appendChild(option);
    });
    statusField.appendChild(statusSelect);

    var saveStatusButton = createElement("button", "button button--primary button--wide", "Сохранить статус");
    saveStatusButton.type = "button";
    saveStatusButton.addEventListener("click", function () {
      updateLeadStatus(lead, statusSelect.value);
    });

    var deleteButton = createElement("button", "button button--danger button--wide", "Удалить заявку");
    deleteButton.type = "button";
    deleteButton.addEventListener("click", function () {
      deleteLead(lead);
    });

    actionsSection.appendChild(statusField);
    actionsSection.appendChild(saveStatusButton);
    actionsSection.appendChild(deleteButton);

    layout.appendChild(mainSection);
    layout.appendChild(actionsSection);
    fragment.appendChild(layout);

    var answersSection = createElement("section", "conversation-section");
    renderAnswers(answersSection, lead.answers_json);
    fragment.appendChild(answersSection);
    elements.detail.replaceChildren(fragment);
  }

  function loadLeads() {
    if (!state.token) {
      setStatus("Сначала войдите в админку.", "error");
      return;
    }

    elements.loadButton.disabled = true;
    setStatus("Загружаем заявки...", "loading");

    requestJson("/api/leads?client_id=" + encodeURIComponent(state.clientId) + "&limit=100", {
      headers: authHeaders()
    })
      .then(function (data) {
        state.leads = data.items || [];
        state.selectedId = state.leads.length ? state.leads[0].id : null;
        renderList();
        if (state.leads.length) {
          renderDetails(state.leads[0]);
        } else {
          elements.detail.replaceChildren(createElement("div", "admin-empty-state", "Заявок пока нет."));
        }
        setStatus("Заявки загружены: " + state.leads.length + ".", "success");
      })
      .catch(function (error) {
        setStatus(error.message || "Не удалось загрузить заявки.", "error");
      })
      .finally(function () {
        elements.loadButton.disabled = false;
      });
  }

  function login() {
    var clientId = state.clientId;
    var username = elements.username.value.trim();
    var password = elements.password.value;

    if (!username || !password) {
      setStatus("Введите логин и пароль.", "error");
      return;
    }

    elements.loginButton.disabled = true;
    setStatus("Входим...", "loading");

    requestJson("/api/admin/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        client_id: clientId || null,
        username: username,
        password: password
      })
    })
      .then(function (data) {
        state.token = data.access_token;
        state.clientId = data.client_id;
        state.username = data.username;
        elements.password.value = "";
        saveSession();
        showLoggedIn();
        setStatus("Вход выполнен.", "success");
        loadLeads();
      })
      .catch(function (error) {
        setStatus(error.message || "Не удалось войти.", "error");
      })
      .finally(function () {
        elements.loginButton.disabled = false;
      });
  }

  function logout() {
    clearSession();
    showLoggedOut();
    setStatus("Вы вышли из админки.", "success");
  }

  function findLeadIndex(leadId) {
    return state.leads.findIndex(function (item) {
      return item.id === leadId;
    });
  }

  function updateLeadStatus(lead, statusValue) {
    setStatus("Сохраняем статус...", "loading");

    requestJson("/api/leads/" + encodeURIComponent(lead.id) + "/status", {
      method: "PATCH",
      headers: Object.assign({
        "Content-Type": "application/json"
      }, authHeaders()),
      body: JSON.stringify({
        status: statusValue
      })
    })
      .then(function (data) {
        var index = findLeadIndex(lead.id);
        if (index >= 0) {
          state.leads[index].status = data.status;
          renderList();
          renderDetails(state.leads[index]);
        }
        setStatus("Статус обновлен.", "success");
      })
      .catch(function (error) {
        setStatus(error.message || "Не удалось обновить статус.", "error");
      });
  }

  function deleteLead(lead) {
    if (!window.confirm("Удалить заявку #" + lead.id + "?")) {
      return;
    }

    setStatus("Удаляем заявку...", "loading");

    requestJson("/api/leads/" + encodeURIComponent(lead.id), {
      method: "DELETE",
      headers: authHeaders()
    })
      .then(function () {
        state.leads = state.leads.filter(function (item) {
          return item.id !== lead.id;
        });
        state.selectedId = state.leads.length ? state.leads[0].id : null;
        renderList();
        if (state.leads.length) {
          renderDetails(state.leads[0]);
        } else {
          elements.detail.replaceChildren();
        }
        setStatus("Заявка удалена.", "success");
      })
      .catch(function (error) {
        setStatus(error.message || "Не удалось удалить заявку.", "error");
      });
  }

  function restoreSession() {
    var saved = readSession();
    if (!saved.token) {
      showLoggedOut();
      return;
    }

    state.token = saved.token;
    state.clientId = saved.clientId || state.clientId;
    state.username = saved.username || "";
    showLoggedIn();
    loadLeads();
  }

  function init() {
    elements.loginPanel = document.getElementById("admin-login-panel");
    elements.content = document.getElementById("admin-content");
    elements.username = document.getElementById("admin-username");
    elements.password = document.getElementById("admin-password");
    elements.loginButton = document.getElementById("admin-login-button");
    elements.currentUser = document.getElementById("admin-current-user");
    elements.loadButton = document.getElementById("admin-load-button");
    elements.logoutButton = document.getElementById("admin-logout-button");
    elements.status = document.getElementById("admin-status");
    elements.total = document.getElementById("admin-total");
    elements.list = document.getElementById("admin-leads-list");
    elements.detail = document.getElementById("admin-detail-panel");

    elements.username.value = "admin";
    elements.loginButton.addEventListener("click", login);
    elements.loadButton.addEventListener("click", loadLeads);
    elements.logoutButton.addEventListener("click", logout);

    [elements.password, elements.username].forEach(function (input) {
      input.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
          login();
        }
      });
    });

    renderList();
    restoreSession();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
