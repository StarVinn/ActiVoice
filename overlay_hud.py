"""Small Grace overlay used by the launcher and background guards."""

import os
import queue
import threading
import tkinter as tk
from PIL import Image, ImageTk

ASSET_NAMES = {
    "WORKING": "grace_working.png", "IDLE": "grace_idle.png",
    "THINKING": "grace_thinking.png", "ANGRY": "grace_angry.png",
    "SLEEP": "grace_sleep.png", "SHUTDOWN": "grace_shutdown.png",
    "DRAG": "grace_drag.png",
}


class GraceHUD:
    """Thread-safe Tk HUD. Public methods may be called from worker threads."""

    def __init__(self, assets_dir=None):
        self.assets_dir = assets_dir or os.path.join(os.path.dirname(__file__), "assets")
        self._commands = queue.Queue()
        self._drag_offset = (0, 0)
        self._positioned = False
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.configure(bg="black")
        try:
            self.root.wm_attributes("-transparentcolor", "black")
        except tk.TclError:
            pass
        self.image_label = tk.Label(self.root, bg="black", borderwidth=0)
        self.image_label.pack()
        self.bubble = tk.Label(self.root, text="", bg="#2A2638", fg="#F5F3FF",
                               font=("Segoe UI", 10), wraplength=240, padx=10, pady=7)
        self._hide_after = None
        for widget in (self.root, self.image_label, self.bubble):
            widget.bind("<Button-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._drag)
            widget.bind("<ButtonRelease-1>", self._end_drag)
        self._set_expression("IDLE")

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
        path = os.path.join(self.assets_dir, ASSET_NAMES.get(str(state).upper(), ASSET_NAMES["IDLE"]))
        if os.path.exists(path):
            image = Image.open(path)
            image.thumbnail((220, 220), Image.Resampling.LANCZOS)
            self._image = ImageTk.PhotoImage(image)
            self.image_label.configure(image=self._image)
        self.root.update_idletasks()
        width, height = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        if not self._positioned:
            self.root.geometry(f"+{max(0, width - self.root.winfo_reqwidth() - 24)}+{max(0, height - self.root.winfo_reqheight() - 24)}")
            self._positioned = True

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

    def _show_dialogue(self, text, seconds):
        self.bubble.configure(text=text)
        self.bubble.place(relx=1.0, rely=0.0, anchor="ne", x=-8, y=8)
        if self._hide_after:
            self.root.after_cancel(self._hide_after)
        self._hide_after = self.root.after(int(seconds * 1000), self.bubble.place_forget)

    def set_state(self, state, text=None, seconds=4):
        if getattr(self, "root", None):
            self._commands.put((self._update, (state, text, seconds)))

    def _update(self, state, text, seconds):
        self._set_expression(state)
        if text:
            self._show_dialogue(text, seconds)

    def shutdown(self, wait=False):
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
