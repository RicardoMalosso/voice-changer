# Install the full VCClient source environment, separate from the Twitch preview.
$ErrorActionPreference = "Stop"
$Server = $PSScriptRoot
$Environment = Join-Path (Split-Path $Server -Parent) ".venv-vcclient"
$Python = Join-Path $Environment "Scripts\python.exe"

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Program failed (exit code $LASTEXITCODE). See the error above."
    }
}

if (-not (Test-Path $Python)) {
    Write-Host "Creating the full VCClient environment with Python 3.10..."
    Invoke-Checked "py" @("-3.10", "-m", "venv", $Environment)
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
