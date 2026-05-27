import os
import json

# アプリの保存用フォルダ・ファイル名
DATA_FILE = "notes.json"
IMAGES_DIR = "images"


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
