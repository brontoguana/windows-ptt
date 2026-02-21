import tkinter as tk
import threading
import ctypes

from ptt.config import SAMPLE_RATE, MIN_RECORDING_DURATION, STREAM_INTERVAL_MS
from ptt.hotkey import HotkeyListener
from ptt.audio import AudioRecorder
from ptt.transcriber import Transcriber
from ptt.overlay import Overlay
from ptt.paster import Paster
from ptt.tray import TrayIcon

# Enable DPI awareness BEFORE creating any tkinter windows
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Win32 constants for event polling
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258

# How often to check if the audio device has come back (ms)
DEVICE_CHECK_INTERVAL_MS = 3000


class App:
    def __init__(self, shutdown_event=None):
        self._root = tk.Tk()
        self._root.withdraw()
        self._root.geometry("0x0+0+0")
        self._root.overrideredirect(True)

        self._shutdown_event = shutdown_event  # Win32 event handle from run.py

        self._overlay = Overlay(self._root)
        self._recorder = AudioRecorder()
        self._transcriber = Transcriber()
        self._paster = Paster(self._root)
        self._hotkey = HotkeyListener(
            on_start_callback=self._on_insert_press,
            on_stop_callback=self._on_insert_release,
            on_cancel_callback=self._on_cancel,
        )
        self._tray = TrayIcon(on_quit_callback=self._shutdown)
        self._is_recording = False
        self._cancelled = False
        self._stream_timer = None       # tkinter after() id for streaming loop
        self._streaming_thread = None   # background thread doing partial transcription

    def run(self):
        print("Loading Whisper model...")
        self._transcriber.load_model()
        print("Model loaded.")

        try:
            self._recorder.init_stream()
        except RuntimeError as e:
            print(f"WARNING: {e}")
            print("Will keep trying to find a microphone...")

        self._hotkey.start()

        tray_thread = threading.Thread(target=self._tray.start, daemon=True)
        tray_thread.start()

        # Start polling for shutdown signal from another instance
        if self._shutdown_event:
            self._poll_shutdown_event()

        # Start device health monitor
        self._check_device_health()

        print("PTT ready. Double-tap Insert to record, tap again to paste.")
        self._root.mainloop()

    # ── Device health monitoring ──

    def _check_device_health(self):
        """Periodically check if the audio device is healthy; try to reconnect if not."""
        if not self._recorder.is_healthy and not self._is_recording:
            if self._recorder.try_reinit():
                print("Audio device reconnected.")
            # else: silently keep trying next time

        self._root.after(DEVICE_CHECK_INTERVAL_MS, self._check_device_health)

    # ── Poll for shutdown signal from another instance ──

    def _poll_shutdown_event(self):
        """Check every 500ms if another instance has signalled us to quit."""
        kernel32 = ctypes.windll.kernel32
        result = kernel32.WaitForSingleObject(self._shutdown_event, 0)
        if result == WAIT_OBJECT_0:
            print("Shutdown signal received from another instance.")
            self._shutdown()
            return
        self._root.after(500, self._poll_shutdown_event)

    # ── Insert press: start recording + streaming transcription ──

    def _on_insert_press(self):
        if self._is_recording:
            return

        # Try to recover the stream if the device was disconnected
        if not self._recorder.is_healthy:
            if not self._recorder.try_reinit():
                # Still no mic — show a brief error in the overlay
                self._root.after(0, self._show_no_mic_error)
                return

        self._is_recording = True
        self._cancelled = False
        self._root.after(0, self._start_recording_ui)

    def _show_no_mic_error(self):
        self._overlay.show()
        self._overlay.set_status("  No microphone detected")
        self._overlay.set_transcription("Please connect a microphone and try again.")
        self._root.after(2000, self._overlay.hide)

    def _start_recording_ui(self):
        self._overlay.show()
        self._recorder.start_recording()
        # Schedule the first streaming transcription tick
        self._stream_timer = self._root.after(
            STREAM_INTERVAL_MS, self._stream_tick
        )

    # ── Streaming loop: periodically transcribe accumulated audio ──

    def _stream_tick(self):
        if not self._is_recording:
            return

        # Only start a new partial transcription if the previous one finished
        if self._streaming_thread is None or not self._streaming_thread.is_alive():
            snapshot = self._recorder.get_snapshot()
            if snapshot.size > 0:
                self._streaming_thread = threading.Thread(
                    target=self._partial_transcribe,
                    args=(snapshot,),
                    daemon=True,
                )
                self._streaming_thread.start()

        # Schedule next tick
        if self._is_recording:
            self._stream_timer = self._root.after(
                STREAM_INTERVAL_MS, self._stream_tick
            )

    def _partial_transcribe(self, audio):
        text = self._transcriber.transcribe(audio)
        if self._is_recording and text:
            self._root.after(0, lambda: self._overlay.set_transcription(text))

    # ── ESC cancel: discard recording ──

    def _on_cancel(self):
        if not self._is_recording:
            return
        self._is_recording = False
        self._cancelled = True

        # Cancel the streaming timer
        if self._stream_timer is not None:
            self._root.after_cancel(self._stream_timer)
            self._stream_timer = None

        # Discard the recorded audio
        self._recorder.stop_recording()
        self._root.after(0, self._overlay.hide)

    # ── Insert release: final transcription + paste ──

    def _on_insert_release(self):
        if not self._is_recording:
            return
        self._is_recording = False

        # Cancel the streaming timer
        if self._stream_timer is not None:
            self._root.after_cancel(self._stream_timer)
            self._stream_timer = None

        audio = self._recorder.stop_recording()

        # Skip if recording was too short (accidental tap)
        duration = len(audio) / SAMPLE_RATE if len(audio) > 0 else 0
        if duration < MIN_RECORDING_DURATION:
            self._root.after(0, self._overlay.hide)
            return

        self._root.after(0, lambda: self._overlay.set_status("  Finalizing..."))
        self._transcriber.transcribe_async(audio, self._on_transcription_done)

    def _on_transcription_done(self, text: str):
        def _finish():
            self._overlay.hide()
            if text and not self._cancelled:
                self._paster.paste(text)

        self._root.after(0, _finish)

    # ── Shutdown ──

    def _shutdown(self):
        self._is_recording = False
        if self._stream_timer is not None:
            self._root.after_cancel(self._stream_timer)
        self._hotkey.stop()
        self._recorder.shutdown()
        self._overlay.destroy()
        self._tray.stop()
        self._root.quit()
