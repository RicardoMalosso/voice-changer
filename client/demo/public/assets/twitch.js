(() => {
    const panel = document.createElement("details");
    panel.style.cssText = "position:fixed;right:12px;bottom:12px;z-index:10000;background:#202124;color:#fff;padding:10px;border:1px solid #777;border-radius:6px;font:14px system-ui;max-width:min(360px,90vw);max-height:80vh;overflow:auto";
    panel.innerHTML = `
        <summary style="cursor:pointer">Twitch triggers</summary>
        <form style="display:grid;gap:8px;margin-top:10px">
            <div>Choose your voice and start audio in VCClient first. Twitch uses that voice.</div>
            <label>Chat command <input name="command" value="!voice" required></label>
            <label>Duration (seconds) <input name="duration" type="number" min="1" max="300" value="20" required></label>
            <label><input name="moderators_only" type="checkbox" checked> Broadcaster and moderators only</label>
            <label>Minimum Bits (0 disables) <input name="minimum_bits" type="number" min="0" value="0" required></label>
            <label>Channel Points reward title or ID <input name="reward" placeholder="Optional"></label>
            <div>
                <button type="submit">Connect Twitch</button>
                <button type="button" data-action="disconnect">Disconnect</button>
            </div>
            <div>
                <button type="button" data-action="test">Test effect</button>
                <button type="button" data-action="normal">Return to normal</button>
            </div>
            <a href="https://www.twitch.tv/activate" target="_blank" rel="noopener" style="color:#ccb9ff">Open Twitch activation page</a>
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
                error.textContent = "";
            }
            const response = await fetch(`/twitch/${action}`, options);
            const data = await response.json();
            if (!response.ok) {
                const detail = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
                throw new Error(detail || "Twitch controls could not reach the local VCClient server.");
            }
            status.textContent = data.status;
            effect.textContent = data.effect;
            form.querySelector('[type="submit"]').disabled = data.connected;
            form.querySelector('[data-action="disconnect"]').disabled = !data.connected;
        } catch (failure) {
            error.textContent = failure.message;
        } finally {
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
        if (panel.open) request("status");
    }, 1000);
})();
