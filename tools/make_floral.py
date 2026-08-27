#!/usr/bin/env python3
"""
Build the floral tile.

Finn sent two captures of the same rose wallpaper. `background.jpeg` is 140x140
and carries the colours he wants -- a near-white ground -- but it is shot so wide
that each rose is about fifteen pixels across, and nothing recovers detail that
was never captured; on the page it reads as fuzz. `floral-light-v1.webp` is
351x351: the same print shot close, with the roses legible, on a warmer
off-white ground.

So the tile is the SHARP capture recoloured to the COLOURS of the other, rather
than either file used as-is. The recolour is a ground swap, not a filter: each
pixel's distance below its own ground is measured and re-applied against the new
one, so the motif and its placement are untouched and only the paper changes.
The same reasoning built the dark swatch that used to live in assets/.

    python3 tools/make_floral.py
    python3 tools/make_floral.py --preview   # side-by-side proof in build/
"""
import argparse, pathlib
from PIL import Image

ROOT   = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SHARP  = ASSETS / "floral-light-v1.webp"      # detail comes from here
COLOUR = ASSETS / "background-source.jpeg"    # colour comes from here
OUT    = ASSETS / "floral-light.webp"

GAIN = 1.18   # motif contrast against the ground; >1 makes the roses read


def ground_of(im, bright=0.9):
    """The paper colour: the most common near-white pixel."""
    from collections import Counter
    px = list(im.getdata())
    hi = [c for c in px if sum(c) / 3 > 235]
    return Counter(hi or px).most_common(1)[0][0]


def recolour(sharp, src_ground, dst_ground, gain=GAIN):
    w, h = sharp.size
    out = Image.new("RGB", (w, h))
    sp, op = sharp.load(), out.load()
    for y in range(h):
        for x in range(w):
            c = sp[x, y]
            op[x, y] = tuple(
                max(0, min(255, round(dst_ground[i] - (src_ground[i] - c[i]) * gain)))
                for i in range(3)
            )
    return out


def seam(im):
    """Wrap-around difference against the internal one -- does it still tile?"""
    w, h = im.size
    px = im.load()
    wv = sum(sum(abs(a - b) for a, b in zip(px[x, 0], px[x, h - 1])) for x in range(w)) / (w * 3)
    wh = sum(sum(abs(a - b) for a, b in zip(px[0, y], px[w - 1, y])) for y in range(h)) / (h * 3)
    step = max(1, w // 120)
    xs, ys = range(0, w, step), range(0, h - 1, step)
    iv = sum(sum(abs(a - b) for a, b in zip(px[x, y], px[x, y + 1])) for x in xs for y in ys) \
         / (len(xs) * len(ys) * 3)
    return wv, wh, iv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gain", type=float, default=GAIN)
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()

    for p in (SHARP, COLOUR):
        if not p.exists():
            raise SystemExit(f"missing source: {p}")

    sharp = Image.open(SHARP).convert("RGB")
    colour = Image.open(COLOUR).convert("RGB")
    g_sharp, g_colour = ground_of(sharp), ground_of(colour)
    print(f"detail  {SHARP.name}  {sharp.size[0]}x{sharp.size[1]}  ground #{'%02x%02x%02x' % g_sharp}")
    print(f"colour  {COLOUR.name}  {colour.size[0]}x{colour.size[1]}  ground #{'%02x%02x%02x' % g_colour}")

    tile = recolour(sharp, g_sharp, g_colour, args.gain)
    wv, wh, iv = seam(tile)
    print(f"tiling  wrap {wv:.2f} / {wh:.2f} vs internal {iv:.2f}", end="  ")
    if max(wv, wh) > iv * 2.2:
        raise SystemExit("FAIL: recolour broke the tile's wrap-around match")
    print("ok")

    tile.save(OUT, "WEBP", quality=95, method=6)
    print(f"wrote   {OUT.name}  {OUT.stat().st_size // 1024} KB  gain {args.gain}")

    if args.preview:
        up = lambda im, n=3: im.resize((im.size[0] * n, im.size[1] * n), Image.NEAREST)
        a = up(colour.resize((140, 140)), 3)
        b = up(tile.crop((0, 0, 140, 140)), 3)
        p = Image.new("RGB", (a.width + b.width + 20, a.height), "white")
        p.paste(a, (0, 0)); p.paste(b, (a.width + 20, 0))
        p.save(ROOT / "build" / "floral-proof.png")
        print("proof   build/floral-proof.png  (his colours | new tile, same scale)")


if __name__ == "__main__":
    main()
