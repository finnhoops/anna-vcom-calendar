#!/usr/bin/env python3
"""
Compare two schedule.json files and describe what the school changed.

Sessions are keyed by content hash, so a lecture that moves day or time keeps
its id and shows up as MOVED. A renamed lecture gets a new id, so it shows up as
a REMOVED/ADDED pair -- and that matters, because any edit Anna made to the old
one is now orphaned. Those are called out explicitly rather than dropped.

Usage:  diff_schedule.py <old.json> <new.json>
"""

import json
import sys
from pathlib import Path


def index(schedule):
    out = {}
    for date, day in schedule["days"].items():
        for s in day["sessions"]:
            out[s["id"]] = dict(s, date=date)
    return out


def describe(s):
    when = f"{s['date']} {s['start'] or '--:--'}"
    return f"{when}  {s.get('label') or s['title']}"


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__.strip())
    old_path, new_path = Path(sys.argv[1]), Path(sys.argv[2])
    if not old_path.exists():
        print("no previous schedule to compare against -- treating everything as new")
        return

    old, new = json.loads(old_path.read_text()), json.loads(new_path.read_text())
    a, b = index(old), index(new)

    added = [b[k] for k in b if k not in a]
    removed = [a[k] for k in a if k not in b]
    moved = [(a[k], b[k]) for k in a if k in b
             and (a[k]["date"], a[k]["start"], a[k]["end"]) !=
                 (b[k]["date"], b[k]["start"], b[k]["end"])]

    meta_lines = []
    for field in ("term_start", "term_end", "weeks", "source_pdf"):
        if old["meta"].get(field) != new["meta"].get(field):
            meta_lines.append(f"  {field}: {old['meta'].get(field)} -> {new['meta'].get(field)}")

    print(f"schedule diff: {old['meta']['source_pdf']} -> {new['meta']['source_pdf']}")
    if meta_lines:
        print("\nterm details changed:")
        print("\n".join(meta_lines))

    print(f"\nmoved ({len(moved)}):")
    for before, after in sorted(moved, key=lambda p: p[1]["date"])[:60]:
        print(f"  {before.get('label') or before['title']}")
        print(f"      {before['date']} {before['start']}  ->  {after['date']} {after['start']}")
    if not moved:
        print("  none")

    print(f"\nadded ({len(added)}):")
    for s in sorted(added, key=lambda s: (s["date"], s["start"] or ""))[:60]:
        print(f"  {describe(s)}")
    if not added:
        print("  none")

    print(f"\nremoved ({len(removed)}):")
    for s in sorted(removed, key=lambda s: (s["date"], s["start"] or ""))[:60]:
        print(f"  {describe(s)}")
    if not removed:
        print("  none")

    if removed:
        print("\nNOTE: any edit Anna made to a removed session no longer has anything to")
        print("attach to. Her edits live in her browser, so they cannot be migrated from")
        print("here -- tell her which of these she had customised.")

    total_old = sum(len(d["sessions"]) for d in old["days"].values())
    total_new = sum(len(d["sessions"]) for d in new["days"].values())
    print(f"\n{total_old} sessions -> {total_new} sessions")


if __name__ == "__main__":
    main()
