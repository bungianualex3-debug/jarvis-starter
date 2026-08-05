---
description: Design and build my assistant a face — a live interface that reacts when it listens, thinks and speaks.
---

# Give it a face

Your memory exists. Now you get a body — a screen that shows you're awake.

Four states, and it has to read across a room: **idle**, **listening**, **thinking**, **speaking**. That's the whole job. Everything else on screen is decoration and should be treated that way.

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

## Stage 2 — Four questions, one at a time

Ask one, stop, wait. Never stack two. Never show the list up front.

1. **The colour.** One colour, and everything on screen is built from it — the glow, the outline, the captions. What is it? *(A hex code, or just a name — "cold blue", "amber", "green like an old terminal". Convert it to hex yourself.)*

2. **The shape in the middle.** Offer three, described by behaviour rather than name:
   - **a ring** that swells and ripples with the voice — the default, and the one that reads best from across a room
   - **an orb** — a soft ball of light that breathes and brightens
   - **a bar** — a line of light that spikes as it speaks, flattest and most machine-like

   Then say plainly there's a fourth option: **describe something else and you'll build it.**

3. **Captions.** Should the words appear on screen as it speaks? Say what it's actually for before they answer: it's the difference between a decoration and something you can use with the sound off.

4. **Where it's going to live.** A spare monitor left on all day, a second window they alt-tab to, or a phone or tablet propped up. This decides how big the shape is and whether the clock earns its place — a screen that's always on wants a clock, a window they open for a minute doesn't.

That's all. Tell them you're building it, and build it.

---

## Stage 3 — Build it

### The file

Copy `.claude/assets/interface-base.html` into the vault root as `interface.html`. **Copy it, don't rewrite it** — it's a tested file and regenerating it from scratch is how you end up with a black screen and nobody who can debug it.

Then edit **only the `CONFIG` block at the top**:

```js
const CONFIG = {
  name:      "…",     // the assistant's name from CLAUDE.md
  accent:    "#…",    // their colour, as hex
  presence:  "ring",  // "ring" | "orb" | "bars"
  size:      0.18,    // bigger for an always-on monitor, smaller for a window
  showClock: true,
  showState: true,
  showCaptions: true,
  particles: 90,
  source:    "/state",
  pollMs:    100
};
```

Also translate the `LABELS` block into their language — it's four words and the state line is the only text that's always on screen.

**Don't touch anything below the config block.** If they want a different shape, that's the next section, not an edit to the engine.

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

**On macOS or Linux**, write the equivalent yourself — a `.command` file they can double-click on macOS, a `.desktop` entry on Linux — using the browser's `--kiosk` and `--user-data-dir` flags the same way. **Tell them plainly that the Windows launchers are the tested pair and theirs is newer**, so if it misbehaves it's the launcher, not their vault.

**Leave the voice hooks alone.** Both files have a marked section near the bottom where the voice command will add its start and stop lines later. That's how one button ends up starting everything.

### Say what it can and can't do yet

Be straight about this, in one short passage, before they see it:

- It runs **on its own right now** — open it and it cycles through the four states so you can see them. The corner says **demo mode** so it's never pretending.
- It goes live when there's something feeding it. It polls `CONFIG.source` for JSON shaped `{ state, level, wave, caption: { text, seq, dur } }`. Anything that serves that — any language — drives it. Nothing to rewrite.
- **This is a viewer, not a microphone.** It doesn't hear anything and doesn't have a voice. That comes later.

---

## Stage 4 — Land it

**Have them open it with the Start shortcut**, not by double-clicking the HTML. The button is the thing they'll use every day, so the first time they see the interface should be the same way they'll see it every time after. It comes up fullscreen on its own.

Then have them **close it with Stop** and open it again. Thirty seconds, and it's the difference between knowing they have a button and trusting it.

Wait until they say they can see it. If it's blank, the first thing to check is whether a `presence.js` you wrote is throwing — the console will say so, and the built-in shape takes over rather than leaving a black screen.

Then, and only then:

- **Show them the config block.** Open `interface.html`, point at the top twelve lines, and tell them that's the whole customisation surface: change a value, save, reload the browser. Have them **change the colour and reload right now**, while you're there. A person who has changed one value once will change more; a person who has only been told they could, won't.
- **Point at the presence function** further down. That's where the shape is drawn, it's the part worth rewriting, and a broken experiment falls back to the built-in shape rather than a black screen. They can ask you to change it any time — you'll have this file in context.
- **Say where it sits in the whole thing:** memory first, face second, voice third. This one is the part they can see.

### Ask about the desktop shortcuts

Now that they've used the buttons, ask — as a real question, and wait for the answer:

> Want these two as shortcuts on your desktop, so you never open a folder for this again?

If yes:

```
powershell -NoProfile -ExecutionPolicy Bypass -File ".claude/assets/launcher-windows/make-shortcuts.ps1" -VaultPath "<vault>" -Name "<assistant>"
```

Then tell them to look at their desktop and confirm the two shortcuts are there. **Not confirmed is not done.**

Ask rather than assume, because this is the **one thing in the whole project that writes outside their folder**. Creating something on somebody's desktop uninvited is the kind of small liberty that makes people distrust everything else you did.

If they say no, say in one line where the two files are inside the vault, so they can make shortcuts themselves later.

### Write it into their vault

You just changed their system, and their own rules say a change that a future session needs to know gets recorded. Follow them — this is the first time those rules apply to something *you* did, and skipping it teaches them the rules are decoration.

Add to `VAULT-INDEX.md`: one line saying `interface.html` exists, what it's for, that the config block at the top is where it's changed, and that it runs in demo mode until something feeds it. Mention the two launcher files and that the desktop shortcuts point at them. Add a line to the folder map if the files need one. Keep it to a couple of sentences — it's a map entry, not a manual.

Don't create a note for this. One home per fact, and the index is the home.

Then stop. Don't offer a list of next steps.

---

## Before you say you're done

A working interface on screen feels like the finish line. It isn't, and this is the exact point where these last steps get quietly dropped — **they have been dropped in real runs.** Check all four. If any is false, go and do it now.

1. `interface.html` exists in the vault root and they have **seen it running**.
2. The two launcher files exist in the vault root, named in their language, and they have **opened it with Start and closed it with Stop at least once**.
3. You **asked** about desktop shortcuts and either made them and had them confirmed, or were told no.
4. `VAULT-INDEX.md` mentions the interface and the launchers.

Number 3 and number 4 are the two that go missing, because by then the screen already looks finished. A person left without a button goes back to not opening it, and an index that doesn't know the interface exists is the start of exactly the drift `/jarvis-check` was written to catch.

---

## Rules while you do all this

- **Copy the base file, don't regenerate it.** Every canvas bug you invent is one they can't fix.
- **One accent colour, black background.** Don't add a second colour because a state "needs" one — states are told apart by movement, not hue. This is the rule that keeps it looking designed.
- **Don't add panels.** No stat readouts, no logs, no menus, however tempting. The value here is that it's calm enough to leave on a screen all day.
- **Everything in their language**, including the state labels.
- **Don't touch anything outside this folder**, and if `interface.html` already exists, stop and ask before overwriting.
