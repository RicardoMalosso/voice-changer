from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
import httpx
import wave
from zipfile import ZipFile

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
import numpy as np

from restapi.Studio import stage_model, studio_router
from restapi.Twitch import twitch_router
from voice_changer.Local.StudioCapture import StudioCapture


def make_app():
    capture = StudioCapture()
    devices = {
        "serverAudioInputDevices": [SimpleNamespace(index=1, name="Test Mic", hostAPI="WASAPI")],
        "serverAudioOutputDevices": [SimpleNamespace(index=2, name="Test Output", hostAPI="WASAPI")],
    }
    settings = SimpleNamespace(serverAudioStated=0, serverInputAudioSampleRate=48000)
    device = SimpleNamespace(settings=settings, studio_capture=capture, get_info=lambda: devices, performance=[7])
    models = [SimpleNamespace(slotIndex=0, voiceChangerType="RVC", name="Test Voice")]
    manager = SimpleNamespace(serverDevice=device, voiceChanger=object(), twitch_pass_through=None,
                              modelSlotManager=SimpleNamespace(getAllSlotInfo=lambda **_: models))

    def update(key, value):
        if key == "serverAudioStated":
            settings.serverAudioStated = int(value)
            if int(value):
                capture.push(np.array([100, -200], dtype=np.int16), np.array([300, -400], dtype=np.int16), 48000)
        if key == "serverAudioSampleRate":
            settings.serverInputAudioSampleRate = int(value)

    manager.update_settings = update
    app = FastAPI()
    app.include_router(studio_router(manager))
    app.include_router(twitch_router(manager))

    @app.get("/info")
    def info():
        return {**devices, "modelSlots": models, "gpus": [{"name": "Test GPU"}],
                "modelSlotIndex": 0, "serverInputDeviceId": 1, "serverOutputDeviceId": 2}

    app.mount("/studio", StaticFiles(directory=Path(__file__).resolve().parents[1] / "studio", html=True))
    return app, capture


class StudioTests(unittest.IsolatedAsyncioTestCase):
    async def test_audio_start_validates_devices_and_records_paired_wavs(self):
        app, capture = make_app()
        transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 9999))
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
            headers = {"X-VCClient-Twitch": "1"}
            start = "/studio/api/audio/start"
            self.assertEqual((await client.post(start, json={"microphone": 1, "output": 2})).status_code, 403)
            self.assertEqual((await client.post(start, headers=headers, json={"microphone": 99, "output": 2})).status_code, 400)
            response = await client.post(start, headers=headers, json={"microphone": 1, "output": 2, "rate": 48000})
            self.assertTrue(response.json()["flowing"])
            self.assertTrue((await client.post("/studio/api/record/start", headers=headers)).json()["recording"])
            capture.push(np.array([100, -200], dtype=np.int16), np.array([300, -400], dtype=np.int16), 48000)
            stopped = (await client.post("/studio/api/audio/stop", headers=headers)).json()
            self.assertFalse(stopped["recording"])
            self.assertFalse(stopped["flowing"])
            for track, values in [("original", [100, -200]), ("converted", [300, -400])]:
                with wave.open(BytesIO((await client.get("/studio/api/record/" + track)).content)) as wav:
                    self.assertEqual(wav.getframerate(), 48000)
                    self.assertEqual(np.frombuffer(wav.readframes(2), dtype="<i2").tolist(), values)

    def test_capture_stops_at_fifteen_seconds(self):
        capture = StudioCapture()
        capture.begin(8)
        block = np.arange(200, dtype=np.int16)
        capture.push(block, block, 8)
        self.assertFalse(capture.status()["recording"])
        self.assertEqual(capture.status()["frames"], 120)

    def test_nested_zip_stages_only_selected_files_and_rejects_ambiguity(self):
        with TemporaryDirectory() as directory:
            upload = SimpleNamespace(filename="Test.zip", file=BytesIO())
            with ZipFile(upload.file, "w") as zip_file:
                zip_file.writestr("../voice.pth", b"model")
                zip_file.writestr("deep/voice.index", b"index")
            name, files = stage_model(upload, None, Path(directory))
            self.assertEqual(name, "Test")
            self.assertEqual([file.read_bytes() for file in files], [b"model", b"index"])
            with ZipFile(upload.file, "a") as zip_file:
                zip_file.writestr("second.pth", b"another")
            with self.assertRaises(HTTPException):
                stage_model(upload, None, Path(directory))
