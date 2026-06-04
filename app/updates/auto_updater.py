import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from app.core.app_logger import LOG_FILE


def is_auto_update_supported(update_info):
    if os.name != "nt":
        return False
    if not getattr(sys, "frozen", False):
        return False
    if not getattr(update_info, "asset_url", ""):
        return False

    try:
        exe_dir = Path(sys.executable).resolve().parent
        with tempfile.NamedTemporaryFile(prefix=".write-test-", dir=exe_dir, delete=True):
            pass
    except OSError:
        return False

    return True


def download_update_exe(update_info):
    update_dir = Path(tempfile.gettempdir()) / "TukushiNoteUpdates"
    update_dir.mkdir(parents=True, exist_ok=True)

    version = str(update_info.latest_version).replace("/", "-").replace("\\", "-")
    target_path = update_dir / f"TukushiNote-{version}.exe"
    request = urllib.request.Request(
        update_info.asset_url,
        headers={"User-Agent": "TukushiNote-auto-updater"},
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        with open(target_path, "wb") as f:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)

    try:
        validate_downloaded_exe(target_path)
    except Exception:
        try:
            target_path.unlink()
        except OSError:
            pass
        raise

    return target_path


def validate_downloaded_exe(path):
    if path.stat().st_size == 0:
        raise RuntimeError("ダウンロードした更新ファイルが空です。")

    with open(path, "rb") as f:
        if f.read(2) != b"MZ":
            raise RuntimeError("ダウンロードした更新ファイルがexe形式ではありません。")


def launch_update_installer(downloaded_exe):
    current_exe = Path(sys.executable).resolve()
    script_path = Path(tempfile.gettempdir()) / f"tukushi_note_update_{os.getpid()}.ps1"
    script = r'''
param(
    [string]$NewExe,
    [string]$CurrentExe,
    [string]$LogFile
)

$updated = $false
$lastError = $null
Start-Sleep -Milliseconds 800

for ($i = 0; $i -lt 80; $i++) {
    try {
        Copy-Item -LiteralPath $NewExe -Destination $CurrentExe -Force
        $updated = $true
        break
    } catch {
        $lastError = $_.Exception.Message
        Start-Sleep -Milliseconds 500
    }
}

if ($updated) {
    Start-Process -FilePath $CurrentExe -WorkingDirectory (Split-Path -Parent $CurrentExe)
} else {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $message = "[$timestamp] アップデートのexe置き換えに失敗しました。 $lastError"
    Add-Content -LiteralPath $LogFile -Value $message -Encoding UTF8 -ErrorAction SilentlyContinue
}

Remove-Item -LiteralPath $NewExe -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue
'''
    script_path.write_text(script, encoding="utf-8-sig")

    creation_flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            str(downloaded_exe),
            str(current_exe),
            str(LOG_FILE),
        ],
        cwd=str(current_exe.parent),
        creationflags=creation_flags,
        close_fds=True,
    )
