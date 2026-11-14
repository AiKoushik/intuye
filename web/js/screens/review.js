import { applyAmbient } from "./base.js";
import { h, icon, parseDate, relativeDay } from "../dom.js";
import { errorBanner, holdToTalk, ratingButtons, reasonTint, spinner, tintChip } from "../components.js";
import { localeFor, speak } from "../speech.js";
import { LessonScreen } from "./lesson.js";

/** Full-screen review session (fullScreenCover on iPhone). */
export class ReviewCover {
  constructor(app, onClose) {
    this.app = app;
    this.onClose = onClose;
    this.cards = [];
    this.index = 0;
    this.revealed = false;
    this.loading = true;
    this.error = null;
    this.reviewed = 0;
    this.nextDue = null;
    this.pron = null;
  }

  get api() { return this.app.api; }
  get current() { return this.cards[this.index] ?? null; }

  mountCover() {
    this.el = h("div", { class: "cover", role: "dialog", "aria-modal": "true", "aria-label": "Review" });
    applyAmbient(this.el, ["sea", "sage"]);
    this.render();
    this.load();
    return this.el;
  }

  async load() {
    this.loading = true; this.render();
    try {
      let due = await this.api.dueCards();
      if (!due.length) { await this.api.nextBatch(); due = await this.api.dueCards(); }
      this.cards = due;
    } catch (e) { this.error = e.message; }
    this.loading = false; this.render();
  }

  close() { this.el.remove(); this.onClose?.(); }

  render() {
    const total = this.cards.length;
    const head = h("div", { class: "split", style: "min-height:44px" },
      h("span", { class: "meta", style: "font-variant-numeric:tabular-nums" }, total ? `${Math.min(this.index + 1, total)} of ${total}` : ""),
      h("button", { class: "navbtn", type: "button", onclick: () => this.close() }, "Close"));
    const bar = h("div", { class: "progressbar" }, h("i", { style: `width:${total ? (this.index / total) * 100 : 0}%` }));
    let body;
    if (this.loading) body = [h("div", { style: "flex:1" }, spinner())];
    else if (this.error) body = [errorBanner(this.error, () => { this.error = null; this.load(); }), h("div", { style: "flex:1" })];
    else if (this.current) body = [this.card(this.current), h("div", { class: `ratings${this.revealed ? "" : " hidden"}` }, ratingButtons((v) => this.rate(v)))];
    else body = [this.summary()];
    this.el.replaceChildren(head, bar, ...body);
  }

  card(c) {
    const ctx = c.context ? c.context.replace(new RegExp(c.es.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "ig"), "____") : null;
    const el = h("div", { class: "rcard", role: "button", tabindex: "0", "aria-label": this.revealed ? c.es : "Tap to show the answer" },
      h("div", { style: "flex:1" }),
      h("div", { class: "cue" }, c.en),
      ctx ? h("div", { class: "ctx" }, ctx) : null,
      this.revealed
        ? h("div", {},
          h("button", { class: "es-xl", type: "button", onclick: (e) => { e.stopPropagation(); speak(c.es, this.app.dialect); }, "aria-label": `Play ${c.es}` }, c.es),
          c.reason ? h("p", { style: "margin-top:10px" }, tintChip(reasonTint(c.reason_kind), c.reason)) : null,
          c.lesson_id ? h("button", { class: "link", type: "button", style: "margin-top:10px",
            onclick: (e) => { e.stopPropagation(); this.app.present(new LessonScreen(this.app, c.lesson_id, { sheet: true })); } },
            "Why it's built this way") : null,
          this.pron ? h("p", { class: `pron ${this.pron.ok ? "ok" : "no"}`, style: "margin-top:8px" }, icon(this.pron.ok ? "check" : "ear"),
            this.pron.ok ? "Sounded right" : "Close — listen and try again") : null)
        : h("div", { class: "hint" }, "Tap to show, or hold the mic and say it"),
      h("div", { style: "flex:1" }),
      this.revealed ? null : holdToTalk({ onBegin: () => this.app.holdBegin(localeFor(this.app.dialect, true)).catch(() => {}), onEnd: () => this.heard(c) }));
    el.addEventListener("click", (e) => { if (!e.target.closest(".mic") && !this.revealed) { this.revealed = true; this.render(); } });
    el.addEventListener("keydown", (e) => { if ((e.key === "Enter" || e.key === " ") && !this.revealed) { e.preventDefault(); this.revealed = true; this.render(); } });
    return el;
  }

  async heard(c) {
    const text = await this.app.holdEnd();
    this.revealed = true;
    if (text) { try { this.pron = await this.api.pronunciation(c.lexeme_id, c.es, text); } catch {} }
    this.render();
  }

  async rate(value) {
    const c = this.current;
    try {
      const r = await this.api.review(c.lexeme_id, value);
      const d = parseDate(r.due_at);
      if (d && value !== 1) this.nextDue = !this.nextDue || d < this.nextDue ? d : this.nextDue;
      this.reviewed += 1;
      if (value === 1) this.cards.push(c);
      this.index += 1; this.revealed = false; this.pron = null;
    } catch (e) { this.error = e.message; }
    this.render();
  }

  summary() {
    return h("div", { style: "flex:1;display:flex;flex-direction:column;justify-content:center;gap:8px" },
      h("h1", { class: "large-title" }, this.reviewed ? `${this.reviewed} words done` : "Nothing to review right now"),
      this.nextDue ? h("p", { class: "body secondary" }, `Next review: ${relativeDay(this.nextDue).toLowerCase()}`) : null,
      h("div", { style: "flex:1" }),
      h("button", { class: "btn", type: "button", onclick: () => this.close() }, "Done"));
  }
}
