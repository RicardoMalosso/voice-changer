(() => {
    const portuguese = {
        "Twitch triggers": "Gatilhos da Twitch",
        "Choose your voice and start audio in VCClient first. Twitch uses that voice.":
            "Escolha a voz e inicie o áudio no VCClient. A Twitch vai usar essa voz.",
        "Chat command": "Comando do chat",
        "Duration (seconds)": "Duração (segundos)",
        "Broadcaster and moderators only": "Somente streamer e moderadores",
        "Minimum Bits (0 disables)": "Mínimo de Bits (0 desativa)",
        "Channel Points reward title or ID": "Nome ou ID da recompensa de Pontos do Canal",
        "Optional": "Opcional",
        "Connect Twitch": "Conectar à Twitch",
        "Disconnect": "Desconectar",
        "Test effect": "Testar efeito",
        "Return to normal": "Voltar à voz normal",
        "Open Twitch activation page": "Abrir página de ativação da Twitch",
        "Checking Twitch status…": "Verificando conexão com a Twitch…",
        "Twitch disconnected.": "Twitch desconectada.",
        "Twitch control off.": "Controle pela Twitch desativado.",
        "Waiting for Twitch authorization…": "Aguardando autorização da Twitch…",
        "Ready. The original mic passes through between triggers.":
            "Pronto. Entre os gatilhos, o áudio do microfone passa sem efeito.",
        "Select a voice model and start audio in VCClient first.":
            "Primeiro, selecione um modelo de voz e inicie o áudio no VCClient.",
        "Disconnect Twitch before changing the trigger settings.":
            "Desconecte a Twitch antes de alterar os gatilhos.",
        "Twitch controls could not reach the local VCClient server.":
            "O painel da Twitch não conseguiu acessar o servidor local do VCClient.",
        "Enter a command such as !voice.": "Digite um comando como !voice.",
        "Twitch control is available only from this PC.":
            "O controle da Twitch só está disponível neste computador.",
        "Open the local VCClient Twitch panel.": "Abra o painel da Twitch no VCClient local.",
    };
    const patterns = [
        [/^Enter (.+) on the Twitch activation page\.$/, "Digite $1 na página de ativação da Twitch."],
        [/^Listening to #(.+)$/, "Ouvindo o chat de #$1"],
        [/^Converted voice active for (\d+) seconds\.$/, "Voz convertida ativa por $1 segundos."],
        [/^Twitch connection failed \((.+)\)\. Reconnect to retry\.$/, "Falha na conexão com a Twitch ($1). Reconecte para tentar novamente."],
        [/^Twitch disconnected\. Retrying \((.+)\)\.$/, "Twitch desconectada. Tentando novamente ($1)."],
    ];
    let language = "en-US";
    try {
        const saved = localStorage.getItem("vcclient-twitch-language");
        if (saved === "pt-BR" || saved === "en-US") language = saved;
        else if (navigator.language.toLowerCase().startsWith("pt")) language = "pt-BR";
    } catch {
        // The desktop webview may disable storage.
    }
    function translate(text) {
        if (language !== "pt-BR") return text;
        if (portuguese[text]) return portuguese[text];
        const rule = patterns.find(([pattern]) => pattern.test(text));
        return rule ? text.replace(...rule) : text;
    }

    const panel = document.createElement("details");
    panel.style.cssText = "position:fixed;right:12px;bottom:12px;z-index:10000;background:#202124;color:#fff;padding:10px;border:1px solid #777;border-radius:6px;font:14px system-ui;max-width:min(360px,90vw);max-height:80vh;overflow:auto";
    panel.innerHTML = `
        <summary data-i18n style="cursor:pointer">Twitch triggers</summary>
        <form style="display:grid;gap:8px;margin-top:10px">
            <div role="group" aria-label="Language / Idioma">
                <button type="button" data-language="pt-BR">
                    <svg aria-hidden="true" width="20" height="14" viewBox="0 0 20 14"><path fill="#009c3b" d="M0 0h20v14H0z"/><path fill="#ffdf00" d="M10 1 19 7 10 13 1 7z"/><circle fill="#002776" cx="10" cy="7" r="3.4"/><path stroke="#fff" stroke-width=".7" d="M7 6c2-.2 4 .4 6 1.8"/></svg>
                    Português
                </button>
                <button type="button" data-language="en-US">
                    <svg aria-hidden="true" width="20" height="14" viewBox="0 0 20 14"><path fill="#fff" d="M0 0h20v14H0z"/><path fill="#d80621" d="M0 0h5v14H0zM15 0h5v14h-5zM10 2l1 3 1-1-.2 3 1.7-1-.2 1.5 1 .4-3 2.2.2 1-1.2-.3V13h-.6v-2.2l-1.2.3.2-1-3-2.2 1-.4L6.5 6l1.7 1L8 4l1 1z"/></svg>
                    English
                </button>
            </div>
            <div data-i18n>Choose your voice and start audio in VCClient first. Twitch uses that voice.</div>
            <label><span data-i18n>Chat command</span> <input name="command" value="!voice" required></label>
            <label><span data-i18n>Duration (seconds)</span> <input name="duration" type="number" min="1" max="300" value="20" required></label>
            <label><input name="moderators_only" type="checkbox" checked> <span data-i18n>Broadcaster and moderators only</span></label>
            <label><span data-i18n>Minimum Bits (0 disables)</span> <input name="minimum_bits" type="number" min="0" value="0" required></label>
            <label><span data-i18n>Channel Points reward title or ID</span> <input name="reward" placeholder="Optional" data-placeholder="Optional"></label>
            <div>
                <button type="submit" data-i18n>Connect Twitch</button>
                <button type="button" data-action="disconnect" data-i18n>Disconnect</button>
            </div>
            <div>
                <button type="button" data-action="test" data-i18n>Test effect</button>
                <button type="button" data-action="normal" data-i18n>Return to normal</button>
            </div>
            <a data-i18n href="https://www.twitch.tv/activate" target="_blank" rel="noopener" style="color:#ccb9ff">Open Twitch activation page</a>
            <div data-status>Checking Twitch status…</div>
            <div data-effect></div>
            <div data-error role="alert" style="color:#ffadad"></div>
        </form>`;
    document.body.append(panel);
    const form = panel.querySelector("form");
    const status = panel.querySelector("[data-status]");
    const effect = panel.querySelector("[data-effect]");
    const error = panel.querySelector("[data-error]");
    const fields = form.elements;
    const key = "vcclient-twitch-settings";

    try {
        const saved = JSON.parse(localStorage.getItem(key) || "{}");
        for (const name of ["command", "duration", "minimum_bits", "reward"]) {
            if (saved[name] !== undefined) fields[name].value = saved[name];
        }
        if (typeof saved.moderators_only === "boolean") fields.moderators_only.checked = saved.moderators_only;
    } catch {
        // Storage is optional in the desktop webview.
    }

    let serverStatus = "Checking Twitch status…";
    let effectStatus = "";
    let errorMessage = "";
    const staticLabels = [...panel.querySelectorAll("[data-i18n]")].map(
        (element) => [element, element.textContent]
    );
    const languageButtons = [...panel.querySelectorAll("[data-language]")];

    function renderLanguage() {
        panel.lang = language;
        for (const [element, label] of staticLabels) element.textContent = translate(label);
        for (const field of panel.querySelectorAll("[data-placeholder]")) {
            field.placeholder = translate(field.dataset.placeholder);
        }
        for (const button of languageButtons) {
            button.setAttribute("aria-pressed", String(button.dataset.language === language));
        }
        status.textContent = translate(serverStatus);
        effect.textContent = translate(effectStatus);
        error.textContent = translate(errorMessage);
    }

    for (const button of languageButtons) {
        button.addEventListener("click", () => {
            language = button.dataset.language;
            try {
                localStorage.setItem("vcclient-twitch-language", language);
            } catch {
                // The selected language still applies to this window.
            }
            renderLanguage();
        });
    }
    renderLanguage();

    let busy = false;
    async function request(action) {
        if (busy) return;
        busy = true;
        try {
            const options = {};
            if (action !== "status") {
                const settings = {
                    command: fields.command.value,
                    duration: Number(fields.duration.value),
                    moderators_only: fields.moderators_only.checked,
                    minimum_bits: Number(fields.minimum_bits.value),
                    reward: fields.reward.value,
                };
                try {
                    localStorage.setItem(key, JSON.stringify(settings));
                } catch {
                    // Keep the form usable if storage is unavailable.
                }
                options.method = "POST";
                options.headers = {"Content-Type": "application/json", "X-VCClient-Twitch": "1"};
                options.body = JSON.stringify(settings);
                errorMessage = "";
            }
            const response = await fetch(`/twitch/${action}`, options);
            const data = await response.json();
            if (!response.ok) {
                const detail = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
                throw new Error(detail || "Twitch controls could not reach the local VCClient server.");
            }
            serverStatus = data.status;
            effectStatus = data.effect;
            form.querySelector('[type="submit"]').disabled = data.connected;
            form.querySelector('[data-action="disconnect"]').disabled = !data.connected;
        } catch (failure) {
            errorMessage = failure.message;
        } finally {
            renderLanguage();
            busy = false;
        }
    }

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        request("connect");
    });
    form.querySelectorAll("[data-action]").forEach((button) => {
        button.addEventListener("click", () => {
            if (button.dataset.action !== "test" || form.reportValidity()) request(button.dataset.action);
        });
    });
    panel.addEventListener("toggle", () => {
        if (panel.open) request("status");
    });
    setInterval(() => {
    const portuguese = {
        "Twitch triggers": "Gatilhos da Twitch",
        "Choose your voice and start audio in VCClient first. Twitch uses that voice.":
            "Escolha a voz e inicie o áudio no VCClient. A Twitch vai usar essa voz.",
        "Chat command": "Comando do chat",
        "Duration (seconds)": "Duração (segundos)",
        "Broadcaster and moderators only": "Somente streamer e moderadores",
        "Minimum Bits (0 disables)": "Mínimo de Bits (0 desativa)",
        "Channel Points reward title or ID": "Nome ou ID da recompensa de Pontos do Canal",
        "Optional": "Opcional",
        "Connect Twitch": "Conectar à Twitch",
        "Disconnect": "Desconectar",
        "Test effect": "Testar efeito",
        "Return to normal": "Voltar à voz normal",
        "Open Twitch activation page": "Abrir página de ativação da Twitch",
        "Checking Twitch status…": "Verificando conexão com a Twitch…",
        "Twitch disconnected.": "Twitch desconectada.",
        "Twitch control off.": "Controle pela Twitch desativado.",
        "Waiting for Twitch authorization…": "Aguardando autorização da Twitch…",
        "Ready. The original mic passes through between triggers.":
            "Pronto. Entre os gatilhos, o áudio do microfone passa sem efeito.",
        "Select a voice model and start audio in VCClient first.":
            "Primeiro, selecione um modelo de voz e inicie o áudio no VCClient.",
        "Disconnect Twitch before changing the trigger settings.":
            "Desconecte a Twitch antes de alterar os gatilhos.",
        "Twitch controls could not reach the local VCClient server.":
            "O painel da Twitch não conseguiu acessar o servidor local do VCClient.",
        "Enter a command such as !voice.": "Digite um comando como !voice.",
        "Twitch control is available only from this PC.":
            "O controle da Twitch só está disponível neste computador.",
        "Open the local VCClient Twitch panel.": "Abra o painel da Twitch no VCClient local.",
    };
    const patterns = [
        [/^Enter (.+) on the Twitch activation page\.$/, "Digite $1 na página de ativação da Twitch."],
        [/^Listening to #(.+)$/, "Ouvindo o chat de #$1"],
        [/^Converted voice active for (\d+) seconds\.$/, "Voz convertida ativa por $1 segundos."],
        [/^Twitch connection failed \((.+)\)\. Reconnect to retry\.$/, "Falha na conexão com a Twitch ($1). Reconecte para tentar novamente."],
        [/^Twitch disconnected\. Retrying \((.+)\)\.$/, "Twitch desconectada. Tentando novamente ($1)."],
    ];
    let language = "en-US";
    try {
        const saved = localStorage.getItem("vcclient-twitch-language");
        if (saved === "pt-BR" || saved === "en-US") language = saved;
        else if (navigator.language.toLowerCase().startsWith("pt")) language = "pt-BR";
    } catch {
        // The desktop webview may disable storage.
    }
    function translate(text) {
        if (language !== "pt-BR") return text;
        if (portuguese[text]) return portuguese[text];
        const rule = patterns.find(([pattern]) => pattern.test(text));
        return rule ? text.replace(...rule) : text;
    }

        if (panel.open) request("status");
    }, 1000);
})();
