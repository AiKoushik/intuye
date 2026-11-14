// Web versions of ios/Intuye/DesignSystem/Components.swift.
import { h, icon } from "./dom.js";

/** The interlinear line: your words on top, the other language beneath; tap a group to pair it. */
export function interlinear(pairs, { toEn = false } = {}) {
  const el = h("div", { class: `il${toEn ? " to-en" : ""}`, role: "group" });
  pairs.forEach((p) => {
    const g = h("button", {
      class: `g${p.new ? " new" : ""}`, type: "button",
      "aria-label": `${p.src}, ${toEn ? "English" : "Spanish"}: ${p.tgt}${p.new ? ", new word" : ""}`,
    }, h("span", { class: "s" }, p.src), h("span", { class: "t" }, p.tgt));
    g.addEventListener("click", () => {
      const was = g.classList.contains("on");
      el.querySelectorAll(".g").forEach((x) => x.classList.remove("on"));
      if (!was) g.classList.add("on");
    });
    el.append(g);
  });
  return el;
}

/* Sober tints say what something is about or why it's here; azulejo stays for things you tap.
   Topic -> tint by keyword (topic first, then title); unknown topics get a stable tint from their name. */
const TOPIC_TINTS = [
  ["sage", "heart", /health|dentist|doctor|medic|pharmac|hospital|body|tooth|clinic|sport|fitness/],
  ["sand", "home", /home|family|kid|son|daughter|child|school|parent|landlord|house|neighbo/],
  ["sea", "briefcase", /work|job|office|meeting|study|science|neuro|tech|career|universit|interview|class/],
  ["rose", "food", /food|restaurant|cook|dinner|lunch|breakfast|friend|party|social|café|cafe|bar\b|order/],
  ["plum", "pin", /travel|errand|bank|shop|ticket|train|bus|airport|hotel|plumber|repair|admin|post office|taxi/],
];
const TINTS = ["sage", "sea", "sand", "rose", "plum"];
const ICON_FOR = { sage: "heart", sea: "briefcase", sand: "home", rose: "food", plum: "pin" };

export function topicTint(topic, title = "") {
  const text = `${topic || ""} ${title || ""}`.toLowerCase();
  for (const [tint, , re] of TOPIC_TINTS) if (re.test(`${topic || ""}`.toLowerCase())) return tint;
  for (const [tint, , re] of TOPIC_TINTS) if (re.test(text)) return tint;
  let hsh = 0; for (const ch of text) hsh = (hsh * 31 + ch.charCodeAt(0)) >>> 0;
  return TINTS[hsh % TINTS.length];
}

/** Why a word is in your batch -> tint. Matches the batch's reason_kind or a lexeme's origin. */
export function reasonTint(kind) {
  return { spoken: "sea", scenario: "sage", struggle: "rose", topic: "plum", base: "sand", grammar: "plum" }[kind] || "sand";
}

export function topicTile(topic, title) {
  const tint = topicTint(topic, title);
  return h("span", { class: `tile t-${tint}`, "aria-hidden": "true" }, icon(ICON_FOR[tint]));
}

export function tile(tint, iconName) { return h("span", { class: `tile t-${tint}`, "aria-hidden": "true" }, icon(iconName)); }

export function tintChip(tint, text) { return h("span", { class: `tchip t-${tint}` }, text); }

export function dots(value, tint = null) {
  return h("span", { class: `dots${tint ? ` t-${tint}` : ""}`, role: "img", "aria-label": value ? `Readiness ${value} of 5` : "Not rated yet" },
    [1, 2, 3, 4, 5].map((i) => h("i", { class: i <= (value || 0) ? "on" : "" })));
}

export function readyDots(value, onRate, tint = null) {
  return h("span", { class: `ready-dots${tint ? ` t-${tint}` : ""}` }, [1, 2, 3, 4, 5].map((v) =>
    h("button", { type: "button", "aria-label": `${v} of 5`, onclick: () => onRate(v) }, h("i", { class: v <= (value || 0) ? "on" : "" }))));
}

const RATINGS = [
  { value: 1, label: "Forgot", cls: "forgot", icon: "x" },
  { value: 2, label: "Hard", cls: "hard", icon: "tilde" },
  { value: 3, label: "Got it", cls: "good", icon: "check" },
  { value: 4, label: "Easy", cls: "easy", icon: "bolt" },
];

export function ratingButtons(onRate) {
  return RATINGS.map((r) => h("button", { class: `rate ${r.cls}`, type: "button", onclick: () => onRate(r.value) }, icon(r.icon), r.label));
}

export function errorBanner(message, retry) {
  return h("div", { class: "error", role: "alert" }, icon("alert"), h("span", {}, message),
    retry ? h("button", { type: "button", onclick: retry }, "Retry") : null);
}

export function emptyCard(message, actionTitle, action) {
  return h("div", { class: "card" }, h("p", { class: "empty" }, message),
    actionTitle ? h("button", { class: "btn subtle", type: "button", onclick: action }, actionTitle) : null);
}

export function spinner() { return h("div", { class: "spinner", role: "progressbar", "aria-label": "Loading" }); }

/** 64-pt hold-to-talk control. Pointer: press and hold. Keyboard: Enter/Space toggles. */
export function holdToTalk({ onBegin, onEnd, label = "Hold to talk" }) {
  let active = false;
  const btn = h("button", { class: "mic", type: "button", "aria-label": label }, icon("mic"));
  const begin = (e) => { if (active) return; active = true; e?.preventDefault?.(); btn.classList.add("rec"); btn.replaceChildren(icon("wave")); btn.setAttribute("aria-label", "Stop and send"); onBegin(); };
  const end = () => { if (!active) return; active = false; btn.classList.remove("rec"); btn.replaceChildren(icon("mic")); btn.setAttribute("aria-label", label); onEnd(); };
  btn.addEventListener("pointerdown", (e) => { btn.setPointerCapture?.(e.pointerId); begin(e); });
  btn.addEventListener("pointerup", end);
  btn.addEventListener("pointercancel", end);
  btn.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); active ? end() : begin(); } });
  btn.begin = begin; btn.end = end;
  return btn;
}

export function chipDir(intent) {
  const tint = intent === "to_en" ? "plum" : intent === "to_es" ? "sea" : "sand";
  return h("span", { class: `chip-dir t-${tint}` }, intent === "to_en" ? "Spanish → English" : intent === "to_es" ? "English → Spanish" : "You asked");
}
