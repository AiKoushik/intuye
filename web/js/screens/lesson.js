import { h, icon } from "../dom.js";
import { spinner, tintChip } from "../components.js";
import { speak } from "../speech.js";
import { Screen, navButton } from "./base.js";

/** A 60-second grammar lesson: the pattern, one plain rule, three examples, one check.
 *  Opened from a review card ("Why it's built this way") or from Progress. */
export class LessonScreen extends Screen {
  constructor(app, lessonId, { youSaid = null, sheet = false } = {}) {
    super(app);
    this.lessonId = lessonId; this.youSaid = youSaid; this.asSheet = sheet;
    this.large = false; this.title = "Lesson"; this.data = null; this.picked = null;
  }
  ambient() { return ["plum", "sand"]; }
  navRight() { return this.asSheet ? [navButton("Done", () => this.app.dismiss(this), { strong: true })] : []; }
  async load() { this.data = await this.api.lesson(this.lessonId); }

  content() {
    const d = this.data;
    if (!d) return this.loaded ? [] : [spinner()];
    const out = [
      h("div", { class: "lesson-head" }, h("h1", { class: "title1" }, d.title), h("p", { class: "es lesson-pattern" }, d.pattern)),
      h("p", { class: "body" }, d.rule),
    ];
    if (this.youSaid) {
      out.push(h("div", { class: "card wash t-sand" }, h("p", { style: "margin-bottom:4px" }, tintChip("sand", "You said")),
        h("p", { class: "secondary", style: "font-size:16px" }, this.youSaid)));
    }
    out.push(h("div", { class: "card" }, d.examples.map((x, i) =>
      h("button", { class: "lesson-ex", type: "button", style: i ? "border-top:1px solid var(--lc-hairline)" : "",
        "aria-label": `${x.es}. ${x.en}. Play`, onclick: () => speak(x.es, this.app.dialect) },
        h("span", { class: "grow" }, h("span", { class: "es", style: "font-size:20px;display:block" }, x.es), h("span", { class: "meta" }, x.en)),
        icon("speaker", "chev")))));
    const c = d.check;
    out.push(h("p", { class: "section-label" }, "Your turn"),
      h("div", { class: "card wash t-plum" }, h("p", { class: "meta" }, "Which is right?"), h("h3", { style: "margin:2px 0 10px" }, c.prompt),
        h("div", { class: "lesson-opts" }, c.options.map((o, i) => {
          const state = this.picked == null ? "" : i === c.answer ? " right" : i === this.picked ? " wrong" : " dim";
          return h("button", { class: `lesson-opt es${state}`, type: "button", disabled: this.picked != null && i !== this.picked && i !== c.answer,
            "aria-pressed": String(this.picked === i), onclick: () => { if (this.picked == null) { this.picked = i; this.update(); if (i === c.answer) speak(o, this.app.dialect); } } },
            o, this.picked != null && i === c.answer ? icon("check") : null);
        })),
        this.picked == null ? null : h("p", { class: "meta", style: "margin-top:10px", role: "status" },
          this.picked === c.answer ? "That's the one." : "Not quite. The green one follows the pattern above.")));
    return out;
  }
}
