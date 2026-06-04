# つくしノート

勉強メモを管理するデスクトップアプリです。ノートに見出しや文字色をつけたり、画像を挿入したり、Gemini AIを使って理解度クイズを作ったりできます。

## 機能

- **リッチテキスト**: Yu Gothic UIフォントで、本文・見出しなどの段落スタイル、文字の色（6種類）、太字、下線を変更できます。Ctrlを押しながら複数範囲を選ぶと、まとめて装飾できます
- **画像挿入**: 小・中・大からサイズを選んで、ノートに画像を直接埋め込めます
- **ノート管理**: 名前順、新しい順、古い順、更新順でノートを並び替えられます
- **AIクイズ**: Gemini APIを使って、ノートの内容から3択クイズを自動生成します（APIキー不要のオフラインモードも使えます）
- **アップデート通知**: 起動時にGitHub Releasesを確認し、新しい配布版がある場合は更新を案内します。exe版では自動アップデートも使えます
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

## 配布版exe

GitHub Releases から `TukushiNote.exe` をダウンロードして起動できます。

exe版では、ノートデータはexeと同じフォルダの `notes.json` に保存され、挿入画像は同じフォルダの `images` に保存されます。`notes.json` にはGemini APIキーも保存されるため、GitHubには公開しないでください。

自動アップデートは現在のexeを同じ場所で置き換えるため、同じフォルダにある `notes.json` と `images` はそのまま残ります。手動で新しいexeを別フォルダに置いて起動した場合は、元のフォルダから `notes.json` と `images` を移してください。

更新通知の「あとで」は、チェックを入れた場合だけ同じバージョンの通知を24時間表示しません。チェックを入れない場合は、次回起動時にも通知されます。

## 開発者向け: exeのビルド

Windowsで次を実行すると、`dist/TukushiNote.exe` が生成されます。

```powershell
.\build_exe.ps1
```

GitHubでは `v1.0.0` のような `v*` タグをpushすると、Windows用exeが自動ビルドされ、Releaseに添付されます。

新しい配布版を作る時は、タグ名に合わせて `ui_config.py` の `APP_VERSION` も更新してください。

## Gemini APIキーの設定

アプリ左下の「⚙ Gemini API 設定」からAPIキーを入力できます。APIキーを保存した後でも、設定画面のスイッチでGemini APIを使うか、モックテストでAIクイズを実行するかを選べます。

APIキーは [Google AI Studio](https://aistudio.google.com/) から取得できます。

## ライセンス

MIT
