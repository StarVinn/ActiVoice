"""Small Grace overlay used by the launcher and background guards."""

import os
import queue
import threading
try:
    import psutil
except ImportError:
    psutil = None
import tkinter as tk
from PIL import Image, ImageTk

ASSET_NAMES = {
    "WORKING": "grace_working.png", "IDLE": "grace_idle.png",
    "THINKING": "grace_thinking.png", "ANGRY": "grace_angry.png",
    "SLEEP": "grace_sleep.png", "SHUTDOWN": "grace_shutdown.png",
    "DRAG": "grace_drag.png",
    "TIRED": "grace_tired.png", "SAD": "grace_sad.png",
}


class GraceHUD:
    """Thread-safe Tk HUD. Public methods may be called from worker threads."""

    def __init__(self, assets_dir=None):
        self.assets_dir = assets_dir or os.path.join(os.path.dirname(__file__), "assets")
        self._commands = queue.Queue()
        self._drag_offset = (0, 0)
        self._positioned = False
        self._monitor_stop = threading.Event()
        self._typewriter_job = None
        self._fallback_after = None
        self._dialogue_generation = 0
        self.current_text = ""
        self._active_state = "IDLE"
        self._hud_width = 520
        self._hud_height = 240
        self._avatar_x = 300
        self._avatar_y = 10
        self._bubble_x = 8
        self._bubble_y = 20
        self._bubble_width = 280
        self._bubble_height = 200
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.configure(bg="black")
        try:
            self.root.wm_attributes("-transparentcolor", "black")
        except tk.TclError:
            pass
        self.root.geometry(f"{self._hud_width}x{self._hud_height}")
        self.content = tk.Frame(self.root, bg="black", highlightthickness=0, bd=0)
        self.content.place(x=0, y=0, width=self._hud_width, height=self._hud_height)
        self.speech_frame = tk.Frame(self.content, bg="black", highlightthickness=0, bd=0)
        self.speech_frame.place(
            x=self._bubble_x,
            y=self._bubble_y,
            width=self._bubble_width,
            height=self._bubble_height,
        )
        self.bubble = tk.Label(
            self.speech_frame,
            text="",
            width=30,
            bg="#2A2638",
            fg="#F5F3FF",
            font=("Segoe UI", 10),
            wraplength=240,
            justify="left",
            anchor="nw",
            padx=12,
            pady=10,
        )
        self.speech_label = self.bubble
        self.image_label = tk.Label(self.content, bg="black", borderwidth=0, highlightthickness=0)
        self.image_label.place(
            x=self._avatar_x,
            y=self._avatar_y,
            width=self._hud_width - self._avatar_x,
            height=self._hud_height - self._avatar_y,
        )
        self.image_label.lower()
        self.speech_frame.place_forget()
        self._hide_after = None
        for widget in (self.root, self.content, self.speech_frame, self.image_label, self.bubble):
            widget.bind("<Button-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._drag)
            widget.bind("<ButtonRelease-1>", self._end_drag)
        self._set_expression("IDLE")
        threading.Thread(target=self._system_expression_loop, daemon=True, name="hud-system-monitor").start()

    def run(self):
        """Run Tk on the thread that created the HUD, normally the main thread."""
        self._pump()
        self.root.mainloop()

    def _pump(self):
        try:
            while True:
                command, args = self._commands.get_nowait()
                command(*args)
        except queue.Empty:
            pass
        if getattr(self, "root", None):
            self.root.after(50, self._pump)

    def _set_expression(self, state):
        state_name = str(state).upper()
        self._active_state = state_name
        filename = ASSET_NAMES.get(state_name, ASSET_NAMES["IDLE"])
        path = os.path.join(self.assets_dir, filename)
        if not os.path.exists(path):
            path = os.path.join(self.assets_dir, ASSET_NAMES["IDLE"])
        if os.path.exists(path):
            image = Image.open(path)
            image.thumbnail((220, 220), Image.Resampling.LANCZOS)
            self._image = ImageTk.PhotoImage(image)
            self.image_label.configure(image=self._image)
            self.image_label.lower()
        width, height = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        if not self._positioned:
            self.root.geometry(
                f"{self._hud_width}x{self._hud_height}+"
                f"{max(0, width - self._hud_width - 24)}+"
                f"{max(0, height - self._hud_height - 24)}"
            )
            self._positioned = True

    def _system_expression_loop(self):
        while not self._monitor_stop.wait(10):
            if not psutil:
                continue
            try:
                battery = psutil.sensors_battery()
                low_battery = bool(battery and not battery.power_plugged and battery.percent < 40)
                overloaded = psutil.cpu_percent(interval=0.5) > 95 or psutil.virtual_memory().percent > 95
                self.set_state("TIRED" if low_battery or overloaded else "IDLE")
            except (psutil.Error, OSError):
                continue

    def _start_drag(self, event):
        """Remember the pointer offset so dragging does not jump the window."""
        self._set_expression("DRAG")
        self._drag_offset = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())

    def _end_drag(self, event):
        self._set_expression("IDLE")

    def _drag(self, event):
        x = event.x_root - self._drag_offset[0]
        y = event.y_root - self._drag_offset[1]
        self.root.geometry(f"+{x}+{y}")

    def _show_dialogue(self, text, seconds=None):
        self._dialogue_generation += 1
        generation = self._dialogue_generation
        self.current_text = text
        if self._hide_after:
            self.root.after_cancel(self._hide_after)
            self._hide_after = None
        if self._fallback_after:
            self.root.after_cancel(self._fallback_after)
            self._fallback_after = None
        if self._typewriter_job:
            self.root.after_cancel(self._typewriter_job)
            self._typewriter_job = None
        self.speech_frame.place(
            x=self._bubble_x,
            y=self._bubble_y,
            width=self._bubble_width,
            height=self._bubble_height,
        )
        self.speech_label.place(x=0, y=0, relwidth=1, relheight=1)
        self._set_expression(self._active_state)

        def type_next(index=0):
            if generation != self._dialogue_generation:
                return
            self.bubble.configure(text=self.current_text[:index])
            if index < len(text):
                self._typewriter_job = self.root.after(25, type_next, index + 1)

        type_next()
        if seconds is not None:
            self._hide_after = self.root.after(int(seconds * 1000), self._clear_dialogue)
        else:
            fallback_seconds = max(3.0, len(text) * 0.08)
            self._fallback_after = self.root.after(
                int(fallback_seconds * 1000), self._clear_dialogue
            )

    def _clear_dialogue(self):
        self._dialogue_generation += 1
        if self._typewriter_job:
            self.root.after_cancel(self._typewriter_job)
            self._typewriter_job = None
        if self._fallback_after:
            self.root.after_cancel(self._fallback_after)
            self._fallback_after = None
        self.bubble.configure(text="")
        self.speech_label.place_forget()
        self.speech_frame.place_forget()
        self.current_text = ""
        self._hide_after = None

    def finish_dialogue(self, hold_seconds=1.0):
        """Hide an audio-synced bubble after playback and a short hold."""
        if getattr(self, "root", None):
            self._commands.put((self._schedule_dialogue_clear, (hold_seconds,)))

    def _schedule_dialogue_clear(self, hold_seconds):
        if self._hide_after:
            self.root.after_cancel(self._hide_after)
        if self._fallback_after:
            self.root.after_cancel(self._fallback_after)
            self._fallback_after = None
        self._hide_after = self.root.after(int(hold_seconds * 1000), self._clear_dialogue)

    def set_state(self, state, text=None, seconds=4):
        if getattr(self, "root", None):
            self._commands.put((self._update, (state, text, seconds)))

    def _update(self, state, text, seconds):
        self._set_expression(state)
        if text:
            self._show_dialogue(text, seconds)

    def shutdown(self, wait=False):
        self._monitor_stop.set()
        if getattr(self, "root", None):
            destroyed = threading.Event() if wait else None

            def destroy_root():
                try:
                    self.root.destroy()
                finally:
                    if destroyed:
                        destroyed.set()

            self._commands.put((destroy_root, ()))
            if destroyed:
                destroyed.wait(timeout=2)
