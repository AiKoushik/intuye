import { applyAmbient } from "./base.js";
import { append, h, icon } from "../dom.js";
import { errorBanner, interlinear, tile } from "../components.js";

const EXAMPLE = [
  { src: "me gusta", tgt: "Me gusta" }, { src: "escuchar", tgt: "escuchar" }, { src: "this", tgt: "esto" },
  { src: "in my", tgt: "en mi" }, { src: "mind", tgt: "mente", new: true },
];

/** Welcome → which Spanish → level → sign in. The web build uses dev sign-in instead of Sign in with Apple. */
export class Onboarding {
  constructor(app) {
    this.app = app;
    this.step = 0;
    this.dialect = "es-419";
    this.level = 0;
    this.name = "";
    this.error = null;
  }

  mountOnboarding() {
    this.el = h("div", { class: "screen" });
    applyAmbient(this.el, ["sea", "plum"]);
    this.render();
    return this.el;
  }

  choice(label, on, onclick) {
    return h("button", { class: `card choice${on ? " on" : ""}`, type: "button", "aria-pressed": String(on), onclick },
      label, h("span", { class: "ring" }, on ? icon("check") : null));
  }

  render() {
    const body = h("div", { class: "onboard" });
    const add = (...kids) => append(body, kids);  // skips nulls (Element.append would print "null")
    if (this.step === 0) {
      add(
        h("div", { class: "brand" }, h("b", {}, "Intuye"), h("span", {}, "in-TOO-yeh: “sense it”. Spanish in your own words.")),
        h("h1", {}, "Say it your way."),
        h("p", { class: "body secondary" }, "Speak English, Spanish or a mix. Get Spanish back that stays close to what you said."),
        h("div", { class: "card" }, interlinear(EXAMPLE)),
        h("p", { class: "fine" }, "Tap a word to see its partner."),
        ...[["sea", "bubble", "Say anything, in any mix", "English, Spanish or both at once"],
            ["sage", "calendar", "Get ready for what's coming up", "The dentist, a meeting, dinner with friends"],
            ["sand", "cards", "Keep 5 to 10 words a day", "Picked from what you actually say"]].map(([t, ic, title, sub]) =>
          h("div", { class: "promise" }, tile(t, ic), h("div", {}, h("b", {}, title), h("span", { class: "sub" }, sub)))),
        h("div", { style: "flex:1" }),
        h("button", { class: "btn", type: "button", onclick: () => this.go(1) }, "Continue"),
      );
    } else if (this.step === 1) {
      add(
        h("h1", {}, "Which Spanish?"),
        h("p", { class: "body secondary" }, "Words differ by place: ordenador or computadora."),
        ...[["es-419", "Latin America"], ["es-MX", "Mexico"], ["es-ES", "Spain"]].map(([code, label]) =>
          this.choice(label, this.dialect === code, () => { this.dialect = code; this.render(); })),
        h("div", { style: "flex:1" }),
        h("button", { class: "btn", type: "button", onclick: () => this.go(2) }, "Continue"),
      );
    } else {
      const input = h("input", { class: "text-input", placeholder: "Your name", value: this.name, autocomplete: "given-name",
        oninput: (e) => { this.name = e.target.value; btn.disabled = !this.name.trim(); },
        onkeydown: (e) => { if (e.key === "Enter" && this.name.trim()) this.signIn(); } });
      const btn = h("button", { class: "btn", type: "button", disabled: !this.name.trim(), onclick: () => this.signIn() }, "Continue");
      add(
        h("h1", {}, "Where are you now?"),
        ...[[0, "Just starting"], [2, "I get by"], [4, "I can hold a conversation"]].map(([v, label]) =>
          this.choice(label, this.level === v, () => { this.level = v; this.render(); })),
        h("p", { class: "fine", style: "margin-top:8px" }, "Test sign-in (the iPhone app uses Sign in with Apple)"),
        input,
        this.error ? errorBanner(this.error) : null,
        h("div", { style: "flex:1" }),
        btn,
      );
    }
    this.el.replaceChildren(body);
  }

  go(step) { this.step = step; this.render(); }

  async signIn() {
    try {
      await this.app.api.devSignIn(this.name.trim());
      await this.app.api.updateSettings({ dialect: this.dialect, level: this.level });
      await this.app.didSignIn();
    } catch (e) {
      this.error = e.code === "http_404" || e.status === 404
        ? "Dev sign-in is off. Start the backend with DEV_LOGIN_ENABLED=true (the run script does this)."
        : e.message;
      this.render();
    }
  }
}
