# Twitch triggers in VCClient

This feature is in the fork's source build. Start the fork's server with its existing dependencies and open the bundled VCClient interface at the loopback address printed at startup. The official Windows ZIP you already have contains the upstream version and will not show the new panel. See [the upstream source setup](README_dev_en.md) for prerequisites. The fork includes the browser assets for this panel.

1. In VCClient, select a model, configure your microphone and output, and click **Start**. Keep the same VB-CABLE and OBS route you already use for VCClient.
2. Open **Twitch triggers** at the bottom right. Use the Brazilian flag for Portuguese or the Canadian flag for English. The panel remembers your choice. Use **Test effect** to check the selected voice before connecting Twitch.
3. Click **Connect Twitch**, open the activation link, and enter the code displayed in the panel. Sign in as the broadcaster. The app uses the existing registered Twitch Public Client ID through Device Code login.
4. Type `!voice` in your channel. The default is 20 seconds and broadcaster/moderator access only. Set a minimum Bits amount or an existing Channel Points reward title or ID before connecting to enable those triggers. Reconnect after changing trigger settings.
5. While connected, VCClient passes through the original microphone between effects. A matching trigger enables the currently selected model. **Return to normal** ends the effect immediately. **Disconnect** hands control back to VCClient's manual passthrough setting.

All three trigger types use the same selected model and duration. Additional triggers during an active effect are ignored. This panel is only available from the PC running VCClient.

## Which files download automatically?

- The fork's normal server startup checks and downloads missing engine weights. These include RVC support files such as HuBERT and RMVPE.
- Startup also attempts to seed the default sample voices if the configured model directory does not already exist. If it exists, sample seeding is skipped.
- A particular model from voice-models.com is a separate download. Download and extract its ZIP, then use VCClient's model slot editor to upload the `.pth` and optional `.index`.

## Quick Windows test without CUDA

From a PowerShell window in the fork checkout on the `codex/twitch-integration` branch, use:

```powershell
py -3.12 -m venv .venv-twitch-test
.\.venv-twitch-test\Scripts\python.exe -m pip install "fastapi==0.95.1" "uvicorn==0.21.1" "websockets==11.0.2" "requests>=2.32,<3"
cd server
..\.venv-twitch-test\Scripts\python.exe -m tests.preview_twitch
```

Open [http://127.0.0.1:18889](http://127.0.0.1:18889) and expand **Twitch triggers**. Test both flags, **Test effect**, and **Return to normal**. You can also connect Twitch and send `!voice` to check that EventSub changes the effect status. The preview simulates the voice engine and produces no audio.

For a real mic and RVC test, use the [upstream source environment](README_dev_en.md) with this fork checked out. Use Python 3.10 in the full VCClient environment. The Python 3.12 preview environment installs only Twitch-panel dependencies. Upstream documents Linux/WSL2 for the full server, with native Windows source setup listed as unsupported. Run `python MMVCServerSIO.py --host 127.0.0.1 -p 18888 --open-app` from `server/`. This starts the real engine and opens the VCClient interface at `http://localhost:18888/front/` when it is ready. On Windows it uses the native client if available, or Edge app mode. Under WSL it opens the UI in Windows. Keep the server terminal open. Select a model and start conversion before testing the Twitch panel. The upstream prebuilt Windows ZIP does not include the changes on this branch.

## Local tests

From `server/`, install `httpx==0.27.2` alongside the server dependencies and run `python -m unittest discover -s tests -v`. The tests use a fake audio manager. Live Twitch authorization and Windows CUDA audio require a real server run.
