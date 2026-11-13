import { h, icon, pct, svg } from "../dom.js";
import { spinner, topicTile } from "../components.js";
import { Screen } from "./base.js";

export class ProgressScreen extends Screen {
  constructor(app) { super(app); this.title = "Progress"; this.data = null; }
  async load() { this.data = await this.api.progress(); }

  content() {
    const d = this.data;
    if (!d) return this.loaded ? [] : [spinner()];
    return [this.spanglish(d.spanglish_ratio), this.confidence(d.confidence), this.words(d.words)];
  }

  spanglish(weeks) {
    const last = weeks[weeks.length - 1];
    if (!last) {
      return h("div", { class: "card" }, h("h3", {}, "English in your Spanish"),
        h("p", { class: "meta", style: "margin-top:6px" }, "Try saying things in Spanish, even mixed with English. This shows how much English is left in them, week by week."));
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
    return h("div", { class: "card" }, h("h3", {}, "English in your Spanish"),
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
}
