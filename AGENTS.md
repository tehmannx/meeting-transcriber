# AGENTS.md

## Active Roadmap — Read First

Before starting feature work on this repository, **read [`PLAN.md`](./PLAN.md)** and [`README.md`](./README.md).

- **Current state (v1):** Single-file Python 3 local macOS transcriber (`transcribe_app.py` + `MeetingTranscriber.app`) using `faster-whisper` and a browser UI on `localhost:7331`.
- **Planned direction (v2):** Evolve into a **cross-platform (macOS + Windows) Tauri desktop app** (Rust + TypeScript/React + `whisper.cpp`) that collapses *record → transcribe → AI analysis* into one local-first, bot-free workflow:
  - Native dual-track audio capture (`ScreenCaptureKit` on macOS, `WASAPI Loopback` on Windows) — **audio-only, not an OBS video alternative**
  - Real-time local transcription ("Me" vs. "Others") + drag-and-drop file transcription
  - Opinionated post-meeting AI analysis (*Action Points, Decisions, Crucial Things, Hard Truths*) via local **Ollama** or **BYOK (OpenAI / Claude)** + lightweight eval suite
  - Distributed as **unsigned open-source installers** (`.dmg` + `.exe`/`.msi`) via **GitHub Releases** — **no paid Apple Developer account / signing required**

## Non-Negotiable Rules

1. **Local-first & bot-free:** Audio recording and Whisper transcription must always run 100% locally on-device. Any cloud LLM call (OpenAI/Claude) must be strictly opt-in BYOK, with Ollama supported for full offline mode.
2. **Never commit recordings, transcripts, or API keys:** Keep API keys in OS secure storage (macOS Keychain / Windows Credential Manager), never plaintext files.
3. **Architect cross-platform, ship macOS first:** Keep OS-specific audio capture behind a clean `AudioCapture` interface so Windows WASAPI drops in cleanly after macOS works.
4. **No paid code-signing dependencies:** Distribution targets GitHub Releases with unsigned open-source builds and clear README instructions.
