// Tiny DOM helpers: h() builds elements, icon() uses the SVG sprite in index.html.
const SVG = "http://www.w3.org/2000/svg";

export function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "style") el.style.cssText = v;
    else if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === "value") el.value = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  append(el, kids);
  return el;
}

export function append(el, kids) {
  for (const k of [kids].flat(Infinity)) {
    if (k == null || k === false) continue;
    el.append(k instanceof Node ? k : document.createTextNode(String(k)));
  }
  return el;
}

export function icon(name, cls = "") {
  const s = document.createElementNS(SVG, "svg");
  if (cls) s.setAttribute("class", cls);
  s.setAttribute("aria-hidden", "true");
  const u = document.createElementNS(SVG, "use");
  u.setAttribute("href", `#i-${name}`);
  s.append(u);
  return s;
}

export function svg(tag, attrs = {}, ...kids) {
  const el = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  for (const k of kids.flat()) if (k) el.append(k);
  return el;
}

// Dates come from Python's isoformat (microseconds, +00:00); Date() parses them fine.
export function parseDate(s) {
  if (!s) return null;
  const d = new Date(s);
  return isNaN(d) ? null : d;
}

function dayDiff(d) {
  const a = new Date(); a.setHours(0, 0, 0, 0);
  const b = new Date(d); b.setHours(0, 0, 0, 0);
  return Math.round((b - a) / 86400000);
}

export function relativeDay(d) {
  const n = dayDiff(d);
  if (n === 0) return "Today";
  if (n === 1) return "Tomorrow";
  if (n === -1) return "Yesterday";
  return n > 1 ? `In ${n} days` : `${-n} days ago`;
}

export function timeLabel(d) {
  return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

export function whenLabel(scene) {
  const d = parseDate(scene.starts_at);
  if (!d) return scene.kind === "recurring" ? "Comes up often" : "Whenever you're ready";
  const base = `${relativeDay(d)} at ${timeLabel(d)}`;
  return scene.kind === "upcoming" ? `${base}, from your calendar` : base;
}

export const pct = (x) => `${Math.round(x * 100)}%`;
