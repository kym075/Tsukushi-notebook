import os
import json
import shutil
import uuid
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import google.generativeai as genai

# ==========================================
# 1. 定数とデザイン設定 (文字色カラーパレット)
# ==========================================

# アプリの保存用フォルダ・ファイル名
DATA_FILE = "notes.json"
IMAGES_DIR = "images"

# 各ノートの「文字色（フォントカラー）」設定
FONT_COLORS = {
    "default": {
        "name": "標準",
        "dark": "#ffffff",      # ダーク時はクリアな白
        "light": "#1e293b"     # ライト時は上品な濃いネイビーグレー
    },
    "rose": {
        "name": "サクラ",
        "dark": "#ff8fa3",      # ダーク時はパステルピンク
        "light": "#b32036"     # ライト時はディープレッド
    },
    "ocean": {
        "name": "オーシャン",
        "dark": "#70a1ff",      # ダーク時は水色
        "light": "#0b52a5"     # ライト時はロイヤルブルー
    },
    "sage": {
        "name": "セージ",
        "dark": "#2ed573",      # ダーク時はグリーン
        "light": "#1b663b"     # ライト時は常盤色
    },
    "amber": {
        "name": "サニー",
        "dark": "#ffa502",      # ダーク時はゴールド
        "light": "#b86e00"     # ライト時はコハク色
    },
    "purple": {
        "name": "ラベンダー",
        "dark": "#d6a2e8",      # ダーク時はパステル紫
        "light": "#5c2a9d"     # ライト時はディープパープル
    }
}

# ==========================================
# 2. データ管理ロジック (JSONヘルパー)
# ==========================================

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


# ==========================================
# 3. メインアプリケーション・クラス
# ==========================================

class NotebookApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # 必要なフォルダの作成
        if not os.path.exists(IMAGES_DIR):
            os.makedirs(IMAGES_DIR)

        # データの初期ロード
        self.data = load_data()
        
        # 状態の管理用変数
        self.selected_category = "全て"      # 現在選択中のジャンル
        self.current_note_id = None         # 現在編集中のノートID
        self.keep_alive_images = []         # Tkinter画像GC対策
        self.auto_save_timer = None         # 自動保存用タイマーID

        # リッチテキストタイピング用のアクティブな装飾設定
        self.active_typing_color = "default"
        self.active_typing_size = 16

        # ウィンドウの基本設定
        self.title("つくしノート")
        
        # 💡 新機能: アプリのオリジナルアイコン (app_icon.ico) を適用
        try:
            if os.path.exists("app_icon.ico"):
                self.iconbitmap("app_icon.ico")
        except Exception as e:
            print(f"アイコン適用に失敗しました: {e}")
            
        self.geometry("1100x700")
        self.minsize(900, 600)

        # 初期表示モードの設定 (最初はダークモードで起動)
        ctk.set_appearance_mode("dark")

        # 画面の分割レイアウト（グリッド）を設定
        self.grid_columnconfigure(0, weight=0, minsize=200)
        self.grid_columnconfigure(1, weight=0, minsize=250)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # UI構築 (ライト・ダークのカラーペアを直接指定)
        self.create_sidebar()
        self.create_notes_list()
        self.create_editor()

        # リッチテキスト装飾タグの初期生成
        self.configure_formatting_tags()

        # 起動時に最初のノートを選択する
        self.refresh_category_list()
        self.refresh_notes_list()
        self.load_first_note()

    # ------------------------------------------
    # UI構築: 各種エリア
    # ------------------------------------------
    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, corner_radius=0, width=200, fg_color=("#e8e8e8", "#161616"))
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_rowconfigure(2, weight=1)

        title_label = ctk.CTkLabel(self.sidebar, text="📚 ジャンル一覧", font=ctk.CTkFont(size=18, weight="bold"), text_color=("#1a1a1a", "#ffffff"))
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        add_cat_btn = ctk.CTkButton(self.sidebar, text="+ 新しい教科を追加", fg_color=("#2980b9", "#1f538d"), hover_color=("#1f6391", "#14375e"), command=self.add_category)
        add_cat_btn.grid(row=1, column=0, padx=15, pady=10, sticky="ew")

        self.cat_scrollable = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.cat_scrollable.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        
        self.theme_switch_var = ctk.StringVar(value="dark")
        self.theme_switch = ctk.CTkSwitch(
            self.sidebar, 
            text="🌙 ダークモード", 
            variable=self.theme_switch_var, 
            onvalue="dark", 
            offvalue="light", 
            text_color=("#1a1a1a", "#ffffff"),
            command=self.toggle_app_theme
        )
        self.theme_switch.grid(row=3, column=0, padx=15, pady=(10, 5), sticky="ew")
        
        settings_btn = ctk.CTkButton(self.sidebar, text="⚙ Gemini API 設定", fg_color=("#7f8c8d", "gray30"), hover_color=("#95a5a6", "gray40"), command=self.open_settings)
        settings_btn.grid(row=4, column=0, padx=15, pady=(5, 20), sticky="ew")

    def create_notes_list(self):
        self.list_frame = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color=("#f0f0f0", "#1c1c1c"))
        self.list_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.list_frame.grid_rowconfigure(2, weight=1)

        self.list_title = ctk.CTkLabel(self.list_frame, text="全て のノート", font=ctk.CTkFont(size=16, weight="bold"), text_color=("#1a1a1a", "#ffffff"))
        self.list_title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        new_note_btn = ctk.CTkButton(self.list_frame, text="📝 新規ノート", fg_color=("#27ae60", "#2b733b"), hover_color=("#219653", "#1c4b26"), command=self.add_new_note)
        new_note_btn.grid(row=1, column=0, padx=15, pady=10, sticky="ew")

        self.notes_scrollable = ctk.CTkScrollableFrame(self.list_frame, fg_color="transparent")
        self.notes_scrollable.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

    def create_editor(self):
        self.editor_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=("#f8f9fa", "#222222"))
        self.editor_frame.grid(row=0, column=2, sticky="nsew", padx=0, pady=0)
        self.editor_frame.grid_rowconfigure(2, weight=1)
        self.editor_frame.grid_columnconfigure(0, weight=1)

        toolbar = ctk.CTkFrame(self.editor_frame, height=50, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))

        font_label = ctk.CTkLabel(toolbar, text="文字サイズ:", font=ctk.CTkFont(size=12), text_color=("#333333", "#e0e0e0"))
        font_label.pack(side="left", padx=5)

        self.font_size_var = tk.IntVar(value=16)
        self.font_size_slider = ctk.CTkSlider(toolbar, from_=12, to=32, number_of_steps=10, variable=self.font_size_var, width=120, command=self.on_font_slider_move)
        self.font_size_slider.pack(side="left", padx=5)

        self.font_size_num_label = ctk.CTkLabel(toolbar, text="16", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#333333", "#ffffff"))
        self.font_size_num_label.pack(side="left", padx=2)

        ctk.CTkLabel(toolbar, text=" | ", text_color="gray50").pack(side="left", padx=8)

        color_label = ctk.CTkLabel(toolbar, text="文字色:", font=ctk.CTkFont(size=12), text_color=("#333333", "#e0e0e0"))
        color_label.pack(side="left", padx=5)

        color_configs = [
            ("default", "#7f8c8d", "標準"),
            ("rose", "#ff6b81", "サクラ"),
            ("ocean", "#54a0ff", "海"),
            ("sage", "#2ed573", "セージ"),
            ("amber", "#ffa502", "サニー"),
            ("purple", "#a55eea", "ラベンダー")
        ]
        for key, hex_color, name in color_configs:
            btn = ctk.CTkButton(toolbar, text="", width=20, height=20, corner_radius=10, fg_color=hex_color, hover_color=hex_color, border_width=1, border_color="white", command=lambda k=key: self.change_typing_color(k))
            btn.pack(side="left", padx=3)

        self.ai_quiz_btn = ctk.CTkButton(toolbar, text="📝 AIクイズ", width=90, fg_color="#8a2be2", hover_color="#6a1b9a", font=ctk.CTkFont(weight="bold"), command=self.start_ai_quiz)
        self.ai_quiz_btn.pack(side="right", padx=5)

        self.insert_img_btn = ctk.CTkButton(toolbar, text="📷 画像挿入", width=90, fg_color="gray30", hover_color="gray40", command=self.insert_image)
        self.insert_img_btn.pack(side="right", padx=5)

        title_row = ctk.CTkFrame(self.editor_frame, fg_color="transparent")
        title_row.grid(row=1, column=0, sticky="ew", padx=15, pady=5)
        title_row.grid_columnconfigure(0, weight=1)

        self.title_entry = ctk.CTkEntry(
            title_row, 
            placeholder_text="無題のノート", 
            font=ctk.CTkFont(size=18, weight="bold"), 
            border_width=1,
            fg_color=("#ffffff", "#2b2b2b"),
            border_color=("#dcdde1", "#3f3f3f")
        )
        self.title_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.title_entry.bind("<KeyRelease>", self.trigger_auto_save)

        delete_note_btn = ctk.CTkButton(title_row, text="🗑 削除", width=70, fg_color="#c0392b", hover_color="#962d22", command=self.delete_current_note)
        delete_note_btn.grid(row=0, column=1, sticky="e")

        self.editor = ctk.CTkTextbox(
            self.editor_frame, 
            font=ctk.CTkFont(size=16), 
            undo=True, 
            wrap="word", 
            border_width=1,
            fg_color=("#ffffff", "#2b2b2b"),
            border_color=("#dcdde1", "#3f3f3f")
        )
        self.editor.grid(row=2, column=0, sticky="nsew", padx=15, pady=(5, 15))
        self.editor.bind("<KeyRelease>", self.trigger_auto_save)
        
        # キー入力でリアルタイム修飾
        self.editor.bind("<KeyPress>", self.on_key_pressed)

    # ==========================================
    # 4. 💫 リッチテキスト装飾エンジン
    # ==========================================

    def configure_formatting_tags(self):
        """文字色とフォントサイズ用の全タグの配色とフォントを現在のテーマに合わせて動的適用する"""
        text_widget = self.editor._textbox
        mode = ctk.get_appearance_mode().lower() # "dark" or "light"
        
        # 1. 文字色タグの適用
        for color_key, color_config in FONT_COLORS.items():
            tag_name = f"color_{color_key}"
            text_hex = color_config[mode]
            text_widget.tag_configure(tag_name, foreground=text_hex)
            
        # 2. フォントサイズタグの適用
        for size in range(12, 33, 2):
            tag_name = f"size_{size}"
            text_widget.tag_configure(tag_name, font=ctk.CTkFont(size=size))

    def on_key_pressed(self, event):
        if event.char and (event.char.isprintable() or event.char in ("\r", "\n", "\t")):
            self.after(1, self.apply_formatting_to_last_typed_char)

    def apply_formatting_to_last_typed_char(self):
        try:
            text_widget = self.editor._textbox
            insert_idx = text_widget.index("insert")
            
            start_idx = f"{insert_idx} - 1 char"
            end_idx = insert_idx
            
            color_tag = f"color_{self.active_typing_color}"
            size_tag = f"size_{self.active_typing_size}"
            
            text_widget.tag_add(color_tag, start_idx, end_idx)
            text_widget.tag_add(size_tag, start_idx, end_idx)
        except Exception as e:
            print(f"タイピングフォーマット適用失敗: {e}")

    def change_typing_color(self, color_key):
        self.active_typing_color = color_key
        
        try:
            text_widget = self.editor._textbox
            if text_widget.tag_ranges("sel"):
                start = text_widget.index("sel.first")
                end = text_widget.index("sel.last")
                
                for ck in FONT_COLORS.keys():
                    text_widget.tag_remove(f"color_{ck}", start, end)
                    
                text_widget.tag_add(f"color_{color_key}", start, end)
                self.trigger_auto_save()
        except tk.TclError:
            pass

    def on_font_slider_move(self, val):
        size = int(float(val))
        self.font_size_num_label.configure(text=str(size))
        self.active_typing_size = size
        
        try:
            text_widget = self.editor._textbox
            if text_widget.tag_ranges("sel"):
                start = text_widget.index("sel.first")
                end = text_widget.index("sel.last")
                
                for s in range(12, 33, 2):
                    text_widget.tag_remove(f"size_{s}", start, end)
                    
                text_widget.tag_add(f"size_{size}", start, end)
                self.trigger_auto_save()
        except tk.TclError:
            pass

    def toggle_app_theme(self):
        """ダーク／ホワイトテーマの滑らかな切り替え"""
        theme = self.theme_switch_var.get()
        if theme == "dark":
            ctk.set_appearance_mode("dark")
            self.theme_switch.configure(text="🌙 ダークモード")
        else:
            ctk.set_appearance_mode("light")
            self.theme_switch.configure(text="☀️ ライトモード")
            
        # 💡 既存のボタン・文字色をその場で直接塗り替える！
        self.configure_formatting_tags()
        
        # 表示中の文字色のみを瞬時に切り替え
        if self.current_note_id:
            note_data = next((n for n in self.data["notes"] if n["id"] == self.current_note_id), None)
            if note_data:
                self.apply_note_font_color(note_data.get("color", "default"))
                
        # 既存ボタンの色だけを直接更新
        self.update_ui_widget_colors_instantly()

    def update_ui_widget_colors_instantly(self):
        """ボタンを全破棄して作り直すのをやめ、既存のボタンの色だけを瞬時に直接塗り替える"""
        mode = ctk.get_appearance_mode().lower()
        active_btn_color = "#3a3a3a" if mode == "dark" else "#d8d8d8"
        text_color = ("#1a1a1a", "#ffffff")
        
        # 1. ジャンルリストのボタン配色を瞬時に塗り替え
        for child in self.cat_scrollable.winfo_children():
            if isinstance(child, ctk.CTkFrame):
                for sub_child in child.winfo_children():
                    if isinstance(sub_child, ctk.CTkButton):
                        if sub_child.cget("text").startswith("• "):
                            cat_name = sub_child.cget("text")[2:]
                            is_active = (self.selected_category == cat_name)
                            bg = active_btn_color if is_active else "transparent"
                            sub_child.configure(fg_color=bg, text_color=text_color, hover_color=("gray75", "gray30"))
            elif isinstance(child, ctk.CTkButton):
                is_active = (self.selected_category == "全て")
                bg = active_btn_color if is_active else "transparent"
                child.configure(fg_color=bg, text_color=text_color, hover_color=("gray75", "gray30"))

        # 2. ノートリストのボタン配色を瞬時に塗り替え
        for child in self.notes_scrollable.winfo_children():
            if isinstance(child, ctk.CTkButton):
                btn_text = child.cget("text")
                title = btn_text.split("\n")[0]
                
                note_data = next((n for n in self.data["notes"] if (n["title"] if n["title"].strip() else "無題のノート") == title), None)
                color_key = "default"
                note_id = None
                if note_data:
                    note_id = note_data["id"]
                    content = note_data.get("content", [])
                    if isinstance(content, list) and len(content) > 0:
                        color_key = content[0].get("color", "default")
                
                font_color_config = FONT_COLORS.get(color_key, FONT_COLORS["default"])
                card_text_color = font_color_config[mode]
                
                is_active = (self.current_note_id == note_id)
                if is_active:
                    bg_color = "#3a3a3a" if mode == "dark" else "#d0d0d0"
                else:
                    bg_color = "#2a2a2a" if mode == "dark" else "#e0e0e0"
                    if color_key == "default":
                        card_text_color = "#888888" if mode == "dark" else "#555555"
                        
                child.configure(fg_color=bg_color, text_color=card_text_color, hover_color=("#c5c5c5", "#4a4a4a"))

    # ==========================================
    # 5. リッチテキストJSONシリアライザ (保存・復元)
    # ==========================================

    def get_rich_content_spans(self):
        """エディタ内の全テキストと装飾状態を解析し、JSON保存可能なリッチスパンのリストとして抽出する"""
        text_widget = self.editor._textbox
        text_str = text_widget.get("1.0", "end-1c")
        if not text_str:
            return []
            
        spans = []
        current_text = ""
        current_color = "default"
        current_size = 16
        
        total_chars = len(text_str)
        for i in range(total_chars):
            char_idx = f"1.0 + {i} chars"
            char = text_widget.get(char_idx)
            
            tags = text_widget.tag_names(char_idx)
            color = "default"
            size = 16
            for tag in tags:
                if tag.startswith("color_"):
                    color = tag.split("_")[1]
                elif tag.startswith("size_"):
                    try:
                        size = int(tag.split("_")[1])
                    except:
                        pass
            
            if i == 0:
                current_text = char
                current_color = color
                current_size = size
            elif color == current_color and size == current_size:
                current_text += char
            else:
                spans.append({
                    "text": current_text,
                    "color": current_color,
                    "size": current_size
                })
                current_text = char
                current_color = color
                current_size = size
                
        if current_text:
            spans.append({
                "text": current_text,
                "color": current_color,
                "size": current_size
            })
            
        for span in spans:
            lines = span["text"].split("\n")
            processed_lines = []
            for line in lines:
                if line.startswith("📷 [画像:") and line.endswith("]"):
                    img_name = line.replace("📷 [画像:", "").replace("]", "").strip()
                    processed_lines.append(f"[image:{img_name}]")
                elif line.strip() == "\ufffc":
                    processed_lines.append("")
                else:
                    processed_lines.append(line)
            span["text"] = "\n".join(processed_lines)
            
        return spans

    def render_note_content(self, spans_or_string):
        """保存データ（リッチスパン）をエディタに完全に復元描画し、画像もインラインレンダリングする"""
        self.editor.configure(state="normal")
        self.editor.delete("1.0", "end")
        self.keep_alive_images.clear()
        
        if isinstance(spans_or_string, str):
            spans = [{"text": spans_or_string, "color": "default", "size": 16}]
        else:
            spans = spans_or_string
            
        text_widget = self.editor._textbox
        
        for span in spans:
            text = span.get("text", "")
            color = span.get("color", "default")
            size = span.get("size", 16)
            
            color_tag = f"color_{color}"
            size_tag = f"size_{size}"
            
            lines = text.split("\n")
            for idx, line in enumerate(lines):
                if line.startswith("[image:") and line.endswith("]"):
                    img_filename = line[7:-1]
                    img_path = os.path.join(IMAGES_DIR, img_filename)
                    if os.path.exists(img_path):
                        try:
                            pil_img = Image.open(img_path)
                            orig_w, orig_h = pil_img.size
                            new_w = 350
                            new_h = int((new_w / orig_w) * orig_h)
                            pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                            
                            tk_img = ImageTk.PhotoImage(pil_img)
                            self.keep_alive_images.append(tk_img)
                            
                            start_pos = text_widget.index(tk.INSERT)
                            text_widget.insert(tk.INSERT, f"📷 [画像: {img_filename}]\n")
                            end_pos = text_widget.index(tk.INSERT)
                            text_widget.tag_add("image_tag_style", start_pos, end_pos)
                            
                            text_widget.image_create(tk.INSERT, image=tk_img)
                            text_widget.insert(tk.INSERT, "\n\n")
                        except Exception as e:
                            text_widget.insert(tk.INSERT, f"[画像の描画失敗: {img_filename}]\n")
                    else:
                        text_widget.insert(tk.INSERT, f"[画像が見つかりません: {img_filename}]\n")
                else:
                    start_pos = text_widget.index(tk.INSERT)
                    text_widget.insert(tk.INSERT, line)
                    end_pos = text_widget.index(tk.INSERT)
                    
                    text_widget.tag_add(color_tag, start_pos, end_pos)
                    text_widget.tag_add(size_tag, start_pos, end_pos)
                    
                    if idx < len(lines) - 1:
                        start_nl = text_widget.index(tk.INSERT)
                        text_widget.insert(tk.INSERT, "\n")
                        end_nl = text_widget.index(tk.INSERT)
                        text_widget.tag_add(color_tag, start_nl, end_nl)
                        text_widget.tag_add(size_tag, start_nl, end_nl)

        text_widget.tag_configure("image_tag_style", foreground="gray50", font=ctk.CTkFont(size=11, slant="italic"))

    # ==========================================
    # 6. リスト更新 ＆ ノート読込・保存
    # ==========================================

    def refresh_category_list(self):
        for child in self.cat_scrollable.winfo_children():
            child.destroy()

        mode = ctk.get_appearance_mode().lower()
        active_btn_color = "#3a3a3a" if mode == "dark" else "#d8d8d8"
        text_color = ("#1a1a1a", "#ffffff")

        all_btn_color = active_btn_color if self.selected_category == "全て" else "transparent"
        all_btn = ctk.CTkButton(self.cat_scrollable, text="📂 全て表示", anchor="w", text_color=text_color, fg_color=all_btn_color, hover_color=("gray75", "gray30"), command=lambda: self.select_category("全て"))
        all_btn.pack(fill="x", pady=2)

        for cat in self.data["categories"]:
            btn_color = active_btn_color if self.selected_category == cat else "transparent"
            
            cat_frame = ctk.CTkFrame(self.cat_scrollable, fg_color="transparent")
            cat_frame.pack(fill="x", pady=1)
            cat_frame.grid_columnconfigure(0, weight=1)

            cat_btn = ctk.CTkButton(cat_frame, text=f"• {cat}", anchor="w", text_color=text_color, fg_color=btn_color, hover_color=("gray75", "gray30"), command=lambda c=cat: self.select_category(c))
            cat_btn.grid(row=0, column=0, sticky="ew")

            del_cat_btn = ctk.CTkButton(cat_frame, text="×", width=20, height=20, fg_color="transparent", text_color="gray60", hover_color="#c0392b", command=lambda c=cat: self.delete_category(c))
            del_cat_btn.grid(row=0, column=1, padx=2)

    def refresh_notes_list(self):
        for child in self.notes_scrollable.winfo_children():
            child.destroy()

        self.list_title.configure(text=f"{self.selected_category} のノート")

        filtered_notes = []
        for note in self.data["notes"]:
            if self.selected_category == "全て" or note.get("category") == self.selected_category:
                filtered_notes.append(note)

        filtered_notes.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

        if not filtered_notes:
            no_note_label = ctk.CTkLabel(self.notes_scrollable, text="ノートがありません", text_color="gray60", font=ctk.CTkFont(size=12, slant="italic"))
            no_note_label.pack(pady=20)
            return

        mode = ctk.get_appearance_mode().lower()

        for note in filtered_notes:
            note_id = note["id"]
            title = note["title"] if note["title"].strip() else "無題のノート"
            
            color_key = "default"
            content = note.get("content", [])
            if isinstance(content, list) and len(content) > 0:
                color_key = content[0].get("color", "default")
            
            font_color_config = FONT_COLORS.get(color_key, FONT_COLORS["default"])
            card_text_color = font_color_config[mode]
            
            if self.current_note_id == note_id:
                bg_color = "#3a3a3a" if mode == "dark" else "#d0d0d0"
            else:
                bg_color = "#2a2a2a" if mode == "dark" else "#e0e0e0"
                if color_key == "default":
                    card_text_color = "#888888" if mode == "dark" else "#555555"

            note_card = ctk.CTkButton(
                self.notes_scrollable, 
                text=f"{title}\n🕒 {note.get('updated_at', '')[:16]}", 
                anchor="w",
                font=ctk.CTkFont(size=13),
                fg_color=bg_color,
                text_color=card_text_color,
                hover_color=("#c5c5c5", "#4a4a4a"),
                height=50,
                command=lambda nid=note_id: self.select_note(nid)
            )
            note_card.pack(fill="x", pady=3)

    def select_category(self, category_name):
        self.selected_category = category_name
        self.refresh_category_list()
        self.refresh_notes_list()
        self.load_first_note()

    def load_first_note(self):
        filtered_notes = [n for n in self.data["notes"] if self.selected_category == "全て" or n.get("category") == self.selected_category]
        if filtered_notes:
            filtered_notes.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            self.select_note(filtered_notes[0]["id"])
        else:
            self.current_note_id = None
            self.title_entry.delete(0, "end")
            self.title_entry.configure(state="disabled")
            self.editor.delete("1.0", "end")
            self.editor.configure(state="disabled")

    def select_note(self, note_id):
        if self.auto_save_timer:
            self.after_cancel(self.auto_save_timer)
            self.auto_save_timer = None
        self.save_current_note_immediately()

        self.current_note_id = note_id
        
        note_data = next((n for n in self.data["notes"] if n["id"] == note_id), None)
        if not note_data:
            return

        self.title_entry.configure(state="normal")
        self.editor.configure(state="normal")

        # タイトルのセット
        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, note_data["title"])

        # 初期アクティブ装飾サイズの設定
        content_data = note_data.get("content", [])
        initial_size = 16
        initial_color = "default"
        if isinstance(content_data, list) and len(content_data) > 0:
            initial_size = content_data[0].get("size", 16)
            initial_color = content_data[0].get("color", "default")
            
        self.font_size_var.set(initial_size)
        self.font_size_num_label.configure(text=str(initial_size))
        self.active_typing_size = initial_size
        self.active_typing_color = initial_color

        # タグの構成を再同期
        self.configure_formatting_tags()

        # 本文と画像のデコード描画
        self.render_note_content(note_data["content"])

        # リストハイライト更新
        self.refresh_notes_list()

    def apply_note_font_color(self, color_key):
        """現在のアクティブなノートに設定された文字色をエディタに適用する"""
        mode = ctk.get_appearance_mode().lower()
        color_config = FONT_COLORS.get(color_key, FONT_COLORS["default"])
        text_hex = color_config[mode]
        self.editor.configure(text_color=text_hex)
        self.title_entry.configure(text_color=text_hex)
        self.editor._textbox.configure(insertbackground=text_hex)

    # ------------------------------------------
    # 自動保存 ＆ 削除
    # ------------------------------------------
    def trigger_auto_save(self, event=None):
        if not self.current_note_id:
            return
        if self.auto_save_timer:
            self.after_cancel(self.auto_save_timer)
        self.auto_save_timer = self.after(1000, self.auto_save_current_note)

    def auto_save_current_note(self):
        self.auto_save_timer = None
        self.save_current_note_immediately()
        self.refresh_notes_list()

    def save_current_note_immediately(self):
        if not self.current_note_id:
            return

        note_data = next((n for n in self.data["notes"] if n["id"] == self.current_note_id), None)
        if note_data:
            note_data["title"] = self.title_entry.get()
            note_data["content"] = self.get_rich_content_spans()
            note_data["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_data(self.data)

    def add_category(self):
        dialog = ctk.CTkInputDialog(text="新しい教科（ジャンル）の名前を入力してください:", title="教科の追加")
        name = dialog.get_input()
        
        if name and name.strip():
            name = name.strip()
            if name in self.data["categories"]:
                messagebox.showwarning("警告", "その教科は既に存在します。")
                return
            
            self.data["categories"].append(name)
            save_data(self.data)
            
            self.selected_category = name
            self.refresh_category_list()
            self.refresh_notes_list()
            self.load_first_note()

    def delete_category(self, category_name):
        if not messagebox.askyesno("ジャンルの削除", f"「{category_name}」を削除しますか？\n(このジャンル内のメモは削除されず『未分類』へ移動します)"):
            return

        self.data["categories"].remove(category_name)
        
        for note in self.data["notes"]:
            if note.get("category") == category_name:
                note["category"] = "未分類"

        if "未分類" not in self.data["categories"] and any(n.get("category") == "未分類" for n in self.data["notes"]):
            self.data["categories"].append("未分類")

        save_data(self.data)
        
        self.selected_category = "全て"
        self.refresh_category_list()
        self.refresh_notes_list()
        self.load_first_note()

    def add_new_note(self):
        new_id = str(uuid.uuid4())
        
        initial_cat = self.selected_category
        if initial_cat == "全て":
            initial_cat = self.data["categories"][0] if self.data["categories"] else "未分類"

        new_note = {
            "id": new_id,
            "title": "",
            "content": [{"text": "", "color": "default", "size": 16}], 
            "category": initial_cat,
            "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        self.data["notes"].append(new_note)
        save_data(self.data)

        self.select_note(new_id)

    def delete_current_note(self):
        if not self.current_note_id:
            return

        if not messagebox.askyesno("ノートの削除", "このノートを本当に削除しますか？"):
            return

        self.data["notes"] = [n for n in self.data["notes"] if n["id"] != self.current_note_id]
        save_data(self.data)

        self.current_note_id = None
        self.refresh_notes_list()
        self.load_first_note()

    def insert_image(self):
        if not self.current_note_id:
            return

        file_path = filedialog.askopenfilename(
            title="挿入する画像を選択",
            filetypes=[("画像ファイル", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if not file_path:
            return

        try:
            ext = os.path.splitext(file_path)[1]
            unique_name = f"{uuid.uuid4()}{ext}"
            dest_path = os.path.join(IMAGES_DIR, unique_name)
            shutil.copy(file_path, dest_path)

            tag_text = f"\n[image:{unique_name}]\n"
            self.editor.insert(tk.INSERT, tag_text)
            self.save_current_note_immediately()
            self.render_note_content(self.get_rich_content_spans())

        except Exception as e:
            messagebox.showerror("エラー", f"画像の挿入に失敗しました: {e}")


    # ==========================================
    # 7. 🤖 AIクイズ (理解度テスト) 機能
    # ==========================================

    def start_ai_quiz(self):
        if not self.current_note_id:
            return

        self.save_current_note_immediately()
        
        note_data = next((n for n in self.data["notes"] if n["id"] == self.current_note_id), None)
        if not note_data:
            return
            
        plain_text = ""
        content_spans = note_data.get("content", [])
        if isinstance(content_spans, list):
            for span in content_spans:
                plain_text += span.get("text", "")
        else:
            plain_text = content_spans 
            
        # 💡 新機能: 問題数の選択ダイアログを表示
        dialog = ctk.CTkInputDialog(
            text="作成するクイズの問題数を入力してください (1〜10問):", 
            title="問題数の選択"
        )
        input_val = dialog.get_input()
        
        # キャンセルされた場合は処理を中断
        if input_val is None:
            return
            
        # 入力値のバリデーション
        try:
            num_questions = int(input_val.strip())
            if num_questions < 1:
                num_questions = 3
            elif num_questions > 10:
                num_questions = 10
        except ValueError:
            num_questions = 3 # エラーや無効な入力時はデフォルト3問にする

        QuizWindow(self, plain_text, num_questions)

    def open_settings(self):
        current_key = self.data.get("gemini_api_key", "")
        masked_key = f"{current_key[:6]}...{current_key[-4:]}" if len(current_key) > 10 else current_key
        
        dialog = ctk.CTkInputDialog(
            text=f"Google Gemini API キーを入力してください。\n(現在設定: {masked_key if current_key else '未設定'})\n\n※キーはローカルの notes.json にのみ安全に保存されます。\n空のまま決定するとモックテストモードで動作します。", 
            title="Gemini API設定"
        )
        new_key = dialog.get_input()
        
        if new_key is not None:
            self.data["gemini_api_key"] = new_key.strip()
            save_data(self.data)
            if new_key.strip():
                messagebox.showinfo("成功", "Gemini API キーを設定しました！次回から本物のAIクイズが生成されます。")
            else:
                messagebox.showinfo("お知らせ", "APIキーを解除しました。モッククイズモードに戻ります。")


# ==========================================
# 8. AIクイズ表示用 ポップアップ
# ==========================================

class QuizWindow(ctk.CTkToplevel):
    def __init__(self, parent, note_content, num_questions=3):
        super().__init__(parent)
        self.parent = parent
        self.note_content = note_content
        self.num_questions = num_questions
        
        self.title("🧠 AI理解度クイズ")
        self.geometry("650x600")
        self.minsize(600, 550)
        
        self.grab_set()
        
        # 💡 改善: 右上の「×」ボタンで閉じられた時も、安全な終了関数を実行するように設定
        self.protocol("WM_DELETE_WINDOW", self.close_quiz)
        
        self.quiz_questions = []
        self.current_q_index = 0
        self.selected_ans_var = tk.IntVar(value=-1)
        self.score = 0
        
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=25, pady=25)
        
        self.loading_label = ctk.CTkLabel(
            self.container, 
            text="🤖 AI先生がメモを読んで\n理解度テストを考えています...\n\n(しばらくお待ちください)", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.loading_label.pack(expand=True)
        
        self.after(500, self.generate_quiz_data)

    def close_quiz(self):
        """クイズウィンドウを安全かつエラー無く破棄する"""
        try:
            self.grab_release()
        except:
            pass
        # 💡 解決策: 現在のボタンイベント処理が完全に終了した直後（10ms後）に破棄を予約する（クラッシュ防止）
        self.after(10, self.destroy)

    def generate_quiz_data(self):
        api_key = self.parent.data.get("gemini_api_key", "")
        
        if api_key:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-2.5-flash")
                
                # 💡 改善: 毎回違う切り口やバリエーションの問題を作成するようにプロンプトを強化！
                prompt = f"""
あなたはプロの家庭教師です。以下の生徒が書いた勉強メモを読み、理解度を測るための「3択問題」を{self.num_questions}問作成してください。
毎回クイズを実行するたび、問題の切り口や出題するポイント、切り口をランダムに変えて、常に新鮮で異なる問題を作ってください。

必ず出力は【以下の指定フォーマットの純粋なJSONデータのみ】にしてください。余計な説明文や```jsonなどのMarkdownタグは一切含めないでください。

【JSONフォーマット】
[
  {{
    "question": "問題文をここに記述（例: ○○について, 正しい説明はどれですか？）",
    "choices": ["選択肢1", "選択肢2", "選択肢3"],
    "answer_index": 正解のインデックス番号を0〜2の整数で指定 (0=選択肢1, 1=選択肢2, 2=選択肢3),
    "explanation": "なぜこれが正解なのかの分かりやすい解説を記述"
  }}
]

【生徒の勉強メモ内容】
{self.note_content}
"""
                # 💡 改善: temperature=0.8 を設定し、AIのクイズ生成のランダム性と多様性を大幅に向上させます
                response = model.generate_content(
                    prompt, 
                    generation_config={"temperature": 0.8}
                )
                text = response.text.strip()
                
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                text = text.strip()
                
                self.quiz_questions = json.loads(text)
                
            except Exception as e:
                print(f"Gemini APIによるクイズ生成失敗: {e}\nモッククイズに切り替えます。")
                self.generate_mock_quiz()
        else:
            self.generate_mock_quiz()

        # 💡 改良: クイズデータが生成された後、すべての問題の選択肢（Choices）の順序をランダムにシャッフルし、
        # 正解のインデックス（answer_index）を自動で追従させる！
        # これにより、お試しモックモードでも、毎回答えの位置（A, B, C）が変化し、新鮮なクイズ体験ができます。
        import random
        if self.quiz_questions:
            for q in self.quiz_questions:
                if "choices" in q and "answer_index" in q:
                    choices = q["choices"]
                    correct_ans = choices[q["answer_index"]]
                    random.shuffle(choices)
                    q["answer_index"] = choices.index(correct_ans)

        self.loading_label.pack_forget()
        
        if self.quiz_questions:
            self.show_question()
        else:
            error_lbl = ctk.CTkLabel(
                self.container, 
                text="ローカルクイズを生成できませんでした。\n\n"
                     "【クイズを作成するためのメモの書き方例】\n"
                     "■ 重要語句 : その意味や説明\n"
                     "■ 公式名 ➔ 公式の内容や解説\n"
                     "■ 英単語 【品詞】 日本語訳\n\n"
                     "このようにメモ帳に書き込んでいただくと、自動的に3択問題が作成されます！\n"
                     "または、Gemini APIキーを設定すると、AIが内容を読み取って自動で問題を作成します。", 
                font=ctk.CTkFont(size=14),
                justify="left"
            )
            error_lbl.pack(expand=True, pady=20)

    def generate_mock_quiz(self):
        """
        【完全動的ローカルクイズ生成エンジン】
        メモ内に書かれた「重要語句」や「公式」の箇条書きを完璧に解析し、
        完全にメモ内容に基づいたオリジナルの3択クイズを100%ローカル（オフライン）で作成します。
        汎用的な定型問題は一切排除します。
        """
        self.quiz_questions = []
        
        # メモ内の語句と定義を解析抽出する辞書
        # 例: {"analyze": "〜を分析する", "二次方程式の解の公式": "x = (-b ± √(b^2 - 4ac)) / 2a"}
        definitions = {}
        
        lines = self.note_content.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # パターンA: ■ 単語 【品詞】 意味
            if "【" in line and "】" in line:
                parts = line.split("【")
                term = parts[0].replace("■", "").replace("-", "").strip()
                meaning = "【" + parts[1].strip()
                if term and meaning:
                    definitions[term] = meaning
                    continue
                    
            # パターンB: ■ 単語 : 意味
            if ":" in line or "：" in line:
                separator = ":" if ":" in line else "："
                parts = line.split(separator, 1)
                term = parts[0].replace("■", "").replace("-", "").strip()
                meaning = parts[1].strip()
                if term and meaning:
                    definitions[term] = meaning
                    continue
                    
            # パターンC: ■ 単語 ➔ 意味
            if "➔" in line or "→" in line:
                separator = "➔" if "➔" in line else "→"
                parts = line.split(separator, 1)
                term = parts[0].replace("■", "").replace("-", "").strip()
                meaning = parts[1].strip()
                if term and meaning:
                    definitions[term] = meaning
                    continue
                    
            # パターンD: ■ 単語（改行）次の行に説明
            if line.startswith("■") and len(line) < 30:
                term = line.replace("■", "").strip()
                # 次の非空行を意味とみなす
                idx = lines.index(line)
                meaning = ""
                for next_line in lines[idx+1:]:
                    if next_line.strip() and not next_line.strip().startswith("■"):
                        meaning = next_line.strip()
                        break
                if term and meaning:
                    definitions[term] = meaning

        # 抽出した定義リストをもとに動的クイズを組み立てる
        all_terms = list(definitions.keys())
        
        # 1. 抽出できた重要語句から直接問題を作る！
        for term, meaning in definitions.items():
            # 誤り選択肢（他の語句の意味をダミーにする）
            distractors = []
            for other_term, other_meaning in definitions.items():
                if other_term != term:
                    distractors.append(other_meaning)
            
            # ダミーの補強
            fallback_dummies = [
                "〜を合成または統合すること",
                "特に意味を持たない一時的な状態",
                "逆の性質を持つ要素の組み合わせ",
                "全く関係の無い無作為な記述",
                "古いシステムから新しいシステムへの移行"
            ]
            while len(distractors) < 2:
                dummy = fallback_dummies[len(distractors) % len(fallback_dummies)]
                if dummy not in distractors:
                    distractors.append(dummy)
                    
            choices = [meaning, distractors[0], distractors[1]]
            
            self.quiz_questions.append({
                "question": f"メモに書かれた『 {term} 』について、正しい説明または定義はどれですか？",
                "choices": choices,
                "answer_index": 0, # 後で自動シャッフルされるので0固定でOK
                "explanation": f"正解は『{meaning}』です！あなたの書いたメモの中にしっかりと記録されています。素晴らしい学習成果です！"
            })

        # 2. 定義が少なすぎて3問未満の場合の、メモ全体に基づく問題
        if len(self.quiz_questions) < 3:
            # 英語用の特製問題（含まれている場合）
            if ("analyze" in self.note_content.lower() or "英語" in self.note_content) and not any("analyze" in q["question"] for q in self.quiz_questions):
                self.quiz_questions.append({
                    "question": "英単語『analyze』の正しい日本語訳はどれでしょうか？",
                    "choices": ["〜を分析・調査する", "〜を合成または統合する", "〜を否定または拒絶する"],
                    "answer_index": 0,
                    "explanation": "『analyze』は『〜を分析する』という意味の重要な動詞です。ITやリバースエンジニアリングで頻出の言葉です！"
                })
                
            # 数学用の特製問題（含まれている場合）
            if ("公式" in self.note_content or "数学" in self.note_content or "sin" in self.note_content.lower()) and not any("三角関数" in q["question"] for q in self.quiz_questions):
                self.quiz_questions.append({
                    "question": "数学の基本三角関数において、常に成り立つ公式は次のうちどれですか？",
                    "choices": [
                        "sin^2(x) + cos^2(x) = 1",
                        "sin^2(x) - cos^2(x) = 1",
                        "sin(x) + cos(x) = 1"
                    ],
                    "answer_index": 0,
                    "explanation": "正解は『sin^2(x) + cos^2(x) = 1』です！これは三平方の定理から導き出される、三角関数の最重要公式です。"
                })

        # 指定された問題数になるように調整（最大指定数）
        self.quiz_questions = self.quiz_questions[:self.num_questions]

    def show_question(self):
        """現在のアクティブなクイズ問題を描画する"""
        for child in self.container.winfo_children():
            child.destroy()

        q_data = self.quiz_questions[self.current_q_index]
        
        prog_lbl = ctk.CTkLabel(
            self.container, 
            text=f"問題 {self.current_q_index + 1} / {len(self.quiz_questions)}", 
            text_color="gray60",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        prog_lbl.pack(anchor="w", pady=(0, 5))

        q_text = ctk.CTkLabel(
            self.container, 
            text=q_data["question"], 
            font=ctk.CTkFont(size=18, weight="bold"), 
            wraplength=580, 
            justify="left"
        )
        q_text.pack(anchor="w", pady=(0, 20))

        self.choices_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.choices_frame.pack(fill="x", pady=10)

        self.selected_ans_var.set(-1)

        for idx, choice in enumerate(q_data["choices"]):
            rb = ctk.CTkRadioButton(
                self.choices_frame, 
                text=choice, 
                variable=self.selected_ans_var, 
                value=idx,
                font=ctk.CTkFont(size=15)
            )
            rb.pack(anchor="w", fill="x", padx=10, pady=12)

        self.submit_btn = ctk.CTkButton(
            self.container, 
            text="この答えで回答する ➔", 
            fg_color="#8a2be2", 
            hover_color="#6a1b9a", 
            height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.submit_answer
        )
        self.submit_btn.pack(fill="x", pady=25)

    def submit_answer(self):
        selected = self.selected_ans_var.get()
        if selected == -1:
            messagebox.showwarning("警告", "選択肢を1つ選んでください。")
            return

        q_data = self.quiz_questions[self.current_q_index]
        correct_idx = q_data["answer_index"]
        is_correct = (selected == correct_idx)

        if is_correct:
            self.score += 1

        # 💡 UI改善: スペースを空けるため、回答し終わった「回答ボタン」と「選択肢」は画面から消去します！
        self.submit_btn.pack_forget()
        self.choices_frame.pack_forget()

        result_title = "🎉 正解です！" if is_correct else "❌ 残念、不正解..."
        result_color = "#2ecc71" if is_correct else "#e74c3c"
        
        # 💡 UI改善: 画面圧迫を防ぐため expand=True を外します
        explanation_box = ctk.CTkFrame(self.container, fg_color=("#eaeaea", "#2b2b2b"), border_width=1, border_color=result_color)
        explanation_box.pack(fill="x", pady=10)
        
        # 💡 改善: タイトルや正解テキストが非常に長い場合に改行されるよう wraplength=540 を設定！
        lbl_title = ctk.CTkLabel(
            explanation_box, 
            text=result_title, 
            text_color=result_color, 
            font=ctk.CTkFont(size=16, weight="bold"),
            wraplength=540,
            justify="left"
        )
        lbl_title.pack(anchor="w", padx=15, pady=(10, 5))

        correct_text = q_data["choices"][correct_idx]
        lbl_correct = ctk.CTkLabel(
            explanation_box, 
            text=f"【正解】 {correct_text}", 
            font=ctk.CTkFont(size=14, weight="bold"), 
            text_color=("#1c1c1c", "#ffffff"),
            wraplength=540,
            justify="left"
        )
        lbl_correct.pack(anchor="w", padx=15, pady=2)

        lbl_exp = ctk.CTkLabel(explanation_box, text=q_data["explanation"], font=ctk.CTkFont(size=13), wraplength=560, justify="left", text_color=("#333333", "#e0e0e0"))
        lbl_exp.pack(anchor="w", padx=15, pady=(5, 10))

        if self.current_q_index + 1 < len(self.quiz_questions):
            next_btn_text = "次の問題へ ➔"
            next_cmd = self.next_question
        else:
            next_btn_text = "最終結果を見る ➔"
            next_cmd = self.show_final_results

        next_btn = ctk.CTkButton(
            self.container, 
            text=next_btn_text, 
            fg_color="gray30", 
            hover_color="gray40", 
            height=45, 
            font=ctk.CTkFont(size=15, weight="bold"),
            command=next_cmd
        )
        next_btn.pack(fill="x", pady=10)

    def next_question(self):
        self.current_q_index += 1
        self.show_question()

    def show_final_results(self):
        for child in self.container.winfo_children():
            child.destroy()

        total = len(self.quiz_questions)
        pct = int((self.score / total) * 100)
        
        if pct == 100:
            msg = "パーフェクト！完璧にメモの内容をマスターしています！天才ですね！✨"
            color = "#2ecc71"
        elif pct >= 60:
            msg = "素晴らしい！かなり高い理解度です。間違えた部分をメモで見直せば完璧です！👍"
            color = "#3498db"
        else:
            msg = "伸びしろがたくさんあります！もう一度ノートを読み返して、再チャレンジしてみましょう！📚"
            color = "#e67e22"

        score_lbl = ctk.CTkLabel(
            self.container, 
            text=f"結果発表\n\nあなたのスコア\n{self.score} / {total} 問正解 ({pct}%)", 
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=color
        )
        score_lbl.pack(pady=20)

        msg_lbl = ctk.CTkLabel(
            self.container, 
            text=msg, 
            font=ctk.CTkFont(size=15), 
            wraplength=520,
            text_color=("#333333", "#ffffff")
        )
        msg_lbl.pack(pady=10)

        # 💡 安全なクローズを呼び出すボタンへ変更！
        close_btn = ctk.CTkButton(
            self.container, 
            text="テストを終了してノートに戻る", 
            fg_color="#1f538d", 
            hover_color="#14375e", 
            height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.close_quiz
        )
        close_btn.pack(fill="x", side="bottom", pady=15)


# ==========================================
# 9. アプリの起動エントリーポイント
# ==========================================

if __name__ == "__main__":
    app = NotebookApp()
    app.mainloop()
