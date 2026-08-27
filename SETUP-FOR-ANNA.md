# Setting this up on your own Mac

One-time setup, then updating the calendar is a single command forever after.

Budget about 30 minutes for the setup. You only do it once.

---

## Before you start — what Finn needs to send you

Ask him for **the whole `Anna VCOM Calendar` folder**, minus the `versions`
folder inside it (that's 19MB of old backups you don't need). AirDrop is easiest.

What actually matters in there: `tools/` (the programs), `data/`, `assets/`,
`schedule/`, and `update-calendar.sh`. About 2MB total.

Put it wherever you like. Your Documents folder is fine.

---

## Step 1 — Open Terminal

It's in Applications → Utilities → Terminal. Or hit `Cmd+Space`, type
"terminal", press Enter.

A window with text in it opens. This is where you'll type things. It looks
intimidating and isn't — you'll use about four commands total, ever.

**Get to your folder.** Type `cd ` (with the space), then drag the calendar
folder from Finder into the Terminal window and press Enter. That fills in the
path for you so you don't have to type it.

To check it worked, type `ls` and press Enter. You should see `tools`, `data`,
`update-calendar.sh` and friends listed.

---

## Step 2 — Install the PDF reader

Copy this, paste it into Terminal, press Enter:

```
python3 -m pip install pymupdf
```

This is the one outside piece of software the calendar needs. It's what reads
the schedule PDF. Free, takes a few seconds.

If it complains about "externally managed environment", use this instead:

```
python3 -m pip install --user --break-system-packages pymupdf
```

That warning sounds alarming and isn't — it's macOS being cautious about its
own built-in Python.

---

## Step 3 — Install the publishing tool

This is the part that turns the built page into a real web link.

First check whether you already have Node (it comes with lots of things):

```
node --version
```

If that prints a version number, skip ahead. If it says "command not found",
go to **nodejs.org**, download the big green "LTS" button, and install it like
any normal Mac app. Then close Terminal, reopen it, and `cd` back to your folder.

Then:

```
npm install -g vercel
```

---

## Step 4 — Make your own free Vercel account

Go to **vercel.com** and sign up. Free. Use whatever email you like — this is
your account, not Finn's, and that's the whole point.

Then connect Terminal to it:

```
vercel login
```

It'll open your browser to confirm. Say yes.

---

## Step 5 — Cut the cord from Finn's account

**Do this or the first publish will fail.** The folder still remembers that it
used to belong to his Vercel account. Run:

```
rm -rf build/.vercel
```

That deletes only the little bookkeeping file that says whose account this
belongs to. It touches nothing else.

---

## Step 6 — Publish it once, under you

```
cd build
vercel deploy --prod
cd ..
```

The first time, it asks you a few questions:

- **Set up and deploy?** → yes
- **Which scope?** → your own name
- **Link to existing project?** → **no**
- **Project name?** → `anna-vcom-calendar` (or anything you like)
- **Directory?** → just press Enter
- **Modify settings?** → no

When it finishes it prints a web address. **That's your calendar, on your
account.** Bookmark it. It will never change again, no matter how many times you
update the schedule.

It'll be a different address from the old one Finn set up. That's expected —
it's the price of not needing him anymore. Bookmark the new one on your laptop
and your phone.

---

## That's the setup done. Here's the part you'll actually use.

When the school sends a new schedule:

1. **Save the PDF to your Downloads folder.**
2. Open Terminal, `cd` to the calendar folder (drag-and-drop trick again).
3. Type this and press Enter:

```
./update-calendar.sh
```

That's it. It will:

- find the new PDF and **ask you to confirm it's the right one** before doing
  anything
- read it
- run every safety check, and **refuse to publish if the PDF came out wrong**
- tell you in plain English what the school moved, added, or removed
- rebuild and publish the calendar
- print your link

If you'd rather point it at a specific file:

```
./update-calendar.sh ~/Downloads/whatever-they-called-it.pdf
```

---

## When it stops and refuses

Sometimes the school reformats the PDF — different columns, merged cells, a new
header. When that happens the program that reads it can get confused and quietly
produce a calendar with days missing. That's much worse than an error, because
it *looks* fine.

So there's a set of checks between reading and publishing. If any fail, you'll
see **"STOPPED. Nothing was published."** followed by what went wrong, in plain
words — things like "51 weekdays came out with no classes at all."

**When that happens: your live calendar is untouched and still correct.** Nothing
was broken. It puts the old schedule back and stops.

Send the PDF to Finn. It means the reading program needs a small fix for the new
layout, and that's a code change, not something the script can work around. Don't
try to force it past — a silently wrong calendar is the one outcome worth
avoiding.

---

## What happens to your checkmarks

Your ticks, your renames, and the to-dos you typed live **in your browser, on
whichever device you're using.** Updating the schedule never erases them.

But be aware:

- **A class the school moved comes back unticked.** Your ticks are saved against
  a date, not against the class. If Anatomy #3 moves from Oct 10 to Oct 17, the
  study tasks appear correctly on Oct 17 — just not checked off.
- **To-dos you typed stay on the date you wrote them.** They don't follow
  anything.
- **If the school renames a class**, any edit you made to it comes loose. The
  script lists these under "removed" — worth reading that bit each time.
- **Your phone and laptop keep separate checkmarks.** They can't be merged. Pick
  one device for ticking things off.

Your *study system itself* — Chat Recall, the Anki line, the before/during/after
boxes, the exam countdown — rebuilds itself around the new dates automatically.
That part you never have to touch.

---

## One thing to do eventually

Right now you'd be the only person with this. **If your laptop dies, it's gone.**

Copy the folder to an external drive or Google Drive every so often. It's 2MB.
Or ask Finn to help you put it on GitHub — that's a proper off-site backup and
it's free. Not urgent, but don't leave it forever.

---

## If something goes wrong

- **"command not found: python3"** → install Python from python.org
- **"No module named fitz"** → Step 2 didn't take. Run it again and read the output.
- **"command not found: vercel"** → Step 3 didn't take, or you need to close and
  reopen Terminal.
- **"no such file or directory: ./update-calendar.sh"** → you're not in the right
  folder. Do the `cd` + drag-and-drop trick again.
- **Publishing fails but the build worked** → everything is saved. Fix the
  publishing problem and just run the script again; it won't re-do the reading.
