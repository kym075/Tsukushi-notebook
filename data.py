import os
import json
import sys
from pathlib import Path


def get_app_dir():
    """ソース実行時はプロジェクト直下、exe実行時はexeのあるフォルダを返す"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


# アプリの保存用フォルダ・ファイル名
APP_DIR = get_app_dir()
DATA_FILE = str(APP_DIR / "notes.json")
IMAGES_DIR = str(APP_DIR / "images")


def load_data():
    """notes.json からデータをロードする。ファイルが無い場合はデフォルト値を返す"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"データの読み込みに失敗しました: {e}")

    return {
        "categories": ["数学", "英語", "世界史"],
        "notes": [],
        "gemini_api_key": ""
    }


def save_data(data):
    """データを notes.json に保存する"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"データの保存に失敗しました: {e}")
