#!/bin/bash
# ---------------------------------------------------------------------------
# Update the calendar from a new block-schedule PDF.
#
#   ./update-calendar.sh                    find the newest PDF automatically
#   ./update-calendar.sh path/to/thing.pdf  use a specific one
#   ./update-calendar.sh --force            rebuild even if the PDF is unchanged
#
# Safe by design: if the PDF does not parse cleanly, this stops before
# publishing and leaves the live calendar exactly as it was.
# ---------------------------------------------------------------------------

set -uo pipefail
cd "$(dirname "$0")" || exit 1

PY="python3"
python3 -c "import fitz" 2>/dev/null || {
  ALT="/Users/finnhoops/Claude/Social Media Training Course/.venv/bin/python3"
  if [ -x "$ALT" ] && "$ALT" -c "import fitz" 2>/dev/null; then PY="$ALT"; else
    echo "STOP: the PDF library isn't installed."
    echo "Fix it by running this once:    python3 -m pip install pymupdf"
    exit 1
  fi
}

FORCE=0
PDF_ARG=""
for a in "$@"; do
  case "$a" in
    --force) FORCE=1 ;;
    *)       PDF_ARG="$a" ;;
  esac
done

say()  { printf '\n%s\n' "$*"; }
step() { printf '\n=== %s ===\n' "$*"; }

# --- 1. find the PDF -------------------------------------------------------
step "Finding the schedule PDF"
if [ -n "$PDF_ARG" ]; then
  PDF="$PDF_ARG"
  [ -f "$PDF" ] || { echo "STOP: there's no file at '$PDF'"; exit 1; }
  echo "Using the file you gave me: $PDF"
else
  # Only consider files that look like a schedule. Blindly taking the newest
  # PDF in Downloads would happily grab a bank statement.
  CANDIDATES=$(find "$HOME/Downloads" "$HOME/Desktop" ./schedule -maxdepth 1 \
                 -iname '*.pdf' -not -path '*/archive/*' -print0 2>/dev/null \
               | xargs -0 ls -t 2>/dev/null \
               | grep -iE 'schedul|calendar|block|curriculum' )
  if [ -z "$CANDIDATES" ]; then
    echo "STOP: I couldn't find anything that looks like a schedule PDF."
    echo
    echo "I looked in your Downloads folder, your Desktop, and schedule/ for a"
    echo "PDF with 'schedule', 'calendar', 'block' or 'curriculum' in the name."
    echo
    echo "Either rename the file so it has one of those words in it, or point me"
    echo "straight at it:    ./update-calendar.sh ~/Downloads/whatever-it-is.pdf"
    exit 1
  fi
  COUNT=$(printf '%s\n' "$CANDIDATES" | wc -l | tr -d ' ')
  PDF=$(printf '%s\n' "$CANDIDATES" | head -1)
  if [ "$COUNT" -gt 1 ]; then
    echo "I found $COUNT files that could be the schedule. The newest is:"
    echo
    printf '%s\n' "$CANDIDATES" | head -5 | nl -w2 -s'. '
    echo
  fi
  echo "About to use:  $PDF"
  echo "   (modified $(date -r "$PDF" '+%a %e %b %Y, %l:%M%p' 2>/dev/null | tr -s ' '))"
  echo
  printf 'Is that the right file? [y/N] '
  read -r ANSWER < /dev/tty
  case "$ANSWER" in
    [yY]*) ;;
    *) echo
       echo "Stopped — nothing was changed."
       echo "Run it again pointing at the right file, like this:"
       echo "    ./update-calendar.sh ~/Downloads/the-right-one.pdf"
       exit 0 ;;
  esac
fi

# --- 2. is it really a PDF? ------------------------------------------------
if [ "$(head -c 4 "$PDF")" != "%PDF" ]; then
  echo "STOP: that file isn't a real PDF (it may be a Word doc or a partial download)."
  echo "Re-download it from the school and try again."
  exit 1
fi

# --- 3. has anything actually changed? -------------------------------------
NEW_HASH=$(shasum -a 256 "$PDF" | cut -d' ' -f1)
OLD_HASH=$(cat data/.last_pdf_hash 2>/dev/null || echo "")
if [ "$NEW_HASH" = "$OLD_HASH" ] && [ "$FORCE" -eq 0 ]; then
  say "This is the same PDF the calendar was already built from — nothing to do."
  echo "Your calendar is already up to date."
  echo "(If you really want to rebuild it anyway, run:  ./update-calendar.sh --force)"
  exit 0
fi

# --- 4. file it, archive what it replaces ----------------------------------
step "Filing the new PDF"
mkdir -p schedule/archive
BASE=$(basename "$PDF")
for old in schedule/*.pdf; do
  [ -e "$old" ] || continue
  [ "$(basename "$old")" = "$BASE" ] && continue
  STAMP=$(date -r "$old" +%Y-%m-%d 2>/dev/null || date +%Y-%m-%d)
  mv "$old" "schedule/archive/$(basename "${old%.pdf}").$STAMP.pdf"
  echo "Moved the old schedule into schedule/archive/ (nothing is ever deleted)"
done
[ "$(cd "$(dirname "$PDF")" && pwd)/$BASE" = "$(pwd)/schedule/$BASE" ] || cp "$PDF" "schedule/$BASE"
echo "Saved as schedule/$BASE"

# --- 5. remember the current schedule so we can compare --------------------
[ -f data/schedule.json ] && cp data/schedule.json data/.schedule_prev.json

# --- 6. read the PDF -------------------------------------------------------
step "Reading the PDF"
PARSE_LOG=$(mktemp)
"$PY" tools/parse_schedule.py "schedule/$BASE" 2>&1 | tee "$PARSE_LOG"
if [ "${PIPESTATUS[0]}" -ne 0 ]; then
  echo; echo "STOP: the PDF could not be read at all. Your live calendar is untouched."
  [ -f data/.schedule_prev.json ] && mv data/.schedule_prev.json data/schedule.json
  rm -f "$PARSE_LOG"; exit 1
fi

# --- 7. safety checks ------------------------------------------------------
step "Checking it came out right"
if ! "$PY" tools/sanity_gate.py --schedule data/schedule.json \
        --prev data/.schedule_prev.json --parse-log "$PARSE_LOG"; then
  echo
  echo "Putting the old schedule back so nothing is left half-changed."
  [ -f data/.schedule_prev.json ] && mv data/.schedule_prev.json data/schedule.json
  rm -f "$PARSE_LOG"
  exit 1
fi
rm -f "$PARSE_LOG"

# --- 8. what the school changed --------------------------------------------
step "What the school changed"
if [ -f data/.schedule_prev.json ]; then
  "$PY" tools/diff_schedule.py data/.schedule_prev.json data/schedule.json
else
  echo "No previous schedule on file — everything is new."
fi

# --- 9. build --------------------------------------------------------------
step "Building the calendar"
"$PY" tools/check_contrast.py || { echo "STOP: the colour check failed — not publishing."; exit 1; }
"$PY" tools/generate_calendar.py || { echo "STOP: the page could not be built — not publishing."; exit 1; }

# --- 10. publish -----------------------------------------------------------
step "Publishing"
if ! command -v vercel >/dev/null 2>&1; then
  echo "The calendar was built successfully but couldn't be published:"
  echo "the 'vercel' command isn't installed. Install it once with:"
  echo "    npm install -g vercel"
  echo "Then run this script again — nothing will need re-reading."
  exit 1
fi
( cd build && vercel deploy --prod --yes ) || {
  echo
  echo "The calendar was BUILT fine but publishing failed."
  echo "Everything is saved, so just run this script again once that's sorted."
  exit 1
}

# --- 11. record ------------------------------------------------------------
echo "$NEW_HASH" > data/.last_pdf_hash
rm -f data/.schedule_prev.json
{
  echo
  echo "## $(date +%Y-%m-%d) — rebuilt from $BASE"
  echo
  echo "Run by update-calendar.sh. All safety checks passed."
} >> CHANGELOG.md

say "Done — your calendar is live and updated."
echo "Open it at the address printed just above (it never changes once set up)."
echo
echo "Reminder: your checkmarks and typed to-dos live in your browser."
echo "They weren't touched. Anything the school MOVED will come back unticked,"
echo "and anything listed as 'removed' above has lost the notes you'd added to it."
