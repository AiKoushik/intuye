import { h, icon, parseDate, relativeDay, timeLabel } from "../dom.js";
import { spinner, tintChip } from "../components.js";
import { speak } from "../speech.js";
import { Screen, navButton } from "./base.js";

const SOURCE = { ambient: ["sand", "Heard"], say: ["sea", "You said"], rehearsal: ["sage", "Rehearsal"] };
const isoDay = (d) => `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;

/** Moments: one day of what you said and what capture heard, grouped by hour. Delete any line. */
export class Moments extends Screen {
  constructor(app) { super(app); this.title = "Moments"; this.day = new Date(); this.data = null; this.note = null; }
  ambient() { return ["sand", "sea"]; }
  async load() { this.data = await this.api.moments(isoDay(this.day)); }
  navRight() { return this.isSheet ? [navButton("Done", () => this.app.dismiss(this), { strong: true })] : []; }

  shift(days) {
    const d = new Date(this.day); d.setUTCDate(d.getUTCDate() + days);
    if (d > new Date()) return;
    this.day = d; this.data = null; this.note = null; this.update(); this.refresh();
  }

  content() {
    const today = isoDay(this.day) === isoDay(new Date());
    const nav = h("div", { class: "day-nav" },
      h("button", { class: "iconbtn", type: "button", "aria-label": "Previous day", onclick: () => this.shift(-1) }, icon("back")),
      h("span", { class: "grow" }, relativeDay(this.day), h("span", { class: "meta", style: "display:block" },
        this.day.toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" }))),
      h("button", { class: "iconbtn flip", type: "button", "aria-label": "Next day", disabled: today, onclick: () => this.shift(1) }, icon("back")));
    if (!this.data) return [nav, this.loaded ? null : spinner()];
    const items = this.data.items;
    if (!items.length) return [nav, h("p", { class: "empty", style: "margin:14px 4px" }, today
      ? "Nothing yet today. Say something on the Say tab, or turn on capture." : "Nothing was captured on this day.")];
    const byHour = new Map();
    for (const it of items) {
      const d = parseDate(it.spoken_at);
      const key = d ? `${String(d.getHours()).padStart(2, "0")}:00` : "—";
      if (!byHour.has(key)) byHour.set(key, []);
      byHour.get(key).push({ ...it, d });
    }
    const out = [nav];
    for (const [hour, list] of byHour) {
      out.push(h("p", { class: "group-title" }, hour), h("div", { class: "group" }, list.map((m) => this.row(m))));
    }
    out.push(h("p", { class: "group-footer" }, `${items.length} ${items.length === 1 ? "sentence" : "sentences"}. Sentences are deleted after your retention period in Settings.`));
    if (today) {
      out.push(h("div", { class: "group", style: "margin-top:16px" },
        h("button", { class: "row destructive", type: "button", onclick: () => this.forget() }, "Forget last 10 minutes")));
    }
    if (this.note) out.push(h("p", { class: "group-footer" }, this.note));
    return out;
  }

  row(m) {
    const [tint, label] = SOURCE[m.source] || ["plum", m.source];
    return h("div", { class: "row moment" },
      h("div", { class: "grow" },
        h("p", { style: "display:flex;gap:8px;align-items:center;margin-bottom:4px" }, tintChip(tint, label),
          h("span", { class: "meta", style: "margin:0" }, m.d ? timeLabel(m.d) : "")),
        h("p", { class: "secondary", style: "font-size:16px;line-height:21px" }, m.text),
        m.close_es ? h("button", { class: "es moment-es", type: "button", "aria-label": `Play ${m.close_es}`, onclick: () => speak(m.close_es, this.app.dialect) }, m.close_es) : null),
      h("button", { class: "iconbtn", type: "button", "aria-label": `Delete “${m.text}”`, onclick: () => this.remove(m) }, icon("x")));
  }

  async remove(m) {
    try { await this.api.deleteMoment(m.id); this.data.items = this.data.items.filter((x) => x.id !== m.id); this.note = "Deleted."; }
    catch (e) { this.error = e.message; }
    this.update();
  }

  async forget() {
    try { const r = await this.api.forget(10); this.note = r.deleted === 1 ? "Forgot 1 sentence." : `Forgot ${r.deleted} sentences.`; await this.load(); }
    catch (e) { this.error = e.message; }
    this.update();
  }
}
