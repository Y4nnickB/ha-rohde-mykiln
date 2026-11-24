/*
 * ROHDE myKiln card for Home Assistant.
 *
 *   type: custom:rohde-mykiln-card
 *   entity: sensor.garage_temperature   # any entity of the kiln device
 *   drawing: auto                      # optional: top | front | auto (from the model)
 *   name: Garage                        # optional
 *   hours: 12                           # optional chart window when not firing
 *
 * Finds the other entities of the kiln by their translation key, so renamed
 * entity ids keep working. No external dependencies.
 */
const CARD_VERSION = "0.6.0";

const KEYS = {
  sensor: ["temperature_1", "temperature_2", "temperature_3", "status", "program", "progress",
    "duration", "last_update", "wifi_signal"],
  binary_sensor: ["online", "firing", "heating", "cooling", "delayed_start"],
};

const STRINGS = {
  en: {
    heating: "Heating", cooling: "Cooling down", idle: "Idle", offline: "Offline",
    waiting: "Delayed start", unavailable: "Kiln not found", progress: "Progress",
    duration: "Firing time", rate: "Rate", updated: "Last report", zone: "Zone",
    left: "left", now: "now", ago: "ago", signal: "Wi-Fi", noProgram: "No program",
    last: "Last", hours: "h",
    eEntity: "Kiln (any of its sensors)", eName: "Name (optional)", eDrawing: "Drawing",
    eHours: "Chart window when not firing (hours)", eAuto: "Automatic, from the model",
    eTop: "Top loader", eFront: "Front loader",
  },
  nl: {
    heating: "Verwarmt", cooling: "Koelt af", idle: "In rust", offline: "Offline",
    waiting: "Uitgestelde start", unavailable: "Oven niet gevonden", progress: "Voortgang",
    duration: "Stookduur", rate: "Snelheid", updated: "Laatste melding", zone: "Zone",
    left: "te gaan", now: "nu", ago: "geleden", signal: "Wifi", noProgram: "Geen programma",
    last: "Laatste", hours: "u",
    eEntity: "Oven (een van zijn sensoren)", eName: "Naam (optioneel)", eDrawing: "Tekening",
    eHours: "Grafiekvenster buiten een stook (uren)", eAuto: "Automatisch, volgens het model",
    eTop: "Toplader", eFront: "Frontlader",
  },
  de: {
    heating: "Heizt", cooling: "Kühlt ab", idle: "Bereit", offline: "Offline",
    waiting: "Verzögerter Start", unavailable: "Ofen nicht gefunden", progress: "Fortschritt",
    duration: "Brenndauer", rate: "Rate", updated: "Letzte Meldung", zone: "Zone",
    left: "übrig", now: "jetzt", ago: "her", signal: "WLAN", noProgram: "Kein Programm",
    last: "Letzte", hours: "Std",
    eEntity: "Ofen (einer seiner Sensoren)", eName: "Name (optional)", eDrawing: "Zeichnung",
    eHours: "Diagrammfenster ohne Brand (Stunden)", eAuto: "Automatisch, nach Modell",
    eTop: "Toplader", eFront: "Frontlader",
  },
};

// Approximate colour of the glow inside a kiln at a temperature in °C.
const GLOW = [
  [400, [90, 20, 12]], [550, [120, 22, 14]], [700, [168, 30, 18]], [800, [205, 42, 22]],
  [900, [232, 80, 30]], [1000, [245, 124, 31]], [1100, [251, 164, 58]], [1200, [255, 205, 100]],
  [1300, [255, 236, 170]],
];

function glowColor(celsius) {
  if (celsius == null || celsius < GLOW[0][0]) return null;
  for (let i = 1; i < GLOW.length; i++) {
    const [t1, c1] = GLOW[i];
    if (celsius <= t1) {
      const [t0, c0] = GLOW[i - 1];
      const f = (celsius - t0) / (t1 - t0);
      const c = c0.map((v, j) => Math.round(v + (c1[j] - v) * f));
      return `rgb(${c.join(",")})`;
    }
  }
  return `rgb(${GLOW[GLOW.length - 1][1].join(",")})`;
}

const toMinutes = (value, unit) => {
  const factor = { s: 1 / 60, min: 1, h: 60, d: 1440 }[unit] ?? 1;
  return value * factor;
};

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[c]));

const langStrings = (hass) =>
  STRINGS[(hass?.locale?.language || hass?.language || "en").slice(0, 2)] || STRINGS.en;

// Visual editor shown in the dashboard's card dialog (uses Home Assistant's ha-form).
class RohdeMyKilnCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    const t = { ...STRINGS.en, ...langStrings(this._hass) };
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (s) => ({
        entity: t.eEntity, name: t.eName, drawing: t.eDrawing, hours: t.eHours,
      })[s.name] ?? s.name;
      this._form.addEventListener("value-changed", (ev) => {
        ev.stopPropagation();
        const config = { ...ev.detail.value };
        for (const [key, value] of Object.entries(config)) {
          if (value === "" || value == null || (key === "drawing" && value === "auto")
            || (key === "hours" && value === 12)) delete config[key];
        }
        this._config = config;
        this.dispatchEvent(new CustomEvent("config-changed", {
          detail: { config }, bubbles: true, composed: true,
        }));
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = [
      { name: "entity", required: true,
        selector: { entity: { filter: { integration: "rohde_mykiln", domain: "sensor" } } } },
      { name: "name", selector: { text: {} } },
      { type: "grid", name: "", schema: [
        { name: "drawing", selector: { select: { mode: "dropdown", options: [
          { value: "auto", label: t.eAuto }, { value: "top", label: t.eTop },
          { value: "front", label: t.eFront }] } } },
        { name: "hours", selector: { number: { min: 1, max: 48, step: 1, mode: "box" } } },
      ] },
    ];
    this._form.data = { drawing: "auto", hours: 12, ...this._config };
  }
}

class RohdeMyKilnCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("rohde-mykiln-card-editor");
  }

  static getStubConfig(hass) {
    const entity = Object.values(hass?.entities ?? {}).find(
      (e) => e.platform === "rohde_mykiln" && e.translation_key === "temperature_1",
    );
    return { entity: entity?.entity_id ?? "sensor.kiln_temperature" };
  }

  setConfig(config) {
    if (!config?.entity) throw new Error("Set 'entity' to any entity of the kiln");
    this._config = { hours: 12, ...config };
    this._history = null;
    this._historyAt = 0;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
  }

  getCardSize() {
    return 6;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  set hass(hass) {
    this._hass = hass;
    this.toggleAttribute("dark", !!hass.themes?.darkMode);
    this._resolve();
    const key = this._renderKey();
    if (key !== this._lastKey) {
      this._lastKey = key;
      this._render();
    }
    this._maybeFetchHistory();
  }

  _t(key) {
    const lang = (this._hass?.locale?.language || this._hass?.language || "en").slice(0, 2);
    return (STRINGS[lang] || STRINGS.en)[key] ?? STRINGS.en[key];
  }

  _resolve() {
    const hass = this._hass;
    const reg = hass.entities?.[this._config.entity];
    const deviceId = reg?.device_id;
    this._device = deviceId ? hass.devices?.[deviceId] : null;
    this._ids = {};
    if (deviceId) {
      for (const e of Object.values(hass.entities)) {
        if (e.device_id !== deviceId || !e.translation_key) continue;
        const domain = e.entity_id.split(".")[0];
        if (KEYS[domain]?.includes(e.translation_key)) this._ids[e.translation_key] = e.entity_id;
      }
    }
    if (!this._ids.temperature_1 && this._config.entity.startsWith("sensor.")) {
      this._ids.temperature_1 = this._config.entity;
    }
  }

  _st(key) {
    const id = this._ids[key];
    return id ? this._hass.states[id] : undefined;
  }

  _num(key) {
    const st = this._st(key);
    const v = st ? parseFloat(st.state) : NaN;
    return Number.isFinite(v) ? v : null;
  }

  _on(key) {
    return this._st(key)?.state === "on";
  }

  _renderKey() {
    const parts = Object.values(this._ids).map((id) => {
      const s = this._hass.states[id];
      return s ? `${s.state}|${s.last_updated}` : "-";
    });
    return parts.join(";") + (this._history ? `;h${this._historyAt}` : "") + this._hass.themes?.darkMode;
  }

  _mode() {
    const online = this._st("online");
    if (!online || online.state !== "on") return "offline";
    if (this._on("delayed_start")) return "waiting";
    if (this._on("cooling")) return "cooling";
    if (this._on("heating") || this._on("firing")) return "heating";
    return "idle";
  }

  async _maybeFetchHistory() {
    const id = this._ids.temperature_1;
    if (!id || !this._hass.callWS || this._fetching) return;
    if (Date.now() - this._historyAt < 5 * 60 * 1000) return;
    this._fetching = true;
    try {
      const firingMin = this._mode() === "heating" || this._mode() === "cooling"
        ? toMinutes(this._num("duration") ?? 0, this._st("duration")?.attributes.unit_of_measurement)
        : 0;
      const hours = Math.min(48, Math.max(this._config.hours, firingMin / 60 + 0.25));
      const start = new Date(Date.now() - hours * 3600 * 1000);
      const result = await this._hass.callWS({
        type: "history/history_during_period",
        start_time: start.toISOString(),
        entity_ids: [id],
        minimal_response: true,
        no_attributes: true,
        significant_changes_only: false,
      });
      this._history = {
        start: start.getTime(),
        points: (result?.[id] ?? [])
          .map((p) => [((p.lu ?? p.lc) * 1000) || Date.parse(p.last_updated), parseFloat(p.s ?? p.state)])
          .filter(([t, v]) => Number.isFinite(t) && Number.isFinite(v)),
      };
    } catch (err) {
      this._history = this._history ?? { start: Date.now(), points: [] };
    } finally {
      this._historyAt = Date.now();
      this._fetching = false;
      this._lastKey = null;
      if (this._hass) this.hass = this._hass;
    }
  }

  _points() {
    const pts = [...(this._history?.points ?? [])];
    const now = this._num("temperature_1");
    if (now != null) pts.push([Date.now(), now]);
    return pts;
  }

  _rate(points) {
    // °/h over the last ~20 minutes, from the recorded temperatures.
    if (points.length < 2) return null;
    const [tEnd, vEnd] = points[points.length - 1];
    const from = tEnd - 20 * 60 * 1000;
    let ref = null;
    for (const p of points) {
      if (p[0] <= from) ref = p;
      else break;
    }
    ref = ref ?? points[0];
    const dtH = (tEnd - ref[0]) / 3600000;
    if (dtH < 0.1) return null;
    return (vEnd - ref[1]) / dtH;
  }

  _spark(points, accent) {
    if (points.length < 2) return "";
    const W = 300, H = 56, P = 3;
    const t0 = this._history?.start ?? points[0][0];
    const t1 = points[points.length - 1][0];
    const vs = points.map((p) => p[1]);
    const lo = Math.min(...vs, 0), hi = Math.max(...vs, 100);
    const x = (t) => P + ((t - t0) / Math.max(1, t1 - t0)) * (W - 2 * P);
    const y = (v) => H - P - ((v - lo) / Math.max(1, hi - lo)) * (H - 2 * P);
    const line = points.map((p, i) => `${i ? "L" : "M"}${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join("");
    const last = points[points.length - 1];
    const max = points.reduce((a, b) => (b[1] > a[1] ? b : a));
    return `
      <svg class="spark" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true">
        <defs><linearGradient id="sf" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="${accent}" stop-opacity=".28"/>
          <stop offset="1" stop-color="${accent}" stop-opacity="0"/></linearGradient></defs>
        <path d="${line}L${x(last[0]).toFixed(1)},${H}L${x(points[0][0]).toFixed(1)},${H}Z" fill="url(#sf)"/>
        <path d="${line}" fill="none" stroke="${accent}" stroke-width="2" vector-effect="non-scaling-stroke"
          stroke-linejoin="round" stroke-linecap="round"/>
        <circle cx="${x(last[0])}" cy="${y(last[1])}" r="3.2" fill="${accent}" class="dot"/>
      </svg>
      <div class="spark-meta"><span>${this._fmtSpan(t1 - t0)}</span>
        <span>max ${Math.round(max[1])}°</span></div>`;
  }

  _fmtSpan(ms) {
    const h = ms / 3600000;
    return `${this._t("last")} ${h >= 10 ? Math.round(h) : h.toFixed(1)} ${this._t("hours")}`;
  }

  _fmtMinutes(min) {
    if (min == null) return "–";
    const h = Math.floor(min / 60), m = Math.round(min % 60);
    if (h >= 48) return `${Math.round(h / 24)} d`;
    if (h >= 10) return `${Math.round(min / 60)} h`;
    return h ? `${h} h ${String(m).padStart(2, "0")}` : `${m} min`;
  }

  _scene(mode, temp, glow) {
    const hot = glow && mode !== "offline";
    const glowOpacity = hot ? Math.min(1, 0.35 + ((temp - 400) / 900) * 0.65) : 0;
    const waves = mode === "heating" && temp > 150;
    const cool = mode === "cooling";
    return `
    <svg class="scene" viewBox="0 0 220 112" aria-hidden="true">
      <defs>
        <radialGradient id="halo"><stop offset="0" stop-color="${glow ?? "#000"}" stop-opacity=".9"/>
          <stop offset="1" stop-color="${glow ?? "#000"}" stop-opacity="0"/></radialGradient>
        <linearGradient id="steel" x1="0" x2="1"><stop offset="0" stop-color="var(--k-steel-1)"/>
          <stop offset="1" stop-color="var(--k-steel-2)"/></linearGradient>
        <linearGradient id="cyl" x1="0" x2="1"><stop offset="0" stop-color="var(--k-steel-2)"/>
          <stop offset=".4" stop-color="var(--k-steel-1)"/><stop offset="1" stop-color="var(--k-steel-2)"/></linearGradient>
      </defs>
      <!-- shelf with pottery -->
      <g class="shelf"><rect x="8" y="46" width="78" height="3" rx="1.5" fill="var(--k-wood)"/>
      <path d="M18 46c-4-3-4-11 0-14h-1v-3h8v3h-1c4 3 4 11 0 14z" fill="var(--k-pot-1)"/>
      <path d="M34 46c-6 0-8-6-6-12h14c2 6 0 12-8 12z" fill="var(--k-pot-2)"/>
      <rect x="31" y="31" width="8" height="3" rx="1" fill="var(--k-pot-2)"/>
      <path d="M52 46c-3-2-5-6-3-12l2-8h6l2 8c2 6 0 10-3 12z" fill="var(--k-pot-3)"/>
      <path d="M66 46h12l-2-9h-8z" fill="var(--k-pot-1)" opacity=".85"/></g>
      ${waves ? `<g class="waves" stroke="${glow ?? "var(--accent)"}" fill="none" stroke-width="2" stroke-linecap="round">
        <path d="M128 18c-3-4 3-6 0-10s3-6 0-10"/><path d="M146 20c-3-4 3-6 0-10s3-6 0-10"/>
        <path d="M164 18c-3-4 3-6 0-10s3-6 0-10"/></g>` : ""}
      ${cool ? `<g class="cool" stroke="var(--accent)" fill="none" stroke-width="1.6" stroke-linecap="round">
        <path d="M134 6v14M128 10l6 4 6-4M146 2v14M140 6l6 4 6-4M158 6v14M152 10l6 4 6-4"/></g>` : ""}
      <g class="drawn">
      ${this._kilnType() === "top" ? this._topLoader(hot, glow, glowOpacity) : `
      <!-- kiln: front loader on a stand, vent on top, door with glowing seam -->
      <rect x="116" y="94" width="62" height="4" rx="1" fill="var(--k-dark)"/>
      <rect x="118" y="97" width="4" height="10" fill="var(--k-dark)"/>
      <rect x="172" y="97" width="4" height="10" fill="var(--k-dark)"/>
      <rect x="142" y="18" width="10" height="7" rx="1.5" fill="var(--k-dark)"/>
      <rect x="112" y="24" width="70" height="70" rx="5" fill="url(#steel)" stroke="var(--k-dark)" stroke-width="1.5"/>
      <rect x="118" y="30" width="58" height="58" rx="3" fill="none" stroke="${hot ? glow : "var(--k-dark)"}"
        stroke-width="${hot ? 6 : 0}" stroke-opacity="${glowOpacity * 0.35}" class="${hot ? "seam" : ""}"/>
      <rect x="118" y="30" width="58" height="58" rx="3" fill="url(#steel)"
        stroke="${hot ? glow : "var(--k-dark)"}" stroke-width="1.6" stroke-opacity="${hot ? 0.6 + glowOpacity * 0.4 : 0.45}"/>
      <rect x="113" y="38" width="5" height="9" rx="1" fill="var(--k-dark)"/>
      <rect x="113" y="71" width="5" height="9" rx="1" fill="var(--k-dark)"/>
      <rect x="167" y="52" width="4" height="18" rx="2" fill="var(--k-dark)"/>
      <circle cx="169" cy="51" r="3" fill="var(--k-dark)"/>
      <rect x="130" y="78" width="22" height="5" rx="1" fill="var(--k-dark)" opacity=".25"/>
      <circle cx="140" cy="44" r="13" fill="url(#halo)" opacity="${glowOpacity}" class="${hot ? "pulse" : ""}"
        style="transform-origin:140px 44px"/>
      <circle cx="140" cy="44" r="4.2" fill="${hot ? glow : "var(--k-hole)"}" stroke="var(--k-dark)" stroke-width="1.4"/>
      <path d="M182 60h4" stroke="var(--k-dark)" stroke-width="1.5"/>`}
      <!-- controller -->
      <rect x="186" y="44" width="24" height="34" rx="3" fill="var(--k-ctrl)" stroke="var(--k-dark)" stroke-width="1.2"/>
      <rect x="189" y="48" width="18" height="9" rx="1.5" fill="${mode === "offline" ? "var(--k-dark)" : "var(--k-lcd)"}"/>
      <circle cx="193" cy="64" r="1.8" fill="var(--k-dark)"/><circle cx="198" cy="64" r="1.8" fill="var(--k-dark)"/>
      <circle cx="203" cy="64" r="1.8" fill="var(--k-dark)"/>
      <circle cx="198" cy="72" r="2" fill="${mode === "offline" ? "var(--k-dark)" : "var(--accent)"}" class="${mode === "offline" ? "" : "blink"}"/>
      </g>
    </svg>`;
  }

  _kilnType() {
    // drawing: top | front | auto (from the model myKiln reports: ROHDE TE and
    // Ecotop kilns are top loaders, the others are drawn as front loaders).
    const choice = this._config.drawing;
    if (choice === "top" || choice === "front") return choice;
    return /ecotop|\bte\s*\d|top/i.test(this._device?.model ?? "") ? "top" : "front";
  }

  _topLoader(hot, glow, glowOpacity) {
    const seam = hot ? glow : "var(--k-dark)";
    return `
      <!-- kiln: round top loader on a stand, lid with vent, glowing lid seam -->
      <rect x="114" y="87" width="68" height="4" rx="2" fill="var(--k-stand)"/>
      <rect x="146" y="90" width="3" height="13" fill="var(--k-stand)" opacity=".55"/>
      <rect x="118" y="89" width="4" height="18" rx="1" fill="var(--k-stand)"/>
      <rect x="174" y="89" width="4" height="18" rx="1" fill="var(--k-stand)"/>
      <path d="M116 44v38a32 7 0 0 0 64 0V44z" fill="url(#cyl)" stroke="var(--k-dark)" stroke-width="1.5"/>
      <path d="M116 57a32 7 0 0 0 64 0M116 72a32 7 0 0 0 64 0" fill="none" stroke="var(--k-dark)" stroke-opacity=".25"/>
      <path d="M116 44a32 7 0 0 0 64 0" fill="none" stroke="${seam}" stroke-width="${hot ? 6 : 0}"
        stroke-opacity="${glowOpacity * 0.45}" class="${hot ? "seam" : ""}"/>
      <path d="M116 44a32 7 0 0 0 64 0" fill="none" stroke="${seam}" stroke-width="1.6"
        stroke-opacity="${hot ? 0.6 + glowOpacity * 0.4 : 0.45}"/>
      <path d="M115 36v6a33 7.5 0 0 0 66 0v-6z" fill="url(#cyl)" stroke="var(--k-dark)" stroke-width="1.3"/>
      <ellipse cx="148" cy="36" rx="33" ry="7.5" fill="var(--k-steel-1)" stroke="var(--k-dark)" stroke-width="1.3"/>
      <ellipse cx="148" cy="35.5" rx="3.6" ry="1.5" fill="${hot ? glow : "var(--k-hole)"}"/>
      <rect x="142" y="44" width="12" height="3" rx="1.5" fill="var(--k-dark)"/>
      <rect x="138" y="77" width="20" height="4" rx="1" fill="var(--k-dark)" opacity=".25"/>
      <circle cx="148" cy="64" r="12" fill="url(#halo)" opacity="${glowOpacity}" class="${hot ? "pulse" : ""}"
        style="transform-origin:148px 64px"/>
      <circle cx="148" cy="64" r="3.8" fill="${hot ? glow : "var(--k-hole)"}" stroke="var(--k-dark)" stroke-width="1.4"/>
      <path d="M180 60h6" stroke="var(--k-dark)" stroke-width="1.5"/>`;
  }

  _render() {
    if (!this.shadowRoot || !this._hass) return;
    const temp = this._num("temperature_1");
    const name = this._config.name || this._device?.name_by_user || this._device?.name
      || this._st("temperature_1")?.attributes.friendly_name || "Kiln";
    if (!this._st("temperature_1") && !this._st("online")) {
      this.shadowRoot.innerHTML = `<ha-card><div class="missing">${this._t("unavailable")}: ${esc(this._config.entity)}</div></ha-card>`;
      return;
    }
    const mode = this._mode();
    const unit = this._st("temperature_1")?.attributes.unit_of_measurement ?? "°C";
    const celsius = temp == null ? null : unit.includes("F") ? (temp - 32) / 1.8 : temp;
    const glow = mode === "offline" ? null : glowColor(celsius);
    const accent = {
      heating: "#e8590c", cooling: "#1c7ed6", idle: "#1b8a98", waiting: "#7048e8", offline: "#868e96",
    }[mode];
    // The progress line runs from the accent to the current glow colour while hot.
    const barFill = mode === "heating" && glow ? `linear-gradient(90deg, ${accent}, ${glow})` : accent;

    const progress = this._num("progress");
    const durSt = this._st("duration");
    const duration = durSt && this._num("duration") != null
      ? toMinutes(this._num("duration"), durSt.attributes.unit_of_measurement) : null;
    const active = mode === "heating" || mode === "cooling";
    const remaining = active && mode === "heating" && progress > 3 && progress < 100 && duration
      ? (duration * (100 - progress)) / progress : null;
    const points = this._points();
    let rate = mode === "offline" ? null : this._rate(points);
    if (rate != null && !active && Math.abs(rate) < 10) rate = null; // sensor noise at rest
    const program = this._st("program")?.state;
    const hasProgram = program && !["unknown", "unavailable", ""].includes(program);
    const statusText = this._st("status")?.state;
    const model = this._device?.model && this._device.model !== "Kiln" ? this._device.model : null;
    const sub = [hasProgram ? program : active ? null : this._t("noProgram"), model].filter(Boolean).join(" · ");

    const zones = ["temperature_2", "temperature_3"]
      .map((k, i) => ({ v: this._num(k), n: i + 2 }))
      .filter((z) => z.v != null);

    const lu = this._st("last_update");
    const luMin = lu && lu.state !== "unavailable" && Number.isFinite(parseFloat(lu.state))
      ? toMinutes(parseFloat(lu.state), lu.attributes.unit_of_measurement) : null;
    const luText = luMin == null ? "–" : luMin < 2 ? this._t("now")
      : `${this._fmtMinutes(luMin)} ${this._t("ago")}`;

    const tiles = [
      active || progress ? { icon: "mdi:progress-clock", label: this._t("progress"),
        value: progress != null ? `${Math.round(progress)}<small>%</small>` : "–" } : null,
      active || duration ? { icon: "mdi:timer-outline", label: this._t("duration"),
        value: this._fmtMinutes(duration) } : null,
      rate != null ? { icon: rate >= 0 ? "mdi:trending-up" : "mdi:trending-down", label: this._t("rate"),
        value: `${rate >= 0 ? "+" : "−"}${Math.abs(Math.round(rate))}<small>°/h</small>` } : null,
      ...zones.map((z) => ({ icon: "mdi:thermometer", label: `${this._t("zone")} ${z.n}`,
        value: `${Math.round(z.v)}<small>${esc(unit)}</small>` })),
      { icon: "mdi:access-point", label: this._t("updated"), value: luText },
    ].filter(Boolean).slice(0, 4);

    const chips = [
      statusText && !["unknown", "unavailable"].includes(statusText)
        ? `<span class="chip"><ha-icon icon="mdi:information-outline"></ha-icon>${esc(statusText)}</span>` : "",
      remaining != null ? `<span class="chip accent"><ha-icon icon="mdi:flag-checkered"></ha-icon>≈ ${this._fmtMinutes(remaining)} ${this._t("left")}</span>` : "",
      this._num("wifi_signal") != null
        ? `<span class="chip"><ha-icon icon="mdi:wifi-strength-${Math.max(0, Math.min(4, Math.round(this._num("wifi_signal"))))}"></ha-icon>${this._t("signal")}</span>` : "",
    ].join("");

    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <ha-card class="${mode}" style="--accent:${accent}">
        <div class="hero">
          <div class="head">
            <div class="ico"><ha-icon icon="mdi:fire-circle"></ha-icon></div>
            <div class="titles">
              <div class="name"><span>${esc(name)}</span>
                <span class="pill"><i></i>${this._t(mode)}</span></div>
              <div class="sub">${esc(sub)}</div>
            </div>
          </div>
          ${this._scene(mode, celsius ?? 0, glow)}
        </div>
        <div class="bar"><div class="fill" style="background:${barFill};width:${active && progress != null ? Math.min(100, progress) : mode === "offline" ? 0 : 100}%"></div></div>
        <div class="body">
          <div class="big">
            <span class="num">${temp == null ? "–" : Math.round(temp)}</span><span class="unit">${esc(unit)}</span>
            ${glow ? `<span class="swatch" style="--sw:${glow}"></span>` : ""}
          </div>
          ${this._spark(points, accent)}
          <div class="tiles">${tiles.map((t) => `
            <div class="tile"><div class="tl"><ha-icon icon="${t.icon}"></ha-icon>${t.label}</div>
              <div class="tv">${t.value}</div></div>`).join("")}</div>
          ${chips ? `<div class="chips">${chips}</div>` : ""}
        </div>
      </ha-card>`;
    this.shadowRoot.querySelector("ha-card").addEventListener("click", (ev) => {
      const id = this._ids.temperature_1;
      if (!id || ev.target.closest(".chip")) return;
      this.dispatchEvent(new CustomEvent("hass-more-info", { bubbles: true, composed: true, detail: { entityId: id } }));
    });
  }
}

const STYLE = `
  :host { --k-steel-1:#e9ecef; --k-steel-2:#ced4da; --k-dark:#495057; --k-hole:#343a40; --k-ctrl:#f1f3f5;
    --k-lcd:#b2f2bb; --k-wood:#c08a5b; --k-floor:#d8c3a5; --k-pot-1:#d9825b; --k-pot-2:#7fa7b5; --k-pot-3:#c9b28f; --k-stand:#1b8a98; }
  :host([dark]) { --k-steel-1:#5c636a; --k-steel-2:#3f454b; --k-dark:#1f2326;
    --k-hole:#15181a; --k-ctrl:#4a5056; --k-lcd:#69db7c; --k-wood:#8a5d3b; --k-floor:#4a3d30; }
  ha-card { display:block; overflow:hidden; cursor:pointer; container-type:inline-size; }
  .hero { position:relative; height:112px; overflow:hidden;
    background:linear-gradient(120deg, color-mix(in srgb, var(--accent) 8%, var(--card-background-color, #fff)),
      color-mix(in srgb, var(--accent) 22%, var(--card-background-color, #fff))); }
  .hero::after { content:""; position:absolute; left:0; right:0; bottom:0; height:7px; background:var(--k-floor); }
  .head { position:relative; z-index:1; display:flex; gap:12px; align-items:flex-start; padding:14px 16px; max-width:58%; }
  .ico { flex:none; width:40px; height:40px; border-radius:50%; display:grid; place-items:center;
    background:color-mix(in srgb, var(--accent) 18%, var(--card-background-color, #fff)); color:var(--accent); }
  .ico ha-icon { --mdc-icon-size:22px; }
  .titles { min-width:0; }
  .name { display:flex; flex-wrap:wrap; align-items:center; gap:6px 8px; font-size:17px; font-weight:600;
    color:var(--primary-text-color); line-height:1.25; }
  .pill { display:inline-flex; align-items:center; gap:5px; font-size:11.5px; font-weight:600; padding:2px 8px;
    border-radius:999px; color:var(--accent); background:color-mix(in srgb, var(--accent) 15%, transparent); }
  .pill i { width:6px; height:6px; border-radius:50%; background:var(--accent); }
  .heating .pill i, .cooling .pill i { animation:blink 1.6s ease-in-out infinite; }
  .sub { margin-top:3px; font-size:12.5px; color:var(--secondary-text-color); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .scene { position:absolute; right:0; bottom:0; height:100%; width:auto; }
  .bar { height:5px; background:color-mix(in srgb, var(--accent) 22%, var(--card-background-color, #fff)); }
  .fill { height:100%; background:var(--accent); border-radius:0 3px 3px 0; transition:width .8s ease; }
  .body { padding:12px 16px 16px; display:flex; flex-direction:column; gap:12px; }
  .big { display:flex; align-items:baseline; gap:4px; color:var(--primary-text-color); }
  .num { font-size:40px; font-weight:600; letter-spacing:-1px; line-height:1; }
  .unit { font-size:16px; color:var(--secondary-text-color); }
  .swatch { align-self:center; margin-left:8px; width:14px; height:14px; border-radius:50%;
    background:var(--sw); box-shadow:0 0 10px 2px var(--sw); }
  .spark { width:100%; height:56px; display:block; }
  .spark .dot { animation:blink 2s ease-in-out infinite; }
  .spark-meta { display:flex; justify-content:space-between; margin-top:-8px; font-size:11px; color:var(--secondary-text-color); }
  .tiles { display:grid; grid-template-columns:repeat(auto-fit, minmax(96px, 1fr)); gap:8px; }
  .tile { background:var(--secondary-background-color, #f1f3f5); border-radius:12px; padding:9px 11px; min-width:0; }
  .tl { display:flex; align-items:center; gap:5px; font-size:11.5px; color:var(--secondary-text-color); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .tl ha-icon { --mdc-icon-size:15px; color:var(--accent); }
  .tv { margin-top:3px; font-size:17px; font-weight:600; color:var(--primary-text-color); white-space:nowrap; }
  .tv small { font-size:11.5px; font-weight:500; color:var(--secondary-text-color); margin-left:2px; }
  .chips { display:flex; flex-wrap:wrap; gap:6px; }
  .chip { display:inline-flex; align-items:center; gap:5px; font-size:12px; padding:4px 10px; border-radius:999px;
    background:var(--secondary-background-color, #f1f3f5); color:var(--primary-text-color); }
  .chip ha-icon { --mdc-icon-size:15px; color:var(--secondary-text-color); }
  .chip.accent { background:color-mix(in srgb, var(--accent) 15%, transparent); color:var(--accent); font-weight:600; }
  .chip.accent ha-icon { color:var(--accent); }
  .missing { padding:16px; color:var(--error-color, #db4437); }
  .waves path { animation:rise 2.4s ease-in infinite; opacity:0; }
  .waves path:nth-child(2) { animation-delay:.8s; } .waves path:nth-child(3) { animation-delay:1.6s; }
  .cool { animation:drift 3s ease-in-out infinite; }
  .pulse { animation:pulse 3s ease-in-out infinite; }
  .seam { animation:blink 3s ease-in-out infinite; }
  .blink { animation:blink 1.4s ease-in-out infinite; }
  .offline .scene { filter:grayscale(1); opacity:.7; }
  @keyframes rise { 0% { transform:translateY(10px); opacity:0 } 30% { opacity:.9 } 100% { transform:translateY(-6px); opacity:0 } }
  @keyframes drift { 0%,100% { transform:translateY(0); opacity:.5 } 50% { transform:translateY(3px); opacity:1 } }
  @keyframes pulse { 0%,100% { transform:scale(1) } 50% { transform:scale(1.15) } }
  @keyframes blink { 0%,100% { opacity:1 } 50% { opacity:.35 } }
  @container (max-width: 440px) {
    .shelf { display:none; }
    .tiles { grid-template-columns:1fr 1fr; }
  }
  @media (prefers-reduced-motion: reduce) { * { animation:none !important; } }
`;

if (!customElements.get("rohde-mykiln-card-editor")) {
  customElements.define("rohde-mykiln-card-editor", RohdeMyKilnCardEditor);
}
if (!customElements.get("rohde-mykiln-card")) {
  customElements.define("rohde-mykiln-card", RohdeMyKilnCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "rohde-mykiln-card",
    name: "ROHDE myKiln",
    description: "Kiln temperature, firing progress and glow colour",
    preview: true,
    documentationURL: "https://github.com/Y4nnickB/ha-rohde-mykiln",
  });
  console.info(`%c ROHDE-MYKILN-CARD %c ${CARD_VERSION} `, "background:#e8590c;color:#fff", "");
}
