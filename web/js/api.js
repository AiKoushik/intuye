// API client mirroring ios/Packages/LangCoachKit/APIClient.swift: bearer auth, single-flight refresh
// rotation, sign-out on revoked sessions. Web test build only: tokens live in localStorage.
const KEY = "lc.session";
const SIGN_OUT_CODES = new Set(["invalid_refresh", "session_revoked", "refresh_reuse", "refresh_expired", "invalid_token"]);

export class APIError extends Error {
  constructor(status, code, message) { super(message); this.status = status; this.code = code; }
}

export class API {
  constructor(base = "") {
    this.base = base;
    this.refreshing = null;
    this.onSignedOut = () => {};
  }

  get session() { try { return JSON.parse(localStorage.getItem(KEY)); } catch { return null; } }
  set session(s) { s ? localStorage.setItem(KEY, JSON.stringify(s)) : localStorage.removeItem(KEY); }

  async send(method, path, body, { auth = true, raw = false } = {}) {
    try {
      return await this.#perform(method, path, body, auth, raw);
    } catch (e) {
      if (auth && e.status === 401 && e.code === "token_expired") {
        await this.#refreshed(true);
        return this.#perform(method, path, body, auth, raw);
      }
      throw e;
    }
  }

  async #perform(method, path, body, auth, raw) {
    const headers = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (auth) headers.Authorization = `Bearer ${(await this.#refreshed(false)).access_token}`;
    let res;
    try {
      res = await fetch(this.base + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    } catch {
      throw new APIError(0, "offline", "Couldn't reach your coach. Is the backend running?");
    }
    if (!res.ok) {
      let env = null;
      try { env = await res.json(); } catch {}
      const err = new APIError(res.status, env?.error?.code ?? `http_${res.status}`, env?.error?.message ?? `Something went wrong (${res.status}).`);
      if (res.status === 401 && SIGN_OUT_CODES.has(err.code)) { this.session = null; this.onSignedOut(); }
      throw err;
    }
    if (raw) return res.blob();
    if (res.status === 204) return null;
    const text = await res.text();
    return text ? JSON.parse(text) : null;
  }

  async #refreshed(force) {
    const s = this.session;
    if (!s) throw new APIError(401, "missing_token", "Sign in to continue.");
    if (!force && s.expiry > Date.now() + 30000) return s;
    if (!this.refreshing) {
      this.refreshing = (async () => {
        try {
          const r = await this.#perform("POST", "/v1/auth/refresh", { refresh_token: s.refresh_token }, false, false);
          return this.#store(r);
        } finally { this.refreshing = null; }
      })();
    }
    return this.refreshing;
  }

  #store(r) {
    const s = { access_token: r.access_token, refresh_token: r.refresh_token, expiry: Date.now() + r.expires_in * 1000 };
    this.session = s;
    return s;
  }

  // Auth
  async devSignIn(name) { const r = await this.send("POST", "/v1/auth/dev", { name }, { auth: false }); this.#store(r); return r.user; }
  async signOut() {
    const s = this.session;
    if (s) { try { await this.send("POST", "/v1/auth/logout", { refresh_token: s.refresh_token }, { auth: false }); } catch {} }
    this.session = null;
  }
  me() { return this.send("GET", "/v1/me"); }
  updateSettings(patch) { return this.send("PATCH", "/v1/me/settings", patch); }
  exportAccount() { return this.send("GET", "/v1/account/export", undefined, { raw: true }); }
  async deleteAccount() { await this.send("DELETE", "/v1/account"); this.session = null; }

  // Features
  coach(text, direction = "auto") { return this.send("POST", "/v1/coach", { text, direction }); }
  upload(items) { return this.send("POST", "/v1/utterances", { items }); }
  forget(minutes) { return this.send("POST", "/v1/utterances/forget", { minutes }); }
  nextBatch(size = 7) { return this.send("POST", "/v1/batches/next", { size }); }
  async dueCards() { return (await this.send("GET", "/v1/reviews/due")).items; }
  review(lexeme_id, rating) { return this.send("POST", "/v1/reviews", { lexeme_id, rating }); }
  pronunciation(lexeme_id, expected, heard) { return this.send("POST", "/v1/pronunciation", { lexeme_id, expected, heard }); }
  scenarios() { return this.send("GET", "/v1/scenarios"); }
  scenario(id) { return this.send("GET", `/v1/scenarios/${id}`); }
  createScenario(title, starts_at, kind = "manual") { return this.send("POST", "/v1/scenarios", { title, starts_at, kind }); }
  async importCalendar(events) { return (await this.send("POST", "/v1/scenarios/calendar", { events })).created; }
  setScenarioStatus(id, status) { return this.send("PATCH", `/v1/scenarios/${id}`, { status }); }
  rate(id, value, phase) { return this.send("POST", `/v1/scenarios/${id}/readiness`, { value, phase }); }
  startRehearsal(scenario_id, difficulty) { return this.send("POST", "/v1/rehearsals", { scenario_id, difficulty }); }
  rehearsalTurn(id, text) { return this.send("POST", `/v1/rehearsals/${id}/turns`, { text }); }
  endRehearsal(id) { return this.send("POST", `/v1/rehearsals/${id}/end`); }
  progress() { return this.send("GET", "/v1/progress"); }
  today() { return this.send("GET", "/v1/today"); }
}
