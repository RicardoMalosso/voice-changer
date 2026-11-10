"""Open the running VCClient source build in an application window."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser


def open_when_ready(port, process, native_client, timeout=120, frontend="front"):
    url = f"http://localhost:{port}/{frontend}/"
    deadline = time.monotonic() + timeout
    while process.is_alive() and time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return open_window(url, native_client)
        except (OSError, URLError):
            time.sleep(0.5)
    return False


def open_window(url, native_client):
    if sys.platform.startswith("win"):
        native = Path(native_client)
        if native.is_file():
            subprocess.Popen([str(native.resolve()), "--disable-gpu", "-u", url])
            return True
        edge = shutil.which("msedge")
        if not edge:
            for key in ("ProgramFiles(x86)", "ProgramFiles"):
                directory = os.environ.get(key)
                if directory:
                    candidate = Path(directory) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
                    if candidate.is_file():
                        edge = str(candidate)
                        break
        if edge:
            subprocess.Popen([edge, f"--app={url}"])
            return True
    elif "WSL_DISTRO_NAME" in os.environ and shutil.which("explorer.exe"):
        subprocess.Popen(["explorer.exe", url])
        return True
    return webbrowser.open(url)

