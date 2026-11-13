import { h, icon, whenLabel } from "../dom.js";
import { dots, interlinear, readyDots, spinner, tintChip, topicTile, topicTint } from "../components.js";
import { localeFor, speak } from "../speech.js";
import { Screen, navButton } from "./base.js";
import { Rehearse } from "./rehearse.js";

const usedLabel = (n) => (n === 1 ? "1 use" : `${n} uses`);
const topicLabel = (tint) => ({ sage: "Health and body", sea: "Work and study", sand: "Home and family", rose: "Food and friends", plum: "Travel and errands" })[tint];

export class Scenes extends Screen {
  ambient() { return ["sage", "sea"]; }
  constructor(app) { super(app); this.title = "Scenes"; this.list = null; this.q = ""; this.results = null; this.popular = []; this.listening = false; }
  async load() { [this.list, this.popular] = await Promise.all([this.api.scenarios(), this.api.library("", 5)]); }
  navRight() { return [navButton("", () => this.newScene(""), { iconName: "plus", aria: "Something coming up" })]; }
  newScene(title) { this.app.present(new NewSceneSheet(this.app, (scene) => this.created(scene), title)); }

  created(scene) {
    this.q = ""; this.results = null; if (this.input) this.input.value = ""; this.refresh();
    if (scene) this.app.push(new SceneDetail(this.app, scene.id));
  }

  /** Search field: type, or tap the mic and say it. Speech becomes text on the device; only text is searched. */
  searchField() {
    this.input ??= h("input", { type: "search", placeholder: "Find or add a scene", "aria-label": "Find or add a scene", enterkeyhint: "search",
      oninput: (e) => { this.q = e.target.value; clearTimeout(this.t); this.t = setTimeout(() => this.search(), 300); },
      onkeydown: (e) => { if (e.key === "Enter") { clearTimeout(this.t); this.search(); } } });
    this.micBtn ??= h("button", { class: "lib-mic", type: "button", "aria-label": "Say a scene", onclick: () => this.toggleMic() }, icon("mic"));
    this.micBtn.classList.toggle("on", this.listening);
    this.micBtn.setAttribute("aria-pressed", String(this.listening));
    this.searchEl ??= h("div", { class: "lib-search", role: "search" }, icon("search"), this.input, this.micBtn);
    return this.searchEl;
  }

  async toggleMic() {
    const placeholder = "Find or add a scene";
    if (this.listening) {
      this.listening = false; this.offRec?.();
      const text = await this.app.holdEnd();
      this.input.placeholder = placeholder;
      if (text) { this.q = text; this.input.value = text; await this.search(); } else this.update();
      return;
    }
    try {
      this.listening = true; this.input.placeholder = "Listening…"; this.update();
      await this.app.holdBegin(localeFor(this.app.dialect, false));
      // Subscribe after the recognizer starts, so ambient capture stopping doesn't end this search.
      this.offRec = this.app.recognizer.on((r) => {
        if (!this.listening) return;
        this.input.value = r.text;
        if (!r.running) this.toggleMic();
      });
    } catch (e) { this.listening = false; this.input.placeholder = placeholder; this.app.toast(e.message); this.update(); }
  }

  async search() {
    const q = this.q.trim();
    if (!q) { this.results = null; this.update(); return; }
    try {
      const res = await this.api.library(q);
      if (q !== this.q.trim()) return;
      const typing = document.activeElement === this.input;
      this.results = res; this.update();
      if (typing) this.input.focus();  // re-rendering moves the field; keep the keyboard up
    }
    catch (e) { this.error = e.message; this.update(); }
  }

  libraryRow(t) {
    return h("button", { class: "row", type: "button", onclick: () => this.app.push(new LibraryScene(this.app, t.id, (scene) => this.created(scene))) },
      topicTile(t.topic, t.title),
      h("span", { class: "grow" }, h("span", { style: "display:block" }, t.title), h("span", { class: "meta" }, t.situation)),
      h("span", { class: "uses" }, usedLabel(t.uses)), icon("chevron", "chev"));
  }

  content() {
    if (!this.list) return this.loaded ? [this.searchField()] : [this.searchField(), spinner()];
    const out = [this.searchField()];
    if (this.results) {
      const q = this.q.trim();
      out.push(h("p", { class: "group-title" }, this.results.length ? "In the library" : "Nothing like this in the library yet"),
        h("div", { class: "group" }, this.results.map((t) => this.libraryRow(t)),
          h("button", { class: "row build", type: "button", onclick: () => this.newScene(q) }, icon("plus"), h("span", { class: "grow" }, `Build “${q}”`))),
        h("p", { class: "group-footer" }, "Matched by meaning, so “going to the dentist's” finds “At the dentist”."));
      return out;
    }
    const { upcoming, recurring, mine } = this.list;
    if (!upcoming.length && !recurring.length && !mine.length) {
      out.push(h("p", { class: "empty", style: "margin:14px 4px 0" }, "Search for something coming up — a dentist visit, a meeting, dinner with friends — or build your own and get the Spanish for it."));
    }
    for (const [label, items] of [["Coming up", upcoming], ["From your conversations", recurring], ["Yours", mine]]) {
      if (!items.length) continue;
      out.push(h("p", { class: "group-title" }, label), h("div", { class: "group" }, items.map((s) => this.row(s))));
    }
    if (this.popular.length) {
      out.push(h("p", { class: "group-title" }, "Popular in the library"), h("div", { class: "group" }, this.popular.map((t) => this.libraryRow(t))));
    }
    out.push(h("p", { class: "group-title" }, " "),
      h("div", { class: "group" }, h("button", { class: "row action", type: "button", onclick: () => this.app.present(new CalendarSheet(this.app, () => this.created(null))) },
        icon("calendar"), h("span", { class: "grow" }, "Use my calendar"))),
      h("p", { class: "group-footer" }, "Only event titles and times for the next two weeks are sent, and calendar scenes are never shared. The web build lets you type test events."));
    return out;
  }

  row(s) {
    if (s.status === "suggested") {
      return h("div", { class: "row" }, topicTile(s.topic, s.title),
        h("span", { class: "grow" }, h("span", { style: "display:block" }, s.title), h("span", { class: "meta" }, "Suggested from what you talk about")),
        h("button", { class: "btn inline subtle", type: "button", onclick: async () => { await this.api.setScenarioStatus(s.id, "done"); this.refresh(); } }, "Not now"),
        h("button", { class: "btn inline", type: "button", onclick: async () => { await this.api.setScenarioStatus(s.id, "active"); this.refresh(); } }, "Add"));
    }
    return h("button", { class: "row", type: "button", onclick: () => this.app.push(new SceneDetail(this.app, s.id)) },
      topicTile(s.topic, s.title),
      h("span", { class: "grow" }, h("span", { style: "display:block" }, s.title), h("span", { class: "meta" }, whenLabel(s))),
      dots(s.readiness.current, topicTint(s.topic, s.title)), icon("chevron", "chev"));
  }
}

export class SceneDetail extends Screen {
  ambient() { return ["sand", "sea"]; }
  constructor(app, id) { super(app); this.id = id; this.title = ""; this.large = false; this.scene = null; }
  async load() { this.scene = await this.api.scenario(this.id); this.title = this.scene.title; }

  content() {
    const s = this.scene;
    if (!s) return this.loaded ? [] : [spinner()];
    const p = s.phrases || { key: [], rescue: [], hear: [] };
    return [
      h("p", { class: "date", style: "display:flex;align-items:center;gap:8px" }, tintChip(topicTint(s.topic, s.title), topicLabel(topicTint(s.topic, s.title))), whenLabel(s)),
      h("h1", { class: "large-title" }, s.title),
      h("div", { class: "card split", style: "padding:6px 8px 6px 16px" }, h("span", { class: "body" }, "How ready do you feel?"),
        readyDots(s.readiness.current, (v) => this.rate(v), topicTint(s.topic, s.title))),
      h("p", { class: "section-label" }, "Key phrases"),
      h("div", { class: "card" }, p.key.map((ph) => h("div", { class: "phrase-row" },
        interlinear(ph.alignment.map((a) => ({ src: a.src, tgt: a.tgt }))),
        h("button", { class: "iconbtn", type: "button", "aria-label": `Play ${ph.es}`, onclick: () => speak(ph.es, this.app.dialect) }, icon("speaker"))))),
      h("p", { class: "section-label" }, "If you get stuck"),
      h("div", { class: "card wash t-rose" }, p.rescue.map((r) => h("button", { class: "rescue", type: "button", onclick: () => speak(r.es, this.app.dialect, true) }, r.es))),
      h("p", { class: "section-label" }, "You might hear"),
      h("div", { class: "card wash t-sea" }, p.hear.map((x) => h("div", { style: "padding:6px 0" },
        h("button", { class: "rescue", style: "padding:0", type: "button", onclick: () => speak(x.es, this.app.dialect, true) }, x.es),
        h("p", { class: "meta" }, x.en)))),
      h("button", { class: "btn", type: "button", onclick: () => this.app.push(new Rehearse(this.app, s)) }, "Rehearse"),
      h("button", { class: "btn quiet", type: "button", onclick: () => this.finish() }, icon("check"), "I'm done with this scene"),
    ];
  }

  async finish() {
    try {
      await this.api.setScenarioStatus(this.scene.id, "done");
      this.app.pop();
      this.app.stacks[this.app.tab].at(-1)?.refresh?.();
      this.app.toast("Scene moved out of your list");
    }
    catch (e) { this.error = e.message; this.update(); }
  }

  async rate(v) {
    await this.api.rate(this.scene.id, v, this.scene.readiness.before == null ? "before" : "after");
    this.refresh();
  }
}

/** A library scene before you add it: what it covers, who shared it, its phrases. */
export class LibraryScene extends Screen {
  ambient() { return ["sage", "plum"]; }
  constructor(app, id, onUsed) { super(app); this.id = id; this.onUsed = onUsed; this.title = ""; this.large = false; this.t = null; }
  async load() { this.t = await this.api.libraryScene(this.id); this.title = this.t.title; this.renderNav(); }

  content() {
    const t = this.t;
    if (!t) return this.loaded ? [] : [spinner()];
    const p = t.phrases;
    return [
      tintChip(topicTint(t.topic, t.title), topicLabel(topicTint(t.topic, t.title))),
      h("h1", { class: "large-title" }, t.title),
      h("p", { class: "situation" }, t.situation),
      h("p", { class: "lib-meta" }, icon("people"), `${usedLabel(t.uses)}. ${t.credit ? `Shared by ${t.credit}` : "Shared anonymously"}.`),
      h("button", { class: "btn", type: "button", onclick: () => this.use() }, "Use this scene"),
      h("p", { class: "section-label" }, "Key phrases"),
      h("div", { class: "card" }, p.key.map((ph) => h("div", { class: "phrase-row" },
        interlinear((ph.alignment || []).map((a) => ({ src: a.src, tgt: a.tgt }))),
        h("button", { class: "iconbtn", type: "button", "aria-label": `Play ${ph.es}`, onclick: () => speak(ph.es, this.app.dialect) }, icon("speaker"))))),
      h("p", { class: "section-label" }, "If you get stuck"),
      h("div", { class: "card wash t-rose" }, p.rescue.map((r) => h("button", { class: "rescue", type: "button", onclick: () => speak(r.es, this.app.dialect, true) }, r.es))),
      h("button", { class: "btn quiet", type: "button", onclick: () => this.app.present(new ReportSheet(this.app, t)) }, icon("flag"), "Report this scene"),
    ];
  }

  async use() {
    try {
      const scene = await this.api.useLibraryScene(this.id);
      this.app.pop();
      this.onUsed?.(scene);
      this.app.toast("Added to your scenes");
    } catch (e) { this.error = e.message; this.update(); }
  }
}

class ReportSheet extends Screen {
  constructor(app, t) { super(app); this.t = t; this.title = "Report scene"; this.large = false; }
  navLeft() { return navButton("Cancel", () => this.app.dismiss(this)); }
  content() {
    const reasons = [["personal", "It has someone's personal details"], ["offensive", "It's offensive or unsafe"], ["wrong", "The Spanish is wrong"], ["other", "Something else"]];
    return [h("p", { class: "group-title" }, `What's wrong with “${this.t.title}”?`),
      h("div", { class: "group" }, reasons.map(([key, label]) => h("button", { class: "row", type: "button", onclick: () => this.send(key) }, h("span", { class: "grow" }, label)))),
      h("p", { class: "group-footer" }, "Scenes reported by three learners are hidden until we review them.")];
  }
  async send(reason) {
    try { await this.api.reportLibraryScene(this.t.id, reason); this.app.dismiss(this); this.app.toast("Thanks. We'll take a look."); }
    catch (e) { this.error = e.message; this.update(); }
  }
}

const SHARED_TOAST = {
  shared: (l) => (l.credit === "name" ? "Added to the library with your name" : "Added to the library, anonymously"),
  already_in_library: (l) => `Already in the library as “${l.template.title}”`,
  private: (l) => (l.reason === "personal" ? "Kept private: it's personal to you" : "Scene ready"),
};

class NewSceneSheet extends Screen {
  constructor(app, onCreated, title = "") {
    super(app); this.title = "New scene"; this.large = false; this.onCreated = onCreated; this.name = title; this.details = "";
    this.hasDate = false; this.share = true; this.showName = false; this.busy = false;
  }

  navLeft() { return navButton("Cancel", () => this.app.dismiss(this)); }
  navRight() { return [navButton(this.busy ? "Preparing…" : "Prepare", () => this.create(), { strong: true, disabled: this.busy || this.name.trim().length < 2 })]; }

  content() {
    const tomorrow = new Date(Date.now() + 86400000); tomorrow.setMinutes(0, 0, 0);
    const local = new Date(tomorrow.getTime() - tomorrow.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    this.dateInput ??= h("input", { type: "datetime-local", class: "input", value: local, style: "text-align:right;width:auto" });
    this.detailsInput ??= h("textarea", { class: "input", rows: "3", placeholder: "Anything that changes what you'll say, e.g. the teacher only speaks Spanish",
      maxlength: "600", oninput: (e) => { this.details = e.target.value; } });
    const toggle = (label, checked, onchange, disabled = false) => h("label", { class: "row" }, h("span", { class: "grow" }, label),
      h("input", { type: "checkbox", class: "switch", role: "switch", checked, disabled, onchange }));
    return [
      h("p", { class: "group-title" }, "What's coming up?"),
      h("div", { class: "group" }, h("div", { class: "row" }, h("input", { class: "input", placeholder: "e.g. Dentist, parent-teacher meeting", value: this.name,
        "aria-label": "Scene", oninput: (e) => { this.name = e.target.value; this.renderNav(); } }))),
      h("p", { class: "group-title" }, "Details (optional, never shared)"),
      h("div", { class: "group" }, h("div", { class: "row" }, this.detailsInput)),
      h("p", { class: "group-title" }, " "),
      h("div", { class: "group" },
        toggle("It has a date", this.hasDate, (e) => { this.hasDate = e.target.checked; this.update(); }),
        this.hasDate ? h("div", { class: "row" }, h("span", { class: "grow" }, "When"), this.dateInput) : null),
      h("p", { class: "group-title" }, "Library"),
      h("div", { class: "group" },
        toggle("Share with other learners", this.share, (e) => { this.share = e.target.checked; this.update(); }),
        toggle("Show my name", this.share && this.showName, (e) => { this.showName = e.target.checked; }, !this.share)),
      h("p", { class: "group-footer" }, "We share a general version with names, places and your details removed, and only if it isn't in the library already."),
    ];
  }

  async create() {
    this.busy = true; this.renderNav();
    try {
      const startsAt = this.hasDate ? new Date(this.dateInput.value).toISOString() : null;
      const scene = await this.api.createScenario(this.name.trim(), startsAt, "manual",
        { details: this.details.trim() || null, share: this.share, credit: this.share && this.showName ? "name" : "anonymous" });
      this.app.dismiss(this);
      this.onCreated?.(scene);
      const lib = scene.library;
      this.app.toast(lib ? (SHARED_TOAST[lib.status] || (() => "Scene ready"))(lib) : "Scene ready");
    } catch (e) { this.error = e.message; this.busy = false; this.renderNav(); this.update(); }
  }
}

/** Web stand-in for EventKit: type events as "Title, YYYY-MM-DD HH:MM". */
class CalendarSheet extends Screen {
  constructor(app, onDone) { super(app); this.title = "Calendar (test)"; this.large = false; this.onDone = onDone; }
  navLeft() { return navButton("Cancel", () => this.app.dismiss(this)); }
  navRight() { return [navButton("Import", () => this.import(), { strong: true })]; }
  content() {
    const d = new Date(Date.now() + 86400000);
    const day = d.toISOString().slice(0, 10);
    this.area ??= h("textarea", { class: "input", rows: "5", value: `Dentist, ${day} 10:00\nTeam dinner, ${day} 19:30` });
    return [h("p", { class: "group-title" }, "One event per line: title, date and time"), h("div", { class: "group" }, h("div", { class: "row" }, this.area)),
      h("p", { class: "group-footer" }, "On iPhone these come from your calendar. Events more than 14 days away are skipped.")];
  }
  async import() {
    const events = this.area.value.split("\n").map((l) => l.split(",")).filter((p) => p.length >= 2)
      .map(([title, ...rest]) => ({ title: title.trim(), starts_at: new Date(rest.join(",").trim().replace(" ", "T")).toISOString() }));
    try {
      const created = await this.api.importCalendar(events);
      this.app.dismiss(this); this.onDone?.();
      this.app.toast(created.length === 1 ? "1 scene prepared" : `${created.length} scenes prepared`);
    } catch (e) { this.error = e.message; this.update(); }
  }
}
