"""Regenerate every hand-made SVG in ../assets.

    FONT_DIR=/path/to/fonts python scripts/build_art.py

Needs fontTools. Fonts: TeX Gyre Heros (+ Cn), DejaVu Sans Mono.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import cards  # noqa: E402
import hero  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "assets")


def write(name, svg):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"{name:40s} {len(svg)/1024:6.1f} KB")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    write("hero.svg", hero.build())
    for i, p in enumerate(cards.PROJECTS):
        write(f"card-{p['slug'].lower()}.svg", cards.card(p, "left" if i % 2 == 0 else "right"))
    write("bom.svg", cards.bom())
    for name, label, icon in cards.BUTTONS:
        write(name, cards.button(label, icon))
