# Meeting Transcriber

A small, fully local macOS app that turns meeting recordings (`.mov`, `.mp4`, `.m4a`, `.mp3`, `.wav`, `.mkv`) into text transcripts.

- Runs offline on your Mac using [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2 port of OpenAI Whisper).
- Launches from a double-clickable `MeetingTranscriber.app` and opens a browser UI at `http://localhost:7331`.
- Drag & drop a recording, pick model/language/timestamps, and the transcript streams in live.
- Transcript is auto-saved to `~/Desktop/<recording-name>_transcript.txt`, and can be copied or downloaded from the page.
- No accounts, API keys or cloud services. Internet is only needed to download a Whisper model the first time you use it.

---

## Contents

1. [How it works](#how-it-works)
2. [Repository layout](#repository-layout)
3. [Requirements](#requirements)
4. [Installation](#installation)
5. [Usage](#usage)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)
8. [Security & privacy notes](#security--privacy-notes)
9. [Uninstall](#uninstall)
10. [Project history](#project-history)

---

## How it works

```
MeetingTranscriber.app  (double-click)
  └─ Contents/MacOS/MeetingTranscriber   bash launcher
       ├─ finds the folder that contains the .app
       ├─ expects transcribe_app.py in that same folder
       └─ runs:  arch -arm64 /usr/bin/python3 transcribe_app.py

transcribe_app.py  (single file, standard library + faster-whisper)
  ├─ adds ~/Library/Python/3.9/lib/python/site-packages to sys.path
  ├─ imports faster_whisper (an import failure is shown in the UI, not a crash)
  ├─ kills any process already listening on port 7331 (stale instance)
  ├─ starts http.server on 127.0.0.1:7331 and opens the default browser
  ├─ GET  /            → embedded single-page HTML/CSS/JS UI
  └─ POST /transcribe  → multipart upload (parsed with the stdlib `cgi` module)
        ├─ writes the upload to a temp file
        ├─ loads WhisperModel(<model>, device="cpu", compute_type="int8")
        │    (cached per model for the lifetime of the process)
        ├─ model.transcribe(..., language=<lang or auto>, vad_filter=True)
        ├─ streams Server-Sent Events: status / progress / segment / done / error
        ├─ saves ~/Desktop/<name>_transcript.txt
        └─ deletes the temp file
```

Audio decoding is done by PyAV (installed with faster-whisper, bundles its own FFmpeg libraries), so no separate `ffmpeg` install is needed.

## Repository layout

```
meeting-transcriber/
├── MeetingTranscriber.app/          macOS app bundle (thin launcher only)
│   └── Contents/
│       ├── Info.plist               bundle metadata (id: com.local.meeting-transcriber)
│       ├── MacOS/MeetingTranscriber bash launcher (must stay executable)
│       └── Resources/
│           ├── AppIcon.icns         app icon (actually PNG data, see Troubleshooting)
│           └── AppIcon.png          same image, 512×512
├── transcribe_app.py                the application (server + embedded web UI)
├── requirements.txt                 direct Python dependency (faster-whisper)
├── requirements-lock.txt            exact known-good dependency versions
├── docs/
│   └── original-README.md           first README (describes an earlier Tkinter version)
├── .gitignore
└── README.md
```

The `.app` and `transcribe_app.py` must live **side by side in the same folder**. The repository is laid out that way, so the app also works straight from a clone.

## Requirements

### System

| Requirement | Why | Notes |
|---|---|---|
| macOS on Apple Silicon (arm64) | Launcher uses `arch -arm64` | Intel Macs: see Troubleshooting |
| Xcode Command Line Tools | Provides `/usr/bin/python3` (Python 3.9.6) used by the launcher | `xcode-select --install` |
| Python **3.9 – 3.12** | The `cgi` module used for uploads was removed in Python 3.13 | Original setup: CLT Python 3.9.6 |
| A web browser | The UI is a local web page | Default browser opens automatically |
| `lsof`, `kill`, `osascript`, `arch` | Used by launcher/script | Built into macOS |
| Internet (first use per model only) | Model download from Hugging Face | Afterwards fully offline |
| Disk space | Whisper models | small ≈ 0.5 GB, medium ≈ 1.5 GB, large-v3 ≈ 3 GB |
| RAM | The whole upload is held in memory, plus the model | Large recordings → see Troubleshooting |

### Python

Direct dependency: `faster-whisper==1.2.1` (see `requirements.txt`).

It pulls in, among others: `ctranslate2` (inference engine), `av` (PyAV, audio/video decoding), `onnxruntime` (Silero VAD used by `vad_filter=True`), `tokenizers`, `huggingface_hub` (model download), `numpy`, `tqdm`. The full pinned tree from the working machine is in `requirements-lock.txt`.

Everything else the script uses is in the Python standard library: `http.server`, `cgi`, `json`, `tempfile`, `threading`, `subprocess`, `webbrowser`, `pathlib`, `os`, `sys`.

## Installation

This reproduces the original setup: Apple's `/usr/bin/python3` with packages installed into the user site-packages, and the app placed in `/Applications`.

```bash
# 1. Command Line Tools (provides /usr/bin/python3). Skip if already installed.
xcode-select --install

# 2. Get the code
git clone https://github.com/tehmannx/meeting-transcriber.git
cd meeting-transcriber

# 3. Install Python dependencies for /usr/bin/python3 (user site-packages)
/usr/bin/python3 -m pip install --user --upgrade pip
/usr/bin/python3 -m pip install --user -r requirements-lock.txt
#    (or, for the newest compatible versions: -r requirements.txt)

# 4. Verify
/usr/bin/python3 -c "import faster_whisper, cgi; print('ok', faster_whisper.__version__)"

# 5. Install the app: copy BOTH items into the same folder
cp -R MeetingTranscriber.app /Applications/
cp transcribe_app.py /Applications/
chmod +x /Applications/MeetingTranscriber.app/Contents/MacOS/MeetingTranscriber
```

Then open **Meeting Transcriber** from Launchpad, Spotlight or `/Applications`.

Notes:

- pip may warn that some scripts are installed in `~/Library/Python/3.9/bin`, which is not on `PATH`. That is harmless; the app does not use them.
- You can skip step 5 and run the app directly from the clone: `open MeetingTranscriber.app`.

### Alternative: run without the .app (any Python 3.9–3.12)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python transcribe_app.py
```

## Usage

1. Launch **Meeting Transcriber** (or `python3 transcribe_app.py`). Your browser opens `http://localhost:7331`.
2. Drop a recording onto the drop zone, or click it to choose a file.
3. Choose:
   - **Model**: `tiny`, `base`, `small` (default, good balance), `medium`, `large-v3` (best for accents and noisy audio, slowest).
   - **Language**: Auto-detect, English, German, Spanish, French, Italian, Dutch, Portuguese.
   - **Timestamps**: `No` (one flowing paragraph) or `Yes` (one line per segment, prefixed `[m:ss]` / `[h:mm:ss]`).
4. Click **Transcribe**. Text streams in as it is recognised, with a progress bar.
5. When finished:
   - The transcript is saved to `~/Desktop/<recording-name>_transcript.txt` (the path is shown under the transcript).
   - **Copy** puts it on the clipboard. **Download .txt** saves another copy through the browser.

The first time each model is used it is downloaded (from 75 MB up to about 3 GB) and cached. Later runs work offline.

**Stopping the server:** quit *Meeting Transcriber* from the Dock, or run `lsof -ti :7331 | xargs kill`. Launching the app again automatically replaces a running instance.

## Configuration

There is no config file. Everything adjustable is either chosen in the UI or a constant in the code.

| What | Where | Default |
|---|---|---|
| Model, language, timestamps | Web UI dropdowns | `small`, auto-detect, no timestamps |
| HTTP port | `PORT` in `transcribe_app.py` | `7331` (bound to `127.0.0.1` only) |
| Inference device / precision | `WhisperModel(..., device="cpu", compute_type="int8")` in `transcribe_app.py` | CPU, int8 |
| Voice activity filter | `vad_filter=True` in `transcribe_app.py` | on (skips silence) |
| Output folder | `desktop = Path.home() / "Desktop"` in `transcribe_app.py` | `~/Desktop` |
| Python interpreter used by the .app | `PYTHON=` in `Contents/MacOS/MeetingTranscriber` | `/usr/bin/python3` |
| Extra package path | `PYTHONPATH` in the launcher and `USER_SITE` in the script | `~/Library/Python/3.9/lib/python/site-packages` |
| Model cache location | Environment variable `HF_HOME` | `~/.cache/huggingface` |
| Strict offline mode | Environment variable `HF_HUB_OFFLINE=1` | off |

Environment variables for the .app must be exported in the launcher script (apps started from Finder do not read your shell profile), for example add `export HF_HUB_OFFLINE=1` before the last line.

## Troubleshooting

**Run from Terminal to see errors.** Request logging is silenced, but errors and the startup message appear in the terminal:

```bash
/usr/bin/python3 /Applications/transcribe_app.py
```

| Symptom | Cause / fix |
|---|---|
| UI shows `Import failed: ModuleNotFoundError: No module named 'faster_whisper'` | Dependencies are not installed for the Python the launcher uses. Run `/usr/bin/python3 -m pip install --user -r requirements-lock.txt`. |
| Alert *"transcribe_app.py not found"* | The script must be in the same folder as `MeetingTranscriber.app` (e.g. both in `/Applications`). |
| `ModuleNotFoundError: No module named 'cgi'` | You are on Python 3.13+. Use Python 3.9–3.12 (the CLT `/usr/bin/python3` is 3.9). |
| App does nothing / `arch: Bad CPU type in executable` on an Intel Mac | Edit `Contents/MacOS/MeetingTranscriber` and change the last line to `"$PYTHON" "$SCRIPT"`. |
| *"MeetingTranscriber is damaged / can't be opened"* | The bundle is unsigned. Right-click → **Open** once, or `xattr -dr com.apple.quarantine /Applications/MeetingTranscriber.app`. |
| Nothing happens, no window | The app has no window of its own; it opens a browser tab. If the tab did not open, go to `http://localhost:7331`. |
| Another program using port 7331 gets killed | On startup the script force-kills (`kill -9`) whatever listens on 7331. Change `PORT` in the script if you need that port. |
| First transcription takes very long | The model is downloading (large-v3 ≈ 3 GB). Watch `~/.cache/huggingface/hub`. |
| Transcription is slow | It runs on CPU (int8). Use `small` or `base`. Expect slower than real time with `large-v3` on long meetings. |
| A file won't decode | Convert to audio first and select the result: `ffmpeg -i "recording.mov" -vn -acodec mp3 "meeting-audio.mp3"` (needs `brew install ffmpeg`). |
| Very large recordings crash or use a lot of memory | The whole upload is held in memory. Extract the audio track first with the `ffmpeg` command above (much smaller file). |
| No *"Saved:"* line / no file on Desktop | Python could not write to `~/Desktop`. Allow it in **System Settings → Privacy & Security → Files and Folders**, or use **Download .txt**. |
| A previous transcript on the Desktop was replaced | Output name is `<recording-name>_transcript.txt` and existing files are overwritten. Rename the recording or move old transcripts. |
| App icon is generic | `AppIcon.icns` contains PNG data. Generate a real icns: `sips -s format icns MeetingTranscriber.app/Contents/Resources/AppIcon.png --out MeetingTranscriber.app/Contents/Resources/AppIcon.icns`, then `touch MeetingTranscriber.app`. |
| pip fails to find wheels for a package | Upgrade pip first: `/usr/bin/python3 -m pip install --user --upgrade pip`. |

## Security & privacy notes

- Recordings and transcripts never leave the machine. The server listens on `127.0.0.1` only.
- Outbound network access: Hugging Face (model download, first use per model) and Google Fonts (the page loads the *Inter* font; it falls back to the system font when offline). No audio or text is sent.
- No credentials, tokens or API keys are used or stored.
- Known limitations of the original code, intentionally left unchanged:
  - `POST /transcribe` has no authentication or origin check, so any local process could submit a file while the app is running.
  - The uploaded file name is used without sanitising when building the output path. A crafted name containing `../` could write a `*_transcript.txt` file outside `~/Desktop`.
  - Startup force-kills any process listening on port 7331.
- Do not commit recordings or transcripts to this repository. `.gitignore` excludes common audio/video formats and `*_transcript.txt`.

## Uninstall

```bash
rm -rf /Applications/MeetingTranscriber.app /Applications/transcribe_app.py
/usr/bin/python3 -m pip uninstall faster-whisper ctranslate2 av onnxruntime tokenizers huggingface_hub
rm -rf ~/.cache/huggingface/hub/models--Systran--faster-whisper-*   # downloaded models
```

## Project history

The app was originally installed by hand:

- `/Applications/MeetingTranscriber.app`: hand-made bundle (Info.plist, icon, bash launcher).
- `/Applications/transcribe_app.py`: the application, placed next to the bundle.
- Dependencies installed with `pip install --user` for the Command Line Tools Python 3.9 (`~/Library/Python/3.9/...`).
- The first README (now `docs/original-README.md`) described an earlier Tkinter desktop version. The current version replaced it with the browser UI and saves transcripts to the Desktop instead of next to the recording.

Differences between this repository and the original installation:

- `Contents/MacOS/MeetingTranscriber`: the hard-coded `/Users/<username>/Library/Python/3.9/...` in `PYTHONPATH` was changed to `$HOME/Library/Python/3.9/...` so the launcher works for any user account.
- Everything else is byte-for-byte identical to the original files.
