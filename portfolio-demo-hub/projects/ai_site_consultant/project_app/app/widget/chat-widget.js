// Этот файл создает автономный плавающий AI-чат на WordPress и других сайтах.

(function initializeUniversalAiSiteConsultantWidget() {
    "use strict";

    if (document.querySelector("[data-uaisc-widget]")) {
        return;
    }

    const widgetScript = document.currentScript
        || Array.from(document.scripts).find((scriptElement) => (
            scriptElement.src.includes("/widget/chat-widget.js")
        ));
    if (!widgetScript?.src) {
        console.error("UAISC: не удалось определить адрес backend.");
        return;
    }

    const backendBaseUrl = new URL(widgetScript.src, document.baseURI).origin;
    const chatEndpoint = `${backendBaseUrl}/api/chat`;
    const sessionStorageKey = `uaisc_session_id:${backendBaseUrl}`;
    const reducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)",
    ).matches;

    function createSessionId() {
        if (globalThis.crypto?.randomUUID) {
            return globalThis.crypto.randomUUID();
        }

        const randomPart = Math.random().toString(36).slice(2);
        return `uaisc-${Date.now()}-${randomPart}`;
    }

    function getSessionId() {
        try {
            const storedSessionId = localStorage.getItem(sessionStorageKey);
            if (storedSessionId) {
                return storedSessionId;
            }

            const newSessionId = createSessionId();
            localStorage.setItem(sessionStorageKey, newSessionId);
            return newSessionId;
        } catch (storageError) {
            console.warn("UAISC: localStorage недоступен.", storageError);
            return createSessionId();
        }
    }

    function mountWidget() {
        const widgetHost = document.createElement("div");
        widgetHost.dataset.uaiscWidget = "true";
        const widgetShadow = widgetHost.attachShadow({mode: "open"});
        const widgetSessionId = getSessionId();

        const widgetStyles = document.createElement("style");
        widgetStyles.textContent = `
            :host {
                all: initial;
                color-scheme: light;
                font-family: Inter, "Segoe UI", system-ui, -apple-system, sans-serif;
            }

            *, *::before, *::after {
                box-sizing: border-box;
            }

            button, textarea {
                font: inherit;
            }

            .uaisc-root {
                --uaisc-green: #156b62;
                --uaisc-green-dark: #0f5b53;
                --uaisc-blue: #1e67c4;
                --uaisc-text: #17202b;
                --uaisc-muted: #687483;
                position: fixed;
                right: 24px;
                bottom: 24px;
                z-index: 2147483000;
                color: var(--uaisc-text);
                line-height: 1.45;
                letter-spacing: 0;
            }

            .uaisc-launcher {
                min-width: 172px;
                height: 54px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 9px;
                padding: 0 17px;
                color: #fff;
                background: var(--uaisc-green);
                border: 1px solid var(--uaisc-green-dark);
                border-radius: 8px;
                box-shadow: 0 12px 30px rgb(20 42 52 / 24%);
                cursor: pointer;
                font-size: 14px;
                font-weight: 700;
                transition: transform 150ms ease, opacity 150ms ease;
            }

            .uaisc-launcher:hover {
                background: var(--uaisc-green-dark);
                transform: translateY(-1px);
            }

            .uaisc-launcher-mark {
                width: 28px;
                height: 28px;
                display: grid;
                place-items: center;
                color: var(--uaisc-green);
                background: #fff;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 900;
            }

            .uaisc-panel {
                position: absolute;
                right: 0;
                bottom: 0;
                width: min(390px, calc(100vw - 48px));
                height: min(580px, calc(100vh - 48px));
                min-height: 480px;
                display: grid;
                grid-template-rows: auto 1fr auto;
                overflow: hidden;
                background: #fff;
                border: 1px solid #d5dce4;
                border-radius: 8px;
                box-shadow: 0 22px 60px rgb(20 34 46 / 22%);
                transform-origin: right bottom;
                animation: uaisc-panel-in 180ms ease-out both;
            }

            .uaisc-panel[hidden] {
                display: none;
            }

            .uaisc-root.uaisc-open .uaisc-launcher {
                opacity: 0;
                pointer-events: none;
                transform: scale(0.94);
            }

            .uaisc-header {
                min-height: 68px;
                display: flex;
                align-items: center;
                gap: 11px;
                padding: 12px 13px;
                background: #fff;
                border-bottom: 1px solid #e2e7ec;
            }

            .uaisc-brand {
                width: 40px;
                height: 40px;
                flex: 0 0 40px;
                display: grid;
                place-items: center;
                color: #fff;
                background: var(--uaisc-green);
                border-radius: 8px;
                font-size: 12px;
                font-weight: 800;
            }

            .uaisc-heading {
                min-width: 0;
                flex: 1;
            }

            .uaisc-title {
                margin: 0;
                font-size: 15px;
                font-weight: 760;
            }

            .uaisc-status {
                display: flex;
                align-items: center;
                gap: 6px;
                margin-top: 3px;
                color: var(--uaisc-muted);
                font-size: 12px;
            }

            .uaisc-status-dot {
                width: 7px;
                height: 7px;
                border-radius: 50%;
                background: #22a06b;
                box-shadow: 0 0 0 3px #dff4ea;
            }

            .uaisc-close {
                width: 36px;
                height: 36px;
                display: grid;
                place-items: center;
                padding: 0;
                color: #52606f;
                background: #fff;
                border: 1px solid #ccd4dc;
                border-radius: 6px;
                cursor: pointer;
                font-size: 22px;
                line-height: 1;
            }

            .uaisc-close:hover {
                color: var(--uaisc-text);
                background: #f4f6f8;
            }

            .uaisc-messages {
                display: flex;
                flex-direction: column;
                gap: 14px;
                overflow-y: auto;
                overscroll-behavior: contain;
                padding: 17px 14px 24px;
                background: #f5f7f9;
                scrollbar-width: thin;
                scrollbar-color: #c3ccd5 transparent;
            }

            .uaisc-message-row {
                width: 100%;
                display: flex;
                align-items: flex-end;
                gap: 8px;
            }

            .uaisc-message-row-user {
                justify-content: flex-end;
            }

            .uaisc-avatar {
                width: 28px;
                height: 28px;
                flex: 0 0 28px;
                display: grid;
                place-items: center;
                color: #fff;
                background: var(--uaisc-green);
                border-radius: 7px;
                font-size: 9px;
                font-weight: 800;
            }

            .uaisc-message {
                width: fit-content;
                max-width: 82%;
                min-height: 40px;
                padding: 10px 12px;
                border-radius: 8px;
                white-space: pre-wrap;
                overflow-wrap: anywhere;
                font-size: 14px;
                animation: uaisc-message-in 160ms ease-out both;
            }

            .uaisc-message-assistant {
                color: #26313d;
                background: #fff;
                border: 1px solid #dce2e8;
                border-bottom-left-radius: 3px;
                box-shadow: 0 3px 12px rgb(28 41 54 / 6%);
            }

            .uaisc-message-user {
                color: #fff;
                background: var(--uaisc-blue);
                border: 1px solid #1559ac;
                border-bottom-right-radius: 3px;
            }

            .uaisc-message-error {
                color: #9c2f35;
                background: #fff0f1;
                border-color: #ecc5c8;
            }

            .uaisc-message-typing {
                width: auto;
                display: flex;
                align-items: center;
                gap: 7px;
                color: #778391;
                font-size: 13px;
            }

            .uaisc-typing-dots {
                display: inline-flex;
                gap: 3px;
            }

            .uaisc-typing-dot {
                width: 5px;
                height: 5px;
                border-radius: 50%;
                background: #84909d;
                animation: uaisc-typing 1s ease-in-out infinite;
            }

            .uaisc-typing-dot:nth-child(2) {
                animation-delay: 120ms;
            }

            .uaisc-typing-dot:nth-child(3) {
                animation-delay: 240ms;
            }

            .uaisc-form {
                padding: 10px;
                background: #fff;
                border-top: 1px solid #e2e7ec;
            }

            .uaisc-composer {
                min-height: 50px;
                display: grid;
                grid-template-columns: minmax(0, 1fr) 40px;
                align-items: end;
                gap: 8px;
                padding: 4px 4px 4px 12px;
                background: #f7f9fb;
                border: 1px solid #cbd4dd;
                border-radius: 8px;
            }

            .uaisc-composer:focus-within {
                border-color: #558ccf;
                box-shadow: 0 0 0 3px rgb(30 103 196 / 10%);
            }

            .uaisc-input {
                width: 100%;
                max-height: 110px;
                min-height: 40px;
                resize: none;
                padding: 9px 0 7px;
                color: var(--uaisc-text);
                background: transparent;
                border: 0;
                outline: 0;
                line-height: 1.4;
                overflow-y: auto;
                font-size: 14px;
            }

            .uaisc-input::placeholder {
                color: #8994a1;
            }

            .uaisc-send {
                width: 40px;
                height: 40px;
                display: grid;
                place-items: center;
                padding: 0;
                color: #fff;
                background: var(--uaisc-green);
                border: 1px solid var(--uaisc-green-dark);
                border-radius: 7px;
                cursor: pointer;
                font-size: 21px;
                line-height: 1;
            }

            .uaisc-send:disabled {
                cursor: wait;
                opacity: 0.52;
            }

            .uaisc-launcher:focus-visible,
            .uaisc-close:focus-visible,
            .uaisc-send:focus-visible,
            .uaisc-input:focus-visible {
                outline: 3px solid rgb(30 103 196 / 22%);
                outline-offset: 2px;
            }

            @keyframes uaisc-panel-in {
                from { opacity: 0; transform: translateY(8px) scale(0.98); }
                to { opacity: 1; transform: translateY(0) scale(1); }
            }

            @keyframes uaisc-message-in {
                from { opacity: 0; transform: translateY(4px); }
                to { opacity: 1; transform: translateY(0); }
            }

            @keyframes uaisc-typing {
                0%, 60%, 100% { opacity: 0.35; transform: translateY(0); }
                30% { opacity: 1; transform: translateY(-2px); }
            }

            @media (max-width: 520px) {
                .uaisc-root {
                    right: 12px;
                    bottom: 12px;
                    left: 12px;
                }

                .uaisc-launcher {
                    min-width: 54px;
                    float: right;
                    padding: 0 13px;
                }

                .uaisc-launcher-label {
                    display: none;
                }

                .uaisc-panel {
                    position: fixed;
                    top: 12px;
                    right: 12px;
                    bottom: 12px;
                    left: 12px;
                    width: auto;
                    height: auto;
                    min-height: 0;
                }

                .uaisc-message {
                    max-width: 86%;
                }
            }

            @media (prefers-reduced-motion: reduce) {
                *, *::before, *::after {
                    animation-duration: 1ms !important;
                    animation-iteration-count: 1 !important;
                    scroll-behavior: auto !important;
                }
            }
        `;

        const widgetRoot = document.createElement("div");
        widgetRoot.className = "uaisc-root";
        widgetRoot.innerHTML = `
            <button
                class="uaisc-launcher"
                type="button"
                aria-label="Открыть AI-консультант"
                aria-expanded="false"
            >
                <span class="uaisc-launcher-mark" aria-hidden="true">AI</span>
                <span class="uaisc-launcher-label">AI-консультант</span>
            </button>
            <section
                class="uaisc-panel"
                aria-label="AI-консультант"
                hidden
            >
                <header class="uaisc-header">
                    <div class="uaisc-brand" aria-hidden="true">AI</div>
                    <div class="uaisc-heading">
                        <h2 class="uaisc-title">AI-консультант</h2>
                        <div class="uaisc-status">
                            <span class="uaisc-status-dot" aria-hidden="true"></span>
                            Онлайн
                        </div>
                    </div>
                    <button
                        class="uaisc-close"
                        type="button"
                        aria-label="Закрыть чат"
                        title="Закрыть"
                    >×</button>
                </header>
                <div class="uaisc-messages" aria-live="polite"></div>
                <form class="uaisc-form">
                    <div class="uaisc-composer">
                        <textarea
                            class="uaisc-input"
                            rows="1"
                            maxlength="4000"
                            placeholder="Напишите ваш вопрос..."
                            aria-label="Ваш вопрос"
                            required
                        ></textarea>
                        <button
                            class="uaisc-send"
                            type="submit"
                            aria-label="Отправить"
                            title="Отправить"
                        >↑</button>
                    </div>
                </form>
            </section>
        `;

        widgetShadow.append(widgetStyles, widgetRoot);
        document.body.append(widgetHost);

        const launcherButton = widgetShadow.querySelector(".uaisc-launcher");
        const widgetPanel = widgetShadow.querySelector(".uaisc-panel");
        const closeButton = widgetShadow.querySelector(".uaisc-close");
        const messagesArea = widgetShadow.querySelector(".uaisc-messages");
        const messageForm = widgetShadow.querySelector(".uaisc-form");
        const messageInput = widgetShadow.querySelector(".uaisc-input");
        const sendButton = widgetShadow.querySelector(".uaisc-send");

        function scrollMessages() {
            messagesArea.scrollTop = messagesArea.scrollHeight;
        }

        function addMessage(content, role, isError = false) {
            const messageRow = document.createElement("div");
            messageRow.className = (
                `uaisc-message-row uaisc-message-row-${role}`
            );

            if (role === "assistant") {
                const assistantAvatar = document.createElement("div");
                assistantAvatar.className = "uaisc-avatar";
                assistantAvatar.setAttribute("aria-hidden", "true");
                assistantAvatar.textContent = "AI";
                messageRow.append(assistantAvatar);
            }

            const messageBubble = document.createElement("div");
            messageBubble.className = (
                `uaisc-message uaisc-message-${role}`
            );
            if (isError) {
                messageBubble.classList.add("uaisc-message-error");
            }
            messageBubble.textContent = content;
            messageRow.append(messageBubble);
            messagesArea.append(messageRow);
            scrollMessages();
            return messageBubble;
        }

        function addTypingMessage() {
            const typingMessage = addMessage("", "assistant");
            typingMessage.classList.add("uaisc-message-typing");

            const typingLabel = document.createElement("span");
            typingLabel.textContent = "Печатает";
            const typingDots = document.createElement("span");
            typingDots.className = "uaisc-typing-dots";
            for (let dotIndex = 0; dotIndex < 3; dotIndex += 1) {
                const typingDot = document.createElement("span");
                typingDot.className = "uaisc-typing-dot";
                typingDots.append(typingDot);
            }
            typingMessage.append(typingLabel, typingDots);
            return typingMessage;
        }

        function createTextAnimator(messageBubble) {
            let textQueue = "";
            let renderingPromise = null;
            let textStarted = false;

            function prepareText() {
                if (textStarted) {
                    return;
                }
                textStarted = true;
                messageBubble.classList.remove("uaisc-message-typing");
                messageBubble.replaceChildren();
            }

            async function renderQueue() {
                prepareText();
                while (textQueue.length > 0) {
                    const batchSize = textQueue.length > 300
                        ? 6
                        : textQueue.length > 120
                            ? 3
                            : 1;
                    const textPart = textQueue.slice(0, batchSize);
                    textQueue = textQueue.slice(batchSize);
                    messageBubble.textContent += textPart;
                    scrollMessages();

                    if (!reducedMotion) {
                        await new Promise((resolveAnimation) => {
                            window.setTimeout(resolveAnimation, 13);
                        });
                    }
                }
                renderingPromise = null;
            }

            function push(text) {
                textQueue += text;
                if (reducedMotion) {
                    prepareText();
                    messageBubble.textContent += textQueue;
                    textQueue = "";
                    scrollMessages();
                    return;
                }
                if (!renderingPromise) {
                    renderingPromise = renderQueue();
                }
            }

            async function finish() {
                if (renderingPromise) {
                    await renderingPromise;
                }
            }

            return {
                push,
                finish,
                hasText: () => (
                    textStarted && Boolean(messageBubble.textContent)
                ),
            };
        }

        function parseSseEvent(eventBlock) {
            let eventName = "message";
            const dataLines = [];

            for (const eventLine of eventBlock.split(/\r?\n/)) {
                if (eventLine.startsWith("event:")) {
                    eventName = eventLine.slice(6).trim();
                } else if (eventLine.startsWith("data:")) {
                    dataLines.push(eventLine.slice(5).trimStart());
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

        async function readStreamingResponse(response, textAnimator) {
            if (!response.body) {
                throw new Error("Streaming не поддерживается браузером.");
            }

            const streamReader = response.body.getReader();
            const streamDecoder = new TextDecoder();
            let streamBuffer = "";

            while (true) {
                const {value, done} = await streamReader.read();
                streamBuffer += streamDecoder.decode(
                    value || new Uint8Array(),
                    {stream: !done},
                );
                const eventBlocks = streamBuffer.split(/\r?\n\r?\n/);
                streamBuffer = eventBlocks.pop() || "";

                for (const eventBlock of eventBlocks) {
                    if (!eventBlock.trim()) {
                        continue;
                    }
                    const parsedEvent = parseSseEvent(eventBlock);
                    if (parsedEvent?.name === "token") {
                        textAnimator.push(parsedEvent.data.text);
                    } else if (parsedEvent?.name === "error") {
                        throw new Error(parsedEvent.data.message);
                    }
                }

                if (done) {
                    break;
                }
            }

            if (streamBuffer.trim()) {
                const finalEvent = parseSseEvent(streamBuffer);
                if (finalEvent?.name === "token") {
                    textAnimator.push(finalEvent.data.text);
                } else if (finalEvent?.name === "error") {
                    throw new Error(finalEvent.data.message);
                }
            }
            await textAnimator.finish();
        }

        function resizeInput() {
            messageInput.style.height = "auto";
            messageInput.style.height = (
                `${Math.min(messageInput.scrollHeight, 110)}px`
            );
        }

        function openWidget() {
            widgetPanel.hidden = false;
            widgetRoot.classList.add("uaisc-open");
            launcherButton.setAttribute("aria-expanded", "true");
            window.setTimeout(() => messageInput.focus(), 50);
        }

        function closeWidget() {
            widgetPanel.hidden = true;
            widgetRoot.classList.remove("uaisc-open");
            launcherButton.setAttribute("aria-expanded", "false");
            launcherButton.focus();
        }

        launcherButton.addEventListener("click", openWidget);
        closeButton.addEventListener("click", closeWidget);
        window.addEventListener("uaisc:open", (openEvent) => {
            openWidget();

            const suggestedMessage = openEvent.detail?.message?.trim();
            if (suggestedMessage) {
                messageInput.value = suggestedMessage;
                resizeInput();
                messageInput.focus();
            }
        });
        messageInput.addEventListener("input", resizeInput);
        messageInput.addEventListener("keydown", (keyboardEvent) => {
            if (keyboardEvent.key === "Enter" && !keyboardEvent.shiftKey) {
                keyboardEvent.preventDefault();
                messageForm.requestSubmit();
            }
        });

        messageForm.addEventListener("submit", async (submitEvent) => {
            submitEvent.preventDefault();
            const userMessage = messageInput.value.trim();
            if (!userMessage) {
                return;
            }

            addMessage(userMessage, "user");
            messageInput.value = "";
            resizeInput();
            messageInput.disabled = true;
            sendButton.disabled = true;
            let assistantMessage = null;

            try {
                const chatResponse = await fetch(chatEndpoint, {
                    method: "POST",
                    mode: "cors",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        session_id: widgetSessionId,
                        message: userMessage,
                    }),
                });
                if (!chatResponse.ok) {
                    throw new Error(`Backend returned ${chatResponse.status}`);
                }

                assistantMessage = addTypingMessage();
                const textAnimator = createTextAnimator(assistantMessage);
                await readStreamingResponse(chatResponse, textAnimator);
                if (!textAnimator.hasText()) {
                    assistantMessage.parentElement.remove();
                    assistantMessage = null;
                }
            } catch (chatError) {
                console.error("UAISC: ошибка чата.", chatError);
                const errorText = (
                    "Не удалось получить ответ. Попробуйте еще раз."
                );
                if (assistantMessage) {
                    assistantMessage.className = (
                        "uaisc-message uaisc-message-assistant "
                        + "uaisc-message-error"
                    );
                    assistantMessage.textContent = errorText;
                } else {
                    addMessage(errorText, "assistant", true);
                }
            } finally {
                messageInput.disabled = false;
                sendButton.disabled = false;
                messageInput.focus();
            }
        });

        addMessage(
            "Здравствуйте! Я AI-консультант. Чем могу помочь?",
            "assistant",
        );
    }

    if (document.body) {
        mountWidget();
    } else {
        document.addEventListener("DOMContentLoaded", mountWidget, {once: true});
    }
}());
