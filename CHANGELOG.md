# Changelog

Every entry is one rebuild of the calendar from a block-schedule PDF.

## 2026-09-03 — the edit modal was eating topic lines

No new PDF. The real cause of Anna's missing topic lines on Clinical Skills
#1 / #4 / Pharmacology #1: the session edit modal has one "Name" field,
prefilled with the class name, and Save wrote `title = nameField` — so saving
any class (a time nudge, a mis-tap) overwrote its **topic** with its **name**,
and the calendar then hid the topic because the two were identical. It was in
her saved edits, so it survived a restart; Private mode looked fine because it
has no saved edits.

- Save now leaves `title` out of a school session's edit entirely, so the
  schedule's real topic always wins. Only a custom/added session, whose stored
  record is the source of truth, takes the name as its title.
- One-time repair on load: any saved edit whose `title` was clobbered to match
  its name has that `title` dropped (and the whole edit binned if that was all
  it held). Verified against a seeded localStorage carrying the bug.

## 2026-09-03 — stale-tab guard and a topic-line gate

No new PDF; the schedule is unchanged. First read of Anna's missing topic lines
(Clinical Skills #1 / #4 / Pharmacology #1) was a stale cache — it wasn't, see
the entry above, but the guard is worth keeping.

- Every build writes `build/version.json` with a fresh build id (timestamp,
  changes on any rebuild) and bakes the same id into `<meta name="build">`.
  A new IIFE at the top of the page script fetches `version.json` uncached on
  load, on back/forward-cache restore, and whenever the tab is brought back to
  the foreground, and reloads the page once if the id has moved on. A 20s
  guard stops a broken deploy reload-looping; a failed/offline fetch is
  swallowed and the page renders from its embedded data as before.
- `vercel.json` sends `/version.json` as `no-store`.
- `generate_calendar.py` now **fails the build** if any clean numbered class
  ("Anatomy #3", "Clinical Skills #1") comes out with no topic line — catches
  both a parser regression and an override that renames a session without
  carrying its topic (the Oct 2026 "Clinical Skills #10" bug). The same check
  runs in `sanity_gate.py`. Current schedule: 129 numbered classes, all clean.
- Classmate repo: `derive.py` copies `version.json` into every calendar folder,
  so the guard works for Chloe / Claire / Livvie too.

## 2026-08-25 — initial build

Source: `Block 1 Learning Calendar_CO28_CC_ Curriculum Schedule - 8.12.26.pdf`

- Block 1 parsed: 20 pages, 100 weekdays + 40 weekend days, 374 sessions, 32 exams.
- Term runs Wed 2 Sep 2026 to Fri 15 Jan 2027. The grid starts Mon 31 Aug, but
  31 Aug and 1 Sep are blank in the PDF — orientation opens on the Wednesday.
- Weekdays with no scheduled classes, all confirmed blank in the source:
  31 Aug, 1 Sep, 13 Nov, 12 Jan, 14 Jan.
- Naming rules applied per Anna: numbered courses, Clinical Skills ALA/MLA/OSCE,
  bare names for Orientation and Professionalism, `Anatomy Lab` for Gross
  Anatomy Lab Experience, and exams as printed.
- 13 sessions matched no naming rule and are waiting on names from Anna.
- To-do list ships manual-only; the STUDY 1.0 rules engine is deferred.

## 2026-08-25 — to-do workflow and floral lace

- To-do list now generates from Anna's study workflow: before-lecture ticks,
  the fixed during-lecture colour rules, and after-lecture steps followed by a
  second set of ticks. Verified against her worked example for Mon 14 Sep
  (Technology & Monitoring #1, #2, Clinical Skills ALA #7).
- `study` / `todoLabel` added to every session by the parser; 128 of 374
  sessions qualify across Block 1.
- Highlighter colours added for the yellow/blue/pink rules, solved numerically
  to clear WCAG AA on every ground rather than picked by eye.
- Floral pack gained a white lace border per STUDY 1.0, and a rose page ground
  so the lace has something to read against. The other five packs are unchanged.

## 2026-08-25 — cream-and-blue floral, vintage lace

- Floral pack repalletted to cream and blue per STUDY 1.0, with a ditsy floral
  on the page background (31 radial gradients in a 184px tile) and a blue accent.
- Lace redrawn as broderie anglaise: ring scallops with genuinely transparent
  eyelets, picot beads at each scallop junction, and a perforated openwork band.
- Established that SVG data URIs do not render as CSS background or border
  images on this machine, in either Chromium build, while rendering fine as an
  `<img>`. Everything decorative is gradients as a result.
- The other five packs are unchanged: no lace, no pattern, identical layout.

## 2026-08-25 — the floral is Anna's actual swatch

No schedule change; design only.

- The page background is now the picture Anna sent, tiled, rather than a
  gradient drawing of it. The swatch is a true 351×351 repeat — its wrap-around
  pixel difference (7.9) matches its internal difference (7.1), so it tiles with
  no seam. It is base64'd into the CSS, keeping `build/index.html` one file.
- The floral palette is sampled from that picture instead of chosen: ground
  `#eff2ef` is the swatch's own ground, and the accent `#4971a2` is its flower
  hue (213°) darkened until white text on it clears 4.5:1. The pack moved from
  warm cream to the picture's cool off-white.
- Dark mode gets the same swatch in a navy colourway, derived pixel-by-pixel by
  `tools/make_dark_swatch.py` rather than redrawn.
- The lace was rebuilt. It had been a solid blue band, which on a ground this
  pale read as a heavy ribbon; it is now a white scalloped band with a fine blue
  thread outline round the scallop and each eyelet. White is what reads here —
  the ground is patterned, so the white band is what stands out.
- Fixed: the today panel and the month grid's today cell both matched a bare
  `.today` selector, so the panel's lace, radius and margin were landing on that
  one day cell and squashing it. The panel is now `#today`.
- Verified: 630 contrast pairs at AA, no horizontal overflow at 375px
  (`scrollWidth == clientWidth == 375`), and the other five packs unchanged
  (`--lace-w: 0`, `--pattern: none`).

## 2026-08-26 — study sections fold

No new PDF; a UI change only. `data/schedule.json` is untouched.

- The three study phases — before, during and after lecture tasks — are now
  disclosures. Each header is a real `<button>` inside its `<h4>`, carrying
  `aria-expanded` and `aria-controls`, so keyboard and screen-reader behaviour
  comes free and the heading outline is unchanged.
- Open/closed is stored per phase and is **global, not per day**: a section Anna
  folds away stays folded on every day, which is the point of folding it. It
  lives in `S.open` in the same `localStorage` record as her ticks, and old
  records get the defaults through `Object.assign(blank(), …)`.
- Defaults: before and after open, during closed. During-lecture is the same
  reference text every day; the other two are the tickable ones she works.
- Folded sections still report progress — the header carries a `2/6` count for
  the tickable phases, and it turns accent-coloured at full marks. The count is
  `aria-hidden` and the same figure is folded into the button's `aria-label`,
  since a bare `2/6` on a span is not reliably announced.
- Toggling updates the DOM in place instead of calling `render()`. That keeps
  focus on the header Anna just pressed, and it matters because **two copies of
  the same day can be on screen at once** — the today panel and the day view.
  Both are updated together via `[data-phase]`, and `aria-controls` ids are
  uniquified with a counter for the same reason.
- Motion is opacity plus a 4px translate on reveal, never height, so nothing
  reflows; the existing `prefers-reduced-motion` block already neutralises it.
- Headers are 44px tall to clear the touch-target minimum, and the hover fill
  spans exactly the section hairline's width so the two line up.
- Verified in headless Chrome at the ≤640px branch: six toggles, defaults
  correct, both copies stay in step, state persists, the count follows a tick,
  ticking does not reopen a folded section, Enter works from the keyboard, no
  horizontal overflow, and the header still fits with room to spare in a column
  squeezed to 279px (narrower than the real 375px one). Contrast gate: 630
  pairs, all AA.

## 2026-08-26 — new swatch, and floral loses dark mode

No new PDF; palette and asset change only.

- **The floral pack no longer has a dark mode.** Finn was looking at the navy
  colourway and called it horrible, and he is right that it was not the same
  thing — it is a picture of white fabric, and the derived navy version read as
  a different print rather than as that fabric at night. The pack now carries
  `"noDark": true`; `generate_calendar.py` emits no dark block for it, so it
  renders identically whatever the device is set to. Verified: the page rendered
  with `preferredColorScheme=2` is pixel-for-pixel identical to the default
  render. The other five packs keep both variants.
- `check_contrast.py` had to learn the flag as well. It builds its ground sets
  per mode across all packs, so a noDark pack's unused dark block was leaking
  near-white grounds into the dark set and failing the dark highlighter hues
  against a state the page cannot reach. `modes_of()` fixes that. 585 pairs, AA.
- New swatch: the `background.jpeg` Finn sent, kept verbatim at
  `assets/background-source.jpeg` and converted to `assets/floral-light.webp`.
  It is a cooler, near-white print than the old one — ground `#feffff` against
  the old `#eff2ef`. The previous 351x351 swatch is kept as
  `floral-light-v1.webp`; it is a different, denser rose, not a better scan of
  this one.
- Palette re-sampled from the new file rather than adjusted: ground `#feffff`,
  hue 210 (the old was 213). Text is now **blue rather than near-black** at
  Finn's request — `ink` `#19334d`, `accent` `#296199`, both well clear of AA.
- `--pattern-size` moved 300px → 200px. The new file is only 140x140, so 300px
  was a 2.1x upscale and visibly mushy; 200px is soft but the roses read. **The
  one real improvement left here is a higher-resolution scan of this pattern** —
  every pixel of sharpness on this page comes from that file.
- Still outstanding: Finn sent a lace border picture to replace the CSS-drawn
  lace, but it never reached disk, so the lace is unchanged. An approximation
  would violate the standing rule against redrawing a specific picture.

## 2026-08-26 — the lace is a photograph now

- `lace.jpeg`, which Finn supplied, replaces the CSS lace. It is cut into a
  nine-slice border-image by the new `tools/make_lace.py` and worn by
  `#today,.month,.weekwrap,.card`. The 17 layers of radial-gradients it replaces
  drew lace convincingly and were still a drawing.
- The file is a screenshot of a transparent PNG, so the transparency arrived as
  a dark checkerboard. Alpha is reconstructed from brightness rather than cut out
  on a threshold — the netting between the motifs is genuinely semi-transparent,
  and a hard threshold turns it into a solid slab that stops reading as lace.
- Two things took a second attempt and are written up in CLAUDE.md so they are
  not repeated: cutting the mirrored repeat at the *sparsest* column put the
  mirror axis on a near-empty line and produced a hairline gap down every edge
  (the densest column is correct), and the bottom-right corner was mitred on the
  wrong diagonal, which tears the join instead of closing it.
- `--lace-w` 18px → 40px, chosen by rendering 28/40/52 side by side over the real
  ground. At 28px the scallops compress into a plain blue stripe and the band
  reads as a ribbon, which is the exact failure the old CSS lace was written to
  avoid. An alpha gamma curve was tried at 1.0/1.8/2.6 to open the netting up and
  made no visible difference at this scale; it is not in the tool.
- The lace is blue `#80a3c6`, not white. White was right against the old
  off-white ground and is invisible against the new near-white one — checked
  against the actual ground before changing it. `--card-outline` is new and goes
  transparent wherever lace is on: a straight 1px rule just inside a scalloped
  edge reads as a mistake.
- Verified: floral carries the border-image at 40px with `padding-box` clipping,
  the other five packs still resolve to `--lace-w:0` / `--lace-img:none` and keep
  their own outline, floral still emits no dark block, the to-do disclosures are
  unaffected, and there is no horizontal overflow. 585 contrast pairs, all AA.

## 2026-08-26 — sharp roses, lace turned outward, lighter blue

- **The blur is fixed, and the fix was not sharpening.** Finn's two captures turn
  out to be the same rose wallpaper: `background.jpeg` is shot wide enough that
  each rose is about fifteen pixels across, and no filter recovers detail that
  was never captured. `floral-light-v1.webp` is the same print shot close. The
  new `tools/make_floral.py` takes the **sharp capture and recolours it to the
  other's colours** — each pixel's distance below its own ground re-applied
  against the new ground, so motif and placement are untouched and only the paper
  changes. `--pattern-size` 200px → 260px, which against a 351px source is now a
  downscale rather than a 1.4x upscale.
- The lace is turned outward: straight picot edge against the card, scallops
  facing away into the floral. One flag in `make_lace.py`.
- Lace blue lightened `#80a3c6` → `#9dbad6`.
- **Fixed a pre-existing accessibility hole this surfaced.** The small uppercase
  line under the masthead title is the only type on the page sitting straight on
  the floral, and at `--ink3` it was at 2.6:1 against the darker roses — under
  the old tile as much as the new one. It is now `--ink2` over a new `--veil`, a
  soft radial wash of the ground behind the masthead. 70% is measured, not
  guessed: at 50% it still fails against the darkest rose in the tile, at 95% the
  wash erases the pattern entirely. Patternless packs get `transparent`.
- Verified: floral at 40px lace / 260px tile / 70% veil, the other five packs
  still at `--lace-w:0` with no veil and their own outline, floral still emits no
  dark block (dark-preference render is pixel-identical), disclosures unaffected,
  no horizontal overflow, 585 contrast pairs all AA.

## 2026-08-26 — Daily Tasks / Chat Recall

- New first section on the to-do list, **Daily Tasks**: one tickable
  `Chat Recall <course> #<n>` box for every qualifying lecture taught **the day
  before**. This is the Day 1 Chat Recall step from STUDY 1.0, which was
  explicitly out of scope until Finn asked for it.
- It sits **first**, ahead of the before/during/after run, because it is about
  yesterday's material and reads oddly after three sections about today's. Open
  by default, like the other two tickable sections.
- "The day before" is the previous **calendar** day, as asked. Worth restating
  because it is visible in the schedule: Friday's lectures surface on Saturday,
  and a Monday following a quiet Sunday carries no recall. Walking back to the
  last teaching day instead is a one-line change in `recallLectures`.
- `studyBlock` no longer bails when a day has no lectures of its own — a Saturday
  after a teaching Friday carries recall and nothing else, and still needs a
  block. `genCheck` grew a label override so a box can read something other than
  the session's own name.
- Tick state is keyed on the day the task appears (`date|recall|sessionId`), so a
  lecture's recall box and its own before/after boxes cannot collide, and the
  content-hash id means the box follows the lecture when the school moves it.
- Verified against the real schedule across 8–14 Sep: 8 Sep (first teaching day)
  has no recall; 9 Sep carries all six of 8 Sep's lectures — Anatomy #1 and #2
  and Clinical Skills ALA #1–#4, which is Finn's own example; 12 Sep (Sat) shows
  recall only, from Friday's Anatomy #6 and #7; 13 Sep and 14 Sep carry none.
  Ticking a recall box moves only the recall count, both on-screen copies stay in
  step, and storage writes `2026-09-09|recall|<hash>`.

## 2026-08-26 — Anki review

- Daily Tasks gained a second kind of box, under the Chat Recall ones: a single
  `Anki review: <lecture>, <lecture>, …` checkbox for the whole day, listing
  every qualifying lecture still in its review window. One box, not one per
  lecture, as asked.
- A lecture enters the list two days after it is taught — the day after its Chat
  Recall — and leaves when its exam is five days away or nearer. The test is
  "more than five days away", so it drops off for good rather than reappearing
  once the exam has passed. Those freed days are the 5/3/1-day exam runway from
  STUDY 1.0, which Finn is going to specify next; `ANKI_STOP` is the boundary it
  has to meet.
- `attach_exam_dates()` in `generate_calendar.py` works out which exam examines
  which lecture by **reading the exam titles the schedule already prints** —
  `EXAM 2: LECTURES 8-14` — so nothing is maintained by hand and the mapping
  re-derives itself whenever the school reissues the PDF. All six qualifying
  courses parse cleanly. Exams with no lecture range are correctly skipped: the
  Clinical Skills practicals, the OSCE stations and the Drug Card exam examine a
  skill, not a numbered run of lectures.
- **One lecture in the whole block has no exam that claims it** — Clinical Skills
  ALA #1, because Clinical Skills Exam 3 starts its range at lecture 2. It is
  kept in Anki review to the end of the block rather than dropped, and the build
  prints it every run so it cannot go unnoticed.
- The list is sorted by course then lecture number. It peaks at 20 items, which
  run together on one line, and by-course is the only order that stays scannable.
- Verified against the real schedule: 9 Sep has Chat Recall and no Anki (8 Sep's
  lectures are only a day old); 10 Sep carries both, the Anki line listing 8 Sep's
  six lectures; **11 Sep is exactly five days before Anatomy Exam 1 on the 16th
  and Anatomy #1 and #2 vanish from the line on that day**; 14 Sep carries Anki
  alone. Ticking the box writes `2026-09-10|anki`, moves only the Daily Tasks
  count, and both on-screen copies stay in step.

## 2026-08-26 — Clinical Skills off the Anki line

- Finn's call after seeing it: **Anki review now skips Clinical Skills ALA**. It
  is the only qualifying course excluded, and only from that one line — Clinical
  Skills ALA is still in Chat Recall and in the before/after boxes. Anki review
  covers Anatomy, Pharmacology, Technology & Monitoring, Physiology and
  Electrophysiology.
- Where a day's only eligible lectures were Clinical Skills, the Anki box is not
  rendered at all rather than rendered empty. 11 Sep is that day in Block 1.
- This retires the orphan warning as a side effect. The one lecture no exam
  claimed was Clinical Skills ALA #1, and the build's report is now filtered to
  courses that can actually reach the Anki line — the only place a missing exam
  date changes what Anna sees. Block 1 reports none.
- The line now peaks at 15 items (was 20) and appears on 111 of the block's 136
  days.
- Verified across all 140 days of the block: no Clinical Skills label reaches an
  Anki line anywhere, and Chat Recall still carries them.

## 2026-08-26 — Upcoming Tests

- New section, first in the to-do list, above Daily Tasks: **Upcoming Tests**,
  which opens five days out from an exam. "Days out" counts Finn's way — one day
  out is the day *before* the test, and the exam day itself is not in the window.
- Five days out gets one tickable
  `Chat test recall: <exam> (Lectures n-m)` box per exam.
- `TEST_WINDOW` is deliberately the same number as `ANKI_STOP`, and the handoff
  is visible in the schedule: Anatomy #1 sits on the Anki review line on 10 Sep
  and is gone on the 11th, which is the day Anatomy Exam 1's window opens.
- The build now annotates the exam list with `examTitle` and `lectureLabel`,
  reading both out of the exam titles the schedule already prints. `examTitle`
  has the title's own ": Lectures 1-7" tail stripped, because the page re-joins
  them as "Anatomy Exam 1 (Lectures 1-7)" and printing the range twice reads as a
  mistake. 23 of the block's 32 exams state a range; the other 9 — the Clinical
  Skills practicals, the OSCE stations and the Drug Card exam — examine a skill
  rather than a numbered run of lectures and are correctly absent.
- **Days 4 to 1 are deliberately empty.** Finn's message describing them was cut
  off mid-sentence, so `testTasks()` returns nothing for them and the section
  does not render on those days rather than rendering an empty dropdown. Verified
  across the whole block: the section appears on 23 days, one per eligible exam,
  and is never empty.

## 2026-08-26 — every exam gets a Day Five

- Upcoming Tests now covers **all 30 exams**, not just the 23 that state a
  lecture range. An exam with no lecture numbers gets `Chat test recall: <name>`
  with nothing in brackets, as Finn asked — the Clinical Skills practicals, the
  OSCE stations and the Drug Card exam.
- That meant fixing the exam names first, and `build_recall_exams()` does it,
  **reporting every repair rather than making it quietly**:
  - The PDF lists two practicals **twice** — once bare, once with the instructors
    and room run into the title. "Clinical Skills Airway Assessment" and
    "Clinical Skills Airway Assessment j. Moon k. Dewitt Classroom" are one exam;
    left alone Anna would get two identical boxes on the same day. Both pairs are
    collapsed and printed at build time. 32 exams → 30 entries.
  - Instructors, rooms, a stray "Evaluators" column header and `(45 minutes)`
    durations are stripped. Without that, three of the ranged exams came out as
    "Electrophysiology Exam 2 (45 minutes) (Lectures 6-11)" — brackets twice.
  - **Nothing else is renamed.** "Clinical Skills Exam 6 (30%) Cumulative (70%)"
    is what that exam is, so it ships as printed and is reported as a name nobody
    has settled. That is Anna's call.
- Verified across the whole block: the section appears on exactly 30 days, one
  box each, never empty, and no day carries two tests at once. A day whose only
  content is a Day Five renders the section alone — 4 Sep, five days out from the
  Drug Card exam, is that day.
- Days 4 to 1 remain deliberately empty, pending Finn's spec.

## 2026-08-26 — day four, and a different day-five wording for practicals

- The exams with no lecture numbers now read `5 days before test: <name>` rather
  than `Chat test recall: <name>`.
- Four days out, exams that **do** have lecture numbers get a second box:
  `Chat test recall and weakness list: <exam> (Lectures n-m)` — identical to
  their day five but for the wording. Practicals get nothing on day four; Finn
  did not ask for one.
- The run-up is now a table (`TEST_RUNUP`) keyed by days out, with a `ranged` and
  a `plain` wording per day. Days 3, 2 and 1 are a line each in that table when
  Finn specifies them, and nothing else has to change.
- Tick keys gained the days-out number, so the same exam's day-five and day-four
  boxes can never collide.
- Verified across the block: 23 day-five ranged boxes, 7 day-five plain, 23
  day-four ranged, 0 day-four plain — one per eligible exam, exactly as intended.
  The section now appears on 52 days carrying 53 boxes; the one day with two is a
  day that is five days out from one exam and four out from another.

## 2026-08-26 — Chat Recall collapses to one dated box

- Daily Tasks used to carry one `Chat Recall <course> #n` box per lecture taught
  the day before — six of them on 9 Sep. It is now a single
  `Chat Recall from 9/8`, at Finn's request. Six boxes saying the same thing in
  six ways is a worse prompt than one saying it once.
- The lectures are still resolved, because whether the previous day taught any
  qualifying ones at all is what decides whether the box appears. Behaviour round
  the weekend is unchanged: a Monday after a quiet Sunday still carries none.
- Daily Tasks is now at most two boxes, so its count reads `0/2` rather than
  `0/7`. Tick keys became `date|recall` and `date|anki`.
- Date reads `9/8` — no leading zeros, no year. It is always a day or two back
  from the day being looked at, so the year is noise.
- Verified across the block: Daily Tasks appears on 115 days, never more than two
  boxes, and every Chat Recall label matches `Chat Recall from M/D`.

## 2026-08-26 — countdown card, and "From the schedule" removed

- **"From the schedule" is gone**, from the today panel and the day view both, at
  Finn's request.
- The month grid's `N assigned` count went with it. That was not asked for, but
  with the list gone the count led nowhere, and a number you cannot click through
  to is worse than no number. Cells now read "6 classes · 2 to-do". Nothing was
  deleted from `data/schedule.json`; restoring any of this is a render away.
- The countdown card is now **filled** with the accent rather than tinted with
  it. On a ground this pale a tint is just another pale rectangle, and the next
  exam is the one thing on that panel worth seeing from across the room. The
  headline moved 34px → 42px. All of it resolves through `--accentInk`, which the
  contrast gate already holds to AA against `--accent` in every pack.
- It now carries **the next three exams**: the first large as before, then two
  under a hairline with how many days out they are.
- Those two put the day count inline at the end of the name rather than in a
  right-hand column. The column looked tidier until a name wrapped — and most of
  these names wrap — at which point the second line stopped short of the count and
  the block went ragged.
- The card reads `DATA.recallExams`, so the two practicals the PDF lists twice do
  not appear twice in a row of three, and the names have their instructors, rooms
  and durations stripped.
- Verified: the card and its sub-rows both flip to left-aligned under 920px
  (right-aligned above it), no month cell mentions "assigned", no empty count
  elements are left behind, and the day view carries no assignment block. The
  ~30px scrollWidth/clientWidth gap seen while testing is **pre-existing** —
  identical in the currently deployed build across all three views — and no
  element's box crosses the viewport edge.

## 2026-08-26 — day four repeats day five, day three goes extreme

- **Day four now reads exactly as day five does** — `Chat test recall: <exam>
  (Lectures n-m)`. This reverses the wording set an hour ago: day four had been
  "Chat test recall and weakness list", and Finn moved the weakness list to day
  three. The two days share one function so they cannot drift apart.
- **Day three** is new: `Extreme chat test recall and weakness list: <exam>
  (Lectures n-m)`.
- Practicals, the OSCE stations and the Drug Card exam are unchanged — day five
  only, nothing on four or three, because they state no lectures and there is
  nothing to put in the brackets.
- Verified across the block: 46 `Chat test recall:` boxes (23 exams over two days
  each), 7 `5 days before test:`, 23 `Extreme…`, and nothing unexpected. No box
  says "and weakness list" without "Extreme" in front of it any more. The section
  now appears on 70 days carrying 76 boxes.
- Days 2 and 1 remain empty, pending Finn.

## 2026-08-26 — standing Anki box, and the exam card in the day view

- Daily Tasks gained a third box: **`Remaining Anki memorization cards`**, every
  day from **11 Sep** to the end of the block, weekends included — it is a
  backlog, not a response to a lecture.
- That date is `ANKI_CARDS_FROM`, and it is **the one date in the to-do engine
  not derived from the schedule** — Finn picked it. It will not follow a new
  block on its own; it needs checking whenever a new PDF is parsed.
- It is also the only thing that can open Daily Tasks on a day with nothing else
  on it, so `studyBlock`'s bail-out had to learn about it.
- **The exam card now appears in the day view too**, at the top of the to-do
  column. `countdownCard(ref)` is now shared by both places and takes a reference
  date: the today panel passes TODAY, the day view passes the day on screen. So
  on 13 Sep the lower card reads "3 days" to Anatomy Exam 1 — the same question
  the to-do list under it is answering. On today's own day view the two cards
  agree.
- Verified: the standing box appears on every day from 11 Sep to 15 Jan and on no
  day before it; all three views render without errors on a pre-term date, a
  mid-term date and a post-term date; the pre-term "Starts in 13 days" card and
  the post-term "None left" card both still work; exactly one card in each place.

## 2026-08-26 — the day view's exam card mirrors today

- The day view's exam card now reads **TODAY**, not the day on screen. It tracked
  the day on screen for one deploy; Finn wanted the opposite, and he is right that
  a countdown is about now rather than about whatever day you are paging through.
  The two cards are now always identical — verified by paging the lower half 25
  days and diffing them.
- No change was needed for "make the top part show the day we're on": it already
  does, and always has. `renderToday` reads `iso(TODAY)`, and paging the lower
  half 20 days leaves the panel on "Wednesday August 26". The confusion came from
  the screenshots in this session, which use `?date=` to fake a September today so
  the term's behaviour can be shown — under that override the panel correctly
  follows the faked date.

## 2026-08-26 — the today panel could be moved by tapping a day (fixed)

- **Bug, reported by Finn and reproduced exactly.** Tapping a day in the month
  grid moved the today panel onto that day. `setView` writes the cursor into the
  URL as `?date=`, and `?date=` was *also* the override that told the page what
  today is. So tapping 11 September rewrote the URL, and the **next load** — a
  refresh, or a phone restoring a backgrounded tab — read it back as "today is 11
  September".
- It never showed up in the same session, because TODAY is read once at load.
  That is why an earlier check of this exact question came back clean: it paged
  with `step()` and re-read the panel live, which can never fail. Reproducing it
  needed the tap **and then a reload from the URL the tap produced**.
- Fixed by splitting the parameter in two. `?today=` fakes today, `?date=` parks
  the lower half, and only `?date=` is ever written back. The today panel is now
  unreachable from anything the lower half does.
- Verified against the previously deployed build side by side: old build reloads
  as "Friday September 11", new build reloads as "Wednesday August 26" with the
  lower half still parked on 11 September. Also checked bare URL, deep link
  alone, faked today alone, both together, and garbage values in both.

## 2026-08-26 — the exam card shows before the block too

- The today panel showed "Starts in 7 days" until the block began. It now shows
  the same exam card as the rest of the time — next exam large, two under it —
  which is what Finn asked for, and identical to the day view's copy.
- Nothing was lost with the countdown: the meta line on the left of that panel
  already reads "First day is Wednesday, September 2."
- `renderToday` no longer builds a card of its own at all; both places call
  `countdownCard(TODAY)` and are byte-identical in every state.
- Verified in all three: pre-term (real today, 26 Aug) reads "14 days · Drug Card
  Exam" with Clinical Skills Exam 1 at 16 and Anatomy Exam 1 at 21; mid-term
  reads "3 days · Anatomy Exam 1"; post-term reads "Exams / None left". Top and
  bottom identical in each.

## 2026-08-26 — the day view's exam card follows the day on screen

- Reverted to the original behaviour at Finn's request: the day view's exam card
  counts from **the day being viewed**, not from today. The today panel's copy
  still counts from today and is unaffected.
- So tapping 11 September gives a lower card reading "Next exam · Today ·
  Clinical Skills Exam 1" with Anatomy Exam 1 five days out, while the panel
  above stays on "Wednesday August 26 · 14 days · Drug Card Exam".
- Verified by tapping a month cell and by paging: the top card never moves, the
  lower one tracks the cursor, and 15 September correctly reads "Tomorrow" for
  the 16th's Anatomy exam.

## 2026-08-26 — Anki review lists only the lectures from two days back

- **Bug Finn caught**: on Sat 12 Sep the Anki line read "Pharmacology #1,
  Pharmacology #2" and was missing Anatomy #3, #4 and #5, which were taught the
  same day as the pharmacology ones.
- Cause was the five-day exam cutoff colliding with the two-day lag. A lecture
  became eligible two days after it was taught and dropped five days before its
  exam, so **any lecture taught inside seven days of its own exam was never
  listed once**. That was 26 of the block's 106 qualifying non-Clinical-Skills
  lectures — the whole of Anatomy #3–#7 among them.
- Fixed by Finn's call: the line now lists **exactly the lectures taught two days
  ago**, with no accumulation and no reference to exams at all. `ANKI_STOP` is
  gone. 12 Sep now reads "Anki review: Anatomy #3, Anatomy #4, Anatomy #5,
  Pharmacology #1, Pharmacology #2".
- Two intended consequences: a day whose two-days-ago taught nothing gets no Anki
  box (Mondays, usually), and the line can name a lecture whose exam is
  imminent — the exam run-up handles those last five days and the two now overlap
  freely.
- Verified across all 140 days: **every one of the 106 lectures appears on exactly
  one Anki line**, none missing, none repeated, no Clinical Skills leaking in.
  Also re-checked that every identifier in the to-do engine resolves and all three
  views render.
- `examDate` is still attached by the build but nothing reads it now. Kept: it is
  the only place the exam-to-lecture mapping is worked out, and the exam run-up is
  still being built.

## 2026-08-26 — colour key beside the view switcher

- A key to the day dots now sits to the right of Month/Week/Day. Six entries, one
  per numbered course, each a swatch plus its name.
- It needed a new `.barleft` wrapper: the bar is `justify-content:space-between`,
  so a third child would have been pushed to the middle rather than sitting next
  to the switcher.
- **Only the six courses are listed.** The other categories a dot can carry —
  Orientation, Professionalism, Break, Holiday, Other — are all near-greys and
  indistinguishable from each other at 6px, so naming them separately would
  promise a precision the dot has not got. Exams render as a labelled chip rather
  than a dot and already say what they are.
- The key carries its own white surface. This bar sits straight on the floral,
  and 11.5px text at `--ink2` does not clear AA against the darker roses — the
  same problem the masthead veil solved.
- Verified: the six swatches resolve to exactly the same computed colours as the
  month dots (checked by diffing computed styles, not by eye); the key renders in
  all three views; every entry has a text label and the swatches are
  `aria-hidden`, so nothing is conveyed by colour alone; no new horizontal
  overflow at 1200 / 940 / 700 / 500px, byte-identical scroll widths to the
  previous build.
- It costs the bar a second row on wide screens. That is the price of a 687px
  strip; the alternative was cramming it or abbreviating a course name.

## 2026-08-27 — add, edit and remove, everywhere

Finn asked for the Add buttons to actually work and for an Edit button beside
them, on the today panel, the to-do list, and the month/week/day grid.

**What was already working, and was not the problem.** Add on the schedule
already opened a modal and added the class; a class was already tap-to-edit;
the to-do Add form already worked. Verified by driving the deployed build
headlessly before changing anything. The gap was discoverability and one real
bug.

**The real bug: the to-do delete was invisible on a phone.** `.task .del` was
`opacity:0` until `:hover`, revealed by `.task:hover`. A touch screen has no
hover, so on the only device Anna uses the control existed, worked, and could
not be seen or reached. Fixed twice over — `@media (hover:none)` forces it
visible, and edit mode replaces it with an always-present bordered set.

**The second real bug: a removed school class was unrecoverable.** Hiding one
took the row away, and the row was the only way to reach the modal that could
reset it. The modal also said "Delete" for a custom class and "Hide" for a school
one — two different promises on one button. Both now say **Remove**, both route
through `S.hidden`, and a "Removed from this day" strip puts anything back.

Added:

- Three **Edit** toggles (`EDIT = {sched, todo, grid}`), each beside what it
  edits, none persisted. `sched` and `todo` are shared by the today panel and the
  day view, which can be showing the same date at once.
- Schedule edit mode: a remove per row, plus the restore strip. The row itself
  stays the edit target — one control per row, not two, because a 375px slot has
  no room for a pencil beside an ✕.
- To-do edit mode: remove on **every** box including the generated ones
  (`S.genHidden`, keyed the same as the ticks and storing the label so the strip
  can name it), and up/down arrows on Anna's own to-dos. Arrows, not drag: a
  32px row dragged on a phone fights the page scroll, and arrows work from a
  keyboard.
- `dayEditor(dateStr)` — the sheet the month and week open, listing a day's
  classes with edit, remove, restore and add. A month cell is 45px wide on a
  phone and a week block can be 22px tall; neither can carry a control per class.
  The month reaches it by tapping any day while Edit is on; the week from an Edit
  button under each day header, which is what the week had no way to do at all.
- `modalAfter`, so opening a class from inside the sheet returns to the sheet,
  and Escape behaves exactly like Cancel.

Consequences worth knowing:

- `checkRow` now returns `null` for a hidden box, so every caller filters, and
  the disclosure counts are computed from surviving rows — otherwise a header
  reads "0/6" over four boxes. A phase with every box removed renders no section.
- The restore strip carries the **time** as well as the name. 15 September
  teaches three consecutive Clinical Skills MLA; three identical rows would say
  nothing about which one went.
- The grid's Edit hides itself on the day view, which already has two of its own.
- `--accentSoft` is now a ground `check_contrast.py` tests, because a month cell
  in edit mode wears it under the day number, the class count and the dots.
  794 pairs, up from 585, all AA.

Verified headlessly: 48 behavioural checks over add / rename / remove / restore
on the panel, the day view, the month sheet and the week; reorder including the
disabled ends; removal and restore of a generated Anki box; a pre-upgrade
`localStorage` save with no `genHidden` or `hidden` key; the pre-term state,
where the panel edits the first day's schedule because that is what it shows.
Horizontal overflow is byte-identical to the previous build at 1200 / 940 / 700
/ 500px. No JS errors in any run.

## 2026-08-27 — removing Lunch removed all 66 of them (fixed)

Found while checking whether Anna's edits survive a re-parse, which is the real
question behind "will my study rules turn over with a new PDF".

`S.hidden` and `S.sessionEdits` were keyed on the session id alone. Session ids
are content hashes — `sha1(category|seq|title|instructor)` — so `Lunch` is **one
id across 66 days**, `Break` across five, `Thanksgiving Holiday` across five.
95 of the block's 374 sessions carry an id shared with another day. Taking Lunch
off Tuesday 15 September took it off all 66 days; renaming one renamed all 66.

Confirmed behaviourally before fixing: removed Lunch on 15 Sep, stepped to 16 Sep,
Lunch was gone there too.

The edit half is pre-existing. The remove half only became reachable yesterday,
when a one-tap ✕ was put on every row — a latent bug made easy to hit.

Fixed with `stateKey(s, dateStr)`: **`date|id` when the id appears on more than
one day, the bare id when it does not.** That is the right line, not a
compromise — an id on 66 days is naming a kind, and a kind has no single
occurrence to move; an id on one day is naming a lecture, and the content hash
exists precisely so Anna's edit follows it when the school moves it. `REPEAT_IDS`
is derived from `DATA` at load, so a new PDF recomputes it. `S.gen` was already
date-keyed, so all three stores now agree.

Verified: Lunch removed on 15 Sep stays on 16 Sep; renaming 15 Sep's lunch leaves
16 Sep's alone; a one-off lecture still stores under a bare id. 48 behavioural
checks from the previous entry re-run with no regressions.

Migration: a `hidden` entry saved before this reads as a bare id and no longer
matches, so an over-broad removal made yesterday simply comes back — which is the
correct outcome, since the only removals possible were the buggy ones. Edits to
one-off lectures keep their key and are untouched.

## 2026-08-27 — a Drive drop folder, and the last hardcoded date removed

Finn asked for a spot to upload reissued schedule PDFs, with all the study rules
carrying over.

**The study rules already carried over** — verified rather than assumed. Every
one of them is derived from the parsed schedule at render time, and a re-parse of
the current PDF is byte-identical to the deployed build including all 374 session
ids. There was exactly **one** hardcoded date in the entire pipeline.

**An upload box on the page is not possible** and was not built. The parser is
PyMuPDF and 780 lines of coordinate-sensitive Python on Finn's Mac; the deployed
page is one static file with no server. A file input there would be a button with
nothing behind it.

Built instead: **`New Schedule PDFs — Drop Here`** in Drive
(`1B4NvqvSvz52nzpEdfworzRV4-QHq7jqM`), inside `ANNA VCOM Calendar`, reachable
from any device. `/anna-calendar` now checks it **first**, then `schedule/`, then
the project root, and reports which of the three a build came from. Verified with
a real round trip: a PDF uploaded there and pulled back with
`download_file_content` is byte-identical and parses.

**`ANKI_CARDS_FROM` is gone.** The standing "Remaining Anki memorization cards"
box ran from a hardcoded 2026-09-11 — the only thing in the to-do engine that
would not have followed a new block. Finn chose "every day, from day one" over an
offset into the block, so `inBlock(dateStr)` now bounds it by the schedule's own
`term_start` / `term_end` and there is no date left to carry over.

Verified by sweeping all 150 days from a week before the block to a week after:
the box appears on **all 136 days inside the block** and on none outside it,
weekends included.


## 2026-08-27 (later) — a direct-upload route into `/anna-calendar`

Finn asked for the skill to accept a PDF handed straight to it, so Anna can send
a reissued schedule from her own device rather than only leaving one in a folder
to be found.

**Added as Step 1a, at higher precedence than every existing source.** An
attached PDF, a pasted path, or a file just saved to `~/Downloads`/`~/Desktop`
now wins over the Drive drop folder, `schedule/`, and the project root. The file
is **copied, not moved**, into `schedule/` before parsing, so the sender keeps
their own copy and the archive chain behaves identically to any other source.
The `%PDF` magic-byte check and the sha256 no-change guard apply unchanged — a
PDF handed over in person gets no more trust than one found in a folder, and the
sanity gate is explicitly non-negotiable for it.

Verified with a real round trip: a PDF placed outside the project resolved,
passed the magic-byte check, copied into `schedule/` leaving the sender's file in
place, and the hash guard correctly refused the rebuild as unchanged. `schedule/`
was left byte-identical afterwards.

**Step 0 no longer hard-fails off this Mac.** It still prefers the canonical
path, but falls back to locating the project by its marker files
(`tools/parse_schedule.py` + `tools/app_template.html`). Verified: the search
finds this folder and only this folder. If no project folder exists the skill
now stops and says so rather than trying to rebuild from the PDF alone — the
parser, template, themes and previous `schedule.json` cannot be reconstructed.

**Step 10 no longer tries to log in to Vercel.** On an unauthenticated machine
it stops, reports that everything up to the deploy is already saved to disk, and
names the fix as a `VERCEL_TOKEN` scoped to `anna-vcom-calendar`. The CLI login
on this Mac is a personal credential covering all five projects under
`finn-hoops-projects` and is not something to hand out for a calendar deploy.

**The permanent URL is now stated in the skill.** Confirmed against Vercel:
`https://anna-vcom-calendar.vercel.app` is the production alias and has survived
all 66 deploys. There is no new link to send after a rebuild, and the hashed
per-deploy URLs the CLI prints must never be passed to Anna — they go stale.

**Still open, deliberately not built:** the Drive drop folder is owned by Finn
and shared with nobody, so Anna cannot reach it yet — sharing it needs her Google
account address. And the project is still not in version control, which is the
one thing blocking the pipeline from running anywhere other than this Mac.

## 2026-08-27 (later still) — Anna takes the pipeline onto her own Mac

Anna asked how to run this herself. The schedule reissues often enough that
routing every update through Finn is not worth it, and she is happy to be the
sole owner — which removes the drift problem that made copying the folder look
unattractive an hour ago.

**Version control turned out to be the wrong tool for what she asked.** Git
solves keeping two machines matched. She is not syncing — she wants the files
once and then ownership. That is a folder copy. The project is ~2MB without
`versions/`, and no tool carries a hardcoded path to Finn's machine (checked),
so it moves as-is. A repo is still worth doing later as an **off-site backup**,
which is a different justification and was recorded as such rather than folded
into the same recommendation.

**`tools/sanity_gate.py`** — the Step 6 checks, mechanised. They previously
existed only as prose in the skill, which assumed someone competent was reading
the parser's output. Anna will not be, so the numbers now enforce themselves:
parse warnings, blank weekdays ≤ 8, exams ≥ 10, real term dates spanning 6–30
weeks, session count within 25% of the last build. Failures print in plain
language ("51 weekdays came out with no classes at all"), never in parser terms.

Verified by corrupting a known-good schedule three ways — half the sessions
dropped, exams cut to 3, `term_end` nulled — and confirming each stops with
exit 1 and names the right check. Passes clean on the real Block 1 schedule.

**`./update-calendar.sh`** — the whole pipeline as one command, safe for a
non-developer to run. Two design decisions worth keeping:

- It **confirms the file before acting**. The first version took the newest PDF
  in `~/Downloads`, which would cheerfully have grabbed a bank statement. It now
  filters to names containing schedul/calendar/block/curriculum, shows the file
  and its date, and waits for a y/N.
- On a gate failure it **restores `data/.schedule_prev.json` over the bad
  parse**. Without that, a refused build leaves a corrupt `schedule.json` on
  disk and the *next* run diffs against garbage. The deployed page was never at
  risk either way — publishing happens after the gate — but the local state was.

Verified end-to-end in an isolated copy with `vercel` stubbed: parse → gate →
diff → contrast → build → deploy → changelog, producing an identical 374-session
build. The live project was confirmed untouched afterwards.

**Vercel: she is getting her own account, not a token from Finn.** A scoped
token was the faster option and was rejected — it leaves her publishing through
his account, which is the thing she asked to stop doing. Cost is a one-time URL
change, which is near-zero given she is the only user. `SETUP-FOR-ANNA.md`
covers it, including `rm -rf build/.vercel` — without that the folder still
carries his project id and the first publish fails.

**Not done:** the Drive drop folder is still shared with nobody, and the project
is still not backed up anywhere off Finn's Mac.

## 2026-08-27 (later still) — the exam run-up is finally complete

Anna specified days 2 and 1, the two rows Finn had twice said he would fill in
and hadn't. `TEST_RUNUP` now covers the whole five-day window.

- **2 days out** — `Extreme Chat test Recall + Focus on weak list: <exam> (Lectures n-m)`
- **1 day out** — `DAY BEFORE EXAM <exam> (Lectures n-m) → Work on focused/weak
  concepts + do some anki if you have time`

Both are **her wording verbatim, capitalisation included**. `Chat test Recall`
with that exact casing is what she wrote; it is not a typo and must not be
normalised. She asked for the exam name and lecture range to land where she had
written `###`, and that is where they land.

Days 2 and 1 were already inside `upcomingTests` (`out >= 1 && out <= 5`) — they
returned no rows only because `TEST_RUNUP` had no entry for them. So this was
two table entries and nothing else, exactly as the table's own comment promised.

Verified by evaluating the real `TEST_RUNUP` out of `app_template.html` against
two real exams from the parsed schedule — Anatomy Exam 1 (ranged) and the Drug
Card Exam (no range) — and reading all ten resulting strings rather than assuming
the interpolation was right.

**Known gap, raised with Anna rather than papered over:** practicals, OSCE
stations and the Drug Card exam get one prompt at five days out and then silence
through the last four days. All four of the later wordings end in a lecture range
those exams do not have, so `plain` stays null. Filling it needs wording from her
per day; inventing one is exactly what the naming rules forbid.

Also settled this round: exam names carrying brackets ship as printed (Anna: "I
don't really care the specifics on that"), and cross-device checkmark syncing
stays out of scope at her request.

Deployed to https://anna-vcom-calendar.vercel.app — 140 days, 374 sessions,
32 exams, 794 contrast pairs at AA.

## 2026-08-27 — publishing moved to GitHub

The project was pushed to `github.com/finnhoops/anna-vcom-calendar` (private —
it carries Anna's name and her real schedule PDF) and the Vercel project was
connected to it. **A push to `master` now deploys the calendar.**

What changed:

- `build/index.html` is committed instead of ignored. It is the artifact Vercel
  serves, so ignoring it would publish an empty site.
- `vercel.json` added, setting `outputDirectory` to `build` so only the built
  page is public — the schedule PDF and `tools/` are not served.
- `update-calendar.sh` step 11 no longer runs `vercel deploy`. It commits the
  rebuilt page, changelog and PDF hash, then pushes. The record step moved
  ahead of publishing so it travels in the same commit.

The sanity gate is deliberately unchanged and still runs locally. Vercel does
no build — a misparsed schedule can't reach the live site because there'd be no
regenerated `index.html` to commit in the first place.

Verified end to end: a marker committed to `build/index.html` appeared on
https://anna-vcom-calendar.vercel.app after a push, then was removed by
regenerating through the normal pipeline.

## 2026-08-28 — rebuilt from Block 1 Learning Calendar_CO28_CC_ Curriculum Schedule - 8.12.26.pdf

Run by update-calendar.sh. All safety checks passed.

## 2026-08-30 — rebuilt from Block 1 Learning Calendar_CO28_CC_ Curriculum Schedule - 8.28.26.pdf

Run by update-calendar.sh. All safety checks passed.

## 2026-09-03 — rebuilt from Block 1 Learning Calendar_CO28_CC_ Curriculum Schedule- 9.3.26.pdf

Run by update-calendar.sh. All safety checks passed.
