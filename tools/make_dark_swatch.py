#!/usr/bin/env python3
"""
Generate assets/floral-dark.webp from assets/floral-light.webp.

The dark colourway is derived, never redrawn: each pixel's distance below the
swatch's own ground becomes an amount of "ink", and that ink is repainted as a
soft blue on a navy ground. Motif, placement and tiling are therefore identical
to Anna's picture -- only the palette flips.

Rerun this whenever the light swatch is replaced.

Usage:  make_dark_swatch.py
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "floral-light.webp"
DST = ROOT / "assets" / "floral-dark.webp"

GROUND = 240.0          # luma of #eff2ef, the swatch's ground
FLOOR = 138.0           # luma of the deepest ink in the swatch
DARK = (15, 21, 29)     # #0f151d -- matches the floral pack's dark --bg
GLOW = (73, 100, 130)   # the flowers, lifted off that ground


def main():
    im = Image.open(SRC).convert("RGB")
    w, h = im.size
    px = im.load()
    out = Image.new("RGB", (w, h))
    o = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
            ink = min(1.0, max(0.0, (GROUND - luma) / (GROUND - FLOOR)))
            o[x, y] = tuple(round(DARK[i] + ink * (GLOW[i] - DARK[i])) for i in range(3))
    out.save(DST, "WEBP", quality=90, method=6)
    print(f"wrote {DST}  ({DST.stat().st_size // 1024} KB, {w}x{h})")


if __name__ == "__main__":
    main()
