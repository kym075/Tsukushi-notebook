$ErrorActionPreference = "Stop"

python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m PyInstaller --clean --noconfirm TukushiNote.spec

Write-Host "Build complete: dist\TukushiNote.exe"
