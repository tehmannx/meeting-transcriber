# Meeting Transcriber v2 Plan — Bot-Free Live Meeting Recorder, Transcriber & AI Analyst

> **Status:** Planned (not started yet — current v1 is a local macOS post-recording transcriber in `transcribe_app.py`).  
> **Target:** Replace the 3-step manual workflow (*OBS recording → Meeting Transcriber → copy-paste to LLM*) with a single local-first, cross-platform (**macOS + Windows**) desktop app for live transcription and opinionated meeting analysis.

---

## Product Goal

Build a **local-first, bot-free meeting recorder, live transcriber, and AI analyst** that:
- Never joins your Zoom/Meet/Teams call as a third-party bot.
- Captures **system audio + microphone** locally on separate tracks (giving **"Me" vs. "Others"** speaker separation for free).
- Streams a **live local transcript** on-device while the meeting is happening.
- Runs an **opinionated AI analysis** afterward (or on demand) extracting **Action Points (with owners)**, **Decisions**, **Crucial Points**, and **Hard Truths** — using either **100% local Ollama** or **BYOK (OpenAI / Claude)** API keys.
- Ships as **unsigned open-source installers** (`.dmg` for macOS, `.exe`/`.msi` for Windows) via **GitHub Releases** — no paid Apple Developer account required.

### Scope Boundaries
- **Not an OBS Studio alternative:** Audio-first capture only (no screen/video compositing, no streaming, no multi-GB video files).
- **Keep v1 intact** (`transcribe_app.py` + `MeetingTranscriber.app`) until v2 reaches parity on file drop + transcription.

---

## Core Architecture (v2)

- **App Shell & UI:** **Tauri** (Rust backend + **TypeScript / React** frontend) — single codebase producing tiny (~15–20 MB) macOS `.dmg` and Windows `.exe`/`.msi` installers.
- **OS Audio Capture (thin platform adapter):**
  - **macOS (13+):** Native `ScreenCaptureKit` (system audio + mic, no BlackHole virtual audio driver needed).
  - **Windows:** Native `WASAPI Loopback` (system audio + mic, no virtual cables needed).
- **Local Live Transcription:** `whisper.cpp` (Metal / Apple Silicon acceleration on macOS; CPU/Vulkan/CUDA on Windows) + Silero VAD chunking for real-time rolling transcripts. Models download inside the app on first launch with a progress bar (keeping installers small).
- **AI Analysis Layer (BYOK / Local LLM):**
  - Supports **Ollama** (100% offline) and **BYOK OpenAI / Anthropic** keys (stored in OS Keychain / Windows Credential Manager, never plaintext).
  - Built-in opinionated analysis lenses: **Action Items & Owners**, **Key Decisions**, **Crucial Details**, and **Hard Truths** (contradictions, vague commitments, unspoken risks), plus user-editable prompt templates.
  - **"Flag Moment" hotkey** during live calls to mark key timestamps for deeper AI focus.
- **Evals:** Lightweight automated **eval suite** in the repo (synthetic sample transcripts + assertions on extracted action items, owners, and hard truths) to measure prompt/model quality reliably.
- **Distribution:** GitHub Actions CI building unsigned macOS `.dmg` + Windows `.exe`/`.msi` on tagged releases (`v*`), published to **GitHub Releases** and linked from the repo README / personal site (with clear 1-line install instructions for unsigned open-source builds: macOS right-click → Open; Windows More info → Run anyway).

---

## Execution Strategy

**Architect for macOS + Windows from day 1, ship macOS first, then drop in the Windows WASAPI adapter right after v2 works on macOS.**

### Milestones
- **M1 — Tauri Skeleton & macOS Live Audio Capture:** Tauri + React/TS shell, abstracted `AudioCapture` trait, macOS `ScreenCaptureKit` dual-track (mic + system audio) recorder, clean permission onboarding.
- **M2 — Real-Time Local Transcription:** In-app Whisper model manager + `whisper.cpp` + VAD streaming pipeline → live rolling transcript UI ("Me" / "Others"), plus backward-compatible drag-and-drop file transcription and timestamped export.
- **M3 — Opinionated AI Analysis + Evals:** Ollama + BYOK (OpenAI/Claude) integration, Keychain secret storage, *"Action Points / Decisions / Crucial Things / Hard Truths"* templates, "Flag Moment" hotkey, and reproducible eval suite.
- **M4 — Windows Support & GitHub Releases:** Windows `WASAPI Loopback` implementation of `AudioCapture`, GitHub Actions release workflow publishing unsigned `.dmg` and `.exe`/`.msi` builds, MIT `LICENSE`, README + demo GIF.

---

## Known v1 Issues to Fix if Touching v1 Before v2
- Replace deprecated/removed Python `cgi` module (breaks on Python 3.13+).
- Sanitize uploaded filenames against path traversal (`../`) before writing to `~/Desktop`.
- Avoid force-killing unrelated processes on port `7331`.
- Stream uploads to disk instead of buffering entire recordings in RAM.
