// Этот файл управляет интерфейсом чата, SSE-потоком и анимацией набора текста.

const form = document.querySelector("#chat-form");
const input = document.querySelector("#message");
const messages = document.querySelector("#messages");
const submitButton = form.querySelector("button[type='submit']");
const newChatButton = document.querySelector("#new-chat");
const reduceMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
).matches;

const sessionId = getSessionId();

function createSessionId() {
    if (globalThis.crypto?.randomUUID) {
        return globalThis.crypto.randomUUID();
    }

    const randomPart = Math.random().toString(36).slice(2);
    return `session-${Date.now()}-${randomPart}`;
}

function getSessionId() {
    try {
        const savedSessionId = localStorage.getItem("chat_session_id");

        if (savedSessionId) {
            return savedSessionId;
        }

        const newSessionId = createSessionId();
        localStorage.setItem("chat_session_id", newSessionId);
        return newSessionId;
    } catch (error) {
        console.warn("Не удалось использовать localStorage", error);
        return createSessionId();
    }
}

function scrollMessages() {
    messages.scrollTop = messages.scrollHeight;
}

function addMessage(content, role, isError = false) {
    const group = document.createElement("div");
    group.className = `message-group message-group--${role}`;

    if (role === "assistant") {
        const avatar = document.createElement("div");
        avatar.className = "message-avatar";
        avatar.setAttribute("aria-hidden", "true");
        avatar.textContent = "AI";
        group.append(avatar);
    }

    const message = document.createElement("div");
    message.className = `message message--${role}`;

    if (isError) {
        message.classList.add("message--error");
    }

    message.textContent = content;
    group.append(message);
    messages.append(group);
    scrollMessages();
    return message;
}

function addTypingMessage() {
    const message = addMessage("", "assistant");
    message.classList.add("message--typing");
    message.append(document.createElement("span"));
    return message;
}

function createTextAnimator(message) {
    let queue = "";
    let rendering = null;
    let hasStarted = false;

    function prepareForText() {
        if (hasStarted) {
            return;
        }

        hasStarted = true;
        message.classList.remove("message--typing");
        message.replaceChildren();
    }

    async function renderQueue() {
        prepareForText();

        while (queue.length > 0) {
            const batchSize = queue.length > 480
                ? 8
                : queue.length > 180
                    ? 4
                    : 1;
            const part = queue.slice(0, batchSize);
            queue = queue.slice(batchSize);
            message.textContent += part;
            scrollMessages();

            if (!reduceMotion) {
                const endsSentence = /[.!?]\s?$/.test(part);
                await new Promise((resolve) => {
                    window.setTimeout(resolve, endsSentence ? 38 : 14);
                });
            }
        }

        rendering = null;
    }

    function push(text) {
        queue += text;

        if (reduceMotion) {
            prepareForText();
            message.textContent += queue;
            queue = "";
            scrollMessages();
            return;
        }

        if (!rendering) {
            rendering = renderQueue();
        }
    }

    async function finish() {
        if (rendering) {
            await rendering;
        }
    }

    return {
        push,
        finish,
        hasText: () => hasStarted && Boolean(message.textContent),
    };
}

function readSseEvent(block) {
    let eventName = "message";
    const dataLines = [];

    for (const line of block.split(/\r?\n/)) {
        if (line.startsWith("event:")) {
            eventName = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
            dataLines.push(line.slice(5).trimStart());
        }
    }

    if (dataLines.length === 0) {
        return null;
    }

    return {
        name: eventName,
        data: JSON.parse(dataLines.join("\n")),
    };
}

function handleSseEvent(event, animator) {
    if (event.name === "token") {
        animator.push(event.data.text);
        return;
    }

    if (event.name === "error") {
        throw new Error(event.data.message || "Ошибка генерации ответа");
    }
}

async function streamResponse(response, animator) {
    if (!response.body) {
        throw new Error("Браузер не поддерживает потоковые ответы");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
        const {value, done} = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), {stream: !done});

        const blocks = buffer.split(/\r?\n\r?\n/);
        buffer = blocks.pop() || "";

        for (const block of blocks) {
            if (!block.trim()) {
                continue;
            }

            const event = readSseEvent(block);
            if (event) {
                handleSseEvent(event, animator);
            }
        }

        if (done) {
            break;
        }
    }

    if (buffer.trim()) {
        const event = readSseEvent(buffer);
        if (event) {
            handleSseEvent(event, animator);
        }
    }

    await animator.finish();
}

function resizeInput() {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 132)}px`;
}

input.addEventListener("input", resizeInput);

input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
    }
});

newChatButton.addEventListener("click", () => {
    try {
        localStorage.removeItem("chat_session_id");
    } catch (error) {
        console.warn("Не удалось очистить session_id", error);
    }

    window.location.reload();
});

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const content = input.value.trim();
    if (!content) {
        return;
    }

    addMessage(content, "user");
    input.value = "";
    resizeInput();
    input.disabled = true;
    submitButton.disabled = true;

    let assistantMessage = null;

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                session_id: sessionId,
                message: content,
            }),
        });

        if (!response.ok) {
            const errorBody = await response.json().catch(() => null);
            throw new Error(
                errorBody?.detail || `Backend returned ${response.status}`,
            );
        }

        assistantMessage = addTypingMessage();
        const animator = createTextAnimator(assistantMessage);
        await streamResponse(response, animator);

        if (!animator.hasText()) {
            assistantMessage.parentElement.remove();
            assistantMessage = null;
        }
    } catch (error) {
        console.error(error);
        const errorText = error.message || "Не удалось отправить сообщение.";

        if (assistantMessage) {
            assistantMessage.classList.remove("message--typing");
            assistantMessage.replaceChildren();
            assistantMessage.textContent = errorText;
            assistantMessage.classList.add("message--error");
        } else {
            addMessage(errorText, "assistant", true);
        }
    } finally {
        input.disabled = false;
        submitButton.disabled = false;
        input.focus();
    }
});

window.addEventListener("error", (event) => {
    console.error("Ошибка интерфейса чата", event.error || event.message);
});
