#!/usr/bin/env python3
"""LangCoach colour-token generator.

Reads `source.json` (OKLCH tonal ramps + semantic tokens per appearance) and writes:

  design/tokens/build/tokens.json         resolved values (OKLCH, Display P3, sRGB hex)
  design/tokens/build/tokens.css          CSS custom properties (light/dark/high-contrast), also copied to web/
  design/tokens/build/contrast-report.md  WCAG 2.2 contrast for every text/UI pair
  ios/LangCoach/Resources/Assets.xcassets/Colors/*.colorset   Display P3 colour sets
  ios/LangCoach/DesignSystem/ColorTokens.swift                SwiftUI accessors

Colour science
--------------
* Ramps are defined in OKLCH (Ottosson, "A perceptual color space for image processing", Dec 2020),
  so equal lightness steps look equal across hues.
* Out-of-gamut colours are mapped by reducing chroma at constant L and h (binary search), the
  approach CSS Color 4 uses, separately for Display P3 and sRGB.
* Contrast is WCAG 2.2 relative-luminance contrast on the sRGB value (W3C, Oct 2023).

No third-party dependencies. Run: python design/tokens/generate.py [--check]
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
XCASSETS = ROOT / "ios" / "LangCoach" / "Resources" / "Assets.xcassets"
SWIFT_OUT = ROOT / "ios" / "LangCoach" / "DesignSystem" / "ColorTokens.swift"

APPEARANCES = ("light", "dark", "lightHC", "darkHC")


# --------------------------------------------------------------------------- colour maths

def oklch_to_oklab(L: float, C: float, h: float) -> tuple[float, float, float]:
    hr = math.radians(h)
    return L, C * math.cos(hr), C * math.sin(hr)


def oklab_to_linear_srgb(L: float, a: float, b: float) -> tuple[float, float, float]:
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def linear_srgb_to_linear_p3(r: float, g: float, b: float) -> tuple[float, float, float]:
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b
    return (
        2.4934969 * x - 0.9313836 * y - 0.4027108 * z,
        -0.8294890 * x + 1.7626641 * y + 0.0236247 * z,
        0.0358458 * x - 0.0761724 * y + 0.9568845 * z,
    )


def encode(c: float) -> float:
    """sRGB / Display P3 transfer function (they share it)."""
    c = min(max(c, 0.0), 1.0)
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def decode(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def in_gamut(rgb: tuple[float, float, float], eps: float = 1e-5) -> bool:
    return all(-eps <= v <= 1 + eps for v in rgb)


def to_space(L: float, C: float, h: float, space: str) -> tuple[float, float, float]:
    lin = oklab_to_linear_srgb(*oklch_to_oklab(L, C, h))
    return linear_srgb_to_linear_p3(*lin) if space == "p3" else lin


def gamut_map(L: float, C: float, h: float, space: str) -> tuple[tuple[float, float, float], float]:
    """Reduce chroma at constant L,h until the colour fits `space`. Returns encoded RGB and chroma used."""
    if in_gamut(to_space(L, C, h, space)):
        lo = hi = C
    else:
        lo, hi = 0.0, C
        for _ in range(40):
            mid = (lo + hi) / 2
            if in_gamut(to_space(L, mid, h, space)):
                lo = mid
            else:
                hi = mid
    rgb = tuple(encode(v) for v in to_space(L, lo, h, space))
    return rgb, lo  # type: ignore[return-value]


def hex_to_rgb(hx: str) -> tuple[float, float, float]:
    hx = hx.lstrip("#")
    return tuple(int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{round(min(max(v, 0), 1) * 255):02X}" for v in rgb)


def srgb_to_oklch(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    r, g, b = (decode(v) for v in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    C = math.hypot(a, bb)
    h = math.degrees(math.atan2(bb, a)) % 360 if C > 1e-6 else 0.0
    return L, C, h


def luminance(rgb: tuple[float, float, float]) -> float:
    r, g, b = (decode(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# --------------------------------------------------------------------------- resolution

def ramp_chroma(L: float, peak: float) -> float:
    """Chroma envelope: full at mid lightness, tapering towards white and black."""
    t = 1 - abs(L - 0.58) / 0.6
    return peak * max(t, 0.12) ** 1.1


def build_ramps(src: dict) -> dict[str, dict[str, dict]]:
    ramps: dict[str, dict[str, dict]] = {}
    for fam, spec in src["families"].items():
        ramps[fam] = {}
        for step, L in src["steps"].items():
            C = ramp_chroma(L, spec["chroma"])
            ramps[fam][step] = resolve_oklch(L, C, spec["hue"])
    return ramps


def resolve_oklch(L: float, C: float, h: float) -> dict:
    p3, c_p3 = gamut_map(L, C, h, "p3")
    srgb, c_srgb = gamut_map(L, C, h, "srgb")
    return {
        "oklch": [round(L, 4), round(c_p3, 4), round(h, 2)],
        "p3": [round(v, 4) for v in p3],
        "srgb": [round(v, 4) for v in srgb],
        "hex": rgb_to_hex(srgb),
    }


OKLCH_LITERAL = re.compile(r"^oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\)$")


def resolve_ref(ref: str, ramps: dict) -> dict:
    if m := OKLCH_LITERAL.match(ref):
        return resolve_oklch(float(m.group(1)), float(m.group(2)), float(m.group(3)))
    if ref.startswith("#"):
        rgb = hex_to_rgb(ref)
        L, C, h = srgb_to_oklch(rgb)
        return {"oklch": [round(L, 4), round(C, 4), round(h, 2)], "p3": [round(v, 4) for v in rgb_srgb_to_p3(rgb)],
                "srgb": [round(v, 4) for v in rgb], "hex": ref.upper()}
    fam, step = ref.split(".")
    return ramps[fam][step]


def rgb_srgb_to_p3(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    lin = tuple(decode(v) for v in rgb)
    return tuple(encode(v) for v in linear_srgb_to_linear_p3(*lin))  # type: ignore[return-value]


def expand_tints(src: dict) -> dict:
    """Turn the tint recipes into semantic tokens: {name}, {name}Subtle, {name}Wash, {name}Ambient."""
    out = {}
    tints = src.get("tints", {})
    for name, hue in tints.get("hues", {}).items():
        for suffix, recipe in tints.get("recipes", {}).items():
            out[f"{name}{suffix}"] = {"role": recipe["role"],
                                     **{ap: f"oklch({recipe[ap][0]} {recipe[ap][1]} {hue})" for ap in APPEARANCES}}
    return out


TINT_NAMES: list[str] = []


def resolve(src: dict) -> tuple[dict, dict]:
    ramps = build_ramps(src)
    tokens: dict[str, dict] = {}
    TINT_NAMES[:] = list(src.get("tints", {}).get("hues", {}))
    for name, spec in {**src["semantic"], **expand_tints(src)}.items():
        tokens[name] = {"role": spec["role"], "on": spec.get("on"),
                        **{ap: {"ref": spec[ap], **resolve_ref(spec[ap], ramps)} for ap in APPEARANCES}}
    return ramps, tokens


# --------------------------------------------------------------------------- checks

EXTRA_PAIRS = [  # (foreground, background, required role)
    ("accent", "accentSubtle", "text"),
    ("textPrimary", "accentSubtle", "text"),
    ("textPrimary", "sunken", "text"),
    ("textSecondary", "sunken", "text"),
    ("textPrimary", "surfaceRaised", "text"),
    ("textSecondary", "surfaceRaised", "text"),
    ("accent", "surfaceRaised", "text"),
    ("borderStrong", "surfaceRaised", "ui"),
    ("success", "surface", "text"),
    ("danger", "surface", "text"),
    ("warning", "surface", "text"),
]


def tint_pairs() -> list[tuple[str, str, str]]:
    pairs = []
    for t in TINT_NAMES:
        pairs += [(t, f"{t}Subtle", "text"), (t, f"{t}Wash", "text"), (t, "surface", "text"), (t, "canvas", "text"),
                  ("textPrimary", f"{t}Subtle", "text"), ("textPrimary", f"{t}Wash", "text"), ("textPrimary", f"{t}Ambient", "text"),
                  ("textSecondary", f"{t}Wash", "text"), ("textSecondary", f"{t}Ambient", "text"),
                  ("accent", f"{t}Wash", "text"), ("borderStrong", f"{t}Wash", "ui")]
    return pairs


def required(role: str, appearance: str) -> float | None:
    hc = appearance.endswith("HC")
    return {"text": 7.0 if hc else 4.5, "largeText": 4.5 if hc else 3.0, "ui": 4.5 if hc else 3.0}.get(role)


def contrast_rows(tokens: dict) -> list[dict]:
    rows = []
    pairs: list[tuple[str, str, str]] = []
    tint_text = set(TINT_NAMES)
    for name, t in tokens.items():
        if t["role"] in ("text", "largeText", "ui") and name not in tint_text:
            backs = [t["on"]] if t["on"] else ["canvas", "surface"]
            pairs += [(name, b, t["role"]) for b in backs]
    pairs += EXTRA_PAIRS + tint_pairs()
    for fg, bg, role in pairs:
        for ap in APPEARANCES:
            need = required(role, ap)
            ratio = contrast(tuple(tokens[fg][ap]["srgb"]), tuple(tokens[bg][ap]["srgb"]))
            rows.append({"fg": fg, "bg": bg, "appearance": ap, "role": role,
                         "ratio": round(ratio, 2), "required": need, "pass": ratio >= (need or 0)})
    return rows


# --------------------------------------------------------------------------- writers

def write_json(ramps: dict, tokens: dict) -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "tokens.json").write_text(json.dumps({"ramps": ramps, "semantic": tokens}, indent=2) + "\n")


def kebab(name: str) -> str:
    return "".join("-" + c.lower() if c.isupper() else c for c in name)


def write_css(ramps: dict, tokens: dict) -> None:
    def block(ap: str, fmt: str) -> str:
        lines = []
        for name, t in tokens.items():
            v = t[ap]
            val = v["hex"] if fmt == "hex" else f"color(display-p3 {v['p3'][0]} {v['p3'][1]} {v['p3'][2]})"
            lines.append(f"  --lc-{kebab(name)}: {val};")
        return "\n".join(lines)

    css = [
        "/* Generated by design/tokens/generate.py. Do not edit by hand. */",
        ":root {", block("light", "hex"), "}",
        '@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {', block("dark", "hex"), "} }",
        ':root[data-theme="dark"] {', block("dark", "hex"), "}",
        '@media (prefers-contrast: more) { :root:not([data-theme="dark"]) {', block("lightHC", "hex"), "} }",
        '@media (prefers-contrast: more) and (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {',
        block("darkHC", "hex"), "} }",
        "@supports (color: color(display-p3 1 1 1)) { @media (color-gamut: p3) {",
        "  :root {", block("light", "p3"), "  }",
        '  :root[data-theme="dark"] {', block("dark", "p3"), "  }",
        '  @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {', block("dark", "p3"), "  } }",
        "} }",
    ]
    (BUILD / "tokens.css").write_text("\n".join(css) + "\n")
    web = ROOT / "web"
    if web.is_dir():
        (web / "tokens.css").write_text("\n".join(css) + "\n")  # web test client uses the same tokens


def write_report(tokens: dict, rows: list[dict]) -> None:
    out = ["# Contrast report", "", "Generated by `design/tokens/generate.py`. WCAG 2.2 contrast on sRGB values.",
           "Text needs 4.5:1 (7:1 in high contrast); large text and UI 3:1 (4.5:1 in high contrast).", "",
           "## Semantic tokens", "", "| Token | Light | Dark | Light HC | Dark HC |", "|---|---|---|---|---|"]
    for name, t in tokens.items():
        out.append(f"| `{name}` | " + " | ".join(f"`{t[ap]['hex']}` ({t[ap]['ref']})" for ap in APPEARANCES) + " |")
    out += ["", "## Pairs", "", "| Foreground | Background | Appearance | Role | Ratio | Needs | |",
            "|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| `{r['fg']}` | `{r['bg']}` | {r['appearance']} | {r['role']} | {r['ratio']} | {r['required']} | "
                   f"{'pass' if r['pass'] else '**FAIL**'} |")
    (BUILD / "contrast-report.md").write_text("\n".join(out) + "\n")


def write_xcassets(tokens: dict) -> None:
    colors = XCASSETS / "Colors"
    colors.mkdir(parents=True, exist_ok=True)
    info = {"info": {"author": "xcode", "version": 1}}
    (XCASSETS / "Contents.json").write_text(json.dumps(info, indent=2) + "\n")
    (colors / "Contents.json").write_text(json.dumps({**info, "properties": {"provides-namespace": False}}, indent=2) + "\n")
    appearance_keys = {
        "light": [],
        "dark": [{"appearance": "luminosity", "value": "dark"}],
        "lightHC": [{"appearance": "contrast", "value": "high"}],
        "darkHC": [{"appearance": "luminosity", "value": "dark"}, {"appearance": "contrast", "value": "high"}],
    }
    for name, t in tokens.items():
        entries = []
        for ap in APPEARANCES:
            r, g, b = t[ap]["p3"]
            entry: dict = {"color": {"color-space": "display-p3", "components": {
                "alpha": "1.000", "red": f"{r:.4f}", "green": f"{g:.4f}", "blue": f"{b:.4f}"}}, "idiom": "universal"}
            if appearance_keys[ap]:
                entry = {"appearances": appearance_keys[ap], **entry}
            entries.append(entry)
        cs = colors / f"{name}.colorset"
        cs.mkdir(exist_ok=True)
        (cs / "Contents.json").write_text(json.dumps({"colors": entries, **info}, indent=2) + "\n")


def write_swift(tokens: dict) -> None:
    SWIFT_OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = ["// Generated by design/tokens/generate.py. Do not edit by hand.", "import SwiftUI", "",
             "/// Semantic colour tokens. Values live in Assets.xcassets/Colors (Display P3, light/dark/high contrast).",
             "public enum LC {", "    public enum Color {"]
    for name in tokens:
        lines.append(f'        public static let {name} = SwiftUI.Color("{name}", bundle: .main)')
    lines += ["    }", "}", ""]
    SWIFT_OUT.write_text("\n".join(lines))


def main() -> int:
    src = json.loads((HERE / "source.json").read_text())
    ramps, tokens = resolve(src)
    rows = contrast_rows(tokens)
    write_json(ramps, tokens)
    write_css(ramps, tokens)
    write_report(tokens, rows)
    write_xcassets(tokens)
    write_swift(tokens)
    failures = [r for r in rows if not r["pass"]]
    print(f"{len(tokens)} tokens x {len(APPEARANCES)} appearances; {len(rows)} contrast checks; {len(failures)} failing")
    for f in failures:
        print(f"  FAIL {f['fg']} on {f['bg']} ({f['appearance']}): {f['ratio']} < {f['required']}")
    return 1 if failures and "--check" in sys.argv else 0


if __name__ == "__main__":
    raise SystemExit(main())
