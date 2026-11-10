"""Local Twitch triggers for the active VCClient voice."""

from ipaddress import ip_address
from threading import Event, Lock, Thread, Timer

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, validator

from restapi.twitch_eventsub import BITS, POINTS, is_command, listen


class TriggerSettings(BaseModel):
    command: str = "!voice"
    duration: int = Field(default=20, ge=1, le=300)
    moderators_only: bool = True
    minimum_bits: int = Field(default=0, ge=0)
    reward: str = ""

    @validator("command")
    def validate_command(cls, value):
        value = value.strip()
        if len(value) < 2 or not value.startswith("!") or len(value.split()) != 1:
            raise ValueError("Enter a command such as !voice.")
        return value


def paid_trigger_matches(settings, kind, event):
    if kind == BITS:
        return (settings.minimum_bits > 0 and event.get("type") == "cheer"
                and event.get("bits", 0) >= settings.minimum_bits)
    if kind == POINTS:
        reward = event["reward"]
        return bool(settings.reward.strip()) and settings.reward.strip().casefold() in {
            reward["id"].casefold(), reward["title"].casefold(),
        }
    return False


class TwitchController:
    def __init__(self, voice):
        self.voice = voice
        self.lock = Lock()
        self.stop = None
        self.timer = None
        self.status = "Twitch disconnected."
        self.effect = "Twitch control off."

    def snapshot(self):
        with self.lock:
            return {"status": self.status, "effect": self.effect, "connected": self.stop is not None}

    def connect(self, settings):
        with self.lock:
            if self.stop is not None:
                raise HTTPException(409, "Disconnect Twitch before changing the trigger settings.")
            stop = self.stop = Event()
            self.status = "Waiting for Twitch authorization…"

        def update(message, **values):
            with self.lock:
                if self.stop is stop:
                    self.status = message.format(**values)
                    if message == "Listening to #{channel}":
                        self.arm()

        def run():
            try:
                listen(stop, update,
                       lambda event, user: self.trigger(settings.duration, stop)
                       if is_command(event, user, settings.command, settings.moderators_only) else None,
                       extra_trigger=lambda kind, event: self.trigger(settings.duration, stop)
                       if paid_trigger_matches(settings, kind, event) else None,
                       bits=settings.minimum_bits > 0, points=bool(settings.reward.strip()))
            except Exception as exc:
                update("Twitch connection failed ({error}). Reconnect to retry.",
                       error=type(exc).__name__)
            finally:
                with self.lock:
                    if self.stop is stop:
                        self.stop = None
                        self.disarm()

        Thread(target=run, daemon=True).start()

    def arm(self):
        if self.timer is None:
            self.voice.twitch_pass_through = True
            self.effect = "Ready. The original mic passes through between triggers."

    def trigger(self, duration, stop=None):
        with self.lock:
            if stop is not None and stop is not self.stop:
                return
            if self.timer is not None:
                return
            if getattr(self.voice, "voiceChanger", None) is None:
                self.effect = "Select a voice model and start audio in VCClient first."
                return
            timer = Timer(duration, lambda: self.finish(timer))
            timer.daemon = True
            self.timer = timer
            self.voice.twitch_pass_through = False
            self.effect = f"Converted voice active for {duration} seconds."
            timer.start()

    def finish(self, timer=None):
        with self.lock:
            if timer is not None and timer is not self.timer:
                return
            if self.timer is not None:
                self.timer.cancel()
                self.timer = None
            if self.stop is not None:
                self.arm()
            else:
                self.disarm()

    def disarm(self):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None
        self.voice.twitch_pass_through = None
        self.effect = "Twitch control off."

    def disconnect(self):
        with self.lock:
            if self.stop is not None:
                self.stop.set()
                self.stop = None
            self.status = "Twitch disconnected."
            self.disarm()


def local_request(request: Request):
    try:
        loopback = request.client is not None and ip_address(request.client.host).is_loopback
    except ValueError:
        loopback = False
    if not loopback or request.url.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(403, "Twitch control is available only from this PC.")
    if request.method != "GET" and request.headers.get("X-VCClient-Twitch") != "1":
        raise HTTPException(403, "Open the local VCClient Twitch panel.")


def twitch_router(voice):
    router = APIRouter(prefix="/twitch", dependencies=[Depends(local_request)])
    control = TwitchController(voice)

    @router.get("/status")
    def status():
        return control.snapshot()

    @router.post("/connect")
    def connect(settings: TriggerSettings):
        control.connect(settings)
        return control.snapshot()

    @router.post("/disconnect")
    def disconnect():
        control.disconnect()
        return control.snapshot()

    @router.post("/test")
    def test(settings: TriggerSettings):
        control.trigger(settings.duration)
        return control.snapshot()

    @router.post("/normal")
    def normal():
        control.finish()
        return control.snapshot()

    router.add_event_handler("shutdown", control.disconnect)
    return router
