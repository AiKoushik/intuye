/** The learner's target language, as the server describes it (GET /v1/languages).
 *  Screens never name a language or a variety themselves: they ask this. The last answer is cached
 *  so the app still knows its language offline. */
const CACHE = "lc.languages";

export class Languages {
  constructor() {
    try { this.data = JSON.parse(localStorage.getItem(CACHE) || "null"); } catch { this.data = null; }
  }

  async load(api) {
    try {
      this.data = await api.languages();
      try { localStorage.setItem(CACHE, JSON.stringify(this.data)); } catch {}
    } catch { /* keep the cached copy */ }
    return this;
  }

  get all() { return this.data?.languages ?? []; }

  /** The pack for a variety code ("es-419" -> Spanish); falls back to the server's default language. */
  forVariety(code) {
    const lang = (code || "").split("-")[0];
    return this.all.find((l) => l.code === lang) ?? this.all.find((l) => l.code === this.data?.default) ?? this.all[0] ?? UNKNOWN;
  }

  variety(code) {
    const pack = this.forVariety(code);
    return pack.varieties.find((v) => v.code === code) ?? pack.varieties.find((v) => v.code === pack.default_variety) ?? UNKNOWN.varieties[0];
  }
}

// Used only before the server has ever answered; nothing language-specific.
const UNKNOWN = { code: "", name: "your new language", native_name: "", default_variety: "", ui: {},
  varieties: [{ code: "", label: "", tts: "", stt: "" }] };
