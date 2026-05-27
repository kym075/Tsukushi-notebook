# つくしノート

勉強メモを管理するデスクトップアプリです。ノートの文字に色やサイズをつけたり、画像を挿入したり、Gemini AIを使って理解度クイズを作ったりできます。

## 機能

- **リッチテキスト**: 文字の色（6種類）やサイズをリアルタイムで変更できます
- **画像挿入**: ノートに画像を直接埋め込めます
- **AIクイズ**: Gemini APIを使って、ノートの内容から3択クイズを自動生成します（APIキー不要のオフラインモードも使えます）
- **ダーク / ライトモード切り替え**
- **自動保存**

## セットアップ

**Python 3.8以上が必要です。**

```bash
pip install -r requirements.txt
```

初回起動時にサンプルデータから始めたい場合は、先にこれを実行してください。

```bash
# Windows
copy notes.json.sample notes.json

# macOS / Linux
cp notes.json.sample notes.json
```

## 起動方法

```bash
python main.py
```

## Gemini APIキーの設定

アプリ左下の「⚙ Gemini API 設定」からAPIキーを入力すると、AIがノートを読んでクイズを生成します。キーなしでも動作します（オフラインのモックモード）。

APIキーは [Google AI Studio](https://aistudio.google.com/) から取得できます。

## ライセンス

MIT
