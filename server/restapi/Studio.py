"""Local controls for the native audio path used by Studio."""

from pathlib import Path, PureWindowsPath
from threading import Lock
from typing import Literal
from uuid import uuid4
from zipfile import BadZipFile, ZipFile
import logging
import shutil

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from restapi.Twitch import local_request


logger = logging.getLogger(__name__)
MAX_MODEL_BYTES = 512 * 1024 * 1024


class AudioSettings(BaseModel):
    microphone: int = Field(ge=0)
    output: int = Field(ge=0)
    monitor: int = Field(default=-1, ge=-1)
    rate: Literal[44100, 48000] = 48000
    chunk: int = Field(default=64, ge=16, le=512)


class Selection(BaseModel):
    slot: int | str


class Tuning(BaseModel):
    tran: int = Field(default=0, ge=-36, le=36)
    indexRatio: float = Field(default=0, ge=0, le=1)
    serverInputAudioGain: float = Field(default=1, ge=0, le=3)
    serverOutputAudioGain: float = Field(default=1, ge=0, le=3)


def copy_model(source, destination):
    size = 0
    with destination.open("wb") as output:
        while chunk := source.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_MODEL_BYTES:
                raise HTTPException(413, "Model file exceeds 512 MiB.")
            output.write(chunk)
    if not size:
        raise HTTPException(400, "Model file is empty.")


def stage_model(upload, index, directory):
    model_name = PureWindowsPath(upload.filename or "").name
    extension = Path(model_name).suffix.lower()
    if extension not in {".zip", ".pth", ".onnx"}:
        raise HTTPException(400, "Choose an RVC ZIP, PTH or ONNX file.")
    if extension == ".zip":
        if index:
            raise HTTPException(400, "Choose the ZIP alone. Its index is imported automatically.")
        try:
            with ZipFile(upload.file) as archive:
                entries = [(entry, Path(PureWindowsPath(entry.filename).name).suffix.lower())
                           for entry in archive.infolist() if not entry.is_dir()]
                models = [(entry, suffix) for entry, suffix in entries if suffix in {".pth", ".onnx"}]
                indexes = [entry for entry, suffix in entries if suffix == ".index"]
                if len(models) != 1 or len(indexes) > 1:
                    raise HTTPException(400, "The ZIP must contain one model and at most one index.")
                files = []
                for entry, suffix in models + [(entry, ".index") for entry in indexes]:
                    path = directory / ("voice" + suffix)
                    with archive.open(entry) as source:
                        copy_model(source, path)
                    files.append(path)
                return Path(model_name).stem, files
        except (BadZipFile, RuntimeError, NotImplementedError) as exc:
            raise HTTPException(400, "The ZIP could not be read.") from exc
    path = directory / ("voice" + extension)
    copy_model(upload.file, path)
    files = [path]
    if index:
        if Path(index.filename or "").suffix.lower() != ".index":
            raise HTTPException(400, "The optional index must end in .index.")
        index_path = directory / "voice.index"
        copy_model(index.file, index_path)
        files.append(index_path)
    return Path(model_name).stem, files


def studio_router(manager):
    router = APIRouter(prefix="/studio/api", dependencies=[Depends(local_request)])
    lock = Lock()
    device = manager.serverDevice
    capture = device.studio_capture

    def slots():
        return {str(slot.slotIndex): slot for slot in manager.modelSlotManager.getAllSlotInfo(reload=True)
                if slot.voiceChangerType}

    def apply(key, value):
        manager.update_settings(key, str(value))

    @router.get("/live")
    def live():
        status = capture.status()
        status["requested"] = bool(device.settings.serverAudioStated)
        status["flowing"] = status["requested"] and status["flowing"]
        status["performance"] = device.performance
        return status

    @router.post("/model/select")
    def select(body: Selection):
        with lock:
            if device.settings.serverAudioStated:
                raise HTTPException(409, "Stop audio before changing models.")
            if str(body.slot) not in slots():
                raise HTTPException(404, "Model slot not found.")
            try:
                apply("modelSlotIndex", body.slot)
                if manager.voiceChanger is None:
                    raise RuntimeError("Engine did not load a model.")
            except Exception as exc:
                logger.exception("Studio model selection failed")
                raise HTTPException(422, "The model could not be loaded. Check the server log.") from exc
        return {"slot": body.slot}

    @router.post("/model/import")
    def import_model(model: UploadFile = File(...), index: UploadFile | None = File(None),
                     trusted: bool = Form(False)):
        from const import MAX_SLOT_NUM, UPLOAD_DIR
        from voice_changer.utils.LoadModelParams import LoadModelParamFile, LoadModelParams

        if not trusted:
            raise HTTPException(400, "Confirm that you trust the model source.")
        with lock:
            if device.settings.serverAudioStated:
                raise HTTPException(409, "Stop audio before importing a model.")
            occupied = slots()
            root = Path(manager.params.model_dir)
            slot = next((i for i in range(MAX_SLOT_NUM)
                         if str(i) not in occupied and not (root / str(i)).exists()), None)
            if slot is None:
                raise HTTPException(409, "No empty model slot is available.")
            tag = "studio-" + uuid4().hex
            staging = Path(UPLOAD_DIR) / tag
            staging.mkdir(parents=True)
            uploads = []
            try:
                name, files = stage_model(model, index, staging)
                for path in files:
                    destination = staging.parent / (tag + path.suffix)
                    path.rename(destination)
                    uploads.append(destination)
                params = LoadModelParams("RVC", slot, False, "", [
                    LoadModelParamFile(path.name, "rvcIndex" if path.suffix == ".index" else "rvcModel", "")
                    for path in uploads
                ], {})
                try:
                    manager.loadModel(params)
                    imported = slots()[str(slot)]
                    imported.name = name
                    manager.modelSlotManager.save_model_slot(slot, imported)
                except Exception as exc:
                    shutil.rmtree(root / str(slot), ignore_errors=True)
                    logger.exception("Studio model import failed")
                    raise HTTPException(422, "Model import failed. Check that this is an RVC inference model.") from exc
                return {"slot": slot, "name": name}
            finally:
                for path in uploads:
                    path.unlink(missing_ok=True)
                shutil.rmtree(staging, ignore_errors=True)

    @router.post("/model/export")
    def export():
        with lock:
            if device.settings.serverAudioStated or manager.voiceChanger is None:
                raise HTTPException(409, "Stop audio and load a model before exporting.")
            try:
                result = manager.export2onnx()
                if not result or result.get("status") != "ok":
                    raise ValueError("No ONNX file was generated.")
                filename = result["filename"]
                if not filename.endswith(".onnx") or PureWindowsPath(filename).name != filename:
                    raise ValueError("Unexpected ONNX filename.")
                return {"filename": filename}
            except Exception as exc:
                logger.exception("Studio ONNX export failed")
                raise HTTPException(422, "This model could not be exported to ONNX.") from exc

    @router.post("/model/defaults")
    def defaults():
        with lock:
            if manager.voiceChanger is None:
                raise HTTPException(409, "Select a voice model first.")
            manager.update_model_default()
        return {"saved": True}

    @router.post("/audio/start")
    def start(body: AudioSettings):
        with lock:
            if device.settings.serverAudioStated:
                raise HTTPException(409, "Audio is already starting or running.")
            if manager.voiceChanger is None:
                raise HTTPException(409, "Select a voice model first.")
            info = device.get_info()
            inputs = {item.index for item in info["serverAudioInputDevices"] or []}
            outputs = {item.index for item in info["serverAudioOutputDevices"] or []}
            if body.microphone not in inputs or body.output not in outputs:
                raise HTTPException(400, "Refresh and select a connected microphone and output.")
            if body.monitor != -1 and (body.monitor not in outputs or body.monitor == body.output):
                raise HTTPException(400, "Choose a different device for monitoring.")
            capture.last_block = 0
            capture.error = None
            for key, value in [
                ("serverInputDeviceId", body.microphone), ("serverOutputDeviceId", body.output),
                ("serverMonitorDeviceId", body.monitor), ("serverAudioSampleRate", body.rate),
                ("serverReadChunkSize", body.chunk), ("enableServerAudio", 1), ("serverAudioStated", 1),
            ]:
                apply(key, value)
        return live()

    @router.post("/audio/stop")
    def stop():
        with lock:
            apply("serverAudioStated", 0)
            capture.stop()
        return live()

    @router.post("/audio/tuning")
    def tune(body: Tuning):
        with lock:
            for key, value in body.dict().items():
                apply(key, value)
        return live()

    @router.post("/record/start")
    def record():
        with lock:
            if not live()["flowing"]:
                raise HTTPException(409, "Start audio and wait for microphone input first.")
            capture.begin(device.settings.serverInputAudioSampleRate)
        return live()

    @router.post("/record/stop")
    def finish_recording():
        capture.stop()
        return live()

    @router.get("/record/{track}")
    def recording(track: Literal["original", "converted"]):
        data = capture.wav(track)
        if data is None:
            raise HTTPException(404, "No recording is available.")
        return Response(data, media_type="audio/wav", headers={"Cache-Control": "no-store"})

    return router
