import os
import json
import shutil
import uuid
import datetime
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import google.generativeai as genai
from data import DATA_FILE, IMAGES_DIR, load_data, save_data
from quiz import QuizWindow

# ==========================================
# 1. 定数とデザイン設定 (文字色カラーパレット)
# ==========================================

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


def resource_path(relative_path):
    """PyInstallerで同梱したファイルとソース実行時のファイルを同じ書き方で参照する"""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)



# ==========================================
# 3. メインアプリケーション・クラス
# ==========================================

class NotebookApp(ctk.CTk):
    def _windows_set_titlebar_color(self, color_mode):
        """Windowsでテーマ切替時にウィンドウが一瞬消えるのを防ぐ。"""
        return

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
        self.pending_format_start_index = None
        self.pending_format_after_id = None

        # リッチテキストタイピング用のアクティブな装飾設定
        self.active_typing_color = "default"
        self.active_typing_size = 16

        # ウィンドウの基本設定
        self.title("つくしノート")
        
        # 💡 新機能: アプリのオリジナルアイコン (app_icon.ico) を適用
        try:
            icon_path = resource_path("app_icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
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
            border_color=("#dcdde1", "#3f3f3f"),
            justify="left"
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
            try:
                text_widget = self.editor._textbox
                if text_widget.tag_ranges("sel"):
                    start_idx = text_widget.index("sel.first")
                else:
                    start_idx = text_widget.index("insert")

                if self.pending_format_start_index is None:
                    self.pending_format_start_index = start_idx

                if self.pending_format_after_id is None:
                    self.pending_format_after_id = self.after_idle(self.apply_formatting_to_pending_insert)
            except tk.TclError:
                pass

    def apply_formatting_to_pending_insert(self):
        try:
            self.pending_format_after_id = None
            if self.pending_format_start_index is None:
                return

            text_widget = self.editor._textbox
            start_idx = self.pending_format_start_index
            end_idx = text_widget.index("insert")
            self.pending_format_start_index = None

            if text_widget.compare(start_idx, "==", end_idx):
                return
            if text_widget.compare(start_idx, ">", end_idx):
                start_idx, end_idx = end_idx, start_idx

            color_tag = f"color_{self.active_typing_color}"
            size_tag = f"size_{self.active_typing_size}"

            for ck in FONT_COLORS.keys():
                text_widget.tag_remove(f"color_{ck}", start_idx, end_idx)
            for size in range(12, 33, 2):
                text_widget.tag_remove(f"size_{size}", start_idx, end_idx)

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
                self.left_align_button_text(child)

    def left_align_button_text(self, button):
        """CTkButtonの複数行テキストを左揃えにする"""
        text_label = getattr(button, "_text_label", None)
        if text_label is not None:
            text_label.configure(anchor="w", justify="left")

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

            rename_cat_btn = ctk.CTkButton(cat_frame, text="✎", width=24, height=20, fg_color="transparent", text_color="gray60", hover_color=("gray75", "gray30"), command=lambda c=cat: self.rename_category(c))
            rename_cat_btn.grid(row=0, column=1, padx=(2, 0))

            del_cat_btn = ctk.CTkButton(cat_frame, text="×", width=24, height=20, fg_color="transparent", text_color="gray60", hover_color="#c0392b", command=lambda c=cat: self.delete_category(c))
            del_cat_btn.grid(row=0, column=2, padx=(2, 0))

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
            self.left_align_button_text(note_card)
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
        self.title_entry.xview_moveto(0)

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

    def rename_category(self, category_name):
        dialog = ctk.CTkInputDialog(text="新しい教科（ジャンル）の名前を入力してください:", title="教科名の変更")
        if hasattr(dialog, "_entry"):
            dialog._entry.insert(0, category_name)
            dialog._entry.select_range(0, "end")

        new_name = dialog.get_input()
        if new_name is None:
            return

        self.apply_category_rename(category_name, new_name)

    def apply_category_rename(self, old_name, new_name):
        new_name = new_name.strip()
        if not new_name or new_name == old_name:
            return

        if new_name in self.data["categories"]:
            messagebox.showwarning("警告", "その教科は既に存在します。")
            return

        try:
            category_index = self.data["categories"].index(old_name)
        except ValueError:
            return

        self.data["categories"][category_index] = new_name
        for note in self.data["notes"]:
            if note.get("category") == old_name:
                note["category"] = new_name

        if self.selected_category == old_name:
            self.selected_category = new_name

        save_data(self.data)
        self.refresh_category_list()
        self.refresh_notes_list()

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
            
        if not plain_text.strip():
            messagebox.showinfo("お知らせ", "メモの中身が空っぽです！勉強用のメモを少し書き込んでからクイズを実行してください。")
            return
            
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
# 8. アプリの起動エントリーポイント
# ==========================================

if __name__ == "__main__":
    app = NotebookApp()
    app.mainloop()

