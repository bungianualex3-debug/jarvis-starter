---
description: Check the whole assistant — memory, face and voice — repair what's safe, report the rest.
---

# Check and repair

Two different things can go wrong, and they fail in opposite ways.

**The memory is plain files, so it doesn't crash — it drifts.** An index stops matching its folder. A note gets renamed and the links pointing at it break. A folder appears with no index note. Nothing looks broken, which is exactly the problem: a wrong map is worse than no map, because it gets trusted.

**The machinery — the face and the voice — does crash**, and usually leaves a trail. It also has a habit of half-working: the face comes up but the voice doesn't, the button starts one but not the other.

This command checks both and fixes what's safe to fix.

## How to work

Go in this order and report as you go. Don't dump everything at the end.

### 1 — The load-bearing files

Check each exists and isn't empty:

- the boot file (`CLAUDE.md`)
- the vault index
- the daily note template
- the active-work list

**If one is missing:** say so immediately and clearly — this is the only genuinely broken state. Offer to rebuild it from what the rest of the vault says, and show what you'd write before writing it.

### 2 — Every folder has an index note

Each folder should hold a note named exactly after it. List any folder missing one.

**Safe to fix automatically:** create the missing index note by reading the folder's actual contents and describing each file in one line.

### 3 — Every index matches its folder

For each index note, compare what it lists against what's actually in the folder. Two kinds of drift:

- **Listed but gone** — the file was deleted or renamed. Flag it; don't guess where it went.
- **Present but unlisted** — a note exists that the map doesn't show. No future session will find it.

**Safe to fix automatically:** add the missing entries, reading each note to write an honest one-line description.
**Not safe:** removing an entry for a file that's gone. It might have been renamed rather than deleted, and deleting the last reference to it destroys the trail. Report those and let them decide.

### 4 — Broken links

Find `[[links]]` pointing at notes that don't exist. Report them grouped by which file they're in.

**Don't auto-fix these.** A broken link usually means a rename happened outside the app, and guessing the new target can silently point a link at the wrong note. Show the broken link, show the closest existing note name, and ask.

### 5 — Frontmatter

Notes missing frontmatter, or carrying a field value outside what the vault index says is valid.

**Safe to fix automatically:** add missing frontmatter, inferring values from the note's content and its folder.

### 6 — Contradictions

The slowest check and the most valuable. Look for places where two notes state different things about the same subject — most often a status recorded as open in one file and done in another.

**Never auto-fix.** You can't know which one is current. Show both, with dates, and ask.

### 7 — The machinery, if they have it

Skip anything they never installed, and say you skipped it rather than reporting it as healthy.

**The face** — `interface.html` present, and the launcher files present alongside it. Open `interface.html` and check the config block still has a name and an accent colour.

**The voice** — `voice/` with its own `.venv`; `voice/config.json` valid JSON; and the voice model it names **actually exists and is over a megabyte**. This last one is the most common real fault: a half-finished download leaves a small file with the right name, and the assistant then fails much later in a way that looks like something else entirely.

**Is the vault self-contained?** If `piper_model` is an absolute path, or points anywhere outside the vault, this vault only works on this computer — copying it elsewhere leaves it mute. Say so plainly. It may well have been a deliberate choice; the fault is only if nothing records it.

**The buttons** — both launcher files should contain their voice lines. A Start button that brings up the face but not the voice is the classic half-working state, and people assume the voice is broken when it was simply never wired in.

**Safe to fix automatically:** adding a missing launcher line, re-downloading a voice model that's obviously truncated, writing a missing entry into the vault index.
**Not safe:** editing any of the Python. Say what looks wrong and let a human decide.

### 8 — What the medic already reported

If `voice/medic-report.txt` or `voice/medic.log` exist, read them. That's the assistant's own record of faults it hit and couldn't fix safely by itself — **written precisely so somebody would come and look, and nobody ever does.**

Summarise what's in there in plain language: what failed, how often, and what it suggested. Ignore anything already resolved. If the log is empty or only shows faults it recovered from on its own, say that in one line — it's good news and worth hearing.

## The line you don't cross

**Fix what's additive and reversible. Report everything else. Never edit the assistant's own code unattended.**

Creating a missing index note, adding an absent entry, filling in frontmatter, restarting something, re-downloading a broken model file — none of those can destroy anything, and none of them change how the thing works. Deleting entries, repointing links, resolving a contradiction, rewriting anyone's words, changing the Python: those can, and they need a human who knows which version was right.

**Why the line sits exactly there.** An assistant that rewrites its own running code, on a machine where nobody can read code, turns a small bug into a dead install with no way back. Diagnosing costs a minute of someone's attention. Guessing wrong costs them the whole thing. So: diagnose, explain, propose — and let a person say yes.

If a check fails in a way you don't recognise, say so plainly and stop. **An assistant that quietly "repairs" itself into a wrong state has done more damage than the drift ever did** — and unlike the drift, nobody will notice.

## Finish

Report in three groups: **fixed** (with what changed), **needs your call** (with the options), and **clean**. If nothing was wrong, say that in one line — don't pad it.

Then tell them, once and without nagging, that running this now and then is the whole maintenance story. There is nothing else to keep up.
