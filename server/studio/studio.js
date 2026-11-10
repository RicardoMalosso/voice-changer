"use strict";

const $ = (id) => document.getElementById(id);
const forms = { audio: $("audio"), model: $("select-model"), tuning: $("tuning"), twitch: $("twitch") };
const labels = [...document.querySelectorAll("[data-pt]")].map((node) => [node, node.textContent]);
const languageButtons = [...document.querySelectorAll("[data-language]")];
let language = localStorage.getItem("pacvoice-language") || (navigator.language.startsWith("pt") ? "pt-BR" : "en-US");
let info = null;
let live = {};
let twitch = {};
let notice = null;
let busy = false;
let online = false;
let audioRevision = 0;
let polling = false;
const t = (en, pt) => language === "pt-BR" ? pt : en;

const statusTranslations = new Map([
    ["Twitch disconnected.", "Twitch desconectada."],
    ["Twitch control off.", "Controle pela Twitch desativado."],
    ["Waiting for Twitch authorization…", "Aguardando autorização da Twitch…"],
    ["Ready. The original mic passes through between triggers.", "Pronto. Entre os gatilhos, o microfone passa sem efeito."],
    ["Select a voice model and start audio in VCClient first.", "Primeiro selecione um modelo e inicie o áudio."],
]);
function localStatus(message = "") {
    if (language !== "pt-BR") return message;
    return statusTranslations.get(message) || message
        .replace(/^Listening to #(.+)$/, "Ouvindo o chat de #$1")
        .replace(/^Enter (.+) on the Twitch activation page\.$/, "Digite $1 na página de ativação da Twitch.")
        .replace(/^Converted voice active for (\d+) seconds\.$/, "Voz convertida ativa por $1 segundos.");
}

try {
    const saved = JSON.parse(localStorage.getItem("pacvoice-twitch-settings") || "{}");
    for (const name of ["command", "duration", "minimum_bits", "reward"]) {
        if (saved[name] !== undefined) forms.twitch.elements[name].value = saved[name];
    }
    if (typeof saved.moderators_only === "boolean") {
        forms.twitch.elements.moderators_only.checked = saved.moderators_only;
    }
} catch {
    // The panel works with defaults when no valid preferences are available.
}

async function api(path, body) {
    const options = { cache: "no-store" };
    if (body !== undefined) {
        options.method = "POST";
        options.headers = { "X-VCClient-Twitch": "1" };
        if (body instanceof FormData) {
            options.body = body;
        } else {
            options.headers["Content-Type"] = "application/json";
            options.body = JSON.stringify(body);
        }
    }
    const response = await fetch(path, { ...options, signal: AbortSignal.timeout(120000) });
    const data = await response.json().catch(() => null);
    if (!response.ok || data === null || data.status === "ERROR") {
        const detail = Array.isArray(data?.detail) ? data.detail.map((entry) => entry.msg).join("; ") : data?.detail;
        throw new Error(detail || data?.msg || `HTTP ${response.status} · ${path}`);
    }
    return data;
}

function setOptions(select, rows, current, placeholder, optional = false) {
    const options = [new Option(placeholder, optional ? "-1" : "")];
    options[0].disabled = !optional;
    for (const [value, name] of rows) options.push(new Option(name, String(value)));
    select.replaceChildren(...options);
    const value = String(current);
    select.value = options.some((option) => option.value === value) ? value : options[0].value;
}

function populate(keepSelection = false) {
    if (!info) return;
    const audio = forms.audio.elements;
    const slots = forms.model.elements.slot;
    const selected = (field, saved) => keepSelection ? field.value : saved;
    const devices = (list) => (list || []).map((device) => [device.index, `${device.name} · ${device.hostAPI}`]);
    const outputRows = devices(info.serverAudioOutputDevices);
    setOptions(audio.microphone, devices(info.serverAudioInputDevices), selected(audio.microphone, info.serverInputDeviceId),
        t("Choose a microphone", "Escolha um microfone"));
    setOptions(audio.output, outputRows, selected(audio.output, info.serverOutputDeviceId),
        t("Choose an output", "Escolha uma saída"));
    setOptions(audio.monitor, outputRows, selected(audio.monitor, info.serverMonitorDeviceId),
        t("Off", "Desligado"), true);
    const modelRows = (info.modelSlots || []).filter((slot) => slot?.voiceChangerType)
        .map((slot) => [slot.slotIndex, `${slot.name || slot.slotIndex} · ${slot.voiceChangerType}`]);
    setOptions(slots, modelRows, selected(slots, info.modelSlotIndex),
        t("Choose an imported model", "Escolha um modelo importado"));
    if (!keepSelection) {
        audio.rate.value = [44100, 48000].includes(info.serverAudioSampleRate) ? info.serverAudioSampleRate : 48000;
        audio.chunk.value = info.serverReadChunkSize || 128;
        for (const field of forms.tuning.elements) {
            if (field.name && Number.isFinite(info[field.name])) field.value = info[field.name];
        }
    }
}

function render() {
    document.documentElement.lang = language;
    for (const [node, english] of labels) node.textContent = t(english, node.dataset.pt);
    for (const button of languageButtons) button.setAttribute("aria-pressed", button.dataset.language === language);
    $("connection").textContent = online ? t("Connected to VCClient", "Conectado ao VCClient")
        : t("VCClient unavailable. Check the server terminal.", "VCClient indisponível. Confira o terminal do servidor.");
    const gpu = (info?.gpus || []).map((item) => item.name).filter(Boolean).join(", ");
    $("hardware").textContent = gpu || t("No GPU reported by VCClient", "O VCClient não informou uma GPU");
    $("notice").hidden = !notice;
    $("notice").textContent = notice?.text || "";
    $("notice").dataset.kind = notice?.kind || "error";

    const status = !online ? t("Audio status unavailable.", "Status do áudio indisponível.")
        : live.error && live.requested ? live.error
        : live.flowing ? t("Microphone blocks are reaching the engine.", "O áudio do microfone está chegando ao motor.")
        : live.requested ? t("Waiting for microphone audio…", "Aguardando áudio do microfone…")
        : t("Audio stopped.", "Áudio parado.");
    const timing = live.flowing && Number.isFinite(live.performance?.[0]) ? ` · ${live.performance[0]} ms` : "";
    $("audio-status").textContent = status + timing;
    $("input-level").value = online && live.flowing ? live.levels[0] : 0;
    $("output-level").value = online && live.flowing ? live.levels[1] : 0;
    $("record-status").textContent = live.recording ? t("Recording…", "Gravando…")
        : live.frames ? t("Sample available.", "Amostra disponível.") : t("No sample yet.", "Nenhuma amostra gravada.");
    $("twitch-status").textContent = localStatus(twitch.status);
    $("effect-status").textContent = localStatus(twitch.effect);
    for (const id of ["start", "stop", "record", "finish", "connect", "disconnect", "test", "normal", "refresh", "defaults", "export"]) {
        $(id).disabled = busy || (!online && id !== "refresh");
    }
    $("start").disabled ||= !!live.requested || !info;
    $("stop").disabled ||= !live.requested;
    $("export").disabled ||= !!live.requested;
    $("record").disabled ||= !live.flowing || !!live.recording;
    $("finish").disabled ||= !live.recording;
    $("connect").disabled ||= !!twitch.connected;
    $("disconnect").disabled ||= !twitch.connected;
    for (const selector of ["#select-model button", "#import-model button", "#tuning button"]) {
        document.querySelector(selector).disabled = busy || !online || (selector !== "#tuning button" && !!live.requested);
    }
}

async function refresh() {
    info = await api("/info");
    online = true;
    populate();
}

function showRecording(previous) {
    if (!live.recording && live.frames && (previous.recording || previous.frames !== live.frames)) {
        audioRevision += 1;
        for (const track of ["original", "converted"]) {
            $(track).src = `api/record/${track}?v=${Date.now()}-${audioRevision}`;
        }
    }
}

async function poll() {
    if (polling || busy) return;
    polling = true;
    try {
        const [nextLive, nextTwitch] = await Promise.all([api("api/live"), api("/twitch/status")]);
        if (busy) return;
        if (!online || !info) await refresh();
        const previous = live;
        live = nextLive;
        twitch = nextTwitch;
        showRecording(previous);
    } catch {
        online = false;
    } finally {
        polling = false;
        render();
    }
}

async function run(en, pt, action) {
    if (busy) return;
    busy = true;
    notice = { kind: "progress", text: t(en, pt) };
    render();
    try {
        await action();
        notice = null;
    } catch (error) {
        notice = { kind: "error", text: error.message };
    } finally {
        busy = false;
        render();
        void poll();
    }
}

function submit(form, en, pt, action) {
    form.addEventListener("submit", (event) => {
        event.preventDefault();
        void run(en, pt, action);
    });
}

function button(id, en, pt, action) {
    $(id).addEventListener("click", () => void run(en, pt, action));
}

const values = (form) => Object.fromEntries(new FormData(form));
const numbers = (form) => Object.fromEntries(Object.entries(values(form)).map(([key, value]) => [key, Number(value)]));
const twitchSettings = () => {
    const { command, duration, minimum_bits, reward } = values(forms.twitch);
    return { command, duration: Number(duration), minimum_bits: Number(minimum_bits), reward,
        moderators_only: forms.twitch.elements.moderators_only.checked };
};

submit(forms.audio, "Starting audio…", "Iniciando áudio…", async () => {
    live = await api("api/audio/start", numbers(forms.audio));
});
submit(forms.model, "Loading model…", "Carregando modelo…", async () => {
    await api("api/model/select", values(forms.model));
    await refresh();
});
submit($("import-model"), "Importing model…", "Importando modelo…", async () => {
    const data = new FormData($("import-model"));
    if (!data.get("index").size) data.delete("index");
    const imported = await api("api/model/import", data);
    await refresh();
    forms.model.elements.slot.value = imported.slot;
    try {
        await api("api/model/select", { slot: imported.slot });
    } catch (error) {
        throw new Error(t(`Imported ${imported.name}, but loading failed. `, `Modelo ${imported.name} importado, mas houve erro ao carregar. `) + error.message);
    }
    $("import-model").reset();
    await refresh();
});
submit(forms.tuning, "Applying tuning…", "Aplicando ajustes…", () => api("api/audio/tuning", numbers(forms.tuning)));
submit(forms.twitch, "Connecting to Twitch…", "Conectando à Twitch…", async () => {
    const settings = twitchSettings();
    twitch = await api("/twitch/connect", settings);
    localStorage.setItem("pacvoice-twitch-settings", JSON.stringify(settings));
});
button("defaults", "Saving model defaults…", "Salvando ajustes no modelo…", () => api("api/model/defaults", {}));
button("export", "Exporting ONNX…", "Exportando ONNX…", async () => {
    $("export-result").hidden = true;
    const { filename } = await api("api/model/export", {});
    $("export-result").href = "/tmp/" + encodeURIComponent(filename);
    $("export-result").download = filename;
    $("export-result").hidden = false;
});
button("refresh", "Refreshing devices…", "Atualizando dispositivos…", refresh);
button("stop", "Stopping audio…", "Parando áudio…", async () => {
    const previous = live;
    live = await api("api/audio/stop", {});
    showRecording(previous);
});
button("record", "Starting recording…", "Iniciando gravação…", async () => {
    live = await api("api/record/start", {});
    for (const track of ["original", "converted"]) {
        $(track).removeAttribute("src");
        $(track).load();
    }
});
button("finish", "Finishing recording…", "Finalizando gravação…", async () => {
    const previous = live;
    live = await api("api/record/stop", {});
    showRecording(previous);
});
button("disconnect", "Disconnecting…", "Desconectando…", async () => { twitch = await api("/twitch/disconnect", {}); });
button("normal", "Ending effect…", "Encerrando efeito…", async () => { twitch = await api("/twitch/normal", {}); });
button("test", "Testing effect…", "Testando efeito…", async () => {
    if (forms.twitch.reportValidity()) twitch = await api("/twitch/test", twitchSettings());
});
for (const button of languageButtons) {
    button.addEventListener("click", () => {
        language = button.dataset.language;
        localStorage.setItem("pacvoice-language", language);
        populate(true);
        render();
    });
}

render();
void poll();
setInterval(() => void poll(), 1000);
