---
description: Build my assistant its panel — a figure that listens, thinks and speaks, and a screen I can actually work in.
---

# Give it a face

Your memory exists. Now you get a body — and a place to work.

The first version of this was a face and nothing else. That is fine on a spare monitor and useless to someone with one screen, because all they can do is talk at it. So it is a **panel** now: the figure on the left, a stage in the middle where you show what you just made, the conversation at the bottom, and three quiet words on the right edge that open what's waiting on them, what you remembered today, and a box for a quick note.

Four states still have to read across a room: **idle**, **listening**, **thinking**, **speaking**.

Do not explain the plan. Do not summarise the stages back to them. Start.

---

## Stage 0 — You should already have a memory

Check for `CLAUDE.md` **in the current folder**.

If there isn't one, this isn't a vault. Say so in one line and tell them to run `/jarvis` first — the interface is built around the assistant they already made, and without that file there's nothing to build it around. Then stop.

If there is one, **read it, and read `VAULT-INDEX.md` too.**

---

## Stage 1 — Don't ask what you can already read

From those two files, take:

- **the assistant's name** — goes on screen
- **the language** — every word you write and say from here is in it
- **their name and how they talk** — the interface should match the person, not a template

**Never ask for any of these.** You have them. Asking a person to retype something they already told you is the clearest possible signal that the memory doesn't work — and this command is partly a demonstration that it does. Open by telling them what you already know: you're building the face for *«their assistant's name»*, in *«their language»*.

---

## Stage 2 — Three questions, one at a time

Ask one, stop, wait. Never stack two. Never show the list up front.

1. **The look.** Two ways to go, and say which one you recommend:
   - **Ours — recommended.** A white android stands on the left, full height, and moves differently when it waits, thinks and speaks. It is the look this project is known by, it is already built and tested, and most people should take it.
   - **Their own.** A shape instead of a figure: **a ring** that swells and ripples with the voice, **an orb** that breathes and brightens, **a bar** that spikes as it speaks — or **they describe something else and you build it.**

2. **The colour.** One colour, and everything on screen is built from it — the glow, the lines, the captions. *(A hex code, or just a name — "cold blue", "amber". Convert it to hex yourself.)* **If they took the android, recommend keeping the red it ships with** and say why in one line: the figure glows red in its clips, and a different accent next to it looks like two designs on one screen. It is still their call.

3. **Where it's going to live.** A spare monitor left on all day, a second window they alt-tab to, or a phone or tablet propped up. This decides how big the shape is and whether the clock earns its place — a screen that's always on wants a clock, a window they open for a minute doesn't.

That's all. Tell them you're building it, and build it.

---

## Stage 3 — Build it

### The file

Copy `.claude/assets/panel-base.html` into the vault root as `interface.html`. **Copy it, don't rewrite it** — it's a tested file and regenerating it from scratch is how you end up with a black screen and nobody who can debug it.

**If they took the android, also copy the whole `.claude/assets/android/` folder into the vault root as `android/`** — three small clips, about a megabyte each. Without them the panel falls back to the ring on its own, so a forgotten copy looks like a different design rather than like a fault. Check the folder is there.

**Copy `NOTICE.md` along with the clips, and say what it means in one line:** the android is the project's own character — theirs to use on their own assistant, not to put on anything else they make or sell. The rest of the vault is theirs without conditions; this is the one thing in it that isn't.

Then edit **only the `CONFIG` block at the top** — these lines, leave the rest of it as it is:

```js
  name:      "…",        // the assistant's name from CLAUDE.md
  owner:     "…",        // their name, for the greeting
  accent:    "#…",       // their colour, as hex
  presence:  "android",  // or "ring" | "orb" | "bars" if they chose a shape
```

**Translate the whole `LABELS` block into their language.** It is longer than it used to be — the names of the cards, the four quick buttons, the greeting — and every line of it is text a person reads. Set `locale` to theirs (`"ro-RO"`, `"de-DE"`…) so the date comes out right. The `demoPanel` part is only what the panel plays before anything is connected; translate it too, it is the first thing they will see.

Leave `showCaptions` off. It prints the spoken words under the figure, and the conversation at the bottom already shows every word that is said — the same sentence in two places on one screen reads as a glitch. Turn it on only if they ask for it.

**Don't touch anything below those two blocks.** If they want a different shape, that's the next section, not an edit to the engine.

### Tell the panel where things are — `panel.json`

The panel shows what is already in the vault: what's waiting on them, what's open, what you wrote down today. The vault is in their language, so nothing can guess its file names. **You know them — you are standing in it.** Write `panel.json` in the vault root:

```json
{
  "active_work": "<the exact file name of their active-work note>",
  "open_heading": "<the heading of its in-progress section, as written>",
  "blocked_heading": "<the heading of its blocked-on-them section, as written>",
  "daily_folder": "<the daily notes folder, as named>",
  "working": "<'Working', in their language>",
  "activity": {
    "Read": "…", "Write": "…", "Edit": "…", "Grep": "…", "Glob": "…",
    "Bash": "…", "WebSearch": "…", "WebFetch": "…", "Task": "…"
  }
}
```

**Open the active-work note and copy the two headings from it; list the vault and copy the folder name.** Do not type them from memory of what you intended to call them — one wrong letter and that card stays empty with no error, which is the kind of fault nobody finds. The `activity` lines are what the panel says while you use each tool ("Reading a note", "Searching the web"): short, plain, in their language.

### If they described their own shape

Write it as a **separate file, `presence.js`, in the vault root**, next to `interface.html`. Don't edit the base file.

**Then add the one line that loads it**, immediately before `</body>` in `interface.html`, where the comment tells you to:

```html
<script src="presence.js"></script>
```

That line is not in the base file on purpose — a script tag pointing at a file nobody wrote throws a 404 into the console on every load, and a stranger opening the console to a red error that isn't a problem learns to ignore the ones that are. **Only add it if you actually wrote the file.** If they took a built-in shape, leave it out.

```js
window.PRESENCE = function (ctx, s) {
  // s.cx, s.cy    centre of the screen, in pixels
  // s.R           base radius in pixels
  // s.t           seconds since the page loaded
  // s.level       0..1, how loud it is right now
  // s.wave        64 floats, roughly -1..1
  // s.w           { idle, listening, thinking, speaking } — eased 0..1 weights
  // s.rgba(a)     colour from their accent, at alpha a
};
```

Three things to get right, and they're the difference between something that looks alive and something that looks like a screensaver:

- **Read `s.w`, not the state name.** The weights ease between states over about half a second. Anything that snaps in one frame looks broken.
- **Use the envelope, not raw samples.** Neighbouring waveform values flip sign, so plotting them directly gives you a spiked star. Take `Math.abs()` and smooth it around the shape first — the base file's `buildEnvelope` shows exactly this.
- **All four states must be visibly different with the sound off.** If idle and thinking look the same, the interface has failed at its only job.

If their idea genuinely needs an image or a video, **say what's needed rather than faking it**, and set the built-in shape in the meantime so they have something working today.

### The buttons — do not skip this

A person who has to open a terminal to look at their own assistant will stop looking at it. **This is the step that decides whether the thing gets used or admired once.** Build it even if they didn't ask.

**On Windows.** Copy both files from `.claude/assets/launcher-windows/` into the vault root, renaming them in their language — `Start.bat` → e.g. `Porneste Jarvis.bat`, `Stop.bat` → `Opreste Jarvis.bat`. **Copy them; they're tested.** They find everything relative to themselves, so there are no paths to substitute and moving the vault doesn't break them.

Translate only the `echo` lines a person actually sees. Leave the logic alone.

What they do, so you can explain it accurately:
- **Start** opens the interface fullscreen in Chrome, or Edge if there's no Chrome — Edge is on every Windows machine, so this works for someone who has never installed anything. If neither is found it falls back to the default browser and says to press F11.
- It uses a **throwaway browser profile** named after the vault, so no tabs, extensions or restore bubbles ride along.
- **Stop** closes only the window Start opened, found by that same profile. **Their normal browser windows are never touched** — say this out loud, because it's the thing a person is right to worry about.

**The desktop shortcuts are not made here.** They happen in Stage 4, after they've seen the buttons work — see *Ask about the desktop shortcuts* below. Don't do it early and don't skip it.

**On macOS.** Copy both files from `.claude/assets/launcher-mac/` into the vault root, renamed in their language the same way (`Start.command` → e.g. `Porneste Jarvis.command`). Then, on the two copies, run `chmod +x` and `xattr -d com.apple.quarantine` (ignore the error if there is no such attribute) — a file that arrived in a downloaded ZIP is otherwise refused on double-click as "from an unidentified developer". Translate only the `echo` lines. They do the same job as the Windows pair: Chrome, then Edge, then Brave, in a throwaway profile, fullscreen; with none of those installed it opens the default browser and says to press Ctrl+Cmd+F. Double-clicking a `.command` file opens a Terminal window alongside — that is normal, say so before they see it.

**Tell them plainly that the Windows launchers are the long-tested pair and the Mac pair is newer**, so if it misbehaves it's the launcher, not their vault.

**On Linux**, write the equivalent yourself — a `.desktop` entry — using the browser's `--kiosk` and `--user-data-dir` flags the same way, and say it is untested.

**Leave the voice hooks alone.** Both files have a marked section near the bottom where the voice command will add its start and stop lines later. That's how one button ends up starting everything.

### Say what it can and can't do yet

Be straight about this, in one short passage, before they see it:

- It runs **on its own right now**, in **demo mode**, and says so under the name in the corner. Everything they see on it at this point — the goal, the lists, what's on the stage — is **an invented example**, there so every part of the panel has something to show. None of it is theirs. Say that in those words, or they will wonder where the supplier and the offer email came from.
- It goes live with `/jarvis-voice`. That is the step that starts the small local server the panel reads from; from then on the cards show **their** vault and typing into it reaches you.
- **This is a viewer, not a microphone.** It doesn't hear anything and doesn't have a voice. That comes with the next command.

---

## Stage 4 — Land it

**Have them open it with the Start shortcut**, not by double-clicking the HTML. The button is the thing they'll use every day, so the first time they see the interface should be the same way they'll see it every time after. It comes up fullscreen on its own.

Then have them **close it with Stop** and open it again. Thirty seconds, and it's the difference between knowing they have a button and trusting it.

Wait until they say they can see it. If it's blank, the first thing to check is whether a `presence.js` you wrote is throwing — the console will say so, and the built-in shape takes over rather than leaving a black screen.

Then, and only then:

- **Walk them across the screen once.** The line at the top is today's one goal. The three words on the right open as drawers — have them click each, and press Esc. The quick buttons appear when they move to the typing box at the bottom; have them press one and watch the stage turn the page. Thirty seconds, and they know where everything is.
- **Show them the config block.** Open `interface.html`, point at the top of the script, and tell them that's the whole customisation surface: change a value, save, reload the browser. Have them **change the colour and reload right now**, while you're there. A person who has changed one value once will change more; a person who has only been told they could, won't.
- **Point at the presence function** further down. That's where the shape is drawn, it's the part worth rewriting, and a broken experiment falls back to the built-in shape rather than a black screen. They can ask you to change it any time — you'll have this file in context.
- **Say where it sits in the whole thing:** memory first, face second, voice third. This one is the part they can see.

### Ask about the desktop shortcuts

Now that they've used the buttons, ask — as a real question, and wait for the answer:

> Want these two as shortcuts on your desktop, so you never open a folder for this again?

If yes, on macOS: make two aliases on the desktop with `ln -s "<vault>/<Start file>.command" ~/Desktop/` and the same for Stop. On Windows:

```
powershell -NoProfile -ExecutionPolicy Bypass -File ".claude/assets/launcher-windows/make-shortcuts.ps1" -VaultPath "<vault>" -Name "<assistant>"
```

Then tell them to look at their desktop and confirm the two shortcuts are there. **Not confirmed is not done.**

Ask rather than assume, because this is the **one thing in the whole project that writes outside their folder**. Creating something on somebody's desktop uninvited is the kind of small liberty that makes people distrust everything else you did.

If they say no, say in one line where the two files are inside the vault, so they can make shortcuts themselves later.

### Write it into their vault

You just changed their system, and their own rules say a change that a future session needs to know gets recorded. Follow them — this is the first time those rules apply to something *you* did, and skipping it teaches them the rules are decoration.

Add to `VAULT-INDEX.md`: one line saying `interface.html` exists, what it's for, that the config block at the top is where it's changed, and that it runs in demo mode until the voice is installed. Say that `panel.json` tells it which note and which headings to read — so if the active-work note or the daily folder is ever renamed, that file changes with it. Mention the `android/` folder if they took it, the two launcher files, and that the desktop shortcuts point at them. Add a line to the folder map if the files need one. Keep it to a couple of sentences — it's a map entry, not a manual.

Don't create a note for this. One home per fact, and the index is the home.

Then stop. Don't offer a list of next steps.

---

## Before you say you're done

A working interface on screen feels like the finish line. It isn't, and this is the exact point where these last steps get quietly dropped — **they have been dropped in real runs.** Check all six. If any is false, go and do it now.

1. `interface.html` exists in the vault root and they have **seen it running**.
2. The two launcher files exist in the vault root, named in their language, and they have **opened it with Start and closed it with Stop at least once**.
3. You **asked** about desktop shortcuts and either made them and had them confirmed, or were told no.
4. `VAULT-INDEX.md` mentions the interface and the launchers.
5. `panel.json` exists, and **each name in it matches a real file, folder or heading — checked by opening them now**, not from memory.
6. If they took the android, `android/` holds three clips and the figure is on screen, not the ring.

Number 3 and number 4 are the two that go missing, because by then the screen already looks finished. A person left without a button goes back to not opening it, and an index that doesn't know the interface exists is the start of exactly the drift `/jarvis-check` was written to catch.

---

## Rules while you do all this

- **Copy the base file, don't regenerate it.** Every canvas bug you invent is one they can't fix.
- **One accent colour, black background.** Don't add a second colour because a state "needs" one — states are told apart by movement, not hue. This is the rule that keeps it looking designed.
- **Nothing in a box.** The first draft of this panel put every list in its own framed card and it read as crowded at a glance. The lists now wait behind a word and a number until they are reached for. If they ask for something new on screen, give it a place on the rail or on the stage — don't add a frame.
- **Everything in their language**, including the state labels.
- **Don't touch anything outside this folder**, and if `interface.html` already exists, stop and ask before overwriting.
