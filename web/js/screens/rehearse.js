import { h } from "../dom.js";
import { holdToTalk, readyDots, topicTint } from "../components.js";
import { speak } from "../speech.js";
import { Screen, navButton } from "./base.js";

/** Voice role-play: the coach plays the other person in the learner's target language. Tap a coach line for its English. */
export class Rehearse extends Screen {
  ambient() { return ["sage", "sand"]; }
  constructor(app, scene) {
    super(app);
    this.scene = scene;
    this.title = scene.title;
    this.large = false;
    this.bubbles = [];
    this.difficulty = "gentle";
    this.busy = false;
    this.done = false;
    this.english = false;
    this.hintIndex = 0;
    this.id = null;
  }

  async load() { if (!this.id) await this.start(); }

  navRight() {
    return [navButton(this.difficulty[0].toUpperCase() + this.difficulty.slice(1), () => {
      const order = ["gentle", "real", "fast"];
      this.difficulty = order[(order.indexOf(this.difficulty) + 1) % 3];
      this.app.toast(`Difficulty: ${this.difficulty}. Restarting.`);
      this.renderNav(); this.start();
    }, { aria: "Change difficulty" }), navButton("End", () => this.end(), { strong: true })];
  }

  bottomBar() {
    this.text = h("input", { class: "field", placeholder: "Or type your line", style: "min-height:44px;padding:10px 16px",
      onkeydown: (e) => { if (e.key === "Enter" && this.text.value.trim()) { const t = this.text.value; this.text.value = ""; this.say(t); } } });
    this.langBtn = h("button", { class: "chip-btn", type: "button", onclick: () => { this.english = !this.english; this.langBtn.classList.toggle("on", this.english);
      this.langBtn.textContent = this.english ? "English" : "In English"; } }, "In English");
    this.mic = holdToTalk({
      onBegin: () => this.app.holdBegin(this.app.stt(!this.english)).catch((e) => this.app.toast(e.message)),
      onEnd: async () => { const t = await this.app.holdEnd(); if (t) this.say(t); },
    });
    return h("div", { style: "flex-direction:column;align-items:stretch;gap:8px" },
      this.text,
      h("div", { class: "split" }, h("button", { class: "chip-btn", type: "button", onclick: () => this.hint() }, "Hint"), this.mic, this.langBtn));
  }

  content() {
    return [h("div", { class: "chat" }, this.bubbles.map((b) => this.bubble(b))), this.busy ? h("div", { class: "shimmer", style: "width:120px" }) : null];
  }

  bubble(b) {
    if (b.kind === "hint") return h("div", { class: "bubble hint-b" }, `Try: ${b.text}`);
    if (b.kind === "coach") {
      const el = h("button", { class: "bubble coach", type: "button", "aria-label": `${b.text}. Tap for English.` }, b.text, b.open ? h("small", {}, b.en) : null);
      el.addEventListener("click", () => { b.open = !b.open; this.update(); });
      return el;
    }
    return h("div", { class: "bubble you" }, b.text,
      b.native ? h("div", { class: "native" }, "A native would say ", h("em", {}, b.native)) : null);
  }

  speak(t) { speak(t, this.app.tts, this.difficulty === "gentle"); }

  async start() {
    this.busy = true; this.bubbles = []; this.done = false; this.update();
    try {
      const r = await this.api.startRehearsal(this.scene.id, this.difficulty);
      this.id = r.rehearsal_id;
      this.bubbles.push({ kind: "coach", text: r.coach.target, en: r.coach.en });
      this.speak(r.coach.target);
    } catch (e) { this.error = e.message; }
    this.busy = false; this.update();
  }

  async say(text) {
    if (!this.id || this.done || !text.trim()) return;
    this.bubbles.push({ kind: "you", text });
    this.busy = true; this.update(); this.scrollToBottom();
    try {
      const r = await this.api.rehearsalTurn(this.id, text);
      this.bubbles[this.bubbles.length - 1].native = r.native;
      this.bubbles.push({ kind: "coach", text: r.coach.target, en: r.coach.en });
      this.speak(r.coach.target);
      this.done = r.done;
    } catch (e) { this.error = e.message; }
    this.busy = false; this.update(); this.scrollToBottom();
    if (this.done) setTimeout(() => this.end(), 1200);
  }

  hint() {
    const keys = this.scene.phrases?.key || [];
    if (!keys.length) return;
    this.bubbles.push({ kind: "hint", text: keys[this.hintIndex++ % keys.length].target });
    this.update(); this.scrollToBottom();
  }

  async end() {
    if (!this.id || this.ending) return;
    this.ending = true;
    try {
      const r = await this.api.endRehearsal(this.id);
      this.app.present(new RehearsalSummary(this.app, this.scene, r));
    } catch (e) { this.error = e.message; this.update(); }
    this.ending = false;
  }
}

class RehearsalSummary extends Screen {
  constructor(app, scene, end) { super(app); this.scene = scene; this.end = end; this.title = "Rehearsal done"; this.large = false; this.rated = null; }
  navRight() { return [navButton("Done", () => { this.app.dismiss(this); this.app.pop(); }, { strong: true })]; }
  content() {
    return [
      h("p", { class: "body", style: "margin:8px 4px 0" }, this.end.summary),
      h("p", { class: "group-title" }, "Keep these"),
      h("div", { class: "group" }, this.end.keep_phrases.map((p) => h("button", { class: "row", type: "button", onclick: () => speak(p.target, this.app.tts) },
        h("span", { class: "grow" }, h("span", { class: "tgt", style: "display:block;font-size:19px" }, p.target), h("span", { class: "meta" }, p.en))))),
      h("p", { class: "group-title" }, "How ready do you feel now?"),
      h("div", { class: "group" }, h("div", { class: "row" }, h("span", { class: "grow" }, this.rated ? `Saved: ${this.rated} of 5` : "Tap a dot"),
        readyDots(this.rated, async (v) => { this.rated = v; await this.api.rate(this.scene.id, v, "after"); this.update(); },
          topicTint(this.scene.topic, this.scene.title)))),
    ];
  }
}
