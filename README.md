# Push-to-Talk Voice-to-Text

A Windows push-to-talk app that transcribes your speech and pastes it into any application. Hold the **Insert** key to record, release to paste. Uses a local Whisper model — no API keys, no cloud, fully offline.

## Features

- **Push-to-talk** — Hold Insert to record, release to transcribe and paste
- **Live transcription** — See your words appear in a floating overlay as you speak
- **Cancel with ESC** — Press Escape while recording to discard
- **Works everywhere** — Pastes into whatever app has focus (Notepad, browser, Slack, etc.)
- **Fully offline** — Runs a local Whisper model, no internet needed after first setup
- **Lightweight** — Sits quietly in the system tray until you need it
- **Single instance** — Launching again cleanly replaces the running copy

## Quick Start

### From Source

Requires **Python 3.12 or 3.14** on Windows (Python 3.13 is not supported due to a missing ctranslate2 wheel).

```bash
# Create virtual environment
py -3.14 -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Generate the tray icon
python generate_icon.py

# Run (first launch downloads the Whisper model ~150MB)
python run.py
```

### From Installer

Run `PTT-1.0.0-win64.msi` and launch "Push-to-Talk" from the Start Menu.

## Usage

| Action | Key | Result |
|--------|-----|--------|
| Start recording | Hold **Insert** | Overlay appears, mic starts capturing |
| Finish & paste | Release **Insert** | Text is transcribed and pasted |
| Cancel | Press **ESC** while holding Insert | Recording discarded, nothing pasted |
| Quit | Right-click tray icon → Quit | App exits |

## Configuration

Edit `ptt/config.py` to customise:

| Setting | Default | Description |
|---------|---------|-------------|
| `WHISPER_MODEL_SIZE` | `"base"` | Model size: tiny, base, small, medium, large-v3 |
| `WHISPER_DEVICE` | `"cpu"` | `"cpu"` or `"cuda"` for GPU acceleration |
| `WHISPER_LANGUAGE` | `"en"` | Language code, or `None` for auto-detect |
| `OVERLAY_POSITION` | `"bottom_right"` | `"bottom_right"`, `"top_right"`, or `"center"` |
| `STREAM_INTERVAL_MS` | `2000` | How often live transcription updates (ms) |
| `MIN_RECORDING_DURATION` | `0.3` | Minimum seconds to avoid accidental taps |

## Building the MSI Installer

```bash
python setup_cx.py bdist_msi
```

Output: `dist/PTT-1.0.0-win64.msi`

## License

All rights reserved.
