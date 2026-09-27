"""Tiny helpers shared by build_art.py: palette, font subsetting, text measuring.

Fonts (all free to embed): TeX Gyre Heros / Heros Cn (GUST licence, CTAN)
and DejaVu Sans Mono. Drop these files into scripts/fonts/ (or point FONT_DIR
at them): texgyreheroscn-bold.otf, texgyreheros-regular.otf,
texgyreheros-bold.otf, DejaVuSansMono.ttf, DejaVuSansMono-Bold.ttf.
"""
import base64
import io
import os
from functools import lru_cache

from fontTools import subset
from fontTools.ttLib import TTFont

FONT_DIR = os.environ.get("FONT_DIR", os.path.join(os.path.dirname(__file__), "fonts"))

FONTS = {
    # key: (file, css family, weight)
    "disp": ("texgyreheroscn-bold.otf", "PmDisp", 700),
    "sans": ("texgyreheros-regular.otf", "PmSans", 400),
    "sansb": ("texgyreheros-bold.otf", "PmSansB", 700),
    "mono": ("DejaVuSansMono.ttf", "PmMono", 400),
    "monob": ("DejaVuSansMono-Bold.ttf", "PmMonoB", 700),
}

# Solid colours only. Graphite + safety orange, one warm secondary.
C = {
    "bg": "#131416",
    "panel": "#16171A",
    "grid": "#1E2024",
    "line": "#2A2D33",
    "ink": "#EDE9E2",
    "dim": "#8C9098",
    "mute": "#5A5E66",
    "steel": "#D6D1C8",
    "steel2": "#A9A49B",
    "orange": "#FF6B1A",
    "orange_dk": "#B8480C",
    "amber": "#FFC247",
}


@lru_cache(maxsize=None)
def _ttf(key):
    return TTFont(os.path.join(FONT_DIR, FONTS[key][0]))


def measure(key, s, size, spacing=0.0):
    """Advance width of s in px (no kerning; good enough for layout)."""
    f = _ttf(key)
    upm = f["head"].unitsPerEm
    cmap = f.getBestCmap()
    hmtx = f["hmtx"]
    w = 0
    for ch in s:
        g = cmap.get(ord(ch))
        if g is None:
            g = ".notdef"
        w += hmtx[g][0]
    return w / upm * size + spacing * max(len(s) - 1, 0)


def font_css(used):
    """used: dict font-key -> set of chars. Returns @font-face css with WOFF subsets."""
    out = []
    for key, chars in used.items():
        if not chars:
            continue
        fname, fam, weight = FONTS[key]
        opts = subset.Options()
        opts.flavor = "woff"
        opts.layout_features = ["kern"]
        opts.name_IDs = [1, 2]
        opts.notdef_outline = True
        opts.hinting = False
        opts.desubroutinize = True
        font = subset.load_font(os.path.join(FONT_DIR, fname), opts)
        sub = subset.Subsetter(opts)
        sub.populate(text="".join(sorted(chars)) + " ")
        sub.subset(font)
        buf = io.BytesIO()
        subset.save_font(font, buf, opts)
        b64 = base64.b64encode(buf.getvalue()).decode()
        out.append(
            f"@font-face{{font-family:'{fam}';font-weight:{weight};"
            f"src:url(data:font/woff;base64,{b64}) format('woff');}}"
        )
    return "\n".join(out)


FALLBACK = {
    "disp": "'Arial Narrow', 'Helvetica Neue', Arial, sans-serif",
    "sans": "'Helvetica Neue', Helvetica, Arial, sans-serif",
    "sansb": "'Helvetica Neue', Helvetica, Arial, sans-serif",
    "mono": "ui-monospace, Menlo, Consolas, monospace",
    "monob": "ui-monospace, Menlo, Consolas, monospace",
}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class SVG:
    def __init__(self, w, h, title, desc=""):
        self.w, self.h = w, h
        self.title, self.desc = title, desc
        self.parts = []
        self.defs = []
        self.css = []
        self.used = {k: set() for k in FONTS}

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, font="mono", size=14, fill=None, anchor="start",
             spacing=0, extra="", raw=False):
        fill = fill or C["ink"]
        self.used[font].update(s)
        fam = f"{FONTS[font][1]}, {FALLBACK[font]}"
        ls = f' letter-spacing="{spacing}"' if spacing else ""
        body = s if raw else esc(s)
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-weight="{FONTS[font][2]}" font-size="{size}" '
                f'fill="{fill}" text-anchor="{anchor}"{ls} {extra}>{body}</text>')

    def put_text(self, *a, **k):
        self.add(self.text(*a, **k))

    def render(self):
        css = font_css(self.used) + "\n" + "\n".join(self.css)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="t d">\n'
            f'<title id="t">{esc(self.title)}</title><desc id="d">{esc(self.desc)}</desc>\n'
            f"<style>{css}</style>\n"
            f"<defs>{''.join(self.defs)}</defs>\n" + "\n".join(self.parts) + "\n</svg>\n"
        )
