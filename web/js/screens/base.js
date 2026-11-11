import { h, icon } from "../dom.js";
import { errorBanner } from "../components.js";

/** One navigation destination, like a SwiftUI view inside a NavigationStack or a sheet. */
export class Screen {
  constructor(app) {
    this.app = app;
    this.title = "";
    this.large = true;
    this.error = null;
    this.loaded = false;
  }

  get api() { return this.app.api; }

  // Overridables
  navLeft() { return null; }
  navRight() { return []; }
  largeTitle() { return h("h1", { class: "large-title" }, this.title); }
  bottomBar() { return null; }
  content() { return []; }
  async load() {}

  mount({ back = null, isSheet = false } = {}) {
    this.back = back;
    this.isSheet = isSheet;
    this.el = h("div", { class: "screen" });
    this.navbarEl = h("div", { class: "navbar" });
    this.scrollEl = h("div", { class: "scroll" });
    this.el.append(this.navbarEl, this.scrollEl);
    const bar = this.bottomBar();
    if (bar) {
      this.el.classList.add("with-bar");
      bar.classList.add("screen-bar");
      this.el.append(h("div", { class: "scrim" }), bar);
    }
    this.renderNav();
    this.update();
    this.refresh();
    return this.el;
  }

  async refresh() {
    try {
      await this.load();
      this.error = null;
    } catch (e) {
      this.error = e.message;
    }
    this.loaded = true;
    this.update();
  }

  renderNav() {
    if (!this.navbarEl) return;
    const left = this.navLeft() ?? (this.back
      ? h("button", { class: "navbtn back", type: "button", onclick: () => this.app.pop() }, icon("back"), this.back)
      : null);
    this.navbarEl.replaceChildren(
      h("div", { class: "left" }, left),
      h("div", { class: "title" }, this.large ? "" : this.title),
      h("div", { class: "right" }, this.navRight()),
    );
  }

  update() {
    if (!this.scrollEl) return;
    const top = this.scrollEl.scrollTop;
    const nodes = [
      this.large ? this.largeTitle() : null,
      this.error ? errorBanner(this.error, () => this.refresh()) : null,
      ...[this.content()].flat(Infinity),
      this.isSheet ? null : h("div", { class: "bottom-pad" }),
    ].filter(Boolean);
    this.scrollEl.replaceChildren(...nodes);
    this.scrollEl.scrollTop = top;
  }

  scrollToBottom() {
    requestAnimationFrame(() => this.scrollEl?.scrollTo({ top: this.scrollEl.scrollHeight, behavior: "smooth" }));
  }
}

export function navButton(label, onclick, { strong = false, disabled = false, iconName = null, aria = null } = {}) {
  return h("button", { class: `navbtn${strong ? " strong" : ""}`, type: "button", onclick, disabled, "aria-label": aria },
    iconName ? icon(iconName) : label);
}
