import datetime
import os
import queue
import threading
import tkinter as tk
import webbrowser

import customtkinter as ctk

from app.core.app_logger import log_error
from app.updates.auto_updater import download_update_exe, is_auto_update_supported, launch_update_installer
from app.core.data import save_data
from app.core.ui_config import APP_VERSION, app_font
from app.updates.update_checker import check_for_update


UPDATE_SNOOZE_HOURS = 24


class UpdateMixin:
    def init_update_state(self):
        self.update_check_after_id = None
        self.update_check_queue = queue.Queue(maxsize=1)
        self.update_window = None

    def start_update_check(self):
        self.update_check_after_id = None
        worker = threading.Thread(target=self.run_update_check, daemon=True)
        worker.start()
        self.update_check_after_id = self.after(200, self.poll_update_check_result)

    def run_update_check(self):
        update_info = None
        try:
            update_info = check_for_update(APP_VERSION)
        except Exception as e:
            log_error("アップデート確認に失敗しました。", e)

        try:
            self.update_check_queue.put_nowait(update_info)
        except queue.Full:
            pass

    def poll_update_check_result(self):
        try:
            update_info = self.update_check_queue.get_nowait()
        except queue.Empty:
            self.update_check_after_id = self.after(200, self.poll_update_check_result)
            return

        self.update_check_after_id = None
        if update_info and not self.is_update_notification_snoozed(update_info):
            self.show_update_notification(update_info)

    def is_update_notification_snoozed(self, update_info):
        if self.data.get("update_snoozed_version") != update_info.latest_version:
            return False

        snoozed_until_text = self.data.get("update_snoozed_until", "")
        try:
            snoozed_until = datetime.datetime.fromisoformat(snoozed_until_text)
        except (TypeError, ValueError):
            return False

        return datetime.datetime.now() < snoozed_until

    def widget_exists(self, widget):
        try:
            return bool(widget.winfo_exists())
        except tk.TclError:
            return False

    def show_update_notification(self, update_info):
        if self.update_window is not None and self.widget_exists(self.update_window):
            self.update_window.focus()
            return

        window = ctk.CTkToplevel(self)
        self.update_window = window
        window.title("アップデートがあります")
        window.geometry("500x350")
        window.resizable(False, False)
        window.transient(self)

        container = ctk.CTkFrame(window, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=22)
        container.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            container,
            text="新しいバージョンがあります",
            font=app_font(size=18, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")

        auto_update_available = is_auto_update_supported(update_info)
        if auto_update_available:
            update_text = "アップデートすると、現在のexeを置き換えて再起動します。ノートデータはそのまま残ります。"
        else:
            update_text = "アップデートする場合は、下のリンクから最新版をダウンロードしてください。"

        message = f"現在のバージョン: {update_info.current_version}\n最新バージョン: {update_info.latest_version}\n\n{update_text}"
        ctk.CTkLabel(
            container,
            text=message,
            font=app_font(size=13),
            justify="left",
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(12, 10))

        release_url_entry = ctk.CTkEntry(container, font=app_font(size=12))
        release_url_entry.grid(row=2, column=0, sticky="ew")
        release_url_entry.insert(0, update_info.release_url)
        release_url_entry.configure(state="readonly")

        snooze_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            container,
            text="あとでを押したら24時間この通知を表示しない",
            variable=snooze_var,
            font=app_font(size=12),
        ).grid(row=3, column=0, sticky="w", pady=(10, 0))

        status_label = ctk.CTkLabel(
            container,
            text="",
            font=app_font(size=12),
            text_color=("#555555", "#bdbdbd"),
            anchor="w",
        )
        status_label.grid(row=4, column=0, sticky="ew", pady=(10, 0))

        button_row = ctk.CTkFrame(container, fg_color="transparent")
        button_row.grid(row=5, column=0, sticky="e", pady=(18, 0))

        ctk.CTkButton(
            button_row,
            text="あとで",
            width=90,
            font=app_font(size=13),
            fg_color="gray40",
            hover_color="gray30",
            command=lambda: self.dismiss_update_notification(update_info, snooze_var, window),
        ).pack(side="right", padx=(8, 0))

        if auto_update_available:
            update_button = ctk.CTkButton(
                button_row,
                text="アップデート",
                width=130,
                font=app_font(size=13, weight="bold"),
            )
            update_button.configure(
                command=lambda: self.start_auto_update(update_info, window, status_label, update_button)
            )
            update_button.pack(side="right")
        else:
            ctk.CTkButton(
                button_row,
                text="リリースページを開く",
                width=160,
                font=app_font(size=13, weight="bold"),
                command=lambda: webbrowser.open(update_info.release_url),
            ).pack(side="right")

    def dismiss_update_notification(self, update_info, snooze_var, window):
        if snooze_var.get():
            snoozed_until = datetime.datetime.now() + datetime.timedelta(hours=UPDATE_SNOOZE_HOURS)
            self.data["update_snoozed_version"] = update_info.latest_version
            self.data["update_snoozed_until"] = snoozed_until.isoformat(timespec="seconds")
            save_data(self.data)

        window.destroy()

    def start_auto_update(self, update_info, window, status_label, update_button):
        update_button.configure(state="disabled", text="ダウンロード中...")
        status_label.configure(text="アップデートファイルをダウンロードしています。")
        result_queue = queue.Queue(maxsize=1)

        def worker():
            try:
                downloaded_exe = download_update_exe(update_info)
                result_queue.put_nowait((downloaded_exe, None))
            except Exception as e:
                log_error("アップデートファイルのダウンロードに失敗しました。", e)
                result_queue.put_nowait((None, e))

        threading.Thread(target=worker, daemon=True).start()
        self.poll_auto_update_download(result_queue, window, status_label, update_button, update_info)

    def poll_auto_update_download(self, result_queue, window, status_label, update_button, update_info):
        try:
            downloaded_exe, error = result_queue.get_nowait()
        except queue.Empty:
            try:
                self.after(
                    200,
                    lambda: self.poll_auto_update_download(
                        result_queue,
                        window,
                        status_label,
                        update_button,
                        update_info,
                    ),
                )
            except tk.TclError:
                pass
            return

        if not self.widget_exists(window):
            if downloaded_exe:
                try:
                    os.remove(downloaded_exe)
                except OSError:
                    pass
            return

        if error:
            self.show_auto_update_failure(status_label, update_button, update_info)
            return

        try:
            launch_update_installer(downloaded_exe)
        except Exception as e:
            log_error("アップデート処理の開始に失敗しました。", e)
            self.show_auto_update_failure(status_label, update_button, update_info)
            return

        status_label.configure(text="アプリを終了してアップデートを適用します。")
        self.after(500, self.on_app_close)

    def show_auto_update_failure(self, status_label, update_button, update_info):
        if not self.widget_exists(status_label) or not self.widget_exists(update_button):
            return

        status_label.configure(text="自動アップデートに失敗しました。手動でダウンロードしてください。")
        update_button.configure(
            state="normal",
            text="リリースページを開く",
            width=160,
            command=lambda: webbrowser.open(update_info.release_url),
        )
