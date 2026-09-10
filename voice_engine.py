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
    """Run TTS on a worker thread and return that worker immediately.

    Normal notifications must leave ``wait`` as ``False`` so the listener stays
    responsive.  ``wait=True`` is reserved for controlled shutdown, where the
    caller deliberately waits for its farewell audio before closing the app.
    The worker lock serializes pygame and the shared temporary audio file.
    """
    if hud:
        hud.set_state(state or "IDLE", text, None)
    worker = threading.Thread(target=_speak_worker, args=(text, state, hud), daemon=True)
    worker.start()
    if wait:
        worker.join()
    return worker
