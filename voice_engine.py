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
        if hud and state:
            hud.set_state(state)


def speak(text, state=None, hud=None, wait=False):
    """Speak asynchronously, or wait until playback completes when requested."""
    if hud and state:
        hud.set_state(state, text)
    worker = threading.Thread(target=_speak_worker, args=(text, state, hud), daemon=True)
    worker.start()
    if wait:
        worker.join()
