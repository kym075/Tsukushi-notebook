import os
import json
import shutil
import datetime
from pathlib import Path
from app.core.app_logger import log_error
from app.core.paths import get_app_dir, get_legacy_app_dir, get_sample_data_file


# アプリの保存用フォルダ・ファイル名
APP_DIR = get_app_dir()
DATA_FILE = str(APP_DIR / "notes.json")
SAMPLE_DATA_FILE = str(get_sample_data_file())
IMAGES_DIR = str(APP_DIR / "images")
_last_load_warning = None


def set_load_warning(message):
    global _last_load_warning
    _last_load_warning = message


def consume_load_warning():
    global _last_load_warning
    message = _last_load_warning
    _last_load_warning = None
    return message


def default_data():
    return {
        "categories": ["数学", "英語", "世界史"],
        "notes": [],
        "gemini_api_key": "",
        "use_gemini_api": False,
        "update_snoozed_version": "",
        "update_snoozed_until": "",
    }


def normalize_data(data):
    if not isinstance(data, dict):
        return default_data()

    normalized = default_data()
    normalized.update(data)

    if not isinstance(normalized.get("categories"), list):
        normalized["categories"] = []
    if not isinstance(normalized.get("notes"), list):
        normalized["notes"] = []
    if not isinstance(normalized.get("gemini_api_key"), str):
        normalized["gemini_api_key"] = ""
    normalized["use_gemini_api"] = bool(normalized.get("use_gemini_api"))
    if not isinstance(normalized.get("update_snoozed_version"), str):
        normalized["update_snoozed_version"] = ""
    if not isinstance(normalized.get("update_snoozed_until"), str):
        normalized["update_snoozed_until"] = ""

    return normalized


def load_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return normalize_data(json.load(f))


def ensure_data_location():
    """保存先を作成し、旧exe横データがあれば初回だけAppDataへコピーする。"""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    Path(IMAGES_DIR).mkdir(parents=True, exist_ok=True)
    migrate_legacy_data_if_needed()


def migrate_legacy_data_if_needed():
    legacy_dir = get_legacy_app_dir()
    if legacy_dir is None:
        return

    source_data = legacy_dir / "notes.json"
    target_data = Path(DATA_FILE)
    if target_data.exists() or not source_data.exists():
        return

    try:
        shutil.copy2(source_data, target_data)
    except Exception as e:
        log_error("旧データのAppData移行に失敗しました。", e)
        return

    try:
        copy_legacy_images(legacy_dir / "images", Path(IMAGES_DIR))
    except Exception as e:
        log_error("旧画像データのAppData移行に失敗しました。", e)

    set_load_warning(
        "以前の保存データをAppDataに移行しました。\n\n"
        f"新しい保存先:\n{APP_DIR}\n\n"
        f"元のデータは削除せず、次の場所に残しています:\n{legacy_dir}"
    )


def copy_legacy_images(source_dir, target_dir):
    if not source_dir.is_dir():
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    for item in source_dir.iterdir():
        if not item.is_file():
            continue

        target_path = target_dir / item.name
        if target_path.exists():
            continue
        shutil.copy2(item, target_path)


def backup_broken_data_file():
    if not os.path.exists(DATA_FILE):
        return None

    backup_file = f"{DATA_FILE}.bak"
    if os.path.exists(backup_file):
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_file = f"{DATA_FILE}.{timestamp}.bak"

    shutil.move(DATA_FILE, backup_file)
    return backup_file


def load_initial_data():
    if os.path.exists(SAMPLE_DATA_FILE):
        try:
            return load_json_file(SAMPLE_DATA_FILE)
        except Exception as e:
            log_error("サンプルデータの読み込みに失敗しました。", e)

    return default_data()


def load_data():
    """notes.json をロードする。初回は notes.json.sample があれば初期データとして使う。"""
    if os.path.exists(DATA_FILE):
        try:
            return load_json_file(DATA_FILE)
        except Exception as e:
            backup_file = None
            backup_error = None
            try:
                backup_file = backup_broken_data_file()
            except Exception as backup_exc:
                backup_error = backup_exc
            backup_text = f" バックアップ: {backup_file}" if backup_file else ""
            if backup_error:
                backup_text = f" バックアップ作成失敗: {backup_error}"
            log_error(f"データの読み込みに失敗しました。{backup_text}", e)
            if backup_file:
                set_load_warning(
                    "notes.json を読み込めなかったため、新しいデータで起動しました。\n\n"
                    f"元のファイルは次の場所に退避しています:\n{backup_file}\n\n"
                    "必要な場合は、この .bak ファイルから復旧できます。"
                )
            elif backup_error:
                set_load_warning(
                    "notes.json を読み込めなかったため、新しいデータで起動しました。\n\n"
                    f"元ファイルのバックアップ作成にも失敗しました:\n{backup_error}"
                )
            else:
                set_load_warning(
                    "notes.json を読み込めなかったため、新しいデータで起動しました。"
                )

    return load_initial_data()


def save_data(data):
    """データを notes.json に保存する。途中失敗で壊れにくいよう一時ファイル経由で置き換える。"""
    temp_file = f"{DATA_FILE}.tmp"
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, DATA_FILE)
    except Exception as e:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass
        log_error("データの保存に失敗しました。", e)
