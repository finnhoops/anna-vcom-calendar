#!/usr/bin/env python3
"""
Verify every colour pair in data/themes.json against WCAG AA.

Design rules only mean something if they are checked, so this asserts rather
than assumes: body text needs 4.5:1, large text and UI components need 3:1.
Run it after any edit to themes.json.

Usage:  check_contrast.py [themes.json]
"""

import json
import sys
from pathlib import Path

AA_TEXT = 4.5
AA_LARGE = 3.0


def srgb(channel):
    c = channel / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour):
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * srgb(r) + 0.7152 * srgb(g) + 0.0722 * srgb(b)


def ratio(fg, bg):
    a, b = luminance(fg), luminance(bg)
    lo, hi = sorted((a, b))
    return (hi + 0.05) / (lo + 0.05)


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/themes.json")
    themes = json.loads(path.read_text())
    failures, checks = [], 0

    def check(label, fg, bg, minimum):
        nonlocal checks
        checks += 1
        value = ratio(fg, bg)
        if value < minimum:
            failures.append(f"{label}: {fg} on {bg} = {value:.2f}:1 (need {minimum})")
        return value

    # A pack marked noDark never renders in dark, so its dark block is not a
    # state the page can reach and must not be pulled into the ground sets --
    # doing so tests the dark highlighters against a near-white ground that only
    # ever appears in light.
    def modes_of(pack):
        return ("light",) if pack.get("noDark") else ("light", "dark")

    for key, pack in themes["packs"].items():
        for mode in modes_of(pack):
            t = pack[mode]
            where = f"{key}/{mode}"
            # accentSoft is a real ground, not just a tint behind ink: a month
            # cell in the grid's edit mode wears it under the day number, the
            # class count and the category dots.
            for ground in ("bg", "surface", "surface2", "accentSoft"):
                check(f"{where} ink on {ground}", t["ink"], t[ground], AA_TEXT)
                check(f"{where} ink2 on {ground}", t["ink2"], t[ground], AA_TEXT)
                check(f"{where} ink3 on {ground}", t["ink3"], t[ground], AA_LARGE)
                check(f"{where} accent on {ground}", t["accent"], t[ground], AA_LARGE)
            check(f"{where} accentInk on accent", t["accentInk"], t["accent"], AA_TEXT)
            check(f"{where} ink on accentSoft", t["ink"], t["accentSoft"], AA_TEXT)
            check(f"{where} line on surface", t["line"], t["surface"], 1.2)

    # Category hues carry meaning, so they must clear 3:1 as UI components on
    # every ground they can sit on, in the matching light/dark variant.
    grounds = {mode: {pack[mode][g] for pack in themes["packs"].values()
                      if mode in modes_of(pack)
                      for g in ("bg", "surface", "surface2", "accentSoft")}
               for mode in ("light", "dark")}
    for name, hues in themes["categories"].items():
        for mode in ("light", "dark"):
            for ground in sorted(grounds[mode]):
                check(f"category {name}/{mode} on {ground}", hues[mode], ground, AA_LARGE)

    for name, hues in themes.get("highlighters", {}).items():
        for mode in ("light", "dark"):
            for ground in sorted(grounds[mode]):
                check(f"highlighter {name}/{mode} on {ground}", hues[mode], ground, AA_TEXT)

    print(f"{checks} pairs checked")
    if failures:
        print(f"\n{len(failures)} FAILED:")
        for line in failures:
            print(f"  {line}")
        sys.exit(1)
    print("all pairs meet WCAG AA")


if __name__ == "__main__":
    main()
