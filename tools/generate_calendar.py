#!/usr/bin/env python3
"""
Build build/index.html from data/schedule.json + data/themes.json.

The page is one self-contained file with the schedule baked in as a JS literal,
the same shape as the money dashboard. Anna's own edits are NOT baked in -- they
live in her browser, so regenerating never overwrites them.

Usage:  generate_calendar.py [-o build/index.html] [--no-archive]
"""

import argparse
import base64
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path(__file__).resolve().parent / "app_template.html"

HIGHLIGHTERS = {}

TOKEN_NAMES = ["bg", "surface", "surface2", "line", "ink", "ink2", "ink3",
               "accent", "accentInk", "accentSoft", "ring"]

def css_var(name):
    """Token names are used verbatim in the template: accentInk -> --accentInk."""
    return "--" + name


ASSETS = ROOT / "assets"

# Anna's reference swatch, tiled. It is a real 351x351 repeat -- its wrap-around
# pixel difference matches its internal difference, so it tiles with no seam.
# Rendered a little under native size so the blossoms sit at the scale of the
# picture and the upscale on a 2x screen stays mild. 260px against a 351px
# source is a DOWNSCALE, which is what keeps the roses crisp -- the 140px
# capture was being blown up 1.4x and read as fuzz. See tools/make_floral.py.
PATTERN_SIZE = "260px 260px"
_PATTERN_CACHE = {}
_LACE_CACHE = {}

# The lace band on screen. Chosen by rendering 28 / 40 / 52px side by side over
# the real floral ground: at 28px the scallops compress into a plain blue stripe
# and the thing reads as a ribbon rather than as lace, and 52px is more frame
# than card. The source band is 96px, so 40px is still a 2.4x reduction and
# holds up on a 2x display.
LACE_W = "40px"
LACE_SLICE = json.loads((ASSETS / "lace-slice.json").read_text(encoding="utf-8")) \
    if (ASSETS / "lace-slice.json").exists() else {"band": 96}


def pattern_url(name, mode):
    """
    Embed the tile as a data URI. The picture IS the pattern -- an approximation
    in gradients was tried and rejected, and an SVG cannot be used at all (see
    the lace note in app_template.html). Keeping it inline means build/index.html
    stays one self-contained file that opens from disk and archives whole.
    """
    key = (name, mode)
    if key not in _PATTERN_CACHE:
        src = ASSETS / f"{name}-{mode}.webp"
        if not src.exists():
            raise SystemExit(f"missing pattern asset: {src}")
        data = base64.b64encode(src.read_bytes()).decode("ascii")
        _PATTERN_CACHE[key] = f'url("data:image/webp;base64,{data}")'
    return _PATTERN_CACHE[key]


def cat_key(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def lace_url(pack_key):
    """
    The lace border, base64'd in like the floral tile. It is a photograph cut
    into a nine-slice by tools/make_lace.py, not drawn in CSS -- the 17 layers of
    gradients this replaces were a good approximation of lace and still only an
    approximation. Run `python3 tools/make_lace.py` after changing a lace colour.
    """
    if pack_key not in _LACE_CACHE:
        src = ASSETS / f"lace-{pack_key}.webp"
        if not src.exists():
            raise SystemExit(f"missing lace asset: {src} -- run tools/make_lace.py")
        data = base64.b64encode(src.read_bytes()).decode("ascii")
        _LACE_CACHE[pack_key] = f'url("data:image/webp;base64,{data}")'
    return _LACE_CACHE[pack_key]


def token_block(tokens, categories, mode, indent="  ", pack_key=None):
    lines = [f"{indent}{css_var(k)}:{tokens[k]};" for k in TOKEN_NAMES if k in tokens]
    lines += [f"{indent}--cat-{cat_key(name)}:{hues[mode]};"
              for name, hues in categories.items()]
    lines += [f"{indent}--hl-{name}:{hues[mode]};"
              for name, hues in (HIGHLIGHTERS or {}).items()]
    pattern = tokens.get("pattern")
    lace = tokens.get("lace", "transparent")
    lines.append(f"{indent}--lace:{lace};")
    lines.append(f"{indent}--lace-line:{tokens.get('laceLine', 'transparent')};")
    lines.append(f"{indent}--lace-w:{'0px' if lace == 'transparent' else LACE_W};")
    lines.append(f"{indent}--lace-img:{lace_url(pack_key) if lace != 'transparent' else 'none'};")
    lines.append(f"{indent}--lace-slice:{LACE_SLICE['band']};")
    # The 1px rule that defines a card's edge is redundant once lace defines it,
    # and worse than redundant: it traces a straight rectangle just inside a
    # scalloped edge, which reads as a mistake.
    lines.append(f"{indent}--card-outline:{tokens.get('line') if lace == 'transparent' else 'transparent'};")
    # Only a patterned pack needs the masthead veil; a flat ground has nothing
    # for the type to fight, and a wash over it would just look like a smudge.
    # 70% of the ground. Measured, not guessed: at 50% the small uppercase type
    # under the title still fails AA against the darkest rose in the tile, and at
    # 95% the veil erases the pattern behind the masthead entirely.
    veil = f"{tokens['bg']}b3" if pattern else "transparent"
    lines.append(f"{indent}--veil:{veil};")
    lines.append(f"{indent}--pattern:{pattern_url(pattern, mode) if pattern else 'none'};")
    lines.append(f"{indent}--pattern-size:{PATTERN_SIZE if pattern else 'auto'};")
    lines.append(f"{indent}color-scheme:{mode};")
    return "\n".join(lines)


def build_theme_css(themes):
    """
    One selector per pack for the chosen season, and a prefers-color-scheme
    block per pack for the viewer's light/dark preference. Every colour the page
    uses is defined here and nowhere else.

    A pack marked `"noDark": true` is single-colourway: no dark block is emitted
    at all, so it looks the same whatever the device is set to. Floral is that
    pack -- it is a picture of white fabric, and the derived navy colourway read
    as a different, worse thing rather than as the same fabric at night.
    """
    cats = themes["categories"]
    HIGHLIGHTERS.update(themes.get("highlighters", {}))
    out = []
    for key in themes["order"]:
        pack = themes["packs"][key]
        selector = f':root[data-theme="{key}"]'
        if key == themes["default"]:
            selector = f':root, {selector}'
        out.append(f"{selector}{{\n{token_block(pack['light'], cats, 'light', pack_key=key)}\n}}")
        if pack.get("noDark"):
            continue
        out.append(
            f"@media (prefers-color-scheme:dark){{\n"
            f"  {selector}{{\n{token_block(pack['dark'], cats, 'dark', '    ', pack_key=key)}\n  }}\n}}"
        )
    return "\n".join(out)


EXAM_RANGE = re.compile(r"LECTURES?\s*(\d+)\s*[-\u2013\u2014]\s*(\d+)", re.I)
LECTURE_NO = re.compile(r"#(\d+)\s*$")


# Trailing junk the PDF leaves on an exam's name. Instructors and a room are not
# part of what the exam is called, "Evaluators" is a column header that ran into
# the cell, and a duration is a logistic note. Everything else is left alone --
# "Exam 6 (30%) Cumulative (70%)" stays, because that is what the exam IS, and
# renaming it would be inventing a name.
NAME_NOISE = [
    re.compile(r"(\s+[A-Za-z]\.\s*[A-Z][a-z]+)+\s*(Classroom|Lab|Laboratory|Sim(ulation)?\s*\w*)?\s*$"),
    re.compile(r"\s+Evaluators\s*$", re.I),
    re.compile(r"\s*\(\s*\d+\s*min(ute)?s?\s*\)", re.I),
]
ARTICLES = re.compile(r"\b(the|a|an)\b", re.I)


def tidy_exam_name(label):
    out = label
    for _ in range(3):                     # noise stacks: names, then a room
        for rx in NAME_NOISE:
            out = rx.sub("", out)
    return re.sub(r"\s{2,}", " ", out).strip(" :,-")


# The same idea for a session's SUBJECT line (the topic shown under the class
# name in the week/day views). The PDF's merged cells run an instructor, a room,
# a role note or a second lecture's title straight onto the subject; none of
# that is what the class is on. A subject that survives every rule unchanged
# was already clean.
SUBJ_LEAD = re.compile(r"^\s*(?:(?:MLA|ALA|SDL|CBL|SGL)\s*:\s*|ALL STUDENTS\s*:\s*)+", re.I)
SUBJ_SPLIT = re.compile(r"\s+(?:MLA|ALA)\s*:\s*\S")          # a 2nd lecture ran on
SUBJ_TAIL = [
    re.compile(r"\s*(?:CLINICAL SKILLS|ANATOMY|PHARMACOLOGY|PHYSIOLOGY|"
               r"ELECTROPHYSIOLOGY|TECHNOLOGY & MONITORING)\s*$"),
    re.compile(r"\s*(?:ALL STUDENTS(?: AS ASSIGNED)?|EVALUATORS?|CLASSROOM|LAB|"
               r"LUNCH PROVIDED|SCHEDULE TO FOLLOW|STAFF PROCTOR|"
               r"FACULTY REMOTE GRADED)\s*$", re.I),
    re.compile(r"(\s+(?:Dr\.|[A-Za-z]\.)\s*[A-Z][a-z]+"
               r"(?:\s*/\s*(?:Dr\.|[A-Za-z]\.)\s*[A-Z][a-z]+)*)+\s*$"),
]


def tidy_title(title):
    out = SUBJ_LEAD.sub("", title or "")
    m = SUBJ_SPLIT.search(out)               # keep only the first lecture's topic
    if m:
        out = out[:m.start()]
    for _ in range(4):                       # instructor, then a room, then a role
        for rx in SUBJ_TAIL:
            out = rx.sub("", out)
    out = re.sub(r"\s{2,}", " ", out).strip(" :,-/")
    # A merged cell can leave a practical's name run onto the lecture's -- and it
    # is usually a phrase already spelled out earlier in the line. Drop the
    # trailing copy ("...LMA Placement Oral and Nasal Intubation" -> "...LMA
    # Placement"), longest match first so the whole repeat goes.
    words = out.split()
    for n in range(min(8, len(words) // 2), 2, -1):
        tail = " ".join(words[-n:])
        head = " ".join(words[:-n])
        if tail.lower() in head.lower():
            out = head.rstrip(" :,-/")
            break
    return out or (title or "").strip()


def build_recall_exams(schedule, report):
    """
    The list "Upcoming Tests" reads from: one clean entry per exam Anna sits.

    Every exam gets an `examTitle`; only the ones that state a lecture range get
    a `lectureLabel` as well, and the page puts that in brackets after the name.

    Two things have to be repaired first, and both are reported rather than done
    quietly. The PDF sometimes emits the same practical twice, once bare and once
    with the instructors and room run into the title -- "Airway Assessment" and
    "Airway Assessment j. Moon k. Dewitt Classroom" are one exam, not two, and
    left alone they would give Anna two identical boxes. And a name that survives
    tidying with brackets still in it is one nobody has named properly yet; that
    is Finn's call, not this script's, so it ships as-is and is printed.
    """
    seen, out = {}, []
    for e in schedule.get("exams", []):
        raw = e.get("label") or e.get("title", "")
        m = EXAM_RANGE.search(e.get("title", ""))
        name = tidy_exam_name(
            re.sub(r"\s*[:,]?\s*LECTURES?\s*\d+\s*[-\u2013\u2014]\s*\d+", "", raw, flags=re.I)
            if m else raw
        )
        if not name:
            continue
        key = (e["date"], ARTICLES.sub("", name).lower().replace(" ", ""))
        entry = {"date": e["date"], "examTitle": name}
        if m:
            entry["lectureLabel"] = f"Lectures {m.group(1)}-{m.group(2)}"
        if key in seen:
            # keep whichever name the PDF gave us cleanly, i.e. the shorter one
            if len(name) < len(seen[key]["examTitle"]):
                seen[key].update(entry)
            report("deduped", f"{e['date']} {raw}")
            continue
        seen[key] = entry
        out.append(entry)
        if name != raw.strip():
            report("tidied", f"{e['date']} {raw!r} -> {name!r}")
        if re.search(r"[()]", name):
            report("unnamed", f"{e['date']} {name!r}")
    return sorted(out, key=lambda x: (x["date"], x["examTitle"]))


def attach_exam_dates(schedule, report):
    """
    Tell every qualifying lecture which exam will examine it.

    The schedule states this in the exam titles themselves -- "EXAM 2: LECTURES
    8-14" -- so the mapping is read off the PDF rather than maintained by hand,
    and it re-derives itself whenever the school reissues the schedule. Exams
    with no lecture range (the Clinical Skills practicals, the OSCE stations, the
    Drug Card exam) are correctly skipped: they examine a skill, not a numbered
    run of lectures.

    Lectures no exam claims are left with no date. Only the ones that can reach
    the Anki review line are reported, because that is the only place a missing
    exam date changes what Anna sees -- Clinical Skills is excluded from that
    line (ANKI_SKIP in app_template.html), which is why Block 1 now reports
    nothing where it used to report Clinical Skills ALA #1.
    """
    windows = {}
    for date, day in schedule["days"].items():          # sessions carry no date; the key is it
        for s in day["sessions"]:
            if s.get("kind") != "exam":
                continue
            cat = (s.get("category") or "").upper()
            m = EXAM_RANGE.search(s.get("title", ""))
            if cat and m:
                windows.setdefault(cat, []).append((int(m.group(1)), int(m.group(2)), date))

    schedule["recallExams"] = build_recall_exams(schedule, report)

    orphans = []
    anki_skip = {"CLINICAL SKILLS"}          # keep in step with ANKI_SKIP
    for date in sorted(schedule["days"]):
        for s in schedule["days"][date]["sessions"]:
            if not (s.get("study") and s.get("todoLabel")):
                continue
            m = LECTURE_NO.search(s["todoLabel"])
            cat = (s.get("category") or "").upper()
            hits = ([w[2] for w in windows.get(cat, []) if w[0] <= int(m.group(1)) <= w[1]]
                    if m else [])
            if hits:
                s["examDate"] = min(hits)
            elif cat not in anki_skip:
                orphans.append(f"{date} {s['todoLabel']}")
    return orphans


def apply_overrides(schedule, path):
    """
    Manual corrections layered on top of the parse. A merged Clinical Skills
    practical cell leaves its middle hours blank, so the parser can't see how
    long it runs -- these say so explicitly. See data/overrides.json.

    Two entry shapes:
      - {"at": "HH:MM", "start"?, "end"?}  -- nudge an existing session's
        start/end and leave its name, topic, category and study flags alone.
        This is the light touch for "the parser truncated a lab that actually
        runs to 5 PM".
      - {"clear": "HH:MM-HH:MM", "start", "end", "label", "title"?, ...}  --
        drop the parsed fragments in the window and drop in one clean block.
        `title` defaults to `label` when omitted.
    """
    if not Path(path).exists():
        return 0
    overrides = json.loads(Path(path).read_text(encoding="utf-8"))
    applied = 0
    for date, entries in overrides.items():
        if date.startswith("_"):
            continue
        day = schedule["days"].get(date)
        if day is None:
            print(f"  override warning: {date} is not in the schedule -- skipped")
            continue
        for e in entries:
            if e.get("at"):
                match = next((s for s in day["sessions"] if s.get("start") == e["at"]), None)
                if match is None:
                    print(f"  override warning: {date} has no session starting {e['at']} -- skipped")
                    continue
                if e.get("start"):
                    match["start"] = e["start"]
                if e.get("end"):
                    match["end"] = e["end"]
                day["sessions"].sort(key=lambda s: s.get("start") or "")
                applied += 1
                continue
            if e.get("clear"):
                lo, hi = e["clear"].split("-")
                day["sessions"] = [s for s in day["sessions"]
                                   if not (s.get("start") and lo <= s["start"] < hi)]
            oid = "ov" + hashlib.sha1(
                f"{date}{e['start']}{e['label']}".encode("utf-8")).hexdigest()[:8]
            sess = {
                "id": oid, "start": e["start"], "end": e["end"],
                "category": e.get("category", ""), "seq": None, "code": None,
                "title": e.get("title", e["label"]), "label": e["label"], "instructor": "",
                "kind": e.get("kind", "lab"), "mandatory": False,
                "study": bool(e.get("study", False)), "todoLabel": e.get("todoLabel"),
            }
            # A "strip" session renders as a thin bar over whatever it overlaps
            # in the week view (e.g. a 4 PM Zoom sitting on an all-afternoon lab).
            if e.get("strip"):
                sess["strip"] = True
            day["sessions"].append(sess)
            day["sessions"].sort(key=lambda s: s.get("start") or "")
            applied += 1
    return applied


def add_zoom_strips(schedule):
    """
    The weekly "4:00 PM TACC - Zoom Meeting" is printed in the assignment strip
    at the foot of the page, not as a class, so the parser never makes it a
    session. Turn it into a 4-5 PM dark-green strip on whatever day carries it.
    """
    added = 0
    for date, day in schedule["days"].items():
        text = " ".join(day.get("assignments", []))
        if not re.search(r"zoom\s*meeting", text, re.I):
            continue
        if any(s.get("kind") == "zoom" for s in day["sessions"]):
            continue
        oid = "zm" + hashlib.sha1(date.encode("utf-8")).hexdigest()[:8]
        day["sessions"].append({
            "id": oid, "start": "16:00", "end": "17:00", "category": "ZOOM",
            "seq": None, "code": None, "title": "TACC - Zoom Meeting",
            "label": "TACC - Zoom Meeting", "instructor": "", "kind": "zoom",
            "mandatory": False, "study": False, "todoLabel": None, "strip": True,
        })
        day["sessions"].sort(key=lambda s: s.get("start") or "")
        added += 1
    return added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=str(ROOT / "build" / "index.html"))
    ap.add_argument("--schedule", default=str(ROOT / "data" / "schedule.json"))
    ap.add_argument("--themes", default=str(ROOT / "data" / "themes.json"))
    ap.add_argument("--no-archive", action="store_true")
    args = ap.parse_args()

    schedule = json.loads(Path(args.schedule).read_text(encoding="utf-8"))
    themes = json.loads(Path(args.themes).read_text(encoding="utf-8"))
    html = TEMPLATE.read_text(encoding="utf-8")

    n_ov = apply_overrides(schedule, ROOT / "data" / "overrides.json")
    if n_ov:
        print(f"  applied {n_ov} manual override(s) from data/overrides.json")
    n_zoom = add_zoom_strips(schedule)
    if n_zoom:
        print(f"  added {n_zoom} weekly Zoom strip(s)")

    # Clean the subject line on every session: strip instructors, rooms, role
    # notes and a run-on second lecture that the PDF's merged cells leave on it.
    n_tidy = 0
    for day in schedule["days"].values():
        for s in day["sessions"]:
            if s.get("kind") == "break":
                continue
            clean = tidy_title(s.get("title", ""))
            if clean != (s.get("title") or ""):
                s["title"] = clean
                n_tidy += 1
    if n_tidy:
        print(f"  tidied {n_tidy} session subject line(s)")

    block = schedule["meta"].get("block") or "Block"
    title = f"Anna's Calendar — {block}"
    description = (f"{block} schedule and to-do list, "
                   f"{schedule['meta']['term_start']} to {schedule['meta']['term_end']}.")

    notes = {}
    def report(kind, msg):
        notes.setdefault(kind, []).append(msg)

    orphans = attach_exam_dates(schedule, report)

    # separators=(",",":") keeps the payload tight; the schedule is the bulk of the file
    # The VCOM Carolinas mark, base64'd in like the floral tile so build/index.html
    # stays one self-contained file. White background already knocked out to
    # transparent (assets/vcom-logo.png); replace that file to change the logo.
    logo_uri = "data:image/png;base64," + base64.b64encode(
        (ROOT / "assets" / "vcom-logo.png").read_bytes()).decode("ascii")

    payload = json.dumps(schedule, separators=(",", ":"), ensure_ascii=False)
    themes_payload = json.dumps(
        {k: v for k, v in themes.items() if not k.startswith("_")},
        separators=(",", ":"), ensure_ascii=False)

    for token, value in (
        ("__THEME_CSS__", build_theme_css(themes)),
        ("__DATA__", payload),
        ("__THEMES__", themes_payload),
        ("__TITLE__", title),
        ("__LOGO__", logo_uri),
        ("__HEADING__", "Anna’s Calendar"),
        ("__DESCRIPTION__", description),
    ):
        if token not in html:
            raise SystemExit(f"template is missing {token}")
        html = html.replace(token, value)

    leftovers = re.findall(r"__[A-Z_]+__", html)
    if leftovers:
        raise SystemExit(f"unsubstituted placeholders remain: {sorted(set(leftovers))}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    if not args.no_archive:
        versions = ROOT / "versions"
        versions.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        shutil.copy2(out, versions / f"index_{stamp}.html")

    days = len(schedule["days"])
    sessions = sum(len(d["sessions"]) for d in schedule["days"].values())
    print(f"wrote {out}  ({out.stat().st_size/1024:.0f} KB)")
    HEADINGS = {
        "deduped": "duplicate exam entries collapsed (the PDF listed them twice)",
        "tidied":  "exam names tidied (instructors, rooms, durations stripped)",
        "unnamed": "exam names that still carry brackets — Anna's call what these "
                   "should be called, they ship as printed",
    }
    # "tidied" is deliberately not printed: stripping an instructor's name off a
    # title is not a decision anyone needs to review. The other two are.
    for kind in ("deduped", "unnamed"):
        if notes.get(kind):
            print(f"  {len(notes[kind])} {HEADINGS[kind]}:")
            for msg in notes[kind]:
                print(f"    {msg}")
    if orphans:
        print(f"  {len(orphans)} qualifying lecture(s) no exam claims — they stay in "
              f"Anki review to the end of the block:")
        for o in orphans:
            print(f"    {o}")
    print(f"  {days} days, {sessions} sessions, {len(schedule['exams'])} exams, "
          f"{len(themes['order'])} themes")


if __name__ == "__main__":
    main()
