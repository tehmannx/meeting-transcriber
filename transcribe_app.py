#!/usr/bin/env python3
"""
Meeting Transcriber — web UI version.
Opens automatically in your browser. Drop a .mov file, get a transcript.
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Add user site-packages so we find faster-whisper regardless of how we're launched
USER_SITE = os.path.expanduser("~/Library/Python/3.9/lib/python/site-packages")
if os.path.isdir(USER_SITE) and USER_SITE not in sys.path:
    sys.path.insert(0, USER_SITE)

try:
    from faster_whisper import WhisperModel
    IMPORT_ERROR = None
except Exception as e:
    WhisperModel = None
    IMPORT_ERROR = f"{type(e).__name__}: {e}"

PORT = 7331

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Meeting Transcriber</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg: #0f0f11;
    --surface: #1a1a1f;
    --surface2: #222228;
    --border: #2e2e38;
    --accent: #7c6cfa;
    --accent-glow: rgba(124,108,250,0.25);
    --text: #e8e8f0;
    --muted: #6b6b80;
    --success: #4ade80;
    --error: #f87171;
  }

  body {
    font-family: 'Inter', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 48px 24px;
  }

  header {
    text-align: center;
    margin-bottom: 40px;
  }

  header h1 {
    font-size: 28px;
    font-weight: 600;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, #fff 40%, var(--accent));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  header p {
    color: var(--muted);
    font-size: 14px;
    margin-top: 6px;
    font-weight: 300;
  }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 32px;
    width: 100%;
    max-width: 680px;
    margin-bottom: 16px;
  }

  /* Drop zone */
  #dropzone {
    border: 2px dashed var(--border);
    border-radius: 12px;
    padding: 48px 24px;
    text-align: center;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
    position: relative;
  }

  #dropzone:hover, #dropzone.dragover {
    border-color: var(--accent);
    background: var(--accent-glow);
  }

  #dropzone input[type=file] {
    position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%;
  }

  .drop-icon {
    font-size: 40px;
    margin-bottom: 12px;
    display: block;
  }

  #dropzone h2 {
    font-size: 16px;
    font-weight: 500;
    margin-bottom: 4px;
  }

  #dropzone p {
    font-size: 13px;
    color: var(--muted);
  }

  #file-name {
    margin-top: 16px;
    font-size: 13px;
    color: var(--accent);
    font-weight: 500;
    min-height: 18px;
  }

  /* Options row */
  .options {
    display: flex;
    gap: 16px;
    margin-top: 24px;
    flex-wrap: wrap;
  }

  .opt-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
    min-width: 140px;
  }

  .opt-group label {
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--muted);
  }

  select {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    padding: 8px 12px;
    font-size: 14px;
    font-family: inherit;
    cursor: pointer;
    outline: none;
    transition: border-color 0.2s;
  }

  select:focus { border-color: var(--accent); }

  /* Transcribe button */
  #go-btn {
    margin-top: 24px;
    width: 100%;
    padding: 14px;
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 600;
    font-family: inherit;
    cursor: pointer;
    transition: opacity 0.2s, transform 0.1s;
    letter-spacing: -0.2px;
  }

  #go-btn:hover:not(:disabled) { opacity: 0.88; transform: translateY(-1px); }
  #go-btn:disabled { opacity: 0.4; cursor: not-allowed; }

  /* Progress */
  #progress-wrap {
    display: none;
    margin-top: 20px;
  }

  #status-text {
    font-size: 13px;
    color: var(--muted);
    margin-bottom: 8px;
  }

  .progress-bar-bg {
    background: var(--surface2);
    border-radius: 99px;
    height: 6px;
    overflow: hidden;
  }

  #progress-bar {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), #a78bfa);
    border-radius: 99px;
    width: 0%;
    transition: width 0.4s ease;
  }

  /* Transcript output */
  #output-card {
    display: none;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px 32px;
    width: 100%;
    max-width: 680px;
  }

  .output-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }

  .output-header span {
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--muted);
  }

  .output-actions { display: flex; gap: 8px; }

  .action-btn {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 7px;
    color: var(--text);
    padding: 6px 14px;
    font-size: 13px;
    font-family: inherit;
    cursor: pointer;
    transition: border-color 0.2s;
  }

  .action-btn:hover { border-color: var(--accent); color: var(--accent); }

  #transcript {
    font-size: 14px;
    line-height: 1.8;
    color: var(--text);
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 480px;
    overflow-y: auto;
    padding-right: 4px;
  }

  #transcript::-webkit-scrollbar { width: 4px; }
  #transcript::-webkit-scrollbar-track { background: transparent; }
  #transcript::-webkit-scrollbar-thumb { background: var(--border); border-radius: 99px; }

  .saved-note {
    margin-top: 12px;
    font-size: 12px;
    color: var(--success);
  }

  .ts-line { color: var(--accent); font-weight: 500; }

  /* Spinner */
  @keyframes spin { to { transform: rotate(360deg); } }
  .spinner {
    display: inline-block;
    width: 14px; height: 14px;
    border: 2px solid rgba(255,255,255,0.2);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    vertical-align: middle;
    margin-right: 8px;
  }
</style>
</head>
<body>

<header>
  <h1>Meeting Transcriber</h1>
  <p>Drop a recording. Get a transcript. Fully local.</p>
</header>

<div class="card">
  <div id="dropzone">
    <input type="file" id="file-input" accept=".mov,.mp4,.m4a,.mp3,.wav,.mkv">
    <span class="drop-icon">🎙️</span>
    <h2>Drop your recording here</h2>
    <p>.mov · .mp4 · .m4a · .mp3 · .wav</p>
  </div>
  <div id="file-name"></div>

  <div class="options">
    <div class="opt-group">
      <label>Model</label>
      <select id="model-select">
        <option value="tiny">Tiny — fastest</option>
        <option value="base">Base — fast</option>
        <option value="small" selected>Small — recommended</option>
        <option value="medium">Medium — accurate</option>
        <option value="large-v3">Large v3 — best</option>
      </select>
    </div>
    <div class="opt-group">
      <label>Language</label>
      <select id="lang-select">
        <option value="">Auto-detect</option>
        <option value="en">English</option>
        <option value="de">German</option>
        <option value="es">Spanish</option>
        <option value="fr">French</option>
        <option value="it">Italian</option>
        <option value="nl">Dutch</option>
        <option value="pt">Portuguese</option>
      </select>
    </div>
    <div class="opt-group">
      <label>Timestamps</label>
      <select id="ts-select">
        <option value="yes">Yes</option>
        <option value="no" selected>No</option>
      </select>
    </div>
  </div>

  <button id="go-btn" disabled>Select a file to begin</button>

  <div id="progress-wrap">
    <div id="status-text">Loading model…</div>
    <div class="progress-bar-bg"><div id="progress-bar"></div></div>
  </div>
</div>

<div id="output-card">
  <div class="output-header">
    <span>Transcript</span>
    <div class="output-actions">
      <button class="action-btn" onclick="copyTranscript()">Copy</button>
      <button class="action-btn" onclick="downloadTranscript()">Download .txt</button>
    </div>
  </div>
  <div id="transcript"></div>
  <div class="saved-note" id="saved-note"></div>
</div>

<script>
  let selectedFile = null;
  let fullTranscript = '';
  let baseFilename = 'transcript';

  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const fileName = document.getElementById('file-name');
  const goBtn = document.getElementById('go-btn');
  const progressWrap = document.getElementById('progress-wrap');
  const statusText = document.getElementById('status-text');
  const progressBar = document.getElementById('progress-bar');
  const outputCard = document.getElementById('output-card');
  const transcriptEl = document.getElementById('transcript');
  const savedNote = document.getElementById('saved-note');

  dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('dragover'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', e => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) setFile(fileInput.files[0]);
  });

  function setFile(f) {
    selectedFile = f;
    baseFilename = f.name.replace(/\.[^.]+$/, '');
    fileName.textContent = '📎 ' + f.name;
    goBtn.disabled = false;
    goBtn.textContent = 'Transcribe';
  }

  goBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    goBtn.disabled = true;
    goBtn.innerHTML = '<span class="spinner"></span>Transcribing…';
    progressWrap.style.display = 'block';
    outputCard.style.display = 'none';
    transcriptEl.innerHTML = '';
    fullTranscript = '';
    savedNote.textContent = '';
    progressBar.style.width = '0%';
    statusText.textContent = 'Uploading file…';

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('filename', selectedFile.name);
    formData.append('model', document.getElementById('model-select').value);
    formData.append('language', document.getElementById('lang-select').value);
    formData.append('timestamps', document.getElementById('ts-select').value);

    try {
      const response = await fetch('/transcribe', { method: 'POST', body: formData });
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n').filter(l => l.startsWith('data: '));
        for (const line of lines) {
          const data = JSON.parse(line.slice(6));
          if (data.type === 'status') {
            statusText.textContent = data.text;
          } else if (data.type === 'progress') {
            progressBar.style.width = data.value + '%';
          } else if (data.type === 'segment') {
            outputCard.style.display = 'block';  // only show once text arrives
            fullTranscript += data.text;
            const ts = data.ts ? `<span class="ts-line">${data.ts}</span> ` : '';
            transcriptEl.innerHTML += ts + escapeHtml(data.words) + '\n';
            transcriptEl.scrollTop = transcriptEl.scrollHeight;
          } else if (data.type === 'done') {
            progressBar.style.width = '100%';
            statusText.textContent = '✅ Done!';
            goBtn.disabled = false;
            goBtn.textContent = 'Transcribe again';
            if (data.saved) savedNote.textContent = '💾 Saved: ' + data.saved;
          } else if (data.type === 'error') {
            statusText.textContent = '❌ ' + data.text;
            goBtn.disabled = false;
            goBtn.textContent = 'Transcribe';
          }
        }
      }
    } catch (err) {
      statusText.textContent = '❌ ' + err.message;
      goBtn.disabled = false;
      goBtn.textContent = 'Transcribe';
    }
  });

  function escapeHtml(t) {
    return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function copyTranscript() {
    navigator.clipboard.writeText(fullTranscript).then(() => {
      savedNote.textContent = '✅ Copied to clipboard!';
      setTimeout(() => savedNote.textContent = '', 2000);
    });
  }

  function downloadTranscript() {
    const blob = new Blob([fullTranscript], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = baseFilename + '_transcript.txt';
    a.click();
  }
</script>
</body>
</html>
"""


def sse(obj):
    return ("data: " + json.dumps(obj) + "\n\n").encode()


class Handler(BaseHTTPRequestHandler):
    model_cache = {}

    def log_message(self, *args):
        pass  # silence request logs

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode())

    def do_POST(self):
        import cgi
        ctype, pdict = cgi.parse_header(self.headers.get("Content-Type", ""))
        pdict["boundary"] = pdict.get("boundary", "").encode()
        pdict["CONTENT-LENGTH"] = int(self.headers.get("Content-Length", 0))
        form = cgi.parse_multipart(self.rfile, pdict)

        def _decode(v, default=""):
            if v is None: return default
            if isinstance(v, bytes): return v.decode()
            return v

        file_data = form.get("file", [None])[0]
        model_name = _decode(form.get("model", [None])[0], "small")
        language = _decode(form.get("language", [None])[0], "") or None
        want_ts = _decode(form.get("timestamps", [None])[0], "no") == "yes"
        orig_name = _decode(form.get("filename", [None])[0], "recording")
        base_name = orig_name.rsplit(".", 1)[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def write(obj):
            try:
                self.wfile.write(sse(obj))
                self.wfile.flush()
            except Exception:
                pass

        if WhisperModel is None:
            write({"type": "error", "text": f"Import failed: {IMPORT_ERROR}"})
            return

        # Save upload to a temp file
        suffix = ".mov"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_data)
            tmp_path = tmp.name

        try:
            write({"type": "status", "text": f"Loading model '{model_name}'…"})
            write({"type": "progress", "value": 5})

            key = model_name
            if key not in Handler.model_cache:
                Handler.model_cache[key] = WhisperModel(model_name, device="cpu", compute_type="int8")
            model = Handler.model_cache[key]

            write({"type": "status", "text": "Transcribing… (hang tight)"})
            write({"type": "progress", "value": 10})

            segments, info = model.transcribe(tmp_path, language=language, vad_filter=True)

            if not language:
                write({"type": "status", "text": f"Detected: {info.language} — transcribing…"})

            total = info.duration or 1
            lines = []

            for seg in segments:
                words = seg.text.strip()
                ts_str = f"[{fmt(seg.start)}]" if want_ts else ""
                line = f"{ts_str} {words}\n" if want_ts else words + " "
                lines.append(line)
                write({"type": "segment", "ts": ts_str, "words": words, "text": line})
                write({"type": "progress", "value": min(98, int(seg.end / total * 100))})

            transcript = "".join(lines).strip()

            # Auto-save next to... well, we don't know the original path, so save to Desktop
            desktop = Path.home() / "Desktop"
            out_path = desktop / f"{base_name}_transcript.txt"
            try:
                out_path.write_text(transcript + "\n", encoding="utf-8")
                saved = str(out_path)
            except Exception:
                saved = None

            write({"type": "done", "saved": saved})

        except Exception as e:
            write({"type": "error", "text": str(e)})
        finally:
            os.unlink(tmp_path)


def fmt(s):
    s = int(s)
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


if __name__ == "__main__":
    # If another instance is already on this port, kill it so we don't end up
    # with a stale server. We use lsof + kill, which always exist on macOS.
    try:
        out = subprocess.check_output(["lsof", "-ti", f":{PORT}"], stderr=subprocess.DEVNULL).decode().strip()
        for pid in out.splitlines():
            if pid and int(pid) != os.getpid():
                subprocess.run(["kill", "-9", pid], stderr=subprocess.DEVNULL)
        if out:
            import time
            time.sleep(0.5)
    except Exception:
        pass

    server = HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Opening Meeting Transcriber at {url}")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
