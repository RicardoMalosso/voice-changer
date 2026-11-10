from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import FastAPI
import httpx

from restapi.Twitch import BITS, POINTS, TriggerSettings, TwitchController, paid_trigger_matches, twitch_router


class TwitchTriggerTests(unittest.TestCase):
    def test_matches_configured_bits_and_reward(self):
        settings = TriggerSettings(minimum_bits=100, reward="Robot Voice")
        self.assertTrue(paid_trigger_matches(settings, BITS, {"type": "cheer", "bits": 100}))
        self.assertFalse(paid_trigger_matches(settings, BITS, {"type": "cheer", "bits": 99}))
        self.assertFalse(paid_trigger_matches(settings, BITS, {"type": "power_up", "bits": 100}))
        self.assertTrue(paid_trigger_matches(settings, POINTS, {"reward": {"id": "123", "title": "Robot Voice"}}))

    def test_trigger_uses_selected_voice_and_restores_dry_passthrough(self):
        manager = SimpleNamespace(voiceChanger=object(), twitch_pass_through=None)
        controller = TwitchController(manager)
        controller.stop = object()
        controller.arm()
        self.assertIs(manager.twitch_pass_through, True)
        with patch("restapi.Twitch.Timer") as timer:
            controller.trigger(20, controller.stop)
            self.assertIs(manager.twitch_pass_through, False)
            controller.trigger(20, controller.stop)
            timer.assert_called_once()
            timer.call_args.args[1]()
        self.assertIs(manager.twitch_pass_through, True)
        controller.stop = None
        controller.disconnect()
        self.assertIsNone(manager.twitch_pass_through)

    def test_trigger_requires_a_selected_voice(self):
        manager = SimpleNamespace(voiceChanger=None, twitch_pass_through=True)
        controller = TwitchController(manager)
        controller.trigger(20)
        self.assertIs(manager.twitch_pass_through, True)
        self.assertIn("Select a voice", controller.snapshot()["effect"])


class TwitchRoutesTests(unittest.IsolatedAsyncioTestCase):
    async def test_panel_can_test_and_cancel_on_loopback(self):
        manager = SimpleNamespace(voiceChanger=object(), twitch_pass_through=None)
        app = FastAPI()
        app.include_router(twitch_router(manager))
        transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 10000))
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
            denied = await client.post("/twitch/test", json={"duration": 20})
            self.assertEqual(denied.status_code, 403)
            headers = {"X-VCClient-Twitch": "1"}
            tested = await client.post("/twitch/test", headers=headers, json={"duration": 20})
            self.assertEqual(tested.status_code, 200)
            self.assertIs(manager.twitch_pass_through, False)
            cancelled = await client.post("/twitch/normal", headers=headers)
            self.assertEqual(cancelled.status_code, 200)
            self.assertIsNone(manager.twitch_pass_through)

    async def test_remote_client_cannot_access_twitch_status(self):
        app = FastAPI()
        app.include_router(twitch_router(SimpleNamespace()))
        transport = httpx.ASGITransport(app=app, client=("192.0.2.15", 10000))
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
            self.assertEqual((await client.get("/twitch/status")).status_code, 403)
