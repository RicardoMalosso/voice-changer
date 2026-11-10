# Install the full VCClient source environment, separate from the Twitch preview.
param([switch]$Launch)

$ErrorActionPreference = "Stop"
$Server = $PSScriptRoot
$Project = Split-Path $Server -Parent
$Environment = Join-Path $Project ".venv-vcclient"
$Python = Join-Path $Environment "Scripts\python.exe"
$Runtime = Join-Path $Project ".vcclient-runtime"

# Some Windows installs still point TEMP or pip's cache at an offline drive.
# Keep build files on the checkout drive for this setup process and its children.
$TempDirectory = Join-Path $Runtime "tmp"
$PipCache = Join-Path $Runtime "pip-cache"
New-Item -ItemType Directory -Path $TempDirectory, $PipCache -Force | Out-Null
$env:TEMP = $TempDirectory
$env:TMP = $TempDirectory
$env:TMPDIR = $TempDirectory
$env:PIP_CACHE_DIR = $PipCache
Write-Host "Using build temp directory: $TempDirectory"

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Program failed (exit code $LASTEXITCODE). See the error above."
    }
}

if (-not (Test-Path $Python)) {
    Write-Host "Creating the full VCClient environment with Python 3.10..."
    $UvCommand = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue
    if ($UvCommand) {
        $Uv = $UvCommand.Source
    }
    else {
        $Bootstrap = Join-Path $Project ".venv-vcclient-bootstrap"
        $BootstrapPython = Join-Path $Bootstrap "Scripts\python.exe"
        $Uv = Join-Path $Bootstrap "Scripts\uv.exe"
        if (-not (Test-Path $BootstrapPython)) {
            Invoke-Checked "python" @("-m", "venv", $Bootstrap)
        }
        if (-not (Test-Path $Uv)) {
            Invoke-Checked $BootstrapPython @("-m", "pip", "install", "uv==0.8.22")
        }
    }

    $PreviousPythonDirectory = $env:UV_PYTHON_INSTALL_DIR
    $PreviousUvCache = $env:UV_CACHE_DIR
    try {
        $env:UV_PYTHON_INSTALL_DIR = Join-Path $Runtime "python"
        $env:UV_CACHE_DIR = Join-Path $Runtime "uv-cache"
        Invoke-Checked $Uv @("venv", "--python", "3.10", "--seed", $Environment)
    }
    finally {
        $env:UV_PYTHON_INSTALL_DIR = $PreviousPythonDirectory
        $env:UV_CACHE_DIR = $PreviousUvCache
    }
}
Invoke-Checked $Python @("-c", "import struct, sys; assert sys.version_info[:2] == (3, 10) and struct.calcsize('P') == 8, 'Install 64-bit Python 3.10 for VCClient.'")

Write-Host "Installing the CUDA PyTorch wheels and VCClient dependencies..."
# Older OmegaConf releases need a pip that accepts their legacy metadata.
Invoke-Checked $Python @("-m", "pip", "install", "pip==24.0", "setuptools<70", "wheel", "Cython<3", "numpy==1.23.5")
Invoke-Checked $Python @("-m", "pip", "install", "torch==2.0.1", "torchaudio==2.0.2", "--index-url", "https://download.pytorch.org/whl/cu118")
$PreviousReadTheDocs = $env:READTHEDOCS
try {
    # Fairseq's inference code does not need its compiled training extensions.
    $env:READTHEDOCS = "True"
    Invoke-Checked $Python @("-m", "pip", "install", "--no-build-isolation", "-r",
        (Join-Path $Server "requirements.txt"), "fairseq==0.12.2", "pyworld==0.3.4", "onnx==1.14.1", "chardet")
}
finally {
    $env:READTHEDOCS = $PreviousReadTheDocs
}

Push-Location $Server
try {
    Invoke-Checked $Python @("-c", "import torch, torchaudio, onnxruntime, faiss, pyworld; from fairseq import checkpoint_utils; from voice_changer.RVC.RVCr2 import RVCr2; print('CUDA available:', torch.cuda.is_available()); assert torch.cuda.is_available(), 'CUDA is unavailable. Check your NVIDIA driver.'")
}
finally {
    Pop-Location
}

Write-Host "Setup complete. From server, start VCClient with:"
Write-Host '..\.venv-vcclient\Scripts\python.exe MMVCServerSIO.py --host 127.0.0.1 -p 18888 --open-app'

if ($Launch) {
    Push-Location $Server
    try {
        Invoke-Checked $Python @("MMVCServerSIO.py", "--host", "127.0.0.1", "-p", "18888", "--open-app")
    }
    finally {
        Pop-Location
    }
}
