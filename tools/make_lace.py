#!/usr/bin/env python3
"""
Turn the lace photograph into a border-image source.

The source Finn supplied (`lace.jpeg`) is a screenshot of a transparent PNG, so
the transparency arrives baked in as a dark checkerboard. It is reconstructed
here rather than hard cut out: the lace is white and the checker is dark, and
the netting between the motifs is genuinely semi-transparent, so alpha comes
from brightness. A hard threshold would turn that netting into a solid slab and
lose what makes it read as lace.

The output is a nine-slice square: a repeatable run of lace along each edge and
a mitred join in each corner, exactly as a picture framer would cut it. The edge
run is built as a motif plus its own mirror image, which is what makes it tile
with no seam -- the lace is photographed, not drawn, so its motifs are not
identical and butt-joining two of them leaves a visible step.

    python3 tools/make_lace.py               # every pack that declares a lace
    python3 tools/make_lace.py --preview     # also drop a PNG proof in build/
"""
import argparse, io, json, pathlib
from PIL import Image, ImageDraw

ROOT   = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / "lace.jpeg"
ASSETS = ROOT / "assets"
THEMES = ROOT / "data" / "themes.json"

# The checkerboard sits at luminance 35 and 59; the lace runs 96..255.
ALPHA_FLOOR, ALPHA_CEIL = 68.0, 250.0
BAND      = 96      # band thickness in source px; renders at --lace-w on screen
SCALLOPS  = "out"   # scalloped edge faces AWAY from the card, straight edge
                    # against it -- the card keeps a clean rectangle and the
                    # lace reads as trim on a doily rather than as a frame
                    # eating into the content.


def extract(path):
    """Photograph -> white lace on real alpha, cropped to the lace itself."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    out = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    o = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            if lum > ALPHA_FLOOR:
                a = min(255, round(255 * (lum - ALPHA_FLOOR) / (ALPHA_CEIL - ALPHA_FLOOR)))
                o[x, y] = (255, 255, 255, a)
    return out.crop(out.getbbox())


def repeat_unit(strip):
    """
    One seamless run of lace.

    The motif period comes from the alpha profile's autocorrelation, and the cut
    is placed at the quietest column inside that period so the mirror line falls
    in open netting rather than through the middle of a flower. Mirroring is what
    guarantees the seam: both ends of the unit are then the same column.
    """
    a = strip.getchannel("A")
    w, h = a.size
    px = a.load()
    col = [sum(px[x, y] for y in range(h)) / h for x in range(w)]
    mean = sum(col) / w
    cen = [c - mean for c in col]
    base = sum(c * c for c in cen) / w

    def score(lag):
        n = w - lag
        return sum(cen[i] * cen[i + lag] for i in range(n)) / n / base

    period = max(range(60, w // 2), key=score)
    # The mirror makes both joins geometrically exact wherever it is cut, so the
    # cut column is chosen for how it LOOKS doubled, not to hide a seam. Cutting
    # at the sparsest column was the first attempt and it is wrong: the mirror
    # axis is then a near-empty column sitting next to its own reflection, which
    # reads as a hairline gap repeating down every edge. Cutting at the densest
    # column puts the axis through solid thread, where the doubling disappears.
    start = max(range(0, period), key=lambda x: col[x])
    unit = strip.crop((start, 0, start + period, h))
    mirror = unit.transpose(Image.FLIP_LEFT_RIGHT).crop((1, 0, period - 1, h))
    out = Image.new("RGBA", (unit.width + mirror.width, h), (255, 255, 255, 0))
    out.paste(unit, (0, 0))
    out.paste(mirror, (unit.width, 0))
    return out, period


def tint(img, rgb):
    t = Image.new("RGBA", img.size, tuple(rgb) + (0,))
    t.putalpha(img.getchannel("A"))
    return t


def triangle(size, corner):
    """
    Mask for one half of a mitred corner, split on the outer-to-inner diagonal.

    The polygon is outlined as well as filled so the two halves overlap by a
    pixel along the diagonal. Without that they meet exactly and antialiasing
    leaves a hairline of ground showing straight through the corner.
    """
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.polygon(corner, fill=255, outline=255, width=2)
    return m


def build(strip, band, scallops):
    """Nine-slice source: mitred corners, one seamless run along each edge."""
    scale = band / strip.height
    strip = strip.resize((max(1, round(strip.width * scale)), band), Image.LANCZOS)
    # The photograph has its straight picot edge at the top and its scallops at
    # the bottom. Whichever edge ends up at y=0 becomes the OUTER edge of the
    # border, so flipping here is what points the scallops away from the card.
    if scallops == "out":
        strip = strip.transpose(Image.FLIP_TOP_BOTTOM)
    run, period = repeat_unit(strip)
    E = run.width
    S = 2 * band + E

    top    = run
    bottom = run.transpose(Image.FLIP_TOP_BOTTOM)
    left   = run.rotate(90, expand=True)
    right  = run.rotate(-90, expand=True)

    out = Image.new("RGBA", (S, S), (255, 255, 255, 0))
    out.paste(top,    (band, 0))
    out.paste(bottom, (band, band + E))
    out.paste(left,   (0, band))
    out.paste(right,  (band + E, band))

    # Corners: the horizontal run keeps the triangle on its side of the diagonal
    # that runs from the outer corner to the inner one, the vertical run the other.
    # The corner pieces are cut from the END of the run, not the start. The run
    # tiles seamlessly, so its last column matches its first -- taking the tail
    # means the corner flows into the run that repeats away from it, instead of
    # restarting the motif and showing a step at the slice boundary.
    b = band
    hpiece = top.crop((E - b, 0, E, b))
    vpiece = left.crop((0, E - b, b, E))
    # Each corner splits on the diagonal running from its OUTER corner to its
    # inner one -- top-left and bottom-right therefore split on the main
    # diagonal, top-right and bottom-left on the anti-diagonal. Getting that
    # backwards on one corner is not subtle: the two runs cross instead of
    # meeting and the join tears open.
    for (ox, oy), hmask, vmask in [
        ((0, 0),               [(0, 0), (b, 0), (b, b)], [(0, 0), (0, b), (b, b)]),
        ((band + E, 0),        [(0, 0), (b, 0), (0, b)], [(b, 0), (b, b), (0, b)]),
        ((0, band + E),        [(0, b), (b, b), (b, 0)], [(0, 0), (0, b), (b, 0)]),
        ((band + E, band + E), [(0, 0), (0, b), (b, b)], [(0, 0), (b, 0), (b, b)]),
    ]:
        h = hpiece.transpose(Image.FLIP_LEFT_RIGHT) if ox else hpiece
        v = vpiece.transpose(Image.FLIP_TOP_BOTTOM) if oy else vpiece
        if oy:
            h = h.transpose(Image.FLIP_TOP_BOTTOM)
        if ox:
            v = v.transpose(Image.FLIP_LEFT_RIGHT)
        out.paste(h, (ox, oy), Image.composite(h.getchannel("A"), Image.new("L", (b, b), 0), triangle(b, hmask)))
        out.paste(v, (ox, oy), Image.composite(v.getchannel("A"), Image.new("L", (b, b), 0), triangle(b, vmask)))
    return out, band, E, period


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--band", type=int, default=BAND)
    ap.add_argument("--scallops", choices=("in", "out"), default=SCALLOPS)
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()

    if not SOURCE.exists():
        raise SystemExit(f"missing lace source: {SOURCE}")
    themes = json.loads(THEMES.read_text(encoding="utf-8"))

    lace = extract(SOURCE)
    print(f"lace extracted: {lace.size[0]}x{lace.size[1]} from {SOURCE.name}")
    frame, band, edge, period = build(lace, args.band, args.scallops)
    print(f"motif period {period}px -> seamless run {edge}px, band {band}px, "
          f"source {frame.size[0]}x{frame.size[1]}, scallops {args.scallops}")

    for key, pack in themes["packs"].items():
        colour = pack["light"].get("lace")
        if not colour or colour == "transparent":
            continue
        rgb = tuple(int(colour.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        dst = ASSETS / f"lace-{key}.webp"
        tint(frame, rgb).save(dst, "WEBP", quality=92, method=6, lossless=False)
        print(f"  {key:12s} {colour}  ->  {dst.name}  {dst.stat().st_size // 1024} KB")
        if args.preview:
            p = Image.new("RGB", (frame.width, frame.height), (254, 255, 255))
            t = tint(frame, rgb)
            p.paste(t, (0, 0), t)
            p.save(ROOT / "build" / f"lace-{key}-proof.png")

    meta = {"band": band, "edge": edge, "size": frame.size[0]}
    (ASSETS / "lace-slice.json").write_text(json.dumps(meta), encoding="utf-8")
    print(f"slice metadata -> assets/lace-slice.json  {meta}")


if __name__ == "__main__":
    main()
