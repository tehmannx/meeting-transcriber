# Meeting Transcriber

A tiny local app: pick a screen recording (`.mov`, `.mp4`, `.m4a`, ...) and get
a transcript back. Runs **fully local and free** using
[faster-whisper](https://github.com/SYSTRAN/faster-whisper) (an optimized,
offline version of OpenAI's Whisper). It only uses the internet once — to
download the model on the first run.

## Setup (one time)

You need Python 3.9+.

```bash
pip install faster-whisper
```

On macOS, if you get a Tkinter error when launching, install Tk for your Python:

```bash
brew install python-tk
```

(You do **not** need a separate ffmpeg install — faster-whisper bundles its own
decoder and reads `.mov` directly.)

## Run

```bash
python transcribe_app.py
```

Then: click **Select recording…**, pick your `.mov`, click **Transcribe**.
The transcript shows up in the window, is auto-saved as
`<your-file>_transcript.txt` next to the original, and there are **Copy** /
**Save .txt** buttons.

## Models (accuracy vs. speed)

| Model      | Speed      | Accuracy  | Notes                          |
|------------|------------|-----------|--------------------------------|
| tiny/base  | fastest    | okay      | quick drafts                   |
| **small**  | fast       | good      | default — good for most meetings |
| medium     | slower     | better    |                                |
| large-v3   | slowest    | best      | best for messy audio / accents |

The first time you pick a model it downloads (a few hundred MB to ~3 GB). After
that it's cached and works offline.

## If a file won't decode

Fall back to your existing command, then select the `.mp3`:

```bash
ffmpeg -i "your-video.mov" -vn -acodec mp3 "meeting-audio.mp3"
```

## Optional upgrade: who said what (speaker labels)

Plain transcripts are usually enough for analysis. If you later want speaker
diarization ("Speaker 1 / Speaker 2"), that's possible with
`pyannote.audio` + a free Hugging Face token — ask and I'll wire it in.
