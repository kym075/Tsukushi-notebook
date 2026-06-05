import json
import re
import urllib.request
from dataclasses import dataclass


LATEST_RELEASE_API_URL = "https://api.github.com/repos/kym075/Tsukushi-notebook/releases/latest"
DEFAULT_RELEASES_URL = "https://github.com/kym075/Tsukushi-notebook/releases/latest"


@dataclass
class UpdateInfo:
    current_version: str
    latest_version: str
    release_url: str
    asset_url: str = ""
    asset_name: str = ""
    asset_sha256: str = ""


def parse_version(version_text):
    numbers = re.findall(r"\d+", version_text or "")
    return tuple(int(number) for number in numbers[:3])


def is_newer_version(latest_version, current_version):
    latest = parse_version(latest_version)
    current = parse_version(current_version)
    if not latest or not current:
        return False

    length = max(len(latest), len(current))
    latest = latest + (0,) * (length - len(latest))
    current = current + (0,) * (length - len(current))
    return latest > current


def fetch_latest_release(timeout=5):
    request = urllib.request.Request(
        LATEST_RELEASE_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "TukushiNote-update-checker",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text_url(url, timeout=5):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "TukushiNote-update-checker"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def find_windows_exe_asset(latest_release):
    assets = latest_release.get("assets") or []
    exe_assets = [
        asset for asset in assets
        if str(asset.get("name", "")).lower().endswith(".exe")
    ]
    if not exe_assets:
        return None

    for asset in exe_assets:
        if str(asset.get("name", "")).lower() == "tukushinote.exe":
            return asset
    return exe_assets[0]


def find_sha256_asset(latest_release, exe_asset):
    if not exe_asset:
        return None

    assets = latest_release.get("assets") or []
    exe_name = str(exe_asset.get("name", "")).lower()
    expected_names = {
        f"{exe_name}.sha256",
        f"{exe_name}.sha256.txt",
        f"{exe_name}.sha256sum",
    }

    for asset in assets:
        asset_name = str(asset.get("name", "")).lower()
        if asset_name in expected_names:
            return asset

    for asset in assets:
        asset_name = str(asset.get("name", "")).lower()
        if asset_name.endswith((".sha256", ".sha256.txt", ".sha256sum")):
            return asset
    return None


def parse_sha256(text):
    match = re.search(r"\b[a-fA-F0-9]{64}\b", text or "")
    return match.group(0).lower() if match else ""


def check_for_update(current_version):
    latest_release = fetch_latest_release()
    latest_version = latest_release.get("tag_name", "")
    release_url = latest_release.get("html_url") or DEFAULT_RELEASES_URL
    exe_asset = find_windows_exe_asset(latest_release)
    sha256_asset = find_sha256_asset(latest_release, exe_asset)
    asset_sha256 = ""

    if not is_newer_version(latest_version, current_version):
        return None

    if sha256_asset and sha256_asset.get("browser_download_url"):
        try:
            sha256_text = fetch_text_url(sha256_asset["browser_download_url"])
            asset_sha256 = parse_sha256(sha256_text)
        except Exception:
            asset_sha256 = ""

    return UpdateInfo(
        current_version=current_version,
        latest_version=latest_version.lstrip("vV"),
        release_url=release_url,
        asset_url=(exe_asset or {}).get("browser_download_url", ""),
        asset_name=(exe_asset or {}).get("name", ""),
        asset_sha256=asset_sha256,
    )
