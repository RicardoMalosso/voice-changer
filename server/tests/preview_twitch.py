"""Run the real Twitch panel and OAuth routes with a simulated voice engine."""

from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from restapi.Twitch import twitch_router


app = FastAPI()
app.include_router(twitch_router(SimpleNamespace(voiceChanger=object(), twitch_pass_through=None)))
assets = Path(__file__).resolve().parents[2] / "client" / "demo" / "public" / "assets"
app.mount("/front/assets", StaticFiles(directory=assets))


@app.get("/", response_class=HTMLResponse)
def preview():
    return """
    <!doctype html>
    <html lang="en"><meta charset="utf-8"><title>VCClient Twitch panel test</title>
    <h1>VCClient Twitch panel test</h1>
    <p>Use Twitch triggers in the bottom right. This test simulates the voice engine and produces no audio.</p>
    <script defer src="/front/assets/twitch.js"></script>
    </html>
    """


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=18889)
