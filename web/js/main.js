// Intuye web test build: the iPhone app's screens running against the local backend.
import { API } from "./api.js";
import { h, icon } from "./dom.js";
import { Languages } from "./language.js";
import { NATIVE_LOCALE, Recognizer } from "./speech.js";
import { Onboarding } from "./screens/onboarding.js";
import { Today } from "./screens/today.js";
import { Say } from "./screens/say.js";
import { Scenes } from "./screens/scenes.js";
import { ProgressScreen } from "./screens/progress.js";
import { CaptureSheet } from "./screens/settings.js";

const TABS = [
  { id: "today", label: "Today", icon: "today", make: (app) => new Today(app) },
  { id: "say", label: "Say", icon: "say", make: (app) => new Say(app) },
  { id: "scenes", label: "Scenes", icon: "scenes", make: (app) => new Scenes(app) },
  { id: "progress", label: "Progress", icon: "progress", make: (app) => new ProgressScreen(app) },
];

/** Ambient capture: continuous recognition while on, queued and uploaded like the iPhone's OfflineQueue. */
class Capture {
  constructor(app) {
    this.app = app;
    this.mode = localStorage.getItem("lc.captureMode") || "off";
    this.listening = false;
    this.paused = false;
    this.error = null;
    this.queue = JSON.parse(localStorage.getItem("lc.queue") || "[]");
    setInterval(() => { this.reconcile(); this.flush(); }, 30000);
  }

  get key() { return `lc.sentences.${new Date().toISOString().slice(0, 10)}`; }
  get count() { return Number(localStorage.getItem(this.key) || 0); }
  bump(n = 1) { localStorage.setItem(this.key, String(this.count + n)); this.app.renderAccessory(); }
  save() { localStorage.setItem("lc.queue", JSON.stringify(this.queue)); }

  setMode(mode) {
    this.mode = mode;
    localStorage.setItem("lc.captureMode", mode);
    this.reconcile();
  }

  get shouldListen() {
    if (this.paused || !this.app.api.session) return false;
    if (this.mode === "always") return true;
    if (this.mode === "windows") { const hr = new Date().getHours(); return (hr >= 9 && hr < 12) || (hr >= 18 && hr < 21); }
    return false;
  }

  async reconcile() {
    if (this.shouldListen && !this.listening) {
      try {
        this.app.recognizer.start("en-US", { continuous: true, onFinal: (s) => this.captured(s) });
        this.listening = true;
        this.error = null;
      } catch (e) { this.error = e.message; }
    } else if (!this.shouldListen && this.listening) {
      this.listening = false;
      await this.app.recognizer.stop();
    }
    this.app.renderAccessory();
  }

  captured(sentence) {
    if (sentence.split(/\s+/).length < 2) return;
    this.queue.push({ text: sentence, spoken_at: new Date().toISOString(), source: "ambient" });
    this.save();
    this.bump();
    if (this.queue.length >= 10) this.flush();
  }

  async flush() {
    if (!this.queue.length || !this.app.api.session) return;
    const batch = this.queue.slice(0, 200);
    try {
      await this.app.api.upload(batch);
      this.queue.splice(0, batch.length);
      this.save();
    } catch { /* keep for next time */ }
  }

  /** Test helper: post sentences as if capture had heard them. */
  async simulate(lines) {
    const now = new Date().toISOString();
    const r = await this.app.api.upload(lines.map((text) => ({ text, spoken_at: now, source: "ambient" })));
    this.bump(r.accepted);
    return r;
  }

  async forget(minutes) {
    const cutoff = Date.now() - minutes * 60000;
    this.queue = this.queue.filter((q) => new Date(q.spoken_at).getTime() < cutoff);
    this.save();
    return (await this.app.api.forget(minutes)).deleted;
  }
}

/** iOS shows the previous title on the back button, or "Back" when it won't fit. */
const backLabel = (title) => (title && title.length <= 12 ? title : "Back");

class App {
  constructor(root) {
    this.root = root;
    this.api = new API("");
    this.recognizer = new Recognizer();
    this.capture = new Capture(this);
    this.languages = new Languages();
    this.me = null;
    this.tab = "today";
    this.stacks = {};
    this.api.onSignedOut = () => this.showOnboarding();
    window.addEventListener("online", () => this.syncReviews());
  }

  get dialect() { return this.me?.settings?.dialect ?? this.languages.data?.languages?.[0]?.default_variety ?? ""; }
  /** The learner's target language (name, varieties, copy) and variety (voice and speech locales), from the server. */
  get lang() { return this.languages.forVariety(this.dialect); }
  get variety() { return this.languages.variety(this.dialect); }
  get tts() { return this.variety.tts; }
  /** Speech-recognition locale: the target language, or the learner's own (English) when `target` is false. */
  stt(target) { return target ? this.variety.stt : NATIVE_LOCALE; }
  get firstName() { return this.me?.user?.display_name?.split(" ")[0] ?? null; }

  async boot() {
    await this.languages.load(this.api);
    document.title = `Intuye: ${this.lang.name} in your own words`;
    if (!this.api.session) return this.showOnboarding();
    await this.loadMe();
    this.showTabs();
    this.capture.reconcile();
    this.syncReviews();
  }

  /** Sends reviews done offline, then tells the learner once they're in. */
  async syncReviews() {
    const before = this.api.queuedReviews;
    if (!before) return;
    const left = await this.api.flushReviews();
    if (left < before) this.toast(`Synced ${before - left} ${before - left === 1 ? "review" : "reviews"} done offline`);
  }

  async loadMe() { try { this.me = await this.api.me(); } catch { /* shown by screens */ } }

  showOnboarding() {
    this.capture.listening && this.recognizer.stop();
    this.capture.listening = false;
    this.dismissAll();
    this.root.replaceChildren(new Onboarding(this).mountOnboarding());
  }

  async didSignIn() {
    await this.loadMe();
    this.tab = "say";
    this.showTabs();
  }

  async signOut() {
    await this.api.signOut();
    this.me = null;
    this.showOnboarding();
  }

  // ---------- tabs & navigation
  showTabs() {
    this.stacks = Object.fromEntries(TABS.map((t) => [t.id, [t.make(this)]]));
    this.host = h("div", { style: "position:absolute;inset:0" });
    this.accessory = h("button", { class: "accessory glass", type: "button", onclick: () => this.present(new CaptureSheet(this), "large") });
    this.tabbar = h("nav", { class: "tabbar glass", "aria-label": "Tabs" });
    this.root.replaceChildren(this.host, this.accessory, this.tabbar);
    this.renderTabbar();
    this.renderAccessory();
    this.render();
  }

  selectTab(id) {
    if (this.tab === id) {
      if (this.stacks[id].length > 1) { this.stacks[id] = [this.stacks[id][0]]; this.render("enter-back"); }
      return;
    }
    this.tab = id;
    this.renderTabbar();
    this.render();
  }

  renderTabbar() {
    this.tabbar?.replaceChildren(...TABS.map((t) => h("button", {
      class: `tab${this.tab === t.id ? " on" : ""}`, type: "button", "aria-current": this.tab === t.id ? "page" : null,
      onclick: () => this.selectTab(t.id),
    }, icon(t.icon), t.label)));
  }

  renderAccessory() {
    if (!this.accessory) return;
    const on = this.capture.listening;
    this.accessory.replaceChildren(
      h("span", { class: `dot${on ? " on" : ""}`, "aria-hidden": "true" }),
      h("span", {}, on ? "Listening" : "Capture off"),
      h("span", { class: "count" }, `${this.capture.count} sentences today`),
    );
    this.accessory.setAttribute("aria-label", on ? `Capture on, ${this.capture.count} sentences today` : "Capture off");
  }

  render(anim = null) {
    const stack = this.stacks[this.tab];
    const top = stack[stack.length - 1];
    if (!top.el) top.mount({ back: stack.length > 1 ? backLabel(stack[stack.length - 2].title) : null });
    else top.refresh();
    this.host.replaceChildren(top.el);
    top.el.classList.remove("enter", "enter-back");
    if (anim) { void top.el.offsetWidth; top.el.classList.add(anim); }
  }

  push(screen) { this.stacks[this.tab].push(screen); this.render("enter"); }
  pop() { const s = this.stacks[this.tab]; if (s.length > 1) { s.pop(); this.render("enter-back"); } }


  // ---------- sheets, covers, toasts
  present(screen, detent = "large") {
    const layer = h("div", { class: "sheet-layer" });
    const body = h("div", { style: "position:relative;flex:1;min-height:0" }, screen.mount({ isSheet: true }));
    const sheet = h("div", { class: `sheet ${detent}`, role: "dialog", "aria-modal": "true" }, h("div", { class: "grabber" }), body);
    layer.append(sheet);
    layer.addEventListener("click", (e) => { if (e.target === layer) this.dismiss(screen); });
    screen.layer = layer;
    screen.el.style.background = "var(--lc-canvas)";
    this.root.append(layer);
    return screen;
  }

  dismiss(screen) {
    screen?.layer?.remove();
    screen?.onDismiss?.();
  }

  presentCover(screen) {
    const el = screen.mountCover();
    screen.layer = el;
    this.root.append(el);
  }

  dismissAll() { this.root.querySelectorAll(".sheet-layer,.cover").forEach((n) => n.remove()); }

  toast(message) {
    const t = h("div", { class: "toast glass", role: "status" }, message);
    this.root.append(t);
    setTimeout(() => t.remove(), 2200);
  }

  /** Hold-to-talk borrows the recognizer from ambient capture and gives it back afterwards. */
  async holdBegin(lang) {
    this.capture.paused = true;
    if (this.capture.listening) { this.capture.listening = false; await this.recognizer.stop(); }
    this.recognizer.start(lang);
  }

  async holdEnd() {
    const text = await this.recognizer.stop();
    this.capture.paused = false;
    this.capture.reconcile();
    return text;
  }
}

// Theme toggle (side panel) — follows the system until pressed.
const themeBtn = document.getElementById("theme-toggle");
themeBtn?.addEventListener("click", () => {
  const dark = document.documentElement.dataset.theme !== "dark" &&
    !(document.documentElement.dataset.theme !== "light" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  themeBtn.textContent = dark ? "Light mode" : "Dark mode";
  themeBtn.setAttribute("aria-pressed", String(dark));
});
const clock = document.getElementById("clock");
const tick = () => { if (clock) clock.textContent = new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }).replace(/\s?[AP]M$/i, ""); };
tick(); setInterval(tick, 15000);

const app = new App(document.getElementById("app"));
window.lcApp = app;
app.boot();
