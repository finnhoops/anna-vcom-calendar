#!/usr/bin/env python3
"""
Parse a VCOM block-schedule PDF into data/schedule.json.

The PDF is a week-per-page grid. Text must be read by coordinate, never by
reading order -- PyMuPDF returns spans in storage order, which interleaves days
and times arbitrarily (page 2 starts with Friday). Every span is assigned to a
(day column, hour row) cell using its bounding box.

Grid anatomy, verified against the Block 1 PDF:
  - Day columns are headed by a bold span like "Monday, September 7, 2026",
    each at its own x-offset. Those x-offsets define the column boundaries.
  - The label column (x < ~130) repeats Class / Subject / Instructor once per
    hour block. The "Class" labels are the row delimiters.
  - Hour labels ("8:00 AM") sit in the same label column and name each row.

Usage:  parse_schedule.py <pdf> [-o data/schedule.json] [--report]
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

import fitz  # PyMuPDF

# --- grid geometry ---------------------------------------------------------
LABEL_COL_MAX_X = 130.0   # spans left of this are row labels / hour labels
HEADER_MAX_Y = 64.0       # date headers live above this; the 8AM Class row starts ~66
BAND_PAD = 4.0            # tolerance when splitting a row into its three bands

DATE_RE = re.compile(
    r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+"
    r"([A-Z][a-z]+)\s+(\d{1,2}),\s+(\d{4})$"
)
TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})\s*(AM|PM)$", re.I)
WEEK_RE = re.compile(r"WEEK\s*(\d+)", re.I)
# "1. ALA: Axial Skeleton" / "5 ALA: Cranial Nerves II" / "6.ALA: Drug Calc"
SEQ_RE = re.compile(r"^\s*(\d{1,2})\s*[.)]?\s*(?=[A-Za-z])")
CODE_RE = re.compile(r"^\s*([A-Z]{2,4})\s*:\s*")
MANDATORY_RE = re.compile(r"\*{0,2}\s*MANDATORY\s*\*{0,2}", re.I)

WEEKEND_NOTE_RE = re.compile(r"^(Saturday|Sunday)\s*:\s*(.+)$", re.I)
ITEMS_HEADER_RE = re.compile(r"important items to complete", re.I)
EVENT_HEADER_RE = re.compile(r"^(WELCOME EVENT|EVENT)\s*:?\s*$", re.I)
# The foot of each page carries a key: "ALA: Asynchronous Learning Activity".
LEGEND_RE = re.compile(r"^([A-Z]{2,4})\s*:\s*([A-Z][a-z]+(?:\s+[A-Za-z]+){1,4})$")
STRIP_MARKER_RE = re.compile(r"^(Saturday|Sunday|Next Week Exams?)\s*:?\s*$", re.I)

EXAM_WORDS = re.compile(r"\b(EXAM|FINAL|ASSESSMENT|QUIZ|PRACTICAL|MIDTERM)\b", re.I)
BREAK_WORDS = re.compile(r"^\s*(LUNCH|BREAK|TBD|TBA|N/?A|-+)\s*$", re.I)

LEGEND = {}
UNLABELLED = {}

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}


def norm(text):
    """Collapse whitespace; PDF spans carry stray newlines and doubled spaces."""
    text = re.sub(r"\s+", " ", text.replace(" ", " ")).strip()
    return re.sub(r"\*+\s*(.*?)\s*\*+", r"\1", text).strip()


def spans_of(page):
    """Every non-empty text span on the page, with position and style."""
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                text = norm(span["text"])
                if text:
                    out.append({
                        "text": text,
                        "x0": span["bbox"][0], "x1": span["bbox"][2],
                        "y0": span["bbox"][1], "y1": span["bbox"][3],
                        "size": span["size"],
                        "bold": bool(span["flags"] & 16),
                    })
    return out


def parse_date(text):
    m = DATE_RE.match(text)
    if not m:
        return None
    _, month, day, year = m.groups()
    if month not in MONTHS:
        return None
    try:
        return date(int(year), MONTHS[month], int(day))
    except ValueError:
        return None


def parse_time(text):
    m = TIME_RE.match(text)
    if not m:
        return None
    hour, minute, meridiem = int(m.group(1)), int(m.group(2)), m.group(3).upper()
    if meridiem == "PM" and hour != 12:
        hour += 12
    if meridiem == "AM" and hour == 12:
        hour = 0
    return hour * 60 + minute


def hhmm(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def build_columns(spans, page_width):
    """Day columns, from the date headers. Returns [(date, x_lo, x_hi), ...]."""
    headers = []
    for s in spans:
        if s["y0"] < HEADER_MAX_Y:
            d = parse_date(s["text"])
            if d:
                headers.append((d, s["x0"], s["x1"]))
    headers.sort(key=lambda h: h[1])
    if not headers:
        return []

    columns = []
    for i, (d, x0, x1) in enumerate(headers):
        lo = x0 - 8 if i == 0 else (headers[i - 1][2] + x0) / 2
        hi = page_width if i == len(headers) - 1 else (x1 + headers[i + 1][1]) / 2
        columns.append((d, max(lo, LABEL_COL_MAX_X), hi))
    return columns


def build_rows(spans, page_height):
    """
    Hour rows, delimited by the hour labels in the left column. The Class /
    Subject / Instructor labels are NOT usable as anchors -- they go missing
    wherever the source merges cells, which silently shifts every band below.
    Hour labels are present and evenly pitched on every page.
    """
    times = sorted(
        ((parse_time(s["text"]), s["y0"]) for s in spans
         if s["x0"] < LABEL_COL_MAX_X and parse_time(s["text"]) is not None),
        key=lambda t: t[1]
    )
    if not times:
        return []

    pitch = ((times[-1][1] - times[0][1]) / (len(times) - 1)) if len(times) > 1 else 42.0
    # Rows must TILE. Deriving each row's top independently of the row above it
    # leaves gaps of a couple of points between them, and any span landing in a
    # gap is dropped -- that is where merged-cell exam titles go missing.
    edges = [times[0][1] - pitch / 2]
    edges += [(times[i][1] + times[i + 1][1]) / 2 for i in range(len(times) - 1)]
    # The last row must NOT run to the foot of the page: below it sits the
    # study-assignment strip, which is not a class hour.
    edges.append(times[-1][1] + pitch / 2)

    rows = []
    for i, (minute, _) in enumerate(times):
        end = times[i + 1][0] if i + 1 < len(times) else minute + 60
        rows.append({"top": edges[i], "bottom": edges[i + 1], "start": minute, "end": end})
    rows[0]["top"] = min(rows[0]["top"], HEADER_MAX_Y)
    return rows


def parse_assignment_strip(spans, columns, strip_top):
    """
    Below the last class hour the PDF carries a per-day study-assignment strip
    ("Drug Card", "Anatomy 1 & 2"). Weekend work appears there too, but laid out
    wherever it fits rather than under Saturday and Sunday -- so a "Saturday:" /
    "Sunday:" marker claims the spans to its right on the same baseline.
    """
    per_day, weekend, legend, upcoming = {}, {}, {}, []
    strip = [s for s in spans if s["y0"] >= strip_top and s["x0"] >= LABEL_COL_MAX_X]
    by_line = {}
    for s in strip:
        by_line.setdefault(round(s["y0"] / 3), []).append(s)

    for _, line_spans in sorted(by_line.items()):
        claimed = None
        for s in sorted(line_spans, key=lambda s: s["x0"]):
            key = LEGEND_RE.match(s["text"])
            if key:
                legend[key.group(1)] = key.group(2)
                continue
            marker = STRIP_MARKER_RE.match(s["text"])
            if marker:
                claimed = marker.group(1).capitalize()
                continue
            inline = WEEKEND_NOTE_RE.match(s["text"])
            if inline:
                weekend.setdefault(inline.group(1).capitalize(), []).append(norm(inline.group(2)))
                continue
            # A faculty name sitting low on the page is not study work.
            if is_instructor(s["text"]):
                continue
            if claimed in ("Saturday", "Sunday"):
                weekend.setdefault(claimed, []).append(s["text"])
                continue
            if claimed:
                upcoming.append(s["text"])
                continue
            cx = (s["x0"] + s["x1"]) / 2
            col = next((c for c in columns if c[1] <= cx < c[2]), None)
            if col:
                per_day.setdefault(col[0], []).append(s["text"])
    return per_day, weekend, legend, upcoming


INSTRUCTOR_RE = re.compile(
    r"^(?:Dr\.|Mr\.|Ms\.|Mrs\.|Prof\.)?\s*"
    r"(?:[A-Z]\.\s*)*[A-Z][A-Za-z'\-]+"
    r"(?:\s*[/&,]\s*(?:Dr\.|Mr\.|Ms\.|Mrs\.)?\s*(?:[A-Z]\.\s*)*[A-Z][A-Za-z'\-]+)*$"
)


def is_instructor(text):
    """
    Faculty names sit on the last line of a cell: 'S. Childress', 'Dr. Cannon'.
    A bare capitalised word is NOT a name -- it is a wrapped subject line
    ('Setting', 'Theraputics'), which is why an initial or title is required.
    """
    if len(text) > 60 or len(text.split()) > 8:
        return False
    if not re.search(r"[a-z]", text):        # ALL CAPS is a category, not a name
        return False
    if not re.search(r"(?:\b[A-Z]\.|\b(?:Dr|Mr|Ms|Mrs|Prof)\b\.?)", text):
        return False
    return bool(INSTRUCTOR_RE.match(text))


SUBJECT_START_RE = re.compile(
    r"^(EXAM|FINAL|OSCE|LECTURES?|ASSESSMENT|EXAMINATION|ACLS|PALS|COMPREHENSIVE|"
    r"CUMULATIVE|MLA|ALA|SPECIAL|STANDARDIZED|NO CLASSES|ALL STUDENTS)\b")


def starts_subject(text):
    """
    Tells a wrapped category line ('MONITORING', continuing 'TECHNOLOGY &')
    apart from an all-caps subject line ('EXAM 2:', 'LECTURES 6-11') that
    happens to sit under a category. Digits and colons mark the latter.
    """
    return bool(SUBJECT_START_RE.match(text) or re.search(r"[\d:#]", text))


def is_category(text):
    """Class-row values are set in caps: ANATOMY, TECHNOLOGY & MONITORING."""
    return bool(re.search(r"[A-Z]", text)) and text == text.upper()


def group_lines(spans):
    """
    Merge spans that share a baseline into single lines, top to bottom. Spans
    that butt up against each other are one word the PDF happened to split
    ("Checklis" + "t"), so they join without a space.
    """
    lines = []
    for s in sorted(spans, key=lambda s: (round(s["y0"], 1), s["x0"])):
        if lines and abs(s["y0"] - lines[-1]["y0"]) <= 2.5:
            gap = s["x0"] - lines[-1]["x1"]
            lines[-1]["parts"].append(("" if gap < 1.0 else " ") + s["text"])
            lines[-1]["x1"] = s["x1"]
        else:
            lines.append({"y0": s["y0"], "x1": s["x1"], "parts": [s["text"]]})
    return [{"y0": ln["y0"], "text": norm("".join(ln["parts"]))} for ln in lines]


def split_bands(spans):
    """
    Assign a cell's lines to class / subject / instructor by content, not by
    position: leading all-caps lines are the class, trailing name-shaped lines
    are the instructor, and whatever remains is the subject.
    """
    lines = [ln for ln in group_lines(spans) if ln["text"]]
    if not lines:
        return "", "", ""

    head = 0
    while head < len(lines) and is_category(lines[head]["text"]):
        if head and starts_subject(lines[head]["text"]):
            break
        head += 1
    tail = len(lines)
    while tail > head and is_instructor(lines[tail - 1]["text"]):
        tail -= 1

    category = norm(" ".join(ln["text"] for ln in lines[:head]))
    subject = norm(" ".join(ln["text"] for ln in lines[head:tail]))
    instructor = norm(" ".join(ln["text"] for ln in lines[tail:]))

    # A cell that is nothing but caps is a category with no separate subject.
    if not subject and not instructor and head == len(lines):
        return category, "", ""
    return category, subject, instructor


def clean_title(text):
    """Strip the leading sequence number and the ALA:/MLA: activity code."""
    seq = None
    m = SEQ_RE.match(text)
    if m:
        seq = int(m.group(1))
        text = text[m.end():]
    code = None
    m = CODE_RE.match(text)
    if m:
        code = m.group(1)
        text = text[m.end():]
    return seq, code, norm(text)


def classify(category, title):
    blob = f"{category} {title}"
    if EXAM_WORDS.search(blob):
        return "exam"
    if BREAK_WORDS.match(title) or BREAK_WORDS.match(category):
        return "break"
    if re.search(r"\bLAB\b|SIMULATION|SKILLS", blob, re.I):
        return "lab"
    if re.search(r"ORIENTATION|WELCOME|ADVISOR|SIGNUP|PHOTOGRAPH", blob, re.I):
        return "admin"
    return "lecture"


# --- display labels --------------------------------------------------------
# How a session is named on the calendar. Anna's rules, verbatim:
#   * Orientation / Professionalism / Zoom meetings / Special events -> bare name
#   * Clinical Skills -> "Clinical Skills" + ALA | MLA | OSCE
#   * Numbered courses -> "<Course> #<lecture number>"
#   * Exam days       -> "<Course> Exam <n>: Lectures <range>"
#   * Gross Anatomy Lab Experience -> "Anatomy Lab"
NUMBERED_COURSES = {
    "ANATOMY": "Anatomy",
    "PHARMACOLOGY": "Pharmacology",
    "TECHNOLOGY & MONITORING": "Technology & Monitoring",
    "PHYSIOLOGY": "Physiology",
    "ELECTROPHYSIOLOGY": "Electrophysiology",
    "CLINICAL SKILLS": "Clinical Skills",
}
BARE_NAME_COURSES = {
    "ORIENTATION": "Orientation",
    "PROFESSIONALISM": "Professionalism",
    "SPECIAL EVENT": "Special Event",
    "WELCOME EVENT": "Special Event",
}
PLAIN_LABELS = {
    "LUNCH": "Lunch", "LUNCH PROVIDED": "Lunch", "BREAK": "Break",
    "NO CLASSES": "No Classes", "LABOR DAY": "Labor Day",
    "THANKSGIVING HOLIDAY": "Thanksgiving Holiday",
    "CHRISTMAS HOLIDAY BREAK": "Christmas Break",
    "CLASSROOM": "Clinical Skills in Classroom",
}
EXAM_LABEL_RE = re.compile(
    r"(FINAL\s+EXAM|EXAM|EXAMINATION)\s*\(?(\d+)\)?\s*:?\s*(.*)", re.I)
ZOOM_RE = re.compile(r"zoom", re.I)
GROSS_LAB_RE = re.compile(r"GROSS ANATOMY LAB|ANATOMY LAB EXPERIENCE|LAB EXPERIENCE", re.I)


def title_case(text):
    """Turn the PDF's shouting into sentence-ish case, keeping acronyms."""
    keep = {"OSCE", "ACLS", "PALS", "ALA", "MLA", "CBL", "SDL", "SGL", "IV",
            "ECG", "TEE", "CNS", "CSF", "SOAP", "MHSA", "VCOM", "TACC", "&"}
    out = []
    for word in text.split():
        bare = word.strip("():,.#")
        if bare.upper() in keep or (bare.isupper() and any(ch.isdigit() for ch in bare)):
            out.append(word)
        elif word.isupper():
            out.append(word.capitalize() if len(word) > 2 else word.lower())
        else:
            out.append(word)
    return norm(" ".join(out))


# Courses that enter Anna's study workflow (preview -> mark -> Anki). Deliberately
# excludes Orientation, Professionalism, Zoom meetings, Special events, and the
# Clinical Skills MLA and OSCE sessions -- those are not lectures she preps for.
STUDY_CATEGORIES = {"ANATOMY", "PHARMACOLOGY", "TECHNOLOGY & MONITORING",
                    "PHYSIOLOGY", "ELECTROPHYSIOLOGY", "CLINICAL SKILLS"}


def study_info(session, label):
    """
    (qualifies, name used in the to-do list). The to-do list spells Clinical
    Skills ALA out in full so it cannot be confused with the MLA and OSCE
    sessions sitting next to it on the same day.
    """
    category = (session["category"] or "").upper().strip()
    if session["kind"] in ("exam", "break"):
        return False, None
    if category not in STUDY_CATEGORIES or session["seq"] is None:
        return False, None
    if category == "CLINICAL SKILLS":
        blob = f"{category} {session['title']}".upper()
        if session.get("code") != "ALA" or "OSCE" in blob:
            return False, None
        return True, f"Clinical Skills ALA #{session['seq']}"
    return True, label


def label_session(session):
    """The name shown on the calendar. Returns (label, matched_a_rule)."""
    category = (session["category"] or "").upper().strip()
    title = session["title"] or ""
    blob = f"{category} {title}"
    course = NUMBERED_COURSES.get(category)

    if GROSS_LAB_RE.search(blob) or GROSS_LAB_RE.search(session.get("location") or ""):
        return "Anatomy Lab", True
    if ZOOM_RE.search(blob):
        return "Zoom Meeting", True
    if category in PLAIN_LABELS:
        return PLAIN_LABELS[category], True
    if category in BARE_NAME_COURSES:
        return BARE_NAME_COURSES[category], True

    if session["kind"] == "exam":
        m = EXAM_LABEL_RE.search(title) or EXAM_LABEL_RE.search(category)
        stem = course or title_case(category) if course or category else ""
        if m:
            kind = "Final Exam" if m.group(1).upper().startswith("FINAL") else "Exam"
            rest = title_case(m.group(3)).strip(" :")
            label = f"{stem} {kind} {m.group(2)}".strip()
            return (f"{label}: {rest}" if rest else label), True
        return norm(f"{stem} {title_case(title)}"), bool(stem)

    if category == "CLINICAL SKILLS":
        # OSCE and MLA are named by activity type; ALA sessions are numbered
        # lectures like the other courses.
        if re.search(r"OSCE", blob):
            return "Clinical Skills OSCE", True
        if session.get("code") == "MLA":
            return "Clinical Skills MLA", True
        if session["seq"] is not None:
            return f"Clinical Skills #{session['seq']}", True
        return "Clinical Skills", True

    if course:
        if session["seq"] is not None:
            return f"{course} #{session['seq']}", True
        return course, True

    return title_case(title or category), False


def session_id(category, seq, title, instructor):
    """
    Content hash, deliberately excluding date and time: when the school moves a
    lecture, its id stays put so any manual edit stays attached to it.
    """
    key = "|".join([category.upper(), str(seq or ""), title.upper(), instructor.upper()])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]


def parse_page(page, page_no, report):
    spans = spans_of(page)
    columns = build_columns(spans, page.rect.width)
    rows = build_rows(spans, page.rect.height)

    week = None
    for s in spans:
        m = WEEK_RE.search(s["text"])
        if m:
            week = int(m.group(1))
            break

    if not columns:
        report.append(f"page {page_no}: no date headers found -- page skipped")
        return {}, week
    if len(columns) != 5:
        report.append(f"page {page_no}: found {len(columns)} day columns, expected 5")

    def blank_day():
        return {"week": week, "sessions": [], "notes": [], "items": [], "assignments": []}

    days = {col[0]: blank_day() for col in columns}

    # Saturday and Sunday get no column of their own; derive them from Monday.
    monday = min(days)
    for offset, name in ((5, "Saturday"), (6, "Sunday")):
        days.setdefault(monday + timedelta(days=offset), blank_day())

    strip_top = rows[-1]["bottom"] if rows else page.rect.height
    per_day_work, weekend_work, legend, upcoming = parse_assignment_strip(
        spans, columns, strip_top)
    LEGEND.update(legend)
    if upcoming:
        days[max(c[0] for c in columns)]["notes"].append(
            "Next week's exams: " + "; ".join(upcoming))
    for day, texts in per_day_work.items():
        days.setdefault(day, blank_day())["assignments"].extend(texts)
    for name, texts in weekend_work.items():
        target = monday + timedelta(days=5 if name == "Saturday" else 6)
        days.setdefault(target, blank_day())["assignments"].extend(texts)

    # Bucket every content span into its (column, row) cell.
    cells = {}
    loose = []
    for s in spans:
        if s["x0"] < LABEL_COL_MAX_X or s["y0"] < HEADER_MAX_Y:
            continue
        if parse_date(s["text"]) or s["y0"] >= strip_top:
            continue
        cx = (s["x0"] + s["x1"]) / 2
        col = next((c for c in columns if c[1] <= cx < c[2]), None)
        row_idx = next((i for i, r in enumerate(rows)
                        if r["top"] <= s["y0"] < r["bottom"]), None)
        if col is None or row_idx is None:
            loose.append(s)
            continue
        cells.setdefault((col[0], row_idx), []).append(s)

    for (day, row_idx), cell_spans in sorted(cells.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        row = rows[row_idx]
        category, subject, instructor = split_bands(cell_spans)

        if not (category or subject):
            continue

        # Weekend work and standalone checklists ride along inside day cells.
        note = WEEKEND_NOTE_RE.match(subject) or WEEKEND_NOTE_RE.match(category)
        if note:
            days[day]["notes"].append(norm(note.group(0)))
            continue
        if ITEMS_HEADER_RE.search(subject) or ITEMS_HEADER_RE.search(category):
            body = ITEMS_HEADER_RE.sub("", f"{category} {subject}").strip(" :")
            if norm(body):
                days[day]["items"].append(norm(body))
            continue

        mandatory = bool(MANDATORY_RE.search(category) or MANDATORY_RE.search(subject))
        category = norm(MANDATORY_RE.sub("", category))
        subject = norm(MANDATORY_RE.sub("", subject))
        if not (category or subject):
            days[day]["notes"].append("MANDATORY")
            continue

        seq, code, title = clean_title(subject or category)
        if not title:
            title = category
        start = row["start"]
        days[day]["sessions"].append({
            "id": session_id(category, seq, title, instructor),
            "start": hhmm(start) if start is not None else None,
            "end": hhmm(row.get("end")) if row.get("end") is not None else None,
            "category": category,
            "seq": seq,
            "code": code,
            "title": title,
            "instructor": instructor,
            "kind": classify(category, title),
            "mandatory": mandatory,
            "_placeholder": not subject,
        })

    # Free-floating text (event banners, checklist bodies) attaches to its column.
    for s in loose:
        cx = (s["x0"] + s["x1"]) / 2
        col = next((c for c in columns if c[1] <= cx < c[2]), None)
        if col is None:
            continue
        text = s["text"]
        if EVENT_HEADER_RE.match(text) or WEEK_RE.search(text):
            continue
        days[col[0]]["items"].append(text)

    return days, week


LOCATION_RE = re.compile(r"^(CLASSROOM|SIM(?:ULATION)?\s+(?:LAB|CENTER)|[A-Z &]*\bLAB\b[A-Z &]*)$")


def is_real_category(text):
    """A category that names a course, as opposed to a fragment of a subject."""
    return bool(text) and text != "SCHEDULE" and not LOCATION_RE.match(text) \
        and not starts_subject(text)


def opens_own_cell(session, previous):
    """
    True when this hour row begins a new cell rather than continuing the one
    above it. A merged multi-hour cell hands its category to the first row and
    its subject to another, and a wrapped subject spills its tail downward.
    """
    if previous is not None and re.search(r"[&,:]$|\b(?:and|or|the|of|in|for|with|to)$",
                                          previous["title"], re.I):
        return False
    if session["_placeholder"]:
        return False
    return is_real_category(session["category"])


def merge_multi_hour(sessions):
    """
    Stitch the rows of one merged cell back into a single session. Breaks end a
    run so LUNCH is never absorbed, and a gap in the clock does too.
    """
    if not sessions:
        return sessions

    runs, current = [], []
    for s in sessions:
        if s["kind"] == "break":
            if current:
                runs.append(current)
            runs.append([s])
            current = []
            continue
        contiguous = bool(current) and current[-1]["end"] == s["start"]
        if contiguous and not opens_own_cell(s, current[-1]):
            current.append(s)
        else:
            if current:
                runs.append(current)
            current = [s]
    if current:
        runs.append(current)

    merged = []
    for run in runs:
        if len(run) == 1:
            merged.extend(run)
            continue

        category = next((s["category"] for s in run if is_real_category(s["category"])),
                        run[0]["category"])
        location = next((s["category"] for s in run if LOCATION_RE.match(s["category"])), None)

        parts = []
        for s in run:
            title, own = s["title"], s["category"]
            if own == category or LOCATION_RE.match(own or ""):
                part = "" if s["_placeholder"] else title
            elif s["_placeholder"] or title == own:
                part = own
            else:
                part = f"{own} {title}".strip() if own else title
            part = norm(part)
            if part and part not in parts:
                parts.append(part)

        head = dict(next((s for s in run if not s["_placeholder"]), run[0]))
        head["category"] = category
        head["title"] = norm(" ".join(parts)) or category
        head["start"] = run[0]["start"]
        head["end"] = run[-1]["end"]
        head["instructor"] = next((s["instructor"] for s in run if s["instructor"]), "")
        head["seq"] = next((s["seq"] for s in run if s["seq"] is not None), None)
        head["code"] = next((s["code"] for s in run if s["code"]), None)
        if location:
            head["location"] = location
        head["kind"] = classify(category, head["title"])
        head["id"] = session_id(category, head["seq"], head["title"], head["instructor"])
        merged.append(head)
    return merged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("-o", "--out", default="data/schedule.json")
    ap.add_argument("--block", default=None, help="block label, e.g. 'Block 1'")
    ap.add_argument("--report", action="store_true", help="print the parse report only")
    args = ap.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        sys.exit(f"no such PDF: {pdf_path}")

    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    doc = fitz.open(pdf_path)
    report = []
    all_days = {}
    weeks_seen = []

    for i, page in enumerate(doc, start=1):
        days, week = parse_page(page, i, report)
        weeks_seen.append(week)
        weekday_count = 0
        for day, payload in days.items():
            key = day.isoformat()
            if key in all_days:
                report.append(f"page {i}: duplicate date {key} -- merging")
                all_days[key]["sessions"].extend(payload["sessions"])
                all_days[key]["notes"].extend(payload["notes"])
                all_days[key]["items"].extend(payload["items"])
            else:
                payload["weekday"] = day.strftime("%A")
                all_days[key] = payload
            if day.weekday() < 5:
                weekday_count += 1
        if weekday_count != 5:
            report.append(f"page {i}: yielded {weekday_count} days, expected 5")

    # Sequence weeks by date order, not by the PDF's own labels -- Block 1 has
    # two pages both labelled "WEEK 19".
    ordered = sorted(all_days)
    first_monday = date.fromisoformat(ordered[0]) if ordered else None
    for idx, key in enumerate(ordered):
        if first_monday:
            all_days[key]["week"] = (date.fromisoformat(key) - first_monday).days // 7 + 1
        day = all_days[key]
        day["sessions"].sort(key=lambda s: (s["start"] or "99:99", s["title"]))
        day["sessions"] = merge_multi_hour(day["sessions"])
        for s in day["sessions"]:
            s.pop("_placeholder", None)
        for s in day["sessions"]:
            s["label"], matched = label_session(s)
            s["study"], todo = study_info(s, s["label"])
            s["todoLabel"] = todo
            if not matched:
                UNLABELLED.setdefault(s["label"], []).append(key)
        day["notes"] = sorted(set(day["notes"]))
        day["items"] = sorted(set(day["items"]))
        day["assignments"] = sorted(set(day.get("assignments", [])))

    taught = [k for k in ordered if all_days[k]["sessions"]]
    exams = [
        {"date": key, "title": s["title"], "label": s["label"],
         "category": s["category"], "start": s["start"]}
        for key in ordered
        for s in all_days[key]["sessions"] if s["kind"] == "exam"
    ]
    categories = sorted({s["category"] for d in all_days.values() for s in d["sessions"]})

    block = args.block or re.sub(r"[_\s]+", " ", pdf_path.stem.split("Learning")[0]).strip() or "Block"
    schedule = {
        "meta": {
            "source_pdf": pdf_path.name,
            "source_sha256": digest,
            "parsed_at": datetime.now().isoformat(timespec="seconds"),
            "block": block,
            "term_start": (taught[0] if taught else (ordered[0] if ordered else None)),
            "grid_start": ordered[0] if ordered else None,
            "term_end": (taught[-1] if taught else (ordered[-1] if ordered else None)),
            "weeks": max((all_days[k]["week"] for k in ordered), default=0),
            "pages": doc.page_count,
        },
        "legend": dict(sorted(LEGEND.items())),
        "categories": categories,
        "exams": exams,
        "days": {k: all_days[k] for k in ordered},
    }

    session_total = sum(len(d["sessions"]) for d in all_days.values())
    report.insert(0, f"pages: {doc.page_count}")
    report.insert(1, f"days: {len(ordered)}  sessions: {session_total}  exams: {len(exams)}")
    report.insert(2, f"term: {schedule['meta']['term_start']} -> {schedule['meta']['term_end']}")
    report.insert(3, f"categories: {', '.join(categories)}")
    empty = [k for k in ordered
             if date.fromisoformat(k).weekday() < 5
             and not all_days[k]["sessions"] and not all_days[k]["notes"]]
    if empty:
        report.append(f"weekdays with no scheduled classes ({len(empty)}) "
                      f"-- verify against the PDF: {', '.join(empty)}")

    if UNLABELLED:
        report.append(f"sessions with no naming rule ({len(UNLABELLED)} distinct) "
                      f"-- Anna should name these:")
        for name, dates in sorted(UNLABELLED.items(), key=lambda kv: -len(kv[1])):
            report.append(f"    {name!r}  x{len(dates)}  first {dates[0]}")

    if args.report:
        print("\n".join(report))
        return

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(schedule, indent=2), encoding="utf-8")
    print("\n".join(report))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
