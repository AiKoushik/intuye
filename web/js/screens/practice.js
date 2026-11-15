import { h, icon } from "../dom.js";
import { holdToTalk, tintChip } from "../components.js";
import { speak } from "../speech.js";
import { Screen } from "./base.js";

/** Rescue-phrase drill (see the English, say it in the target language) and shadowing (hear it, say it back).
 *  Both are scored phoneme by phoneme on the server from what speech recognition heard. */
export class Practice extends Screen {
  constructor(app, scene, mode) {
    super(app);
    this.scene = scene; this.mode = mode; this.large = false;
    this.title = mode === "drill" ? "Rescue drill" : "Shadowing";
    this.items = (mode === "drill" ? scene.phrases.rescue : scene.phrases.key).slice(0, 8);
    this.i = 0; this.result = null; this.heard = ""; this.busy = false; this.correct = 0;
  }
  ambient() { return this.mode === "drill" ? ["rose", "sand"] : ["sea", "plum"]; }
  get item() { return this.items[this.i]; }

  content() {
    if (!this.items.length) return [h("p", { class: "empty" }, "This scene has no phrases to practise yet.")];
    if (this.i >= this.items.length) {
      return [h("div", { class: "card wash t-sage", style: "text-align:center" }, h("h3", {}, "Done"),
        h("p", { class: "meta" }, `${this.correct} of ${this.items.length} sounded right.`)),
        h("button", { class: "btn", type: "button", onclick: () => { this.i = 0; this.correct = 0; this.result = null; this.update(); } }, "Go again"),
        h("button", { class: "btn subtle", type: "button", onclick: () => this.app.pop() }, "Back to the scene")];
    }
    const it = this.item, drill = this.mode === "drill";
    const prompt = h("div", { class: `card wash ${drill ? "t-rose" : "t-sea"} practice-card` },
      h("p", { class: "meta" }, `${this.i + 1} of ${this.items.length}`),
      drill
        ? [h("p", { class: "practice-cue" }, it.en), h("p", { class: "meta" }, `Say it in ${this.app.lang.name}`)]
        : [h("p", { class: "tgt practice-tgt" }, it.target), h("p", { class: "meta" }, it.en),
          h("div", { style: "display:flex;gap:8px;margin-top:8px" },
            h("button", { class: "btn inline subtle", type: "button", onclick: () => speak(it.target, this.app.tts) }, icon("speaker"), "Listen"),
            h("button", { class: "btn inline subtle", type: "button", onclick: () => speak(it.target, this.app.tts, true) }, "Slowly"))]);
    const out = [prompt];
    if (this.result) out.push(this.feedback());
    this.typed ??= h("input", { class: "text-input", placeholder: "Or type what you'd say", enterkeyhint: "done",
      onkeydown: (e) => { if (e.key === "Enter" && e.target.value.trim()) this.check(e.target.value.trim()); } });
    out.push(h("div", { class: "practice-mic" },
      holdToTalk({ label: `Hold and say it in ${this.app.lang.name}`, onBegin: () => this.app.holdBegin(this.app.stt(true)).catch(() => {}),
        onEnd: async () => { const t = await this.app.holdEnd(); if (t) this.check(t); } }),
      this.typed));
    if (this.result) {
      out.push(h("div", { style: "display:flex;gap:8px" },
        h("button", { class: "btn subtle", type: "button", onclick: () => { this.result = null; this.update(); } }, "Try again"),
        h("button", { class: "btn", type: "button", onclick: () => this.next() }, this.i === this.items.length - 1 ? "Finish" : "Next")));
    }
    return out;
  }

  feedback() {
    const r = this.result, it = this.item;
    return h("div", { class: "card" },
      h("p", { style: "margin-bottom:8px" }, tintChip(r.ok ? "sage" : "rose", r.ok ? "Sounded right" : "Close. Listen and try again")),
      h("div", { class: "practice-words" }, r.words.map((w) => h("span", { class: `pw${w.ok ? " ok" : " miss"}`, title: w.heard ? `heard “${w.heard}”` : "not heard" },
        w.word, h("small", {}, w.phonemes.map((p) => p.ok ? p.p : `[${p.p}]`).join(""))))),
      this.heard ? h("p", { class: "meta", style: "margin-top:8px" }, `Heard: “${this.heard}”`) : null,
      ...r.tips.map((t) => h("p", { class: "meta", style: "margin-top:6px" }, t)),
      this.mode === "drill" ? h("button", { class: "tgt practice-answer", type: "button", onclick: () => speak(it.target, this.app.tts, true),
        "aria-label": `Play ${it.target}` }, it.target, icon("speaker")) : null);
  }

  async check(text) {
    if (this.busy) return;
    this.busy = true; this.heard = text;
    try {
      this.result = await this.api.practiceCompare(this.item.target, text);
      if (this.result.ok) this.correct += 1;
      if (this.typed) this.typed.value = "";
    } catch (e) { this.error = e.message; }
    this.busy = false; this.update();
  }

  next() { this.i += 1; this.result = null; this.heard = ""; this.update(); }
}
