"""Asynchronous Grace voice feedback."""

import asyncio
import os
import threading

_lock = threading.Lock()


def _speak_worker(text, state, hud):
    path = os.path.join(os.path.dirname(__file__), "temp_voice.mp3")
    try:
        import edge_tts
        import pygame

        async def synthesize():
            communicate = edge_tts.Communicate(text, "en-US-MichelleNeural", rate="-5%", pitch="+18Hz")
            await communicate.save(path)

        with _lock:
            asyncio.run(synthesize())
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(1.0)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(20)
            pygame.mixer.music.unload()
            pygame.mixer.quit()
    except Exception as exc:
        print(f"[voice] {exc}", flush=True)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
        if hud:
            hud.finish_dialogue(1.0)
            if state:
                hud.set_state(state)


def speak(text, state=None, hud=None, wait=False):
    """Queue voice feedback on a daemon thread without blocking the caller.

    ``wait`` is retained for compatibility with existing call sites, but TTS must
    never join the command/listener thread.  The worker lock serializes access
    to pygame and the shared temporary audio file while commands continue to be
    accepted in the foreground.
    """
    if hud:
        hud.set_state(state or "IDLE", text, None)
    worker = threading.Thread(target=_speak_worker, args=(text, state, hud), daemon=True)
    worker.start()
