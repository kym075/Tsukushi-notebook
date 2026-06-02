import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from data import save_data
from ui_config import app_font


class SettingsMixin:
    def open_settings(self):
        current_key = self.data.get("gemini_api_key", "")
        current_use_api = bool(current_key and self.data.get("use_gemini_api", bool(current_key)))

        settings_window = ctk.CTkToplevel(self)
        settings_window.title("⚙ Gemini API設定")
        settings_window.geometry("500x280")
        settings_window.resizable(False, False)
        settings_window.transient(self)
        settings_window.grab_set()

        container = ctk.CTkFrame(settings_window, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=22)
        container.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            container,
            text="🔑 Google Gemini API キー",
            font=app_font(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")

        masked_key = f"{current_key[:6]}...{current_key[-4:]}" if len(current_key) > 10 else current_key
        ctk.CTkLabel(
            container,
            text=f"現在設定: {masked_key if current_key else '未設定'}",
            font=app_font(size=12),
            text_color="gray60",
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 8))

        api_key_entry = ctk.CTkEntry(
            container,
            font=app_font(size=13),
            show="*",
            placeholder_text="APIキーを入力してください",
        )
        api_key_entry.grid(row=2, column=0, sticky="ew")
        api_key_entry.insert(0, current_key)

        use_api_var = tk.BooleanVar(value=current_use_api)
        use_api_switch = ctk.CTkSwitch(
            container,
            text="🧠 AIクイズでGemini APIを使用する",
            variable=use_api_var,
            onvalue=True,
            offvalue=False,
            font=app_font(size=13),
        )
        use_api_switch.grid(row=3, column=0, sticky="w", pady=(18, 6))

        ctk.CTkLabel(
            container,
            text="OFFにすると、APIキーを保存したままモックテストでAIクイズを実行します。",
            font=app_font(size=12),
            text_color="gray60",
            anchor="w",
            wraplength=440,
            justify="left",
        ).grid(row=4, column=0, sticky="ew")

        button_row = ctk.CTkFrame(container, fg_color="transparent")
        button_row.grid(row=5, column=0, sticky="e", pady=(22, 0))

        def save_settings():
            new_key = api_key_entry.get().strip()
            self.data["gemini_api_key"] = new_key
            self.data["use_gemini_api"] = bool(new_key and use_api_var.get())
            save_data(self.data)
            settings_window.destroy()

            if not new_key:
                messagebox.showinfo("設定", "APIキーを解除しました。モックテストでAIクイズを実行します。")
            elif self.data["use_gemini_api"]:
                messagebox.showinfo("設定", "Gemini APIを使用してAIクイズを実行します。")
            else:
                messagebox.showinfo("設定", "APIキーは保存しました。AIクイズはモックテストで実行します。")

        ctk.CTkButton(
            button_row,
            text="キャンセル",
            width=90,
            font=app_font(size=13),
            fg_color="gray40",
            hover_color="gray30",
            command=settings_window.destroy,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            button_row,
            text="保存",
            width=90,
            font=app_font(size=13, weight="bold"),
            command=save_settings,
        ).pack(side="right")

        settings_window.wait_window()

