---
description: Edit a vertical video — cut the pauses, add effects, captions and sound — from one raw take.
---

# Edit a video

The person hands you one raw take, usually filmed on a phone, and you turn it into a finished vertical video: pauses and retakes gone, effects on top, captions synced to the voice, a sound for every effect, loudness right for the platform. No editing software. You write the edit as code with **Remotion** (React for video) and render it.

This is the setup that made the Jarvis launch video: 20 effects, one take, no human editor. Everything it used is in `.claude/assets/editor/`:

- `template/`: a Remotion project. `src/Launch.tsx` is **the composition from that video, as a reference**: 20 working effects, a camera, a colour grade, captions and an ending. It is not plug-and-play. You build *their* composition from it.
- `tools/`: the pipeline, one script per step. Each script's header says what it does, why, and what it needs.

## Before anything

1. **Ask what the video is.** Ask what they say in it, where it will be posted, and the feeling they want (funny, clean, cinematic). Then ask for the file path. Ask these one at a time.
2. **Check the machine.** Run `node -v` (18+), `ffmpeg -version`, and `python --version` (3.10+). Install whatever is missing, and say what you are installing and why.
3. **Make a project folder next to their video, not inside this repo.** Copy `template/` into it, then run `npm install`. Copy `tools/` in beside it, then run `pip install faster-whisper numpy`. Add `torch` only if they want cut-out effects; see step 4.
4. **Say what it costs, once.** Remotion is free for individuals and for companies of up to 3 people; bigger companies need a licence (remotion.dev/license). Everything else here is free and runs on their machine.

## The steps

Do them in order. Show the result of each before you go on. A wrong cut found at the end costs the whole render.

1. **Transcribe.** Run `python tools/transcribe.py <video> --lang <code>`. Read `speech.json` all the way through. Raw takes are full of restarts and "wait, again". Find the **last clean version** of every line. That is the version you keep.
2. **Decide the cut.** Write `cuts.json` as name, start and end in source seconds for every piece you keep. Leave ~0.45 s before a word and ~0.75 s after it, so it doesn't sound clipped. Show them the list as plain sentences and get an ok. Then run `python tools/cut.py <video> cuts.json` to make `public/edit/body.mp4`, `body.wav` and `timeline.json`.
   - **Anything on screen that should not be readable** gets a light blur through `--vf`: another monitor, a face, a notification. Ask if you are unsure.
   - **Phone footage is often mirrored** (front camera) and sometimes rotated. Look at a frame before you crop.
3. **Measure the timings.** Run `python tools/onsets.py public/edit/body.wav <rough times>` for every word an effect or caption hangs on. Captions placed from Whisper's word times alone land a few frames late, and people notice. Write `public/edit/timing.json` in the shape `Launch.tsx` documents at its top.
4. **Cut-out (optional).** Run `python tools/matte.py public/edit/body.mp4 public/edit`, then `python tools/head_track.py public/edit/matte.mp4 public/edit/head.json`. You need this for anything that puts the person on their own layer. Without a GPU it is slow, so warn them.
5. **Build their composition.** Start from `Launch.tsx`.
   - Keep the effects they want, rename them to what they actually say, and delete the rest along with any data they read.
   - Every effect is one component that runs only between its own word and the next effect's word. That keeps them easy to move.
   - Anything that needs data they don't have, drop it rather than fake it. The examples are the hologram (`holo.webm`, `jenv.json`, `jsegs.json`), the empty-room plate and the portal video.
6. **Check stills before the render.** Run `node src/stills.mjs <frames>` with a frame from the middle of every effect, plus the joins between effects, and **look at every still yourself**. You are checking for:
   - text that runs off the screen
   - an effect covering the face
   - a frame or two of the plain take flashing between effects
   - captions that are not on the word

   Fix, then check again. A still takes seconds; a full render takes tens of minutes.
7. **Sound.** Run `python tools/sfx.py public/edit/timing.json public/edit/sfx.wav`. Every effect gets a sound, and with no music under it, the sounds are what make each effect land. Keep the voice clearly above them: measure it, don't guess.
8. **Render.** Run `npx remotion render src/index.ts Launch out/video.mp4 --concurrency=3 --timeout=300000`. Run it in the background and tell them roughly how long it will take.
   - **If you stop a render, check that it really stopped.** The browser processes it starts can keep running and eat the machine.
   - Once the render is done, make a contact sheet at 2 frames per second and **look at all of it** before you call it finished.
9. **Finish.** Run `python tools/post.py out/video.mp4 <final>.mp4`, adding `--cut A-B` if a pause only shows up once the whole video plays. It trims and sets loudness to -14 LUFS. Put the final file in their folder and open it for them.

## How to work with them

- **They judge the result, you judge the details.** Show the video. Don't describe it. Their notes will be things like "it feels delayed" or "this comes in too early". Turn each one into a measurement, fix that, and show it again.
- **You can't hear.** You can measure levels, but whether a sound is nice is their call. Say so.
- **Re-render only what changed.** For a change confined to one effect, render just those frames with `--frames=A-B`, lay them over the full render with `ffmpeg overlay=enable='between(n,A,B)'`, and run `post.py` again.
- **Their face, their voice and anything they filmed stay in their project folder.** They never go into this repo, and they are never uploaded anywhere unless they ask.
