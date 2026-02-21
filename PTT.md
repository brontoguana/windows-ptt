# PTT — Developer Documentation

Everything a developer needs to get up to speed on the Push-to-Talk Voice-to-Text application.

## Architecture Overview

PTT is a multi-threaded Python desktop app for Windows. It captures microphone audio while a hotkey is held, transcribes it using a local Whisper model, and pastes the result into the focused application.

```
┌─────────────────────────────────────────────────────┐
│                    run.py                            │
│  Single-instance mutex + shutdown event (Win32 API)  │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                   app.py (Orchestrator)              │
│  Wires all components, manages state & threading     │
│  Runs tkinter mainloop on main thread                │
├─────────┬──────────┬───────────┬──────────┬─────────┤
│ hotkey  │  audio   │transcriber│ overlay  │ paster  │
│  .py    │   .py    │   .py     │   .py    │  .py    │
│(pynput) │(sound-   │(faster-   │(tkinter +│(clip-   │
│         │ device)  │ whisper)  │ Win32)   │ board + │
│         │          │           │          │ pynput) │
└─────────┴──────────┴───────────┴──────────┴─────────┘
                                        ▲
                                   tray.py (pystray)
```

## Project Structure

```
PTT/
├── run.py                 # Entry point — single-instance enforcement
├── requirements.txt       # Pip dependencies
├── setup_cx.py            # cx_Freeze MSI build script
├── generate_icon.py       # Converts hires_mic.png → icon.png + icon.ico
├── ptt/
│   ├── __init__.py
│   ├── config.py          # All constants and tunables
│   ├── app.py             # Orchestrator — wires everything together
│   ├── hotkey.py          # Global Insert key + ESC detection (pynput)
│   ├── audio.py           # Microphone recording (sounddevice)
│   ├── transcriber.py     # Whisper model loading + transcription
│   ├── overlay.py         # Non-focus-stealing overlay (tkinter + Win32 API)
│   ├── paster.py          # Clipboard write + Ctrl+V simulation
│   └── tray.py            # System tray icon (pystray)
└── assets/
    ├── hires_mic.png      # Source icon (high-res, transparent)
    ├── icon.png           # Generated 64x64 tray icon
    └── icon.ico           # Generated multi-size Windows icon
```

## Threading Model

The app runs 5 threads:

| Thread | Owner | Purpose | Notes |
|--------|-------|---------|-------|
| **Main** | `tkinter.mainloop()` | Event loop, overlay updates, clipboard, paste | All tkinter ops must happen here |
| **Hotkey** | `pynput.keyboard.Listener` | Global Insert/ESC key monitoring | Daemon thread, started by pynput |
| **Audio** | `sounddevice.InputStream` | Microphone sample capture via callback | PortAudio callback thread |
| **Transcription** | `Transcriber` worker | Whisper inference (one per recording + partials) | Daemon thread, created per request |
| **Tray** | `pystray.Icon.run()` | System tray icon and menu | Daemon thread |

### Thread Safety Rules

1. **All tkinter operations** must happen on the main thread. Cross-thread calls use `root.after(0, callable)`.
2. **Audio buffer** uses `collections.deque` (GIL-safe append) plus an explicit `threading.Lock` for `stop_recording()`.
3. **Transcriber** has a `threading.Lock` to prevent concurrent Whisper model access.
4. **Callbacks from hotkey/transcriber threads** are always marshalled to main thread via `root.after(0, ...)`.

## Component Details

### run.py — Single Instance Enforcement

Uses Windows named kernel objects:
- **Mutex** (`Global\PTT_VoiceToText_SingleInstance`) — only one process can hold it
- **Event** (`Global\PTT_VoiceToText_Shutdown`) — new instance signals this to tell the old one to quit

Flow:
1. Try `CreateMutexW`. If `ERROR_ALREADY_EXISTS`, another instance is running.
2. Open and `SetEvent` on the shutdown event to signal the old instance.
3. Wait 500ms for old instance to exit, then re-acquire mutex.
4. Create the shutdown event for future instances to signal.
5. Pass the event handle to `App` so it can poll it.

### app.py — Orchestrator

Central controller that wires all components and manages the recording lifecycle.

**DPI Awareness**: Calls `SetProcessDpiAwareness(2)` before creating any tkinter windows. This is critical — without it, fonts render blurry on high-DPI displays.

**Root Window**: The tkinter `Tk()` root is hidden (`withdraw()`, `geometry("0x0+0+0")`, `overrideredirect(True)`). It exists only to drive the event loop and provide clipboard access.

**Event Flow**:
```
Insert Press  → _on_insert_press()
              → overlay.show() + recorder.start_recording()
              → schedule _stream_tick() every STREAM_INTERVAL_MS

Stream Tick   → recorder.get_snapshot()
              → transcriber.transcribe() in background thread
              → overlay.set_transcription(partial_text)

Insert Release → _on_insert_release()
               → recorder.stop_recording()
               → check min duration
               → transcriber.transcribe_async(final_audio)
               → overlay.hide() + paster.paste(text)

ESC (cancel)  → _on_cancel()
              → recorder.stop_recording() (discard)
              → overlay.hide()
              → no paste
```

**Shutdown Event Polling**: Every 500ms, checks if another instance has signalled the shutdown event via `WaitForSingleObject`.

### hotkey.py — Global Key Detection

Uses `pynput.keyboard.Listener` which runs in its own daemon thread.

Key design decisions:
- **`_insert_held` flag** prevents Windows key-repeat from firing multiple press callbacks. Without this, holding Insert would trigger `on_press` many times.
- **ESC detection** only fires if Insert is currently held (`_insert_held` is True). This avoids intercepting ESC during normal use.
- Uses `keyboard.Key.insert` enum. Fallback if needed: `keyboard.KeyCode.from_vk(0x2D)`.

### audio.py — Microphone Recording

Uses `sounddevice.InputStream` with a callback-based architecture.

Key design decisions:
- **Stream stays open permanently** to avoid 50-100ms latency of opening/closing PortAudio streams. The `_is_recording` flag controls whether samples are buffered.
- **`deque` buffer** — `deque.append()` is thread-safe under CPython's GIL.
- **`indata.copy()`** is critical because sounddevice reuses the buffer between callbacks.
- **`get_snapshot()`** copies the buffer without stopping recording (for streaming partial transcription).
- **Output format**: 1D `float32` numpy array at 16kHz — exactly what faster-whisper requires.

### transcriber.py — Whisper Integration

Uses `faster-whisper` (CTranslate2-based, ~4x faster than OpenAI's whisper).

Key design decisions:
- **Model loaded once at startup** and kept in memory (~300MB for `base`).
- **`vad_filter=True`** with Silero VAD skips silence segments before transcription.
- **`beam_size=1`** (greedy decoding) is fastest. Beam 5 is more accurate but slower.
- **`compute_type="int8"`** on CPU gives ~2x speedup over float32.
- **`language="en"`** avoids the 30-second language detection step.
- **Thread-safe**: `threading.Lock` prevents concurrent model access from streaming + final transcription.

Expected performance (base model, int8, CPU, beam_size=1):
- 5-second recording: ~300-500ms transcription
- 15-second recording: ~800-1200ms transcription

### overlay.py — Non-Focus-Stealing Overlay

This is the most technically nuanced component. The overlay must appear on top of all windows without stealing focus from the target application.

**Win32 API integration via ctypes:**

| API | Purpose |
|-----|---------|
| `WS_EX_NOACTIVATE` | Prevents window from becoming foreground when shown |
| `WS_EX_TOOLWINDOW` | Hides from Alt+Tab and taskbar |
| `SetWindowPos` + `SWP_NOACTIVATE` | Re-assert topmost without activating |
| `overrideredirect(True)` | Remove title bar and window chrome |

**HWND retrieval**: `GetParent(winfo_id())` — `winfo_id()` returns the Tk frame handle, `GetParent()` gives the actual Win32 top-level handle.

**Layout**:
- Status label at top: "Recording... (hit ESC to cancel)"
- 1px separator line
- Scrolling `tk.Text` widget (read-only, word-wrap, auto-scroll to bottom)

### paster.py — Clipboard + Paste

1. Writes text to clipboard via `tkinter.clipboard_clear()` + `clipboard_append()` + `update()`
2. Waits `PASTE_DELAY_MS` (50ms) for clipboard to be ready
3. Simulates Ctrl+V via `pynput.keyboard.Controller`

The paste targets whatever window had focus before the overlay appeared, because the overlay uses `WS_EX_NOACTIVATE` so focus never moved.

**Known limitation**: Overwrites the user's clipboard. A future improvement could save/restore clipboard contents.

### tray.py — System Tray

Uses `pystray` which requires its `Icon.run()` to be called from a non-main thread on Windows.

Menu items:
- "Push-to-Talk Active" (disabled label)
- Separator
- "Quit" (triggers `App._shutdown()`)

Falls back to a generated solid-colour icon if `assets/icon.png` is missing.

## Config Reference (ptt/config.py)

### Audio
| Constant | Value | Notes |
|----------|-------|-------|
| `SAMPLE_RATE` | 16000 | Whisper requires 16kHz |
| `CHANNELS` | 1 | Mono |
| `DTYPE` | "float32" | Whisper requires float32 in [-1.0, 1.0] |
| `BLOCK_SIZE` | 1024 | Frames per PortAudio callback |

### Whisper
| Constant | Value | Notes |
|----------|-------|-------|
| `WHISPER_MODEL_SIZE` | "base" | tiny/base/small/medium/large-v3 |
| `WHISPER_DEVICE` | "cpu" | "cpu" or "cuda" |
| `WHISPER_COMPUTE_TYPE` | "int8" | int8 for CPU, float16 for CUDA |
| `WHISPER_LANGUAGE` | "en" | None for auto-detect (slower) |
| `WHISPER_BEAM_SIZE` | 1 | 1=greedy (fast), 5=beam search (accurate) |

### Streaming
| Constant | Value | Notes |
|----------|-------|-------|
| `STREAM_INTERVAL_MS` | 2000 | Partial transcription every 2s while recording |

### Overlay
| Constant | Value | Notes |
|----------|-------|-------|
| `OVERLAY_WIDTH` | 550 | Pixels |
| `OVERLAY_HEIGHT` | 250 | Pixels |
| `OVERLAY_BG` | "#0f1923" | Dark navy background |
| `OVERLAY_FG` | "#7eb8e0" | Light blue text |
| `OVERLAY_FG_DIM` | "#3d6a8a" | Dimmed status text |
| `OVERLAY_FONT` | ("Segoe UI", 11) | Font family and size |
| `OVERLAY_POSITION` | "bottom_right" | bottom_right / top_right / center |
| `OVERLAY_OPACITY` | 0.92 | Window transparency |

### Controls
| Constant | Value | Notes |
|----------|-------|-------|
| `PASTE_DELAY_MS` | 50 | Delay between clipboard write and Ctrl+V |
| `MIN_RECORDING_DURATION` | 0.3 | Seconds, skips accidental taps |

## Dependencies

| Package | Purpose |
|---------|---------|
| `faster-whisper` | Local Whisper transcription via CTranslate2 |
| `sounddevice` | Microphone recording via PortAudio |
| `numpy` | Audio buffer manipulation |
| `pynput` | Global hotkey listener + Ctrl+V simulation |
| `pystray` | System tray icon |
| `Pillow` | Icon image loading |
| `cx_Freeze` | MSI installer packaging |

**Python version**: 3.12 or 3.14 (not 3.13 — ctranslate2 has no Windows wheel for 3.13).

## Building

### Run from source
```bash
py -3.14 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python generate_icon.py
python run.py
```

### Build MSI installer
```bash
python setup_cx.py bdist_msi
# Output: dist/PTT-1.0.0-win64.msi
```

The MSI includes:
- Bundled Python runtime + all dependencies
- Start Menu shortcut under "Push-to-Talk"
- Fixed `upgrade_code` GUID — new versions upgrade over old installations
- Install path: `C:\Program Files\PTT\`

**Not bundled**: The Whisper model (~150MB) downloads on first launch to `~/.cache/huggingface/`.

### Bumping the version
Change `version="1.0.0"` in `setup_cx.py`, rebuild, and the new MSI will upgrade over the old one.

## Known Limitations

- **Clipboard overwrite**: Pasting uses clipboard + Ctrl+V, which overwrites whatever was on the clipboard.
- **Insert key**: Some apps use Insert for overwrite mode. The key is configurable in `config.py` but requires code changes to support modifier combos.
- **First launch**: Downloads the Whisper model (~150MB) which takes a few seconds on slow connections.
- **CPU only by default**: GPU acceleration requires CUDA 12.x and changing `WHISPER_DEVICE` to `"cuda"`.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No audio input device found" | Connect a microphone before launching |
| Blurry/pixelated text | DPI awareness is set in `app.py` — ensure it runs before `Tk()` |
| Overlay steals focus | Check `WS_EX_NOACTIVATE` is applied in `overlay.py` |
| Paste goes to wrong window | Overlay must not steal focus — see above |
| Multiple instances running | The mutex mechanism in `run.py` handles this; kill stale processes if needed |
| ctranslate2 won't install | Use Python 3.12 or 3.14, not 3.13 |
