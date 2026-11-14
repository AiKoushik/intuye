import { h, icon, whenLabel } from "../dom.js";
import { dots, emptyCard, reasonTint, spinner, tile, tintChip, topicTile, topicTint } from "../components.js";
import { Screen, navButton } from "./base.js";
import { SceneDetail } from "./scenes.js";
import { ReviewCover } from "./review.js";
import { Moments } from "./moments.js";
import { SettingsSheet } from "./settings.js";
import { reflectionCard } from "./progress.js";

export class Today extends Screen {
  constructor(app) { super(app); this.title = "Today"; this.data = null; }
  ambient() { return ["sand", "rose"]; }

  /** The weekly reflection shows on Mondays (local time), or any day with ?reflect in the URL. */
  get reflectDay() { return new Date().getDay() === 1 || new URLSearchParams(location.search).has("reflect"); }
  async load() {
    const [today, progress] = await Promise.all([this.api.today(), this.reflectDay ? this.api.progress().catch(() => null) : null]);
    this.data = today; this.reflection = progress?.reflection ?? null;
  }

  navRight() { return [navButton("", () => this.app.present(new SettingsSheet(this.app)), { iconName: "person", aria: "Settings" })]; }

  largeTitle() {
    const hr = new Date().getHours();
    const part = hr < 12 ? "Good morning" : hr < 18 ? "Good afternoon" : "Good evening";
    const name = this.app.firstName;
    return h("div", {},
      h("p", { class: "date" }, new Date().toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" })),
      h("h1", { class: "large-title" }, name ? `${part}, ${name}` : part));
  }

  content() {
    const d = this.data;
    if (!d) return this.loaded ? [] : [spinner()];
    const out = [];
    const s = d.next_scenario;
    if (s) {
      out.push(h("button", { class: `card tap wash t-${topicTint(s.topic, s.title)}`, type: "button", onclick: () => this.app.push(new SceneDetail(this.app, s.id)) },
        h("div", { class: "split", style: "align-items:flex-start" },
          h("div", { class: "lead" }, topicTile(s.topic, s.title), h("div", {}, h("h3", {}, s.title), h("p", { class: "meta" }, whenLabel(s)))),
          dots(s.readiness.current, topicTint(s.topic, s.title))),
        h("span", { class: "btn" }, s.readiness.after ? "Rehearse again" : "Prep")));
    } else {
      out.push(emptyCard("Nothing coming up yet. Tell your coach about a situation you'd like to be ready for.", "Add a scene",
        () => this.app.selectTab("scenes")));
    }
    if (d.suggested_scenarios > 0) {
      out.push(h("button", { class: "row action", type: "button", style: "padding-left:4px", onclick: () => this.app.selectTab("scenes") },
        icon("sparkles"), d.suggested_scenarios === 1 ? "1 scene suggested from what you talk about" : `${d.suggested_scenarios} scenes suggested from what you talk about`));
    }
    if (this.reflection) out.push(reflectionCard(this.reflection));
    const n = d.words_ready.count;
    out.push(h("div", { class: "card wash t-sea" },
      h("div", { class: "lead" }, tile("sea", "cards"), h("div", {},
        h("h3", {}, n > 0 ? `${n} words ready` : "Your words"),
        h("p", { class: "meta" }, n > 0 ? "From what you said and what's coming up" : "Get 5–10 words picked from your week"))),
      (d.words_ready.preview_items || []).length
        ? h("div", { class: "chips" }, d.words_ready.preview_items.map((w) => h("span", { class: `chip t-${reasonTint(w.origin)}` }, w.es)))
        : null,
      h("button", { class: "btn subtle", type: "button", onclick: () => this.app.presentCover(new ReviewCover(this.app, () => this.refresh())) },
        n > 0 ? "Start review" : "Get today's words")));
    if (d.recent.length) {
      out.push(h("div", { class: "section-head" }, h("p", { class: "section-label" }, "Recent sentences"),
        h("button", { class: "link", type: "button", onclick: () => this.app.push(new Moments(this.app)) }, "See all")));
      for (const r of d.recent) {
        const at = r.spoken_at ? new Date(r.spoken_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : null;
        out.push(h("div", { class: "card" }, at ? h("p", { style: "margin-bottom:6px" }, tintChip("sand", `Heard at ${at}`)) : null,
          h("p", { class: "secondary", style: "font-size:16px" }, r.text),
          r.close_es ? h("p", { class: "es", style: "font-size:20px;margin-top:2px" }, r.close_es) : null));
      }
    } else {
      out.push(emptyCard("Say anything in English to get started.", "Open Say", () => this.app.selectTab("say")));
    }
    return out;
  }
}
