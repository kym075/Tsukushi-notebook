import os
import sys
from pathlib import Path

APP_NAME = "TukushiNote"


def get_project_dir():
    return Path(__file__).resolve().parents[2]


def get_user_data_dir():
    if os.name == "nt":
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / APP_NAME

    return Path.home() / ".tukushi-note"


def get_app_dir():
    """ソース実行時はプロジェクト直下、exe実行時はユーザーごとの保存先を返す。"""
    if getattr(sys, "frozen", False):
        return get_user_data_dir()
    return get_project_dir()


def get_legacy_app_dir():
    if not getattr(sys, "frozen", False):
        return None

    legacy_dir = Path(sys.executable).resolve().parent
    if legacy_dir == get_app_dir():
        return None
    return legacy_dir


def get_bundle_dir():
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return get_project_dir()


def get_sample_data_file():
    bundled_sample = get_bundle_dir() / "notes.json.sample"
    if bundled_sample.exists():
        return bundled_sample

    return get_project_dir() / "notes.json.sample"
