import { h, icon } from "../dom.js";
import { chipDir, emptyCard, errorBanner, holdToTalk, interlinear } from "../components.js";
import { localeFor, speak, speechSupported } from "../speech.js";
import { Screen, navButton } from "./base.js";

// Phrasebook (H9): kept on device, like the iPhone app.
export const Phrasebook = {
  key: "lc.phrasebook",
  all() { try { return JSON.parse(localStorage.getItem(this.key)) || []; } catch { return []; } },
  has(id) { return this.all().some((e) => e.id === id); },
  toggle(r) {
    const all = this.all();
    const i = all.findIndex((e) => e.id === r.id);
    if (i >= 0) all.splice(i, 1);
    else all.unshift({ id: r.id, spanish: r.intent === "to_es" ? r.close : r.source, english: r.intent === "to_es" ? r.source : r.close });
    localStorage.setItem(this.key, JSON.stringify(all));
  },
};

export class Say extends Screen {
  constructor(app) {
    super(app);
    this.title = "Say";
    this.items = [];
    this.busy = false;
    this.pending = "";
    this.listenSpanish = false;
    this.err = null;
  }

  navRight() {
    return [
      navButton("", () => { this.listenSpanish = !this.listenSpanish; this.app.toast(this.listenSpanish ? "Mic listens for Spanish" : "Mic listens for English or Spanglish"); this.renderNav(); },
        { iconName: "globe", aria: this.listenSpanish ? "Speech language: Spanish" : "Speech language: English" }),
      navButton("", () => this.app.push(new PhrasebookScreen(this.app)), { iconName: "star", aria: "Phrasebook" }),
    ];
  }

  bottomBar() {
    this.field = h("textarea", { class: "field", rows: "1", placeholder: "Say or type anything", "aria-label": "Say or type anything" });
    this.field.addEventListener("input", () => { this.field.style.height = "auto"; this.field.style.height = `${Math.min(this.field.scrollHeight, 120)}px`; });
    this.field.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); this.send(this.field.value); }
      if (e.key === " " && !this.field.value && !e.repeat) { e.preventDefault(); this.mic.begin(); }
    });
    this.field.addEventListener("keyup", (e) => { if (e.key === " " && this.app.recognizer.running) this.mic.end(); });
    this.mic = holdToTalk({ onBegin: () => this.beginTalking(), onEnd: () => this.endTalking() });
    this.app.recognizer.on((r) => { if (this.talking) this.field.value = r.text; });
    return h("div", {}, this.field, this.mic);
  }

  content() {
    const out = [];
    if (!this.items.length && !this.busy) {
      out.push(emptyCard("Say anything in English, Spanish or a mix — like “me gusta escuchar esto en mi mind” or “what does cómo te va mean?”"));
      if (!speechSupported) out.push(h("p", { class: "fine", style: "margin:4px 4px 12px" }, "This browser can't do speech. Type instead, or use Chrome or Edge."));
    }
    for (const r of this.items) out.push(r.intent === "ask" ? this.answerCard(r) : this.resultCard(r));
    if (this.busy) out.push(h("div", { class: "card", "aria-label": "Translating" },
      h("p", { class: "secondary", style: "font-size:16px" }, this.pending || " "), h("div", { class: "shimmer" })));
    if (this.err) out.push(errorBanner(this.err, () => this.send(this.lastText)));
    return out;
  }

  resultCard(r) {
    const saved = Phrasebook.has(r.id);
    const spanish = r.intent === "to_es" ? r.close : r.source;
    return h("div", { class: "card" },
      h("div", { class: "split", style: "margin-bottom:10px" }, chipDir(r.intent),
        h("span", {},
          h("button", { class: "iconbtn", type: "button", "aria-label": "Play Spanish", onclick: () => speak(spanish, this.app.dialect) }, icon("speaker")),
          h("button", { class: "iconbtn", type: "button", "aria-label": saved ? "Remove from phrasebook" : "Save to phrasebook",
            onclick: () => { Phrasebook.toggle(r); this.update(); } }, icon(saved ? "star-fill" : "star")))),
      interlinear(r.alignment, { toEn: r.intent === "to_en" }),
      r.natural ? h("details", { class: "natural" }, h("summary", {}, "More natural"), h("p", {}, r.natural)) : null);
  }

  answerCard(r) {
    return h("div", { class: "card" }, h("p", { class: "answer-q" }, r.source), h("p", { class: "body" }, r.answer));
  }

  async send(text) {
    const t = (text || "").trim();
    if (!t || this.busy) return;
    this.lastText = t;
    this.busy = true; this.err = null; this.pending = t;
    this.field.value = ""; this.field.style.height = "auto";
    this.update(); this.scrollToBottom();
    try {
      const r = await this.api.coach(t);
      r.id = r.utterance_id || `${Date.now()}`;
      this.items.push(r);
    } catch (e) {
      this.err = e.code === "offline" ? "Couldn't reach your coach. Your sentence is still here; retry when the backend is up." : e.message;
      this.field.value = t;
    }
    this.busy = false;
    this.update(); this.scrollToBottom();
  }

  async beginTalking() {
    try {
      this.talking = true;
      this.field.placeholder = "Listening…";
      await this.app.holdBegin(localeFor(this.app.dialect, this.listenSpanish));
    } catch (e) {
      this.talking = false; this.mic.end?.();
      this.err = e.message; this.update();
    }
  }

  async endTalking() {
    if (!this.talking) return;
    const text = await this.app.holdEnd();
    this.talking = false;
    this.field.placeholder = "Say or type anything";
    await this.send(text || this.field.value);
  }
}

class PhrasebookScreen extends Screen {
  constructor(app) { super(app); this.title = "Phrasebook"; this.large = false; this.q = ""; }
  content() {
    const all = Phrasebook.all().filter((e) => !this.q || `${e.spanish} ${e.english}`.toLowerCase().includes(this.q.toLowerCase()));
    const search = h("input", { class: "text-input", placeholder: "Search", value: this.q, style: "margin:4px 0 12px",
      oninput: (e) => { this.q = e.target.value; clearTimeout(this.t); this.t = setTimeout(() => { this.update(); this.scrollEl.querySelector("input")?.focus(); }, 250); } });
    if (!Phrasebook.all().length) return [h("p", { class: "empty", style: "margin-top:12px" }, "Tap the star on any result to keep it here.")];
    return [search, h("div", { class: "group" }, all.map((e) => h("button", { class: "row", type: "button", onclick: () => speak(e.spanish, this.app.dialect) },
      h("span", { class: "grow" }, h("span", { class: "es", style: "display:block;font-size:18px" }, e.spanish), h("span", { class: "meta" }, e.english)),
      icon("speaker", "chev"))))];
  }
}
