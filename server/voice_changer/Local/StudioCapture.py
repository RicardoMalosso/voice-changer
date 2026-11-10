"""Bounded, opt-in recording of matching input and output blocks."""

from io import BytesIO
from threading import Lock
from time import monotonic
import wave


class StudioCapture:
    def __init__(self):
        self.lock = Lock()
        self.last_block = 0
        self.levels = (0.0, 0.0)
        self.error = None
        self.active = False
        self.rate = 0
        self.frames = 0
        self.input = bytearray()
        self.output = bytearray()

    def begin(self, rate):
        with self.lock:
            self.rate = rate
            self.frames = 0
            self.input.clear()
            self.output.clear()
            self.active = True

    def stop(self):
        with self.lock:
            self.active = False

    def push(self, dry, wet, rate):
        if not dry.size or not wet.size:
            return
        with self.lock:
            self.last_block = monotonic()
            self.levels = tuple(max(abs(int(block.min())), abs(int(block.max()))) / 32768
                                for block in (dry, wet))
            self.error = None
            if not self.active:
                return
            if rate != self.rate:
                self.active = False
                return
            count = min(len(dry), len(wet), rate * 15 - self.frames)
            self.input.extend(dry[:count].astype("<i2", copy=False).tobytes())
            self.output.extend(wet[:count].astype("<i2", copy=False).tobytes())
            self.frames += count
            if self.frames >= rate * 15:
                self.active = False

    def status(self):
        with self.lock:
            return {"flowing": monotonic() - self.last_block < 2, "levels": self.levels,
                    "error": self.error, "recording": self.active, "frames": self.frames}

    def wav(self, track):
        with self.lock:
            rate = self.rate
            pcm = bytes(self.input if track == "original" else self.output)
        if not pcm:
            return None
        result = BytesIO()
        with wave.open(result, "wb") as output:
            output.setparams((1, 2, rate, 0, "NONE", "not compressed"))
            output.writeframes(pcm)
        return result.getvalue()
