import { h, icon } from "../dom.js";
import { Screen, navButton } from "./base.js";
import { Moments } from "./moments.js";

/** Settings and privacy centre. */
export class SettingsSheet extends Screen {
  constructor(app) { super(app); this.title = "Settings"; this.large = false; this.s = app.me?.settings ?? null; this.confirm = false; }
  async load() { await this.app.loadMe(); this.s = this.app.me?.settings ?? null; }
  navRight() { return [navButton("Done", () => this.app.dismiss(this), { strong: true })]; }

  async save(patch) {
    try { this.s = await this.api.updateSettings(patch); await this.app.loadMe(); this.error = null; } catch (e) { this.error = e.message; }
    this.update();
  }

  content() {
    const s = this.s;
    if (!s) return [];
    const select = (value, options, onchange) => h("select", { class: "input", style: "width:auto;text-align:right;color:var(--lc-text-secondary)", onchange },
      options.map(([v, label]) => h("option", { value: v, selected: String(v) === String(value) }, label)));
    return [
      h("p", { class: "group-title" }, "Your Spanish"),
      h("div", { class: "group" },
        h("div", { class: "row" }, h("span", { class: "grow" }, "Variety"),
          select(s.dialect, [["es-419", "Latin America"], ["es-MX", "Mexico"], ["es-ES", "Spain"]], (e) => this.save({ dialect: e.target.value }))),
        h("div", { class: "row" }, h("span", { class: "grow" }, "Level"),
          select(s.level, [[0, "Just starting"], [1, "Beginner"], [2, "I get by"], [3, "Intermediate"], [4, "Conversational"], [5, "Fluent"]],
            (e) => this.save({ level: Number(e.target.value) })))),
      h("p", { class: "group-title" }, "Notifications"),
      h("div", { class: "group" },
        h("div", { class: "row" }, h("span", { class: "grow" }, `At most ${s.daily_notification_budget} a day`),
          h("span", { class: "stepper" },
            h("button", { type: "button", "aria-label": "Fewer", onclick: () => this.save({ daily_notification_budget: Math.max(0, s.daily_notification_budget - 1) }) }, "−"),
            h("button", { type: "button", "aria-label": "More", onclick: () => this.save({ daily_notification_budget: Math.min(6, s.daily_notification_budget + 1) }) }, "+"))),
        h("div", { class: "row", style: "flex-wrap:wrap;row-gap:4px" }, h("span", { class: "grow", style: "min-width:100%" }, "Quiet hours"),
          h("span", { style: "display:flex;align-items:center;gap:8px;margin-left:auto;font-size:15px" },
            h("input", { type: "time", class: "input", style: "width:auto;font-size:15px", "aria-label": "Quiet hours start", value: s.quiet_start,
              onchange: (e) => e.target.value && this.save({ quiet_start: e.target.value }) }),
            h("span", { class: "secondary" }, "to"),
            h("input", { type: "time", class: "input", style: "width:auto;font-size:15px", "aria-label": "Quiet hours end", value: s.quiet_end,
              onchange: (e) => e.target.value && this.save({ quiet_end: e.target.value }) })))),
      h("p", { class: "group-footer" }, "Never more than one an hour. Each one says why it's there."),
      h("p", { class: "group-title" }, "Capture"),
      h("div", { class: "group" }, h("button", { class: "row", type: "button", onclick: () => this.app.present(new CaptureSheet(this.app)) },
        h("span", { class: "grow" }, "Capture and privacy"), icon("chevron", "chev"))),
      h("p", { class: "group-title" }, "Your data"),
      h("div", { class: "group" },
        h("div", { class: "row" }, h("span", { class: "grow" }, "Audio"), h("span", { class: "secondary" }, "Stays on your iPhone")),
        h("div", { class: "row" }, h("span", { class: "grow" }, "Keep sentences for"),
          select(s.moment_retention_days, [[7, "7 days"], [30, "30 days"], [90, "90 days"], [365, "A year"]],
            (e) => this.save({ moment_retention_days: Number(e.target.value) }))),
        h("button", { class: "row", type: "button", onclick: () => this.app.present(new Moments(this.app)) },
          h("span", { class: "grow" }, "See your sentences"), icon("chevron", "chev")),
        h("button", { class: "row action", type: "button", onclick: () => this.export() }, "Export my data"),
        this.confirm
          ? h("button", { class: "row destructive", type: "button", onclick: () => this.deleteAccount() }, "Tap again to delete everything")
          : h("button", { class: "row destructive", type: "button", onclick: () => { this.confirm = true; this.update(); } }, "Delete account")),
      h("p", { class: "group-footer" }, "Deleting removes your sentences, words, scenes and progress from the server. It can't be undone."),
      h("p", { class: "group-title" }, "About"),
      h("div", { class: "group" },
        h("div", { class: "row" }, h("span", { class: "grow" }, "Intuye"), h("span", { class: "secondary" }, "Sense it. Say it.")),
        h("a", { class: "row action", href: "https://github.com/AiKoushik/intuye", target: "_blank", rel: "noopener" }, "Source code"),
        h("div", { class: "row" }, h("span", { class: "grow" }, "Licence"), h("span", { class: "secondary" }, "GNU AGPL v3 or later"))),
      h("p", { class: "group-footer" }, "Intuye is free software. You can read, change and share its code."),
      h("p", { class: "group-title" }, " "),
      h("div", { class: "group" }, h("button", { class: "row action", type: "button", onclick: async () => { this.app.dismiss(this); await this.app.signOut(); } }, "Sign out")),
    ];
  }

  async export() {
    try {
      const blob = await this.api.exportAccount();
      const a = h("a", { href: URL.createObjectURL(blob), download: "intuye-export.json" });
      document.body.append(a); a.click(); a.remove();
    } catch (e) { this.error = e.message; this.update(); }
  }

  async deleteAccount() {
    try { await this.api.deleteAccount(); this.app.dismiss(this); this.app.showOnboarding(); } catch (e) { this.error = e.message; this.update(); }
  }
}

/** Capture controls, plus a web-only helper to feed sentences as if capture had heard them. */
export class CaptureSheet extends Screen {
  constructor(app) { super(app); this.title = "Capture"; this.large = false; this.note = null; }
  navRight() { return [navButton("Done", () => this.app.dismiss(this), { strong: true })]; }

  content() {
    const c = this.app.capture;
    const opt = (mode, label) => h("button", { class: "row", type: "button", onclick: async () => { await c.setMode(mode); setTimeout(() => this.update(), 300); } },
      h("span", { class: "grow" }, label), c.mode === mode ? icon("check", "check") : null);
    this.area ??= h("textarea", { class: "input", rows: "4", placeholder: "One sentence per line",
      value: "my brain is tired after work\nthe neuroscience paper was really interesting\nI want to cook dinner for my son" });
    return [
      h("p", { class: "group-title" }, "Capture"),
      h("div", { class: "group" }, opt("off", "Off"), opt("windows", "During my windows"), opt("always", "Always")),
      h("p", { class: "group-footer" }, c.error ?? "Windows: 9–12 and 18–21. In this web build the browser's speech service transcribes; on iPhone it stays on device."),
      h("p", { class: "group-title" }, " "),
      h("div", { class: "group" },
        h("button", { class: "row", type: "button", onclick: () => this.app.present(new Moments(this.app)) },
          h("span", { class: "grow" }, "See today's sentences"), icon("chevron", "chev")),
        h("button", { class: "row destructive", type: "button", onclick: () => this.forget() }, "Forget last 10 minutes")),
      this.note ? h("p", { class: "group-footer" }, this.note) : null,
      h("p", { class: "group-title" }, "Test: pretend capture heard these"),
      h("div", { class: "group" }, h("div", { class: "row" }, this.area),
        h("button", { class: "row action", type: "button", onclick: () => this.simulate() }, "Send as heard sentences")),
      h("p", { class: "group-footer" }, "Topics you mention three times in a week become suggested scenes; English words become word-batch candidates."),
    ];
  }

  async forget() {
    try { const n = await this.app.capture.forget(10); this.note = n === 1 ? "Forgot 1 sentence" : `Forgot ${n} sentences`; } catch (e) { this.error = e.message; }
    this.update();
  }

  async simulate() {
    const lines = this.area.value.split("\n").map((l) => l.trim()).filter(Boolean);
    if (!lines.length) return;
    try {
      const r = await this.app.capture.simulate(lines);
      this.note = `Sent ${r.accepted} sentences; ${r.lexemes_touched} words tracked${r.suggested_scenarios.length ? `; suggested: ${r.suggested_scenarios.map((s) => s.title).join(", ")}` : ""}.`;
    } catch (e) { this.error = e.message; }
    this.update();
  }
}
