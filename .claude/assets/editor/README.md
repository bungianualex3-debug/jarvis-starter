# The editor

What `/jarvis-edit` works from. You don't need to read this to use it. Run `claude` in the repo and type `/jarvis-edit`.

- `template/` is a Remotion project. `src/Launch.tsx` is the composition behind the Jarvis launch video ("20 effects, one take"), with its 20 effects, camera, grade, captions and ending. It's kept as a reference that your assistant builds your video from. It won't render as is, because it expects media and timing measured from a real take.
- `tools/` is the pipeline, in order:
  1. `transcribe.py` turns the video into `speech.json`, with words and times. It splits on silences first, so Whisper doesn't loop on long pauses.
  2. `cut.py` turns `cuts.json` into `body.mp4`, `body.wav` and `timeline.json`. Cuts are frame-exact, and the audio is joined in memory so it stays in sync.
  3. `onsets.py` gives each word's real start, measured on loudness.
  4. `matte.py` cuts the person out with no green screen (RobustVideoMatting). Optional.
  5. `head_track.py` gives the head position for every frame, read from the matte. Optional.
  6. `sfx.py` synthesises a sound for every effect, so there are no samples to license.
  7. `post.py` removes late trims and normalises loudness to -14 LUFS.

Remotion is free for individuals and for companies of up to 3 people. Larger companies need a licence: remotion.dev/license.
