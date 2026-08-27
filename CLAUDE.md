# Anna's VCOM Calendar

Anna's schedule and to-do list for each block of her MHSA (Anesthesiologist
Assistant) programme at VCOM. She is Finn's girlfriend; this calendar is built
for her and shared with her as a web link.

## What this is

- The **schedule** comes from a block-schedule PDF the school issues and reissues.
  Nothing in the schedule is typed by hand — it is parsed.
- The **to-do list** is generated from Anna's study workflow (STUDY 1.0) plus a
  manual list she can add to. See "To-do rules" below.
- The **UI** is: a today panel at the top carrying that day's schedule and
  to-do list, then a month grid you can click into for a week, and into a week
  for a single day.
- The calendar must stay **ready to re-parse a new PDF at any time**. That is
  what `/anna-calendar` does.

## Layout

```
schedule/          source PDFs (drop new ones here or in the project root)
schedule/archive/  superseded PDFs, date-suffixed
tools/             the pipeline (see below)
assets/            floral-light.webp (Anna's swatch) + the dark colourway
data/              schedule.json (generated), themes.json (hand-authored)
build/index.html   the deployed page
versions/          timestamped archive of every build
```

## Where new PDFs arrive

Two routes, and `/anna-calendar` handles both. **A PDF handed straight to the
session always wins over one it has to go looking for.**

**1. Handed to the session.** An attached or dragged-in PDF, a pasted path, or
a file just saved to `~/Downloads`. This is the route for "Anna sent me the new
schedule" and for anyone driving a Claude Code session that can reach this
project folder. The skill copies it into `schedule/` before parsing — copies,
not moves, so the sender's own file stays put — and from there it is treated
exactly like any other source: same hash check, same archive chain, same sanity
gate. A file handed over in person gets no more trust than one found in a
folder.

**2. The Drive drop folder.** `New Schedule PDFs — Drop Here`, folder id
`1B4NvqvSvz52nzpEdfworzRV4-QHq7jqM`, inside `ANNA VCOM Calendar`
(`1TEx7lb8PqiAqczL0JcWueUkqxarKMsaq`). Drop a reissued schedule there from
whatever device is to hand and ask for the calendar to be updated. When no PDF
was supplied directly, `/anna-calendar` checks that folder **first**, then
`schedule/`, then the project root.

As of 2026-08-27 the drop folder is owned by Finn and **shared with nobody**.
Anna cannot reach it until it is shared with her Google account.

Verified 2026-08-27: a PDF uploaded to that folder and pulled back with
`download_file_content` is **byte-identical** and parses. Use
`download_file_content` (base64), never `read_file_content`, which returns prose.
Check the bytes start with `%PDF` before parsing — a Google-native mime type that
got converted on upload is not a PDF.

### What is not a route

**The parser cannot run in a browser** — it is PyMuPDF and 780 lines of
coordinate-sensitive Python — so an upload box on the deployed page would be a
button with nothing behind it. For the same reason, a browser-only chat with no
filesystem cannot run this pipeline no matter what is uploaded to it: there is
nowhere to run the parser and no way to deploy. The two routes above are the
ones that reach the parser.

**Running the pipeline off this Mac** needs the project folder, not just the
skill. The skill is instructions; the parser, `app_template.html`, `themes.json`,
the assets and the previous `data/schedule.json` are all required, and the
project is not in version control, so there is currently no mechanism to sync it
anywhere. The tools themselves resolve their paths from `__file__` and are
portable — the folder is the thing that has to travel.

**Deploying off this Mac** needs a `VERCEL_TOKEN` scoped to `anna-vcom-calendar`.
The CLI login on this machine is a personal credential covering all of
`finn-hoops-projects` — webapp, fh-ai-consulting, ai-news, hockey-analytics —
and must not be handed to anyone to deploy a calendar.

## The live URL is permanent

`https://anna-vcom-calendar.vercel.app` is the production alias and it survives
every redeploy. There is no new link to send after a rebuild. The hashed
`*-finn-hoops-projects.vercel.app` URLs the CLI prints are per-deploy snapshots
that go stale — never pass one to Anna.

## Pipeline

```bash
python3 tools/parse_schedule.py "schedule/<pdf>"   # PDF  -> data/schedule.json
python3 tools/sanity_gate.py                       # is the parse trustworthy? exit 1 = stop
python3 tools/diff_schedule.py old.json new.json   # what the school changed
python3 tools/generate_calendar.py                 # JSON -> build/index.html
python3 tools/check_contrast.py                    # WCAG AA gate for themes.json
python3 tools/make_dark_swatch.py                  # only if the floral swatch changes
```

**`./update-calendar.sh` runs all of that as one command** and is what Anna uses.
Added 2026-08-27 so she can drive the pipeline from her own Mac without Claude.
It finds the PDF (asking her to confirm which), refuses on an unchanged hash,
archives the old one, parses, **runs the sanity gate and aborts on failure —
restoring the previous `schedule.json` so nothing is left half-changed**, prints
the diff, builds, deploys, and appends to this changelog. `--force` rebuilds an
unchanged PDF; a path argument skips the search.

`tools/sanity_gate.py` is the mechanised version of the checks that used to live
only as instructions in the `/anna-calendar` skill: page-level parse warnings,
blank weekdays ≤ 8, exams ≥ 10, real term dates spanning 6–30 weeks, and session
count within 25% of the previous build. It exists because Anna runs this without
anyone expert reading the parser's output. **It prints plain-language failures on
purpose** — the audience is not a developer. Verified against three deliberately
corrupted schedules (dropped sessions, lost exams, null term date): all three
stopped with exit 1.

Its thresholds and the skill's Step 6 gate are the same numbers and must stay in
step. Baseline as of Block 1: 140 days, 374 sessions, 32 exams, 5 blank weekdays,
2026-09-02 → 2027-01-15.

`SETUP-FOR-ANNA.md` is the one-time setup for her own Mac, also published at
https://claude.ai/code/artifact/eb53005c-6a94-49f9-b27c-2219933a9e69 so she can
read it on a phone while working on the laptop.

`tools/app_template.html` holds all HTML, CSS and JS with `__DATA__`-style
placeholders. Edit that, never `build/index.html` — it is overwritten.

## Things that will bite you

**Parse by coordinate, never by reading order.** PyMuPDF returns spans in
storage order, which interleaves days and times arbitrarily (page 2 of Block 1
starts with Friday). Every span is placed into a (day column, hour row) cell
from its bounding box. Day columns come from the date headers; hour rows come
from the hour labels in the left column — *not* from the Class/Subject/
Instructor labels, which go missing wherever the source merges cells.

**Hour rows must tile.** Deriving each row's top edge independently of the row
above leaves 2pt gaps, and any span landing in a gap is silently dropped. That
is how merged-cell exam titles disappear. `build_rows` computes shared edges.

**A merged multi-hour cell splits across rows.** The category lands in one hour
row and the subject in another; `merge_multi_hour` stitches the run back
together. Breaks end a run so LUNCH is never absorbed.

**Session ids are content hashes, not date hashes** —
`sha1(category|seq|title|instructor)`. Date and time are mutable attributes.
When the school moves a lecture, Anna's edit to it follows. When the school
*renames* one, the id changes and her edit is orphaned; `diff_schedule.py`
reports those instead of dropping them silently.

**Anna's edits are not in this repo.** They live in her browser's
`localStorage` under `anna-vcom-cal-v1`. Regenerating the page never touches
them. The flip side: they do not sync between her devices and Finn cannot see
them. Upgrading to a shared backend means replacing the two storage functions
in `app_template.html` and nothing else.

**The interpreter matters.** `fitz` (PyMuPDF) resolves from bare `python3` only
because Finn's shell exports `VIRTUAL_ENV` pointing at the Social Manor venv.
If that breaks, use
`"/Users/finnhoops/Claude/Social Media Training Course/.venv/bin/python3"`.
`pdfplumber` and `pdftotext` are not installed on this machine.

## Naming rules (Anna's, verbatim)

Applied in `label_session()` in `tools/parse_schedule.py`:

- **Orientation, Professionalism, Zoom meetings, Special events** — the class
  name alone, nothing else.
- **Clinical Skills** — `Clinical Skills MLA` or `Clinical Skills OSCE`.
  Clinical Skills **ALA** is numbered like the courses below.
- **Anatomy, Pharmacology, Technology & Monitoring, Physiology,
  Electrophysiology, Clinical Skills ALA** — class then lecture number:
  `Anatomy #1`.
- **Exams** — class, exam number, lectures covered, as printed on the schedule:
  `Anatomy Exam 1: Lectures 1-7`.
- **Gross Anatomy Lab Experience** → `Anatomy Lab`.

Anything that matches no rule is reported at the end of every parse run as
"sessions with no naming rule". Take that list to Finn — Anna names them, and
the name goes into the rules above. Never invent a name.

## Design

Global rules in `~/.claude/CLAUDE.md` apply, and `ui-ux-pro-max` must be
invoked before any visual change. Note that skill is **SKILL.md only** on this
machine — the `scripts/search.py` the global CLAUDE.md references does not
exist, so use the rules and checklists in the skill body directly.

- Fonts: Fraunces (display) and Public Sans (body). Inter, Roboto and
  system-ui are forbidden.
- Every colour resolves through a custom property. The only literal hex values
  in the project are in `data/themes.json`.
- Six seasonal packs, each with light and dark variants; the viewer's
  `prefers-color-scheme` picks the variant. Theme switching is **manual** —
  nothing changes on a date. Anna picks from the swatches in the header.
- **The colour key** (`.legend`, built by `buildLegend()`) sits beside the
  Month/Week/Day switcher, inside a new `.barleft` wrapper so it lands to the
  *right* of the switcher rather than being pushed to the middle by the bar's
  `space-between`. It lists the **six numbered courses only**. The other
  categories a dot can carry — Orientation, Professionalism, Break, Holiday,
  Other — are all near-greys and indistinguishable from one another at 6px, so
  naming them separately would promise a precision the dot has not got. Exams are
  not in it either: they render as a labelled chip, not a dot, so they say what
  they are.
  - It carries **its own `--surface` background** for the same reason the
    masthead carries a veil: this bar sits straight on the floral, and 11.5px
    text at `--ink2` does not clear AA against the darker roses.
  - Swatches resolve through the same `--cat-*` tokens the dots use, so the key
    cannot drift from what it describes — worth re-checking with a computed-style
    diff after any change to either.
  - It costs the bar a second row on desktop, which is the honest price of a
    687px strip; the alternative was cramming or abbreviating a label Anna knows.
- Course colours are deliberately the same in every pack. The season changes
  the ground and the accent, never what a course colour means.
- Run `tools/check_contrast.py` after any themes.json edit. It fails the build
  on anything under WCAG AA.
- **`?today=` and `?date=` are two different things and must stay that way.**
  `?today=YYYY-MM-DD` fakes what the page believes today is, and is how the
  pre-term and mid-term states get tested. `?date=YYYY-MM-DD` (with
  `?view=month|week|day`) only parks the lower half, and `setView` rewrites it
  every time Anna opens a day.

  They were one parameter until 2026-08-26, and that was a real bug Finn hit:
  tapping 11 September in the month grid wrote `date=2026-09-11` into the URL,
  and the **next load** — a refresh, or a phone restoring a backgrounded tab —
  read it back as "today is 11 September" and moved the today panel there. It
  never happened in the same session, because TODAY is read once at load, which
  is why paging with the arrows never showed it and an earlier test using
  `step()` missed it. **The today panel must not be reachable from anything the
  lower half writes.** Any screenshot taken with `?today=` will show the panel on
  that faked date — that is expected, not a bug.
- **Floral is single-colourway. It has no dark mode, on purpose.** The pack
  carries `"noDark": true` in `themes.json`; `generate_calendar.py` then emits no
  `prefers-color-scheme:dark` block for it, so it renders identically whatever
  the device is set to. Finn asked for this outright -- the derived navy
  colourway read as a different, worse thing rather than as the same fabric at
  night. `check_contrast.py` knows about the flag too, via `modes_of()`: without
  that, the dark highlighter hues get tested against floral's near-white grounds,
  which is a state the page cannot reach, and the gate fails on nothing.
  The other five packs keep both variants.
- **The floral tile is built, not picked** -- `tools/make_floral.py`, rerun it
  if either source changes. Finn sent two captures of the *same* rose wallpaper:
  `background-source.jpeg` (140x140) has the colours he wants but is shot so wide
  that each rose is ~15px across and reads as fuzz at any size, and
  `floral-light-v1.webp` (351x351) is the same print shot close, roses legible,
  on a warmer off-white ground. The tile is the **sharp capture recoloured to the
  other's colours**: each pixel's distance below its own ground is re-applied
  against the new ground, so motif and placement are untouched and only the paper
  changes -- the same derivation the old dark swatch used. `GAIN` (1.18) is the
  motif contrast; raising it darkens the roses and eats into the masthead's text
  contrast, so check that before touching it. The tool refuses to write a tile
  whose wrap-around match has drifted past 2.2x its internal one.
- `--pattern-size` is 260px against a 351px source, which is a **downscale** --
  that is what keeps the roses crisp. The previous 200px against the 140px
  capture was a 1.4x upscale and Finn rightly called it blurred.
  `generate_calendar.py` base64s it into `--pattern` so `build/index.html` stays
  one self-contained file. **Do not redraw this in gradients** -- that was tried,
  and an approximation of a specific picture is not the picture. An SVG is not an
  option either: an SVG data URI renders correctly as an `<img>` but paints
  **nothing** as a CSS `background-image` or `border-image`, in headless-shell and
  in full Chromium alike. It fails silently, so the decoration just never appears
  -- verified with a five-way side-by-side test.
- `assets/floral-dark.webp` is **no longer referenced** now that floral has no
  dark mode; it is kept only so the derivation is not lost. It was generated
  from the light one, not drawn: each
  pixel's distance below the swatch's own ground becomes a blue glow on a navy
  ground, so the motif and its placement are identical and only the colourway
  flips. `tools/make_dark_swatch.py` is that derivation -- rerun it whenever the
  light swatch is replaced, rather than hand-picking dark colours.
- The floral palette is **sampled from that picture**, not chosen: ground
  `#feffff` is the swatch's own ground and hue 210 is its flower hue, each
  token being that hue at a fixed saturation/lightness, darkened until it clears
  AA on the ground. Text is deliberately **blue, not near-black** (`ink`
  `#19334d`) -- Finn asked for a blue that pops against this ground.
- **The lace is a photograph, not CSS.** `lace.jpeg` (Finn's, 1179x594, a
  screenshot of a transparent PNG so the transparency arrives as a dark
  checkerboard) is turned into a nine-slice border-image by
  `tools/make_lace.py`, and `#today,.month,.weekwrap,.card` wear it as a single
  `border-image`. This replaced 17 layers of radial-gradients that drew lace
  convincingly and were still a drawing. Rerun `tools/make_lace.py` after any
  change to a pack's `lace` colour -- the tint is **baked into the asset**, so
  editing the token alone does nothing.
  - Alpha is reconstructed from *brightness*, not cut out on a threshold. The
    lace is white, the checker is dark, and the netting between the motifs is
    genuinely semi-transparent; a hard threshold turns that netting into a solid
    slab and the result stops reading as lace.
  - The edge run is a motif **plus its own mirror image**. The lace is
    photographed, so its motifs are not identical and butt-joining two of them
    leaves a visible step; mirroring makes both joins exact by construction.
  - The mirror is cut at the motif's **densest** column. Cutting at the sparsest
    one was the first attempt and it is wrong: the mirror axis is then a
    near-empty column sitting beside its own reflection, which reads as a
    hairline gap repeating down every edge.
  - Corners are mitred on the diagonal from the **outer** corner to the inner
    one -- so top-left and bottom-right split on the main diagonal, top-right and
    bottom-left on the anti-diagonal. Getting one backwards tears the join open.
    The two halves overlap by a pixel or antialiasing leaves a hairline through
    the corner.
  - `background-clip:padding-box` is load-bearing: it stops the card's white
    surface at the padding edge so the floral shows through every hole. Without
    it the lace sits on a white slab.
  - `round`, not `repeat` -- `repeat` cuts the motif wherever the edge ends.
  - `--lace-w` is **40px**, chosen by rendering 28/40/52 side by side over the
    real ground. At 28px the scallops compress into a plain blue stripe and it
    reads as a ribbon; 52px is more frame than card.
  - Scallops face **outward**, straight picot edge against the card
    (`SCALLOPS = "out"`). Whichever edge of the photograph ends up at y=0 becomes
    the outer edge of the border, so the flag is a single flip. Facing them
    inward was the first version and Finn asked for the reverse: the card keeps a
    clean rectangle and the lace reads as trim rather than as a frame eating the
    content.
  - The lace is **blue (`#9dbad6`), not white**. White was right on the old
    off-white ground and is invisible on this near-white one -- verified before
    changing it. `--card-outline` goes transparent wherever lace is on, because a
    straight 1px rule just inside a scalloped edge reads as a mistake.
  - Still not an SVG, for the reason below.
- **`--veil` is the masthead's text protection, and it is measured.** The
  masthead is the only place type sits straight on the floral rather than on a
  card, and the small uppercase line under the title falls below AA against the
  darker roses -- it did against the old tile too, so this is a pre-existing
  hole that a sharper tile only widened. `.masthead::before` lays a radial wash
  of the ground behind it at **70%**: at 50% that type still fails against the
  darkest rose in the tile, and at 95% the veil erases the pattern behind the
  masthead altogether. Packs with no pattern get `transparent` -- a wash over a
  flat ground just looks like a smudge. `.brand .sub` and `.themepick .lbl`
  moved `--ink3` -> `--ink2` at the same time.
- The **countdown card** (`.countdown`) is filled with `--accent`, not tinted
  with `--accentSoft`. On a ground this pale a tint is just another pale
  rectangle, and the next exam is the one thing on the panel Anna needs from
  across the room. Everything on it resolves through `--accentInk`, which
  `check_contrast.py` already holds to AA against `--accent` in every pack. It
  carries the next exam large, then the two after it. Those two put the day count
  **inline** at the end of the name rather than in a column: as a column it looked
  tidier until a name wrapped — and most of these names wrap — at which point the
  second line stopped short of the count and the block went ragged. The card
  flips to left-aligned under 920px and **the sub-rows have to flip with it**.
- The countdown reads `DATA.recallExams`, not `DATA.exams` — deduplicated and
  with instructors, rooms and durations stripped. Two of the practicals are
  listed twice in the PDF, and showing one of them twice in a row of three would
  read as a bug.
- **The "From the schedule" assignment lists are gone** from the today panel and
  the day view, at Finn's request, and the month grid's "N assigned" count went
  with them — the count had nowhere left to lead. The assignments are untouched
  in `data/schedule.json`, so restoring any of it is a render away.
- **`countdownCard(ref)` is shared** by the today panel and the day view, and
  the two pass **different** dates on purpose. The today panel passes `TODAY` and
  must keep doing so. The day view passes **the day on screen**, so its count
  answers the same question the to-do list beside it answers: from this day, how
  far is the next exam. They agree only while the day view is showing today.
  (This flipped twice during the session before landing here — the day view
  following the cursor is what Finn wants.)
  It shows in **every state of the block, including before it starts** — it used
  to count down to day one while pre-term, and Finn wanted the exams there
  instead. Nothing was lost: the meta line on the left of the panel already reads
  "First day is Wednesday, September 2." After the last exam both cards fall back
  to "Exams / None left".
- **The today panel does not follow the cursor and never has** — `renderToday`
  reads `iso(TODAY)`, and paging the lower half 20 days does not move it. If this
  looks wrong while testing, check for a `?date=` in the URL: that override
  changes what the page believes TODAY is, so the panel follows it. Every
  screenshot taken with `?date=` will show the panel on that date.
  `.card-cd` is the day view's wrapper — it drops the min-width, since the column sets the
  width there, and left-aligns. The pre-term "Starts in N days" card is still
  built inline in `renderToday`, because before the block there is no next exam
  to count to.
- The today **panel** is `#today`; a month grid cell for today is `.day.today`.
  Do not style the panel with a bare `.today` selector -- it matches both, and
  the panel's lace and margin then squash that one day cell.
- Packs other than floral omit `pattern` and set `lace: transparent`, so they get
  `--lace-w: 0`, `--pattern: none`, and an identical layout. Only the floral pack
  carries a picture; the seasonal packs are colour-only by design.

## Editing — add, change, remove

Everything Anna can change is reachable from an **Edit** toggle sitting next to
the thing it edits. There are three, in `EDIT = {sched, todo, grid}`, and they
are **not persisted**: edit mode is somewhere you are for a minute, not a
setting, and opening the calendar tomorrow already in it would be a trap.

`sched` and `todo` are **shared by the today panel and the day view**, which can
both be showing the same date at once — a control that only worked on one of the
two copies would read as broken. Same reasoning as `S.open` for the disclosures,
except this one calls `render()`, because rows appear and disappear rather than
just unfolding.

**An id shared across days is a KIND, not an occurrence.** `Lunch` is one content
hash across 66 days, `Break` across five; 95 of the block's 374 sessions carry an
id like that. Keyed on the id alone, removing Lunch from one Tuesday removed it
from all 66, and renaming one renamed all 66 — verified, not theorised. So
`stateKey(s, dateStr)` returns **`date|id` for a repeated id and the bare id for a
one-off**, and `S.hidden` / `S.sessionEdits` both go through it. That keeps what
the content hash was actually for: when the school moves Anatomy #3, Anna's
rename of it still follows. `REPEAT_IDS` is derived from `DATA` at load, so a new
PDF recomputes it rather than inheriting the old block's answer. Note the tick
state in `S.gen` was always date-keyed, so this makes the three stores agree.

**Nothing is ever destroyed.** Removing a class pushes its id onto `S.hidden`
and a "Removed from this day" strip puts it back; removing a generated to-do box
writes `S.genHidden[key] = label` and the same strip restores it. Two reasons,
both learned the hard way:

- A one-tap delete with no undo on a phone is a real loss.
- Before this, hiding a school class made it **unrecoverable**. The only control
  that could reset it lived in the modal you open by tapping the row — and the
  row was the thing that had just gone. The modal's button also said "Delete" for
  a custom class and "Hide" for a school one: two different promises on one
  button. It is now **"Remove"** for both, and both route through `S.hidden`.

**The to-do delete was invisible on the only device Anna uses.** `.task .del` was
`opacity:0` until `:hover`, and a phone has no hover — so the control existed,
worked, and could not be seen or reached. That is the actual bug behind "the
to-do list can't be edited". Fixed twice over: `@media (hover:none)` forces it
visible, and edit mode replaces it with a bordered set that is always there.
**Never gate a control on `:hover` alone in this project.**

Reordering to-dos is **arrows, not drag**. Dragging a 32px row on a phone fights
the page scroll, and arrows are the only version that also works from a keyboard.
Only Anna's own to-dos reorder; the generated ones are rebuilt from the schedule
every render, so their order is not hers to hold.

**`checkRow` returns `null` when a box is hidden**, so every caller has to cope
with that — `testTasks` filters, the recall rows filter, and the before/after
sections build from `shown(phase)`. The disclosure counts come from the
**surviving rows**, not from the lecture list they were made from; otherwise a
header reads "0/6" over four boxes. A phase whose every box has been removed
renders no section at all, for the same reason `testsBlock` returns null on no
rows.

**The month and the week cannot carry a control per class** — a month cell is
45px wide on a phone and a week block can be 22px tall. So the grid's Edit opens
`dayEditor(dateStr)`, a sheet listing that day's classes with edit, remove,
restore and add. The month reaches it by tapping any day (edit mode replaces
navigation, because a cell has room for exactly one gesture); the week reaches it
from an Edit button under each day header, which is what the week had no way to
do before — its blocks were already tap-to-edit, but there was no add.

The grid's Edit button **hides itself on the day view**, which already carries
its own two Edit buttons over the two columns they act on. A third one in the bar
with nothing left to do would read as broken.

`modalAfter` is how the sheet survives opening a class from inside itself: it is
set by whoever opened a modal and read in `closeModal`, so Escape and a scrim
click behave exactly like Cancel.

**The restore strip names the time as well as the class.** 15 September teaches
three consecutive Clinical Skills MLA, and a strip offering three identical rows
tells Anna nothing about which one she took off (`sessStamp`).

**`--accentSoft` is now a tested ground**, not just a tint behind `ink`: a month
cell in edit mode wears it under the day number, the class count and the category
dots. `check_contrast.py` checks it for every pack — 794 pairs, up from 585.
The dashed ring on an editable cell is 1.5px inset 4px, not 2px inset 3px: at 2px
against the grid's own rules it read as a cage over the month, and the month still
has to be readable while you look for the day you want. Dashed, not solid, because
today's ring is solid and the two land on the same cell.

## To-do rules (Anna's, from STUDY 1.0)

Source doc: Drive id `1jTZjsWrdx4W0X5OmqkirDGCjCx5wFpzPO-67xaQ7ypE` — read that
id, not the shortcut in the Drive folder, which will not resolve. Note
`read_file_content` **truncates** it; use `download_file_content` to see the
bottom, which is where the newest instructions get added.

Each day gets up to five sections, in this order:

0. **Upcoming Tests** — appears from `TEST_WINDOW` (5) days out from an exam.
   "Days out" counts Finn's way: **one day out is the day BEFORE the test**, and
   the exam day itself is not in the window.

   `TEST_RUNUP` is the whole spec, a table keyed by days out. Each day has a
   `ranged` wording and a `plain` one, because the exams that state a lecture
   range and the ones that do not are not the same task and do not read the same:

   | Days out | Ranged exam | Practical / OSCE / Drug Card |
   |---|---|---|
   | 5 | `Chat test recall: <exam> (Lectures n-m)` | `5 days before test: <exam>` |
   | 4 | same wording as day 5 | *(nothing)* |
   | 3 | `Extreme chat test recall and weakness list: <exam> (Lectures n-m)` | *(nothing)* |
   | 2 | `Extreme Chat test Recall + Focus on weak list: <exam> (Lectures n-m)` | *(nothing)* |
   | 1 | `DAY BEFORE EXAM <exam> (Lectures n-m) → Work on focused/weak concepts + do some anki if you have time` | *(nothing)* |

   **The table is complete as of 2026-08-27.** Days 2 and 1 are Anna's own
   wording, given verbatim including its capitalisation — `Chat test Recall`
   is hers, not a typo to tidy. Do not normalise it.

   **Every practical gets exactly one prompt, five days out, and then nothing.**
   That falls out of `plain: null` on days 4, 3, 2 and 1, which in turn falls out
   of all four of those wordings ending in a lecture range a practical does not
   have. Anna was shown this explicitly and it is a known gap, not an oversight —
   filling it needs a wording from her per day, never an invented one.

   Days 5 and 4 share one function (`chatRecall`) so they cannot drift apart —
   they are meant to be word-for-word the same. Day 4 briefly read "Chat test
   recall and weakness list" and Finn replaced that with a plain repeat, moving
   the weakness list to day 3 with "Extreme" in front of it. Only day 5 has a
   `plain` wording; a practical states no lectures, so there is nothing to put in
   the brackets on the days that ask for them.

   `null` means that day asks nothing of that exam. **Adding days 2 and 1 is a
   line each in that table and nothing else** — that is the whole point of its
   shape. Do not invent content for them; a day where nothing is asked of any
   exam renders no section at all, because an empty dropdown is worse than no
   dropdown, which is why `testsBlock` returns null on no rows.
   `TEST_WINDOW` is deliberately the same number as `ANKI_STOP`: a lecture leaves
   the Anki line on exactly the day its exam's window opens.

   `build_recall_exams()` in the generator repairs two things in the PDF's exam
   names before any of this, and **reports both every run rather than doing them
   quietly**. The PDF lists two practicals twice, once bare and once with the
   instructors and room run into the title — "Airway Assessment" and "Airway
   Assessment j. Moon k. Dewitt Classroom" are one exam, and left alone they give
   Anna two identical boxes. And it strips instructors, rooms, a trailing
   "Evaluators" column header and `(45 minutes)`-style durations, which are
   logistics rather than a name. Everything else is left alone: **"Clinical
   Skills Exam 6 (30%) Cumulative (70%)" is what that exam IS**, so it ships as
   printed and is reported as a name nobody has settled — that is Anna's call,
   not the script's.
1. **Daily Tasks** — up to three boxes: `Chat Recall from 9/8` when the previous
   day taught any qualifying lecture, `Anki review: a, b, c` listing every
   qualifying lecture still in its review window, and a standing
   `Remaining Anki memorization cards` on **every day of the block**. See below.
2. **Before lecture tasks** — one tickable box per qualifying lecture.
3. **During lecture tasks** — the same every day, bullets only, never tickable:
   a lead line plus the yellow / blue / pink colour rules.
4. **After lecture tasks** — the same four bullets every day, then one tickable
   box per qualifying lecture again.

Then Anna's own "My to-dos", then any assignments the PDF itself lists.

All three study sections are **disclosures**. Open/closed is per phase and
global, not per day, and is stored in `S.open` (defaults: before and after open,
during closed). Toggling deliberately does **not** call `render()` — it patches
the DOM in place, because the today panel and the day view can both be showing
the same date, and a full re-render would drop focus off the header just pressed.
Both copies are kept in step through `[data-phase]`, and `aria-controls` ids
carry a counter so they stay unique across those two copies.

**Chat Recall** is **one box naming the day** — `Chat Recall from 9/8` — not a
box per lecture. It listed every lecture at first and Finn cut it back: six boxes
saying the same thing in six ways is a worse prompt than one saying it once. The
lectures are still resolved, because whether the day taught any qualifying ones
at all is what decides whether the box appears.

`recallLectures` reads **the previous calendar day**, not the previous teaching
day. That is what he
asked for and it is what a one-day spacing means, but it has a consequence worth
knowing before "fixing" it: **Friday's lectures surface on Saturday, and a Monday
after a quiet Sunday carries no recall at all.** Changing it to walk back to the
last teaching day is a one-line change in `recallLectures` — do it only if Finn
says so.

Two things follow from recall living on a different day than its lecture:

- `studyBlock` must not bail on "no lectures today". A Saturday after a teaching
  Friday has recall and nothing else, and that day still needs a study block.
- Tick state is keyed on the day the task **appears** — `date|recall`, and
  `date|anki` beside it — so nothing in Daily Tasks can collide with the
  before/after boxes, which stay keyed per session.

**Anki review** (`ankiLectures`) lists the qualifying lectures taught **exactly
`ANKI_LAG` (2) days ago** — the day after their Chat Recall. It does **not**
accumulate and it does **not** look at exams. `ANKI_SKIP` drops **Clinical Skills
ALA**, here and only here; it is still in Chat Recall and in the before/after
boxes.

Two consequences, both intended:

- A day whose two-days-ago taught nothing gets **no Anki box at all**. Monday is
  usually that day, because Saturday rarely teaches.
- The box can name a lecture whose exam is tomorrow. The exam run-up in Upcoming
  Tests is what handles the last five days, and the two overlap freely.

**It accumulated with a five-day exam cutoff until 2026-08-26, and that had a
real hole** — worth knowing before anyone reintroduces it. A lecture became
eligible two days after it was taught and dropped five days before its exam, so
any lecture taught inside seven days of its own exam was **never listed once**.
That was 26 of the block's 106 lectures. Finn caught it on 12 September, where
Anatomy #3–#5 were missing from a line that should have carried them. Every
lecture now appears on exactly one Anki line — that is worth re-testing after any
change here.

**The standing Anki-cards box runs on every day of the block, weekends
included** — `inBlock(dateStr)`, bounded by `DATA.meta.term_start` and
`term_end`. It ran from a hardcoded `ANKI_CARDS_FROM = "2026-09-11"` until
2026-08-27, and that was **the only date in the whole to-do engine not derived
from the schedule** — so it was the one thing that would not have followed a new
block. Finn chose "every day, from day one" over an offset into the block, which
removes the date entirely: there is now nothing here to check when a new PDF is
parsed. Days outside the block get no box, because before day one there is
nothing to have made cards from.

`attach_exam_dates()` still writes `examDate` onto each qualifying lecture, and
**nothing reads it any more**. It is kept because it is the only place the
exam↔lecture mapping is worked out and the exam run-up is still being built.

**Qualifying** means Anatomy, Pharmacology, Technology & Monitoring, Physiology,
Electrophysiology, and Clinical Skills **ALA** — set by `study_info()` in
`tools/parse_schedule.py`, which writes `study` and `todoLabel` onto each
session. Orientation, Professionalism, Zoom meetings, Special events, Clinical
Skills MLA and Clinical Skills OSCE are excluded, as are exams and breaks. A day
with no qualifying lectures shows no study sections at all.

In the to-do list Clinical Skills ALA is spelled out in full
(`Clinical Skills ALA #7`) even though the calendar shows `Clinical Skills #7`,
so it cannot be confused with the MLA and OSCE sessions beside it. That is
Anna's wording from the doc.

Tick state is keyed `date|phase|sessionId` in `S.gen`, kept separate from manual
to-dos in `S.tasks`. Rebuilding from a new PDF disturbs neither.

## Out of scope until Finn says otherwise

- Day 1 Chat Recall and the Anki review list are **in** as of 2026-08-26. The
  5/3/1-day exam runway is still **not** — Finn has said he will specify it, and
  `ANKI_STOP` (5 days) is deliberately the boundary it has to meet. The Anki time
  budget from STUDY 1.0 is not in either. Do not add either uninvited.
- Any sync of Anna's edits between devices.
- Google Calendar export. The Google Calendar connector is not authorised.
