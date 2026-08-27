#!/usr/bin/env python3
"""
Decide whether a freshly parsed schedule is trustworthy enough to publish.

The parser reads the PDF by coordinate. When the school reformats the document
-- shifts a column, merges a cell, changes the header row -- the parser does not
crash. It quietly produces a schedule with days missing or classes dropped, and
that is far worse than an error, because the calendar looks fine.

This gate is what catches that. It runs on numbers, not judgement, so it works
without anyone expert reading the output. Any failure stops the publish.

Usage:
    sanity_gate.py --schedule data/schedule.json
                   [--prev data/.schedule_prev.json]
                   [--parse-log /tmp/parse.txt]

Exit 0 = safe to publish. Exit 1 = stop, something is wrong.
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

WEEKEND = {"Saturday", "Sunday"}

MAX_EMPTY_WEEKDAYS = 8
MIN_EXAMS = 10
MAX_SESSION_DRIFT = 0.25          # vs the previous build
MIN_TERM_WEEKS = 6
MAX_TERM_WEEKS = 30

failures = []
warnings = []


def check(ok, label, detail_ok="", detail_bad=""):
    if ok:
        print(f"  PASS  {label}{('  — ' + detail_ok) if detail_ok else ''}")
    else:
        print(f"  FAIL  {label}{('  — ' + detail_bad) if detail_bad else ''}")
        failures.append(f"{label}: {detail_bad}")
    return ok


def parse_date(v):
    try:
        return datetime.strptime(v, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schedule", default="data/schedule.json")
    ap.add_argument("--prev", default=None)
    ap.add_argument("--parse-log", default=None)
    args = ap.parse_args()

    sched_path = Path(args.schedule)
    if not sched_path.exists():
        sys.exit(f"STOP: {sched_path} does not exist — the parser did not finish.")

    sched = json.loads(sched_path.read_text(encoding="utf-8"))
    meta = sched.get("meta", {})
    days = sched.get("days", {})
    exams = sched.get("exams", [])

    print("Safety checks")
    print("-------------")

    # 1 — the parser's own complaints ---------------------------------------
    if args.parse_log and Path(args.parse_log).exists():
        log = Path(args.parse_log).read_text(encoding="utf-8", errors="replace")
        bad_lines = [ln.strip() for ln in log.splitlines()
                     if "expected 5" in ln or "no date headers found" in ln]
        check(not bad_lines,
              "Every page of the PDF gave up a full week",
              "no pages came out short",
              f"{len(bad_lines)} page(s) parsed wrong — "
              f"first: {bad_lines[0] if bad_lines else ''}")
    else:
        warnings.append("parser output was not captured, so page-level warnings "
                        "could not be checked")

    # 2 — days present -------------------------------------------------------
    check(len(days) > 0, "The schedule has days in it",
          f"{len(days)} days", "the schedule is empty")

    weekdays = [d for d, v in days.items() if v.get("weekday") not in WEEKEND]
    empty = [d for d in weekdays if not days[d].get("sessions")]
    check(len(empty) <= MAX_EMPTY_WEEKDAYS,
          f"Blank weekdays stayed at or below {MAX_EMPTY_WEEKDAYS}",
          f"{len(empty)} blank",
          f"{len(empty)} weekdays came out with no classes at all — "
          f"that usually means the parser lost them, not that they are days off")
    if empty:
        print(f"        blank weekdays: {', '.join(sorted(empty))}")
        print("        (check a couple against the PDF — genuine days off are fine)")

    # 3 — sessions -----------------------------------------------------------
    total = sum(len(v.get("sessions", [])) for v in days.values())
    check(total > 0, "Classes were found", f"{total} sessions",
          "no classes at all were read out of the PDF")

    # 4 — exams --------------------------------------------------------------
    check(len(exams) >= MIN_EXAMS,
          f"At least {MIN_EXAMS} exams were found",
          f"{len(exams)} exams",
          f"only {len(exams)} exams found — exam titles live in merged cells and "
          f"are the first thing lost when the layout shifts")

    # 5 — term dates ---------------------------------------------------------
    ts, te = parse_date(meta.get("term_start")), parse_date(meta.get("term_end"))
    if check(ts is not None and te is not None,
             "Block start and end dates are real dates",
             f"{meta.get('term_start')} to {meta.get('term_end')}",
             f"got start={meta.get('term_start')!r} end={meta.get('term_end')!r}"):
        span_weeks = (te - ts).days / 7
        check(te > ts, "The block ends after it starts",
              "", f"start {ts} is not before end {te}")
        check(MIN_TERM_WEEKS <= span_weeks <= MAX_TERM_WEEKS,
              f"Block length is believable ({MIN_TERM_WEEKS}-{MAX_TERM_WEEKS} weeks)",
              f"{span_weeks:.0f} weeks",
              f"the block came out {span_weeks:.0f} weeks long")
        if not (date(2025, 1, 1) <= ts <= date(2032, 12, 31)):
            warnings.append(f"block starts {ts}, which is an odd year — worth a look")

    # 6 — drift against the previous build -----------------------------------
    if args.prev and Path(args.prev).exists():
        prev = json.loads(Path(args.prev).read_text(encoding="utf-8"))
        prev_total = sum(len(v.get("sessions", [])) for v in prev.get("days", {}).values())
        if prev_total:
            drift = abs(total - prev_total) / prev_total
            check(drift <= MAX_SESSION_DRIFT,
                  f"Class count is close to last time (within {int(MAX_SESSION_DRIFT*100)}%)",
                  f"{prev_total} → {total}",
                  f"{prev_total} → {total}, a {drift*100:.0f}% change — too big to be "
                  f"an ordinary reshuffle, the parser probably misread the new layout")
    else:
        warnings.append("no previous schedule to compare against, so the "
                        "class-count check was skipped (normal on a first run)")

    # ------------------------------------------------------------------------
    print()
    for w in warnings:
        print(f"  note: {w}")
    if warnings:
        print()

    if failures:
        print("STOPPED. Nothing was published.")
        print()
        print("What went wrong:")
        for f in failures:
            print(f"  - {f}")
        print()
        print("Your existing calendar is untouched and still live. This almost")
        print("always means the school changed the PDF's layout and the parser")
        print("needs a fix — send the PDF to Finn rather than trying to force it.")
        return 1

    print("All checks passed — safe to publish.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
