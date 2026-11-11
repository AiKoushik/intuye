import { h, icon, whenLabel } from "../dom.js";
import { dots, interlinear, readyDots, spinner } from "../components.js";
import { speak } from "../speech.js";
import { Screen, navButton } from "./base.js";
import { Rehearse } from "./rehearse.js";

export class Scenes extends Screen {
  constructor(app) { super(app); this.title = "Scenes"; this.list = null; }
  async load() { this.list = await this.api.scenarios(); }
  navRight() { return [navButton("", () => this.app.present(new NewSceneSheet(this.app, () => this.refresh())), { iconName: "plus", aria: "Something coming up" })]; }

  content() {
    if (!this.list) return this.loaded ? [] : [spinner()];
    const { upcoming, recurring, mine } = this.list;
    const out = [];
    if (!upcoming.length && !recurring.length && !mine.length) {
      out.push(h("p", { class: "empty", style: "margin:0 4px" }, "Add something coming up — a dentist visit, a meeting, dinner with friends — and get the Spanish for it."));
    }
    for (const [label, items] of [["Coming up", upcoming], ["From your conversations", recurring], ["Yours", mine]]) {
      if (!items.length) continue;
      out.push(h("p", { class: "group-title" }, label), h("div", { class: "group" }, items.map((s) => this.row(s))));
    }
    out.push(h("p", { class: "group-title" }, " "),
      h("div", { class: "group" }, h("button", { class: "row action", type: "button", onclick: () => this.app.present(new CalendarSheet(this.app, () => this.refresh())) },
        icon("calendar"), h("span", { class: "grow" }, "Use my calendar"))),
      h("p", { class: "group-footer" }, "Only event titles and times for the next two weeks are sent. The web build lets you type test events."));
    return out;
  }

  row(s) {
    if (s.status === "suggested") {
      return h("div", { class: "row" },
        h("span", { class: "grow" }, h("span", { style: "display:block" }, s.title), h("span", { class: "meta" }, "Suggested from what you talk about")),
        h("button", { class: "btn inline", type: "button", onclick: async () => { await this.api.setScenarioStatus(s.id, "active"); this.refresh(); } }, "Add"));
    }
    return h("button", { class: "row", type: "button", onclick: () => this.app.push(new SceneDetail(this.app, s.id)) },
      h("span", { class: "grow" }, h("span", { style: "display:block" }, s.title), h("span", { class: "meta" }, whenLabel(s))),
      dots(s.readiness.current), icon("chevron", "chev"));
  }
}

export class SceneDetail extends Screen {
  constructor(app, id) { super(app); this.id = id; this.title = ""; this.large = false; this.scene = null; }
  async load() { this.scene = await this.api.scenario(this.id); this.title = this.scene.title; }

  content() {
    const s = this.scene;
    if (!s) return this.loaded ? [] : [spinner()];
    const p = s.phrases || { key: [], rescue: [], hear: [] };
    return [
      h("p", { class: "date" }, whenLabel(s)),
      h("h1", { class: "large-title" }, s.title),
      h("div", { class: "card split", style: "padding:6px 8px 6px 16px" }, h("span", { class: "body" }, "How ready do you feel?"),
        readyDots(s.readiness.current, (v) => this.rate(v))),
      h("p", { class: "section-label" }, "Key phrases"),
      h("div", { class: "card" }, p.key.map((ph) => h("div", { class: "phrase-row" },
        interlinear(ph.alignment.map((a) => ({ src: a.src, tgt: a.tgt }))),
        h("button", { class: "iconbtn", type: "button", "aria-label": `Play ${ph.es}`, onclick: () => speak(ph.es, this.app.dialect) }, icon("speaker"))))),
      h("p", { class: "section-label" }, "If you get stuck"),
      h("div", { class: "card" }, p.rescue.map((r) => h("button", { class: "rescue", type: "button", onclick: () => speak(r.es, this.app.dialect, true) }, r.es))),
      h("p", { class: "section-label" }, "You might hear"),
      h("div", { class: "card" }, p.hear.map((x) => h("div", { style: "padding:6px 0" },
        h("button", { class: "rescue", style: "padding:0", type: "button", onclick: () => speak(x.es, this.app.dialect, true) }, x.es),
        h("p", { class: "meta" }, x.en)))),
      h("button", { class: "btn", type: "button", onclick: () => this.app.push(new Rehearse(this.app, s)) }, "Rehearse"),
    ];
  }

  async rate(v) {
    await this.api.rate(this.scene.id, v, this.scene.readiness.before == null ? "before" : "after");
    this.refresh();
  }
}

class NewSceneSheet extends Screen {
  constructor(app, onCreated) { super(app); this.title = "New scene"; this.large = false; this.onCreated = onCreated; this.name = ""; this.hasDate = false; this.busy = false; }

  navLeft() { return navButton("Cancel", () => this.app.dismiss(this)); }
  navRight() { return [navButton(this.busy ? "Preparing…" : "Prepare", () => this.create(), { strong: true, disabled: this.busy || this.name.trim().length < 2 })]; }

  content() {
    const tomorrow = new Date(Date.now() + 86400000); tomorrow.setMinutes(0, 0, 0);
    const local = new Date(tomorrow.getTime() - tomorrow.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    this.dateInput ??= h("input", { type: "datetime-local", class: "input", value: local, style: "text-align:right;width:auto" });
    return [
      h("p", { class: "group-title" }, "What's coming up?"),
      h("div", { class: "group" }, h("div", { class: "row" }, h("input", { class: "input", placeholder: "e.g. Dentist, parent-teacher meeting", value: this.name,
        oninput: (e) => { this.name = e.target.value; this.renderNav(); } }))),
      h("p", { class: "group-title" }, " "),
      h("div", { class: "group" },
        h("label", { class: "row" }, h("span", { class: "grow" }, "It has a date"),
          h("input", { type: "checkbox", checked: this.hasDate, onchange: (e) => { this.hasDate = e.target.checked; this.update(); } })),
        this.hasDate ? h("div", { class: "row" }, h("span", { class: "grow" }, "When"), this.dateInput) : null),
    ];
  }

  async create() {
    this.busy = true; this.renderNav();
    try {
      const startsAt = this.hasDate ? new Date(this.dateInput.value).toISOString() : null;
      await this.api.createScenario(this.name.trim(), startsAt, "manual");
      this.app.dismiss(this);
      this.onCreated?.();
      this.app.toast("Scene ready");
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
