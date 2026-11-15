import { h, icon, pct, svg } from "../dom.js";
import { spinner, tile, tintChip, topicTile } from "../components.js";
import { Screen } from "./base.js";
import { LessonScreen } from "./lesson.js";

export const LEVELS = ["Just starting", "Beginner", "I get by", "Intermediate", "Conversational", "Fluent"];

/** The weekly reflection card, shared with Today (shown there on Mondays). */
export function reflectionCard(r, language) {
  if (!r) return null;
  const facts = [
    [r.sentences, r.sentences === 1 ? "sentence" : "sentences"],
    [r.target_share == null ? "–" : pct(r.target_share), `in ${language}`],
    [r.words_kept, r.words_kept === 1 ? "word stuck" : "words stuck"],
    [r.scenes_rehearsed, r.scenes_rehearsed === 1 ? "scene rehearsed" : "scenes rehearsed"],
  ];
  return h("div", { class: "card wash t-sage" },
    h("div", { class: "lead" }, tile("sage", "calendar"), h("div", {}, h("h3", {}, "Your week"), h("p", { class: "meta" }, "The last seven days"))),
    h("p", { class: "body", style: "margin-top:8px" }, r.line),
    r.best_target ? h("div", {}, h("p", { style: "margin-top:10px" }, tintChip("sage", `Your best ${language} this week`)),
      h("p", { class: "reflect-best" }, r.best_target)) : null,
    h("div", { class: "mini-stats" }, facts.map(([n, l]) => h("span", {}, h("b", {}, n), l))));
}

export class ProgressScreen extends Screen {
  ambient() { return ["plum", "sea"]; }
  constructor(app) { super(app); this.title = "Progress"; this.data = null; this.lessons = []; }
  async load() { [this.data, this.lessons] = await Promise.all([this.api.progress(), this.api.lessons()]); }

  content() {
    const d = this.data;
    if (!d) return this.loaded ? [] : [spinner()];
    return [reflectionCard(d.reflection, this.app.lang.name), this.spanglish(d.spanglish_ratio), this.level(d.level_estimate), this.confidence(d.confidence),
      this.words(d.words), this.lessonList()];
  }

  spanglish(weeks) {
    const last = weeks[weeks.length - 1];
    if (!last) {
      return h("div", { class: "card" }, h("h3", {}, `English in your ${this.app.lang.name}`),
        h("p", { class: "meta", style: "margin-top:6px" }, `Try saying things in ${this.app.lang.name}, even mixed with English. This shows how much English is left in them, week by week.`));
    }
    const prev = weeks.length > 1 ? weeks[weeks.length - 2].ratio : null;
    const W = 300, H = 90, pad = 8;
    const xs = (i) => weeks.length === 1 ? W / 2 : pad + (i * (W - 2 * pad)) / (weeks.length - 1);
    const ys = (r) => pad + (1 - r) * (H - 2 * pad);
    const pts = weeks.map((w, i) => `${xs(i)},${ys(w.ratio)}`).join(" ");
    const chart = svg("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: "90", role: "img",
      "aria-label": `Weekly share of English: ${weeks.map((w) => `${w.week} ${pct(w.ratio)}`).join(", ")}` },
      svg("line", { x1: 0, x2: W, y1: ys(0.5), y2: ys(0.5), stroke: "var(--lc-hairline)", "stroke-dasharray": "3 4" }),
      svg("polyline", { points: pts, fill: "none", stroke: "var(--lc-plum)", "stroke-width": 2.5, "stroke-linecap": "round", "stroke-linejoin": "round" }),
      ...weeks.map((w, i) => svg("circle", { cx: xs(i), cy: ys(w.ratio), r: 3.5, fill: "var(--lc-plum)" })));
    chart.style.cssText = "width:100%;height:90px;margin-top:10px";
    return h("div", { class: "card wash t-plum" }, h("h3", {}, `English in your ${this.app.lang.name}`),
      h("div", { class: "split", style: "align-items:flex-end;margin-top:6px" }, h("span", { class: "big" }, pct(last.ratio)),
        prev != null ? h("span", { class: "meta" }, `${last.ratio <= prev ? "down" : "up"} from ${pct(prev)} last week`) : h("span", { class: "meta" }, `${last.sentences} sentences this week`)),
      chart);
  }

  confidence(rows) {
    return h("div", { class: "card" }, h("h3", { style: "margin-bottom:6px" }, "Confidence by scene"),
      rows.length ? rows.map((r) => h("div", { class: "conf-row", "aria-label": `${r.title}: ${r.before ?? "not rated"} before, ${r.after ?? "not rated"} after` },
        topicTile(null, r.title), h("span", { class: "grow" }, r.title), h("span", { class: "secondary" }, r.before ?? "–"), icon("arrow", "chev"),
        h("span", { class: (r.after ?? 0) > (r.before ?? 0) ? "up" : "" }, r.after ?? "–")))
        : h("p", { class: "meta" }, "Rate how ready you feel before and after rehearsing a scene."));
  }

  words(w) {
    return h("div", { class: "stats" },
      h("div", { class: "t-sea" }, h("b", {}, w.met), h("span", {}, "words met")),
      h("div", { class: "t-sage" }, h("b", {}, w.kept), h("span", {}, "kept")),
      h("div", { class: "t-sand" }, h("b", {}, w.due), h("span", {}, "due now")));
  }

  level(est) {
    if (!est) return null;
    const same = est.level === est.current_setting;
    const b = est.basis;
    const why = [`${b.words_kept} ${b.words_kept === 1 ? "word" : "words"} kept`,
      b.target_share != null ? `${pct(b.target_share)} ${this.app.lang.name} in what you tried this month` : null,
      b.avg_target_words != null ? `about ${Math.round(b.avg_target_words)} words a sentence` : null].filter(Boolean).join(", ");
    return h("div", { class: "card wash t-sand level-card" },
      h("h3", {}, "Your level, roughly"),
      h("div", { class: "split", style: "align-items:flex-end;margin-top:4px" },
        h("span", { class: "band" }, est.band), h("span", { class: "meta" }, LEVELS[est.level])),
      h("p", { class: "meta", style: "margin-top:4px" }, `From ${why}.`),
      same ? h("p", { class: "meta", style: "margin-top:6px" }, "Matches your setting.")
        : h("button", { class: "btn subtle", type: "button", style: "margin-top:10px", onclick: () => this.useLevel(est.level) },
          `Use this level (you're set to ${LEVELS[est.current_setting]})`));
  }

  async useLevel(level) {
    try { await this.api.updateSettings({ level }); await this.app.loadMe(); this.app.toast(`Level set to ${LEVELS[level]}`); await this.refresh(); }
    catch (e) { this.error = e.message; this.update(); }
  }

  lessonList() {
    if (!this.lessons.length) return null;
    return [h("p", { class: "section-label" }, "Grammar from your sentences"),
      h("div", { class: "group" }, this.lessons.map((l) => h("button", { class: "row tap", type: "button",
        "aria-label": `${l.title}. ${l.pattern}`, onclick: () => this.app.push(new LessonScreen(this.app, l.id, { youSaid: l.you_said })) },
        tile("plum", "sparkles"), h("span", { class: "grow" }, h("span", { style: "display:block" }, l.title), h("span", { class: "meta tgt" }, l.pattern)),
        icon("chevron", "chev"))))];
  }
}
