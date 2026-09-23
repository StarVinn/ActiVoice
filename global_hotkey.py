"""Global Ctrl+Alt push-to-talk listener for Windows."""

import threading

try:
    import keyboard
except ImportError:  # pragma: no cover
    keyboard = None


class GlobalPushToTalk:
    """Global Ctrl+Alt trigger for a dedicated Gemini voice turn."""

    def __init__(self, on_activate, hotkey="ctrl+alt"):
        self.on_activate = on_activate
        self.hotkey = hotkey
        self._hooks = []
        self._active = False
        self._lock = threading.Lock()

    def start(self):
        if keyboard is None:
            raise RuntimeError("keyboard package is not installed")

        # Start listening immediately when the combo is pressed. This avoids
        # missing the beginning of the user's speech.
        self._hooks.append(
            keyboard.add_hotkey(
                self.hotkey,
                self._fire,
                suppress=False,
                trigger_on_release=False,
            )
        )
        return True

    def _fire(self):
        with self._lock:
            if self._active:
                return
            self._active = True
        try:
            self.on_activate()
        finally:
            with self._lock:
                self._active = False

    def stop(self):
        if keyboard is not None:
            for hook in self._hooks:
                try:
                    keyboard.remove_hotkey(hook)
                except (KeyError, ValueError):
                    pass
            self._hooks.clear()
