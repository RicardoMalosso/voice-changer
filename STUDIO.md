# PacVoice Studio

Studio is a separate localhost interface in the VCClient fork. It uses the same model slots, native audio devices, conversion engine, and Twitch integration as VCClient.

## Open Studio

On the Studio branch, from PowerShell in `server/`, install the full engine and launch:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup-windows.ps1 -Launch
```

For an existing environment, launch without reinstalling:

```powershell
..\.venv-vcclient\Scripts\python.exe MMVCServerSIO.py --host 127.0.0.1 -p 18888 --open-app --studio
```

The server opens [Studio](http://localhost:18888/studio/) when ready. Leave the server terminal open. The existing `/front/` interface is linked at the bottom and is still available for advanced tools and browser audio mode.

## First run

1. Load an existing model or import a trusted RVC ZIP, PTH, or ONNX file. A ZIP may contain one model and one optional index. A direct model upload can include an optional separate index. Imports use an empty slot.
2. Choose a mic and output. To route into OBS with VB-CABLE, select **CABLE Input** in Studio and **CABLE Output** in OBS. Optional monitoring must use a different output device.
3. Start audio. Studio distinguishes a requested start from actual input blocks arriving. Adjust the sample rate or block size if your devices require it.
4. Record a short sample and compare the original and processed WAVs. Recording is opt-in, limited to 15 seconds, and kept in memory until the next recording or server shutdown.
5. Configure Twitch chat, Bits, and/or Channel Points. Use **Test effect** and **Return to normal** before testing a live trigger. The broadcaster login link uses Twitch's device activation page.

Studio includes pitch and index tuning, input/output gains, model defaults, ONNX export, device selection and monitoring, and English / Brazilian Portuguese controls. Other model-family imports, sample downloads, model merging, and browser audio controls use the original interface.

## Verification

Run `python -m unittest discover -s tests -v` from `server/` with the server dependencies and `httpx==0.27.2`. Studio tests exercise HTTP input validation, recording, and ZIP staging with simulated audio. The release check on a physical Windows machine is a fresh install on the project drive, real RVC import, audio to OBS, and live Twitch activation followed by passthrough. A successful simulated test does not verify CUDA, a sound card, or OBS.
