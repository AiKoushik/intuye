// Browser stand-ins for the iPhone's on-device SpeechAnalyzer and AVSpeechSynthesizer.
// Web Speech recognition (Chrome/Edge) uses the browser's speech service, not on-device transcription.
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
export const speechSupported = Boolean(SR);

export class Recognizer {
  constructor() {
    this.running = false;
    this.text = "";
    this.listeners = new Set();
    this.rec = null;
  }

  on(fn) { this.listeners.add(fn); return () => this.listeners.delete(fn); }
  #emit() { for (const fn of this.listeners) fn(this); }

  /** Starts listening. In continuous mode it restarts itself until stop() (Chrome ends sessions after silence). */
  start(lang, { continuous = false, onFinal } = {}) {
    if (!SR) throw new Error("Speech needs Chrome or Edge. You can type instead.");
    if (this.running) return;
    this.final = "";
    this.text = "";
    this.keepAlive = continuous;
    this.running = true;
    this.ended = new Promise((resolve) => { this.resolveEnded = resolve; });
    this.#open(lang, onFinal);
    this.#emit();
  }

  #open(lang, onFinal) {
    const rec = new SR();
    rec.lang = lang;
    rec.interimResults = true;
    rec.continuous = true;
    rec.onresult = (e) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) {
          this.final += (this.final ? " " : "") + r[0].transcript.trim();
          onFinal?.(r[0].transcript.trim());
        } else interim += r[0].transcript;
      }
      this.text = `${this.final} ${interim}`.trim();
      this.#emit();
    };
    rec.onerror = (e) => { this.error = e.error; };
    rec.onend = () => {
      if (this.keepAlive && this.error !== "not-allowed") { this.#open(lang, onFinal); return; }
      this.running = false;
      this.#emit();
      this.resolveEnded(this.final || this.text);
    };
    this.error = null;
    this.rec = rec;
    rec.start();
  }

  async stop() {
    if (!this.running || !this.rec) return this.text;
    this.keepAlive = false;
    this.rec.stop();
    const t = await this.ended;
    this.rec = null;
    return t.trim();
  }
}

/** Speaks target-language text. `lang` is the variety's voice language from the server (e.g. "es-MX"). */
export function speak(text, lang, slow = false) {
  if (!("speechSynthesis" in window) || !lang) return;
  const voices = speechSynthesis.getVoices();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang;
  const base = lang.split("-")[0];
  u.voice = voices.find((v) => v.lang.replace("_", "-") === lang) || voices.find((v) => v.lang.startsWith(base)) || null;
  u.rate = slow ? 0.8 : 0.95;
  speechSynthesis.cancel();
  speechSynthesis.speak(u);
}

export const NATIVE_LOCALE = "en-US";
