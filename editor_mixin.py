import os
import ctypes
import tkinter as tk
import customtkinter as ctk
from PIL import ImageTk
from app_logger import log_error
from data import IMAGES_DIR
from image_embed import DEFAULT_IMAGE_WIDTH, image_marker_text, load_resized_image, parse_image_marker
from platform_ime import LOGFONTW, imm32, wintypes
from ui_config import BLOCK_STYLES, DEFAULT_BLOCK_STYLE_LABEL, DEFAULT_FONT_SIZE, FONT_COLORS, FONT_SIZE_VALUES, app_font


class EditorMixin:
    def configure_formatting_tags(self):
        """文字色とフォントサイズ用の全タグの配色とフォントを現在のテーマに合わせて動的適用する"""
        text_widget = self.editor._textbox
        mode = ctk.get_appearance_mode().lower() # "dark" or "light"
        
        # 1. 文字色タグの適用
        for color_key, color_config in FONT_COLORS.items():
            tag_name = f"color_{color_key}"
            text_hex = color_config[mode]
            text_widget.tag_configure(tag_name, foreground=text_hex)
            
        # 2. フォントサイズ・太字・下線タグの適用
        for size in FONT_SIZE_VALUES:
            text_widget.tag_configure(self.font_tag_name(size, False), font=self.scaled_editor_font(size=size))
            text_widget.tag_configure(self.font_tag_name(size, True), font=self.scaled_editor_font(size=size, weight="bold"))
        text_widget.tag_configure("underline", underline=True)
        text_widget.tag_configure("image_marker", elide=True)
        multi_select_bg = "#b8d8ff" if mode == "light" else "#315a83"
        text_widget.tag_configure("multi_select", background=multi_select_bg)
        text_widget.tag_configure("multi_select_preview", background=multi_select_bg)

    def scaled_editor_font(self, size=DEFAULT_FONT_SIZE, weight="normal", slant="roman", underline=False):
        """Tk Textタグ用に、CTkTextboxと同じスケーリング済みフォントタプルを返す。"""
        return self.editor._apply_font_scaling(app_font(size=size, weight=weight, slant=slant, underline=underline))

    def sync_editor_input_style(self):
        """IME変換中の文字も現在の入力スタイルで表示されるよう、本文の基準スタイルを同期する。"""
        if not hasattr(self, "editor"):
            return

        weight = "bold" if self.active_typing_bold else "normal"
        mode = ctk.get_appearance_mode().lower()
        color_config = FONT_COLORS.get(self.active_typing_color, FONT_COLORS["default"])
        text_hex = color_config[mode]

        self.editor.configure(
            font=app_font(
                size=self.active_typing_size,
                weight=weight,
                underline=self.active_typing_underline,
            ),
            text_color=text_hex,
        )
        self.editor._textbox.configure(insertbackground=text_hex)
        self.sync_windows_ime_font(weight)

    def sync_editor_cursor_color(self):
        mode = ctk.get_appearance_mode().lower()
        color_config = FONT_COLORS.get(self.active_typing_color, FONT_COLORS["default"])
        self.editor._textbox.configure(insertbackground=color_config[mode])

    def sync_windows_ime_font(self, weight="normal"):
        """Windows IMEの変換中文字にも、現在の入力フォントサイズを反映する。"""
        if imm32 is None or not hasattr(self, "editor"):
            return

        text_widget = self.editor._textbox
        try:
            hwnd = wintypes.HWND(text_widget.winfo_id())
            himc = imm32.ImmGetContext(hwnd)
            if not himc:
                return

            scaled_font = self.scaled_editor_font(
                size=self.active_typing_size,
                weight=weight,
                underline=self.active_typing_underline,
            )

            logfont = LOGFONTW()
            logfont.lfHeight = int(scaled_font[1])
            logfont.lfWeight = 700 if weight == "bold" else 400
            logfont.lfUnderline = 1 if self.active_typing_underline else 0
            logfont.lfCharSet = 1
            logfont.lfQuality = 5
            logfont.lfFaceName = str(scaled_font[0])[:31]
            imm32.ImmSetCompositionFontW(himc, ctypes.byref(logfont))
        except Exception:
            pass
        finally:
            try:
                if "himc" in locals() and himc:
                    imm32.ImmReleaseContext(hwnd, himc)
            except Exception:
                pass

    def color_swatch_color(self, color_key):
        mode = ctk.get_appearance_mode().lower()
        return FONT_COLORS.get(color_key, FONT_COLORS["default"])[mode]

    def update_color_swatch_buttons(self):
        if not hasattr(self, "color_buttons"):
            return
        for color_key, button in self.color_buttons.items():
            color = self.color_swatch_color(color_key)
            border_color = "#777777" if color_key == "default" and ctk.get_appearance_mode().lower() == "dark" else "white"
            button.configure(fg_color=color, hover_color=color, border_color=border_color)

    def font_tag_name(self, size, bold):
        return f"bold_size_{size}" if bold else f"size_{size}"

    def get_text_style_at(self, index):
        tags = self.editor._textbox.tag_names(index)
        color = "default"
        size = DEFAULT_FONT_SIZE
        bold = False
        underline = False

        for tag in tags:
            if tag.startswith("color_"):
                color = tag.split("_", 1)[1]
            elif tag.startswith("bold_size_"):
                try:
                    size = int(tag.split("_")[2])
                    bold = True
                except (IndexError, ValueError):
                    pass
            elif tag.startswith("size_"):
                try:
                    size = int(tag.split("_")[1])
                    bold = False
                except (IndexError, ValueError):
                    pass
            elif tag == "underline":
                underline = True

        return color, size, bold, underline

    def set_active_typing_style(self, size=None, bold=None, underline=None, color=None):
        if size is not None:
            self.active_typing_size = int(size)
        if bold is not None:
            self.active_typing_bold = bool(bold)
        if underline is not None:
            self.active_typing_underline = bool(underline)
        if color is not None:
            self.active_typing_color = color

        self.update_block_style_label()
        self.update_style_buttons()
        self.sync_editor_input_style()

    def update_block_style_label(self):
        for label, config in BLOCK_STYLES.items():
            if config["size"] == self.active_typing_size and config["bold"] == self.active_typing_bold:
                self.block_style_var.set(label)
                return

    def is_control_pressed(self, event):
        return bool(getattr(event, "state", 0) & 0x0004)

    def on_editor_button_press(self, event):
        if not self.is_control_pressed(event):
            self.clear_multi_select_ranges()
        return None

    def on_editor_button_release(self, event):
        if not self.is_control_pressed(event):
            return None

        self.add_current_selection_to_multi_select()
        return None

    def text_index_at_event(self, event):
        return self.editor._textbox.index(f"@{event.x},{event.y}")

    def ordered_text_range(self, start, end):
        text_widget = self.editor._textbox
        if text_widget.compare(start, "==", end):
            return None
        if text_widget.compare(start, ">", end):
            start, end = end, start
        return text_widget.index(start), text_widget.index(end)

    def add_multi_select_range(self, start, end):
        text_range = self.ordered_text_range(start, end)
        if text_range is None:
            return False

        self.editor._textbox.tag_add("multi_select", text_range[0], text_range[1])
        return True

    def on_multi_select_press(self, event):
        text_widget = self.editor._textbox
        self.add_current_selection_to_multi_select()
        text_widget.tag_remove("multi_select_preview", "1.0", "end")

        try:
            self.multi_select_anchor = self.text_index_at_event(event)
            text_widget.mark_set("insert", self.multi_select_anchor)
        except tk.TclError:
            self.multi_select_anchor = None

        return "break"

    def on_multi_select_drag(self, event):
        anchor = getattr(self, "multi_select_anchor", None)
        if anchor is None:
            return "break"

        text_widget = self.editor._textbox
        text_widget.tag_remove("multi_select_preview", "1.0", "end")

        try:
            current = self.text_index_at_event(event)
            text_range = self.ordered_text_range(anchor, current)
            if text_range is not None:
                text_widget.tag_add("multi_select_preview", text_range[0], text_range[1])
        except tk.TclError:
            pass

        return "break"

    def on_multi_select_release(self, event):
        anchor = getattr(self, "multi_select_anchor", None)
        if anchor is None:
            return "break"

        text_widget = self.editor._textbox
        text_widget.tag_remove("multi_select_preview", "1.0", "end")

        try:
            current = self.text_index_at_event(event)
            self.add_multi_select_range(anchor, current)
        except tk.TclError:
            pass

        self.multi_select_anchor = None
        text_widget.tag_remove("sel", "1.0", "end")
        return "break"

    def add_current_selection_to_multi_select(self):
        text_widget = self.editor._textbox
        try:
            if not text_widget.tag_ranges("sel"):
                return
            start = text_widget.index("sel.first")
            end = text_widget.index("sel.last")
            self.add_multi_select_range(start, end)
            text_widget.tag_remove("sel", "1.0", "end")
        except tk.TclError:
            return

    def clear_multi_select_ranges(self, _event=None):
        if hasattr(self, "editor"):
            try:
                self.editor._textbox.tag_remove("multi_select", "1.0", "end")
                self.editor._textbox.tag_remove("multi_select_preview", "1.0", "end")
                self.multi_select_anchor = None
            except tk.TclError:
                pass
        return None

    def selected_text_ranges(self):
        text_widget = self.editor._textbox
        ranges = []

        tag_ranges = text_widget.tag_ranges("multi_select")
        for i in range(0, len(tag_ranges), 2):
            ranges.append((text_widget.index(tag_ranges[i]), text_widget.index(tag_ranges[i + 1])))

        try:
            if text_widget.tag_ranges("sel"):
                ranges.append((text_widget.index("sel.first"), text_widget.index("sel.last")))
        except tk.TclError:
            pass

        normalized_ranges = []
        for start, end in ranges:
            if text_widget.compare(start, "==", end):
                continue
            if text_widget.compare(start, ">", end):
                start, end = end, start
            normalized_ranges.append((text_widget.index(start), text_widget.index(end)))

        return normalized_ranges

    def apply_text_style_to_selected_ranges(self, color=None, size=None, bold=None, underline=None):
        ranges = self.selected_text_ranges()
        if not ranges:
            return False

        for start, end in ranges:
            self.apply_text_style_range(start, end, color=color, size=size, bold=bold, underline=underline)

        self.trigger_auto_save()
        return True

    def selected_block_lines(self):
        text_widget = self.editor._textbox
        try:
            if text_widget.tag_ranges("sel"):
                start = text_widget.index("sel.first")
                end = text_widget.index("sel.last")
            else:
                start = text_widget.index("insert")
                end = start
        except tk.TclError:
            start = text_widget.index("insert")
            end = start

        start_line = int(start.split(".")[0])
        end_line = int(end.split(".")[0])
        if text_widget.compare(end, "==", f"{end_line}.0") and end_line > start_line:
            end_line -= 1
        return start_line, end_line

    def apply_block_style_to_lines(self, start_line, end_line, size=None, bold=None):
        text_widget = self.editor._textbox
        for line in range(start_line, end_line + 1):
            line_start = f"{line}.0"
            line_end = f"{line}.end"
            if text_widget.compare(line_start, "!=", line_end):
                self.apply_text_style_range(line_start, line_end, size=size, bold=bold)

    def apply_block_style_to_current_blocks(self, size=None, bold=None):
        selected_ranges = self.selected_text_ranges()
        if not selected_ranges:
            start_line, end_line = self.selected_block_lines()
            self.apply_block_style_to_lines(start_line, end_line, size=size, bold=bold)
            return

        handled_lines = set()
        for start, end in selected_ranges:
            start_line = int(start.split(".")[0])
            end_line = int(end.split(".")[0])
            if self.editor._textbox.compare(end, "==", f"{end_line}.0") and end_line > start_line:
                end_line -= 1
            for line in range(start_line, end_line + 1):
                if line in handled_lines:
                    continue
                handled_lines.add(line)
                self.apply_block_style_to_lines(line, line, size=size, bold=bold)

    def on_block_style_changed(self, style_label):
        if style_label not in BLOCK_STYLES:
            return

        config = BLOCK_STYLES[style_label]
        self.set_active_typing_style(size=config["size"], bold=config["bold"])
        self.apply_block_style_to_current_blocks(size=config["size"], bold=config["bold"])
        self.trigger_auto_save()

    def apply_text_style_range(self, start, end, color=None, size=None, bold=None, underline=None):
        text_widget = self.editor._textbox
        if text_widget.compare(start, "==", end):
            return
        if text_widget.compare(start, ">", end):
            start, end = end, start

        count_result = text_widget.count(start, end, "chars")
        char_count = count_result[0] if count_result else 0
        if char_count <= 0:
            return

        segments = []
        segment_start = start
        previous_style = None

        for i in range(char_count):
            char_idx = text_widget.index(f"{start} + {i} chars")
            current_style = self.get_text_style_at(char_idx)
            next_style = (
                color if color is not None else current_style[0],
                size if size is not None else current_style[1],
                bold if bold is not None else current_style[2],
                underline if underline is not None else current_style[3],
            )

            if previous_style is None:
                previous_style = next_style
            elif next_style != previous_style:
                segment_end = text_widget.index(f"{start} + {i} chars")
                segments.append((segment_start, segment_end, previous_style))
                segment_start = segment_end
                previous_style = next_style

        segments.append((segment_start, end, previous_style))

        for color_key in FONT_COLORS.keys():
            text_widget.tag_remove(f"color_{color_key}", start, end)
        for font_size in FONT_SIZE_VALUES:
            text_widget.tag_remove(self.font_tag_name(font_size, False), start, end)
            text_widget.tag_remove(self.font_tag_name(font_size, True), start, end)
        text_widget.tag_remove("underline", start, end)

        for segment_start, segment_end, style in segments:
            segment_color, segment_size, segment_bold, segment_underline = style
            text_widget.tag_add(f"color_{segment_color}", segment_start, segment_end)
            text_widget.tag_add(self.font_tag_name(segment_size, segment_bold), segment_start, segment_end)
            if segment_underline:
                text_widget.tag_add("underline", segment_start, segment_end)

    def on_key_pressed(self, event):
        if event.char and (event.char.isprintable() or event.char in ("\r", "\n", "\t")):
            try:
                text_widget = self.editor._textbox
                self.move_insert_out_of_image_marker()
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

    def clear_pending_formatting(self):
        if self.pending_format_after_id is not None:
            try:
                self.after_cancel(self.pending_format_after_id)
            except Exception:
                pass
        self.pending_format_after_id = None
        self.pending_format_start_index = None

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

            self.apply_text_style_range(
                start_idx,
                end_idx,
                color=self.active_typing_color,
                size=self.active_typing_size,
                bold=self.active_typing_bold,
                underline=self.active_typing_underline,
            )
        except Exception as e:
            log_error("タイピングフォーマット適用に失敗しました。", e)

    def image_marker_range_containing_index(self, index):
        text_widget = self.editor._textbox
        try:
            normalized_index = text_widget.index(index)
            ranges = text_widget.tag_prevrange("image_marker", f"{normalized_index} + 1c")
            if not ranges:
                return None

            marker_start, marker_end = ranges
            if text_widget.compare(marker_start, "<=", normalized_index) and text_widget.compare(normalized_index, "<", marker_end):
                return marker_start, marker_end
        except tk.TclError:
            return None

        return None

    def image_block_range_from_marker(self, marker_start, marker_end):
        text_widget = self.editor._textbox
        block_start = text_widget.index(marker_start)
        block_end = text_widget.index(marker_end)

        try:
            block_end = text_widget.index(f"{block_end} + 1c")
        except tk.TclError:
            return block_start, block_end

        for _ in range(2):
            try:
                next_char = text_widget.get(block_end, f"{block_end} + 1c")
                if next_char != "\n":
                    break
                block_end = text_widget.index(f"{block_end} + 1c")
            except tk.TclError:
                break

        return block_start, block_end

    def move_insert_out_of_image_marker(self, _event=None):
        try:
            marker_range = self.image_marker_range_containing_index("insert")
            if not marker_range:
                return None

            _, block_end = self.image_block_range_from_marker(marker_range[0], marker_range[1])
            self.editor._textbox.mark_set("insert", block_end)
        except tk.TclError:
            return None

        return None

    def image_marker_range_near_delete_cursor(self, keysym):
        text_widget = self.editor._textbox
        try:
            insert = text_widget.index("insert")
        except tk.TclError:
            return None

        for index in (insert, f"{insert} - 1c", f"{insert} + 1c"):
            marker_range = self.image_marker_range_containing_index(index)
            if marker_range:
                return marker_range

        if keysym == "BackSpace":
            ranges = text_widget.tag_prevrange("image_marker", insert)
            if ranges:
                block_start, block_end = self.image_block_range_from_marker(ranges[0], ranges[1])
                if text_widget.compare(block_start, "<", insert) and text_widget.compare(insert, "<=", block_end):
                    return ranges

        if keysym == "Delete":
            ranges = text_widget.tag_nextrange("image_marker", insert)
            if ranges:
                block_start, block_end = self.image_block_range_from_marker(ranges[0], ranges[1])
                if text_widget.compare(block_start, "<=", insert) and text_widget.compare(insert, "<", block_end):
                    return ranges

        return None

    def on_delete_key_pressed(self, event):
        self.clear_pending_formatting()

        if getattr(event, "keysym", "") not in ("BackSpace", "Delete"):
            return None

        marker_range = self.image_marker_range_near_delete_cursor(event.keysym)
        if not marker_range:
            return None

        text_widget = self.editor._textbox
        block_start, block_end = self.image_block_range_from_marker(marker_range[0], marker_range[1])
        try:
            text_widget.delete(block_start, block_end)
            text_widget.mark_set("insert", block_start)
            self.trigger_auto_save()
            return "break"
        except tk.TclError:
            return None

    def on_return_pressed(self, _event):
        self.after_idle(self.reset_new_block_to_body)

    def reset_new_block_to_body(self):
        body_style = BLOCK_STYLES[DEFAULT_BLOCK_STYLE_LABEL]
        self.set_active_typing_style(size=body_style["size"], bold=body_style["bold"])

    def change_typing_color(self, color_key):
        if self.apply_text_style_to_selected_ranges(color=color_key):
            return

        self.active_typing_color = color_key
        self.sync_editor_cursor_color()

    def toggle_typing_bold(self):
        self.active_typing_bold = not self.active_typing_bold
        self.update_block_style_label()
        self.update_style_buttons()
        self.sync_editor_input_style()
        self.apply_text_style_to_selected_ranges(bold=self.active_typing_bold)

    def toggle_typing_underline(self):
        self.active_typing_underline = not self.active_typing_underline
        self.update_block_style_label()
        self.update_style_buttons()
        self.sync_editor_input_style()
        self.apply_text_style_to_selected_ranges(underline=self.active_typing_underline)

    def update_style_buttons(self):
        active_color = ("#d8d8d8", "#3a3a3a")
        inactive_color = ("#f1f1f1", "#2b2b2b")
        if hasattr(self, "bold_btn"):
            self.bold_btn.configure(fg_color=active_color if self.active_typing_bold else inactive_color, text_color=("#111111", "#ffffff"))
        if hasattr(self, "underline_btn"):
            self.underline_btn.configure(fg_color=active_color if self.active_typing_underline else inactive_color, text_color=("#111111", "#ffffff"))

    def toggle_app_theme(self):
        """表示テーマを切り替える。"""
        theme = self.theme_switch_var.get()
        if theme == "dark":
            ctk.set_appearance_mode("dark")
            self.theme_switch.configure(text="🌙 ダークモード")
        else:
            ctk.set_appearance_mode("light")
            self.theme_switch.configure(text="☀ ライトモード")
            
        self.configure_formatting_tags()
        self.update_color_swatch_buttons()
        
        if self.current_note_id:
            note_data = next((n for n in self.data["notes"] if n["id"] == self.current_note_id), None)
            if note_data:
                self.apply_note_font_color(note_data.get("color", "default"))

        self.sync_editor_input_style()
                
        self.update_ui_widget_colors_instantly()

    def update_ui_widget_colors_instantly(self):
        """テーマ変更後にリスト周辺の配色を更新する。"""
        mode = ctk.get_appearance_mode().lower()
        active_btn_color = "#3a3a3a" if mode == "dark" else "#d8d8d8"
        text_color = ("#1a1a1a", "#ffffff")
        
        # ジャンルリストの配色を更新する。
        for child in self.cat_scrollable.winfo_children():
            if isinstance(child, ctk.CTkFrame):
                for sub_child in child.winfo_children():
                    if isinstance(sub_child, ctk.CTkButton):
                        if int(sub_child.grid_info().get("column", -1)) != 0:
                            continue
                        cat_name = sub_child.cget("text")
                        if cat_name:
                            is_active = (self.selected_category == cat_name)
                            bg = active_btn_color if is_active else "transparent"
                            sub_child.configure(fg_color=bg, text_color=text_color, hover_color=("gray75", "gray30"))
            elif isinstance(child, ctk.CTkButton):
                is_active = (self.selected_category == "全て")
                bg = active_btn_color if is_active else "transparent"
                child.configure(fg_color=bg, text_color=text_color, hover_color=("gray75", "gray30"))

        # ノートリストの配色を更新する。
        for child in self.notes_scrollable.winfo_children():
            if isinstance(child, ctk.CTkButton):
                note_id = getattr(child, "note_id", None)
                note_data = next((n for n in self.data["notes"] if n.get("id") == note_id), None)
                if note_data:
                    bg_color, card_text_color = self.note_card_colors(note_data)
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
        current_chars = []
        current_color = "default"
        current_size = DEFAULT_FONT_SIZE
        current_bold = False
        current_underline = False
        
        total_chars = len(text_str)
        for i in range(total_chars):
            char_idx = f"1.0 + {i} chars"
            char = text_widget.get(char_idx)
            
            tags = text_widget.tag_names(char_idx)
            color = "default"
            size = DEFAULT_FONT_SIZE
            bold = False
            underline = False
            for tag in tags:
                if tag.startswith("color_"):
                    color = tag.split("_", 1)[1]
                elif tag.startswith("bold_size_"):
                    try:
                        size = int(tag.split("_")[2])
                        bold = True
                    except (IndexError, ValueError):
                        pass
                elif tag.startswith("size_"):
                    try:
                        size = int(tag.split("_")[1])
                        bold = False
                    except (IndexError, ValueError):
                        pass
                elif tag == "underline":
                    underline = True
            
            if i == 0:
                current_chars = [char]
                current_color = color
                current_size = size
                current_bold = bold
                current_underline = underline
            elif color == current_color and size == current_size and bold == current_bold and underline == current_underline:
                current_chars.append(char)
            else:
                spans.append({
                    "text": "".join(current_chars),
                    "color": current_color,
                    "size": current_size,
                    "bold": current_bold,
                    "underline": current_underline
                })
                current_chars = [char]
                current_color = color
                current_size = size
                current_bold = bold
                current_underline = underline
                
        if current_chars:
            spans.append({
                "text": "".join(current_chars),
                "color": current_color,
                "size": current_size,
                "bold": current_bold,
                "underline": current_underline
            })
            
        for span in spans:
            lines = span["text"].split("\n")
            processed_lines = []
            for line in lines:
                old_image_prefix = "\U0001f4f7 [画像:"
                image_marker = parse_image_marker(line)
                if image_marker:
                    img_name, image_width = image_marker
                    processed_lines.append(image_marker_text(img_name, image_width))
                    continue
                if (line.startswith(old_image_prefix) or line.startswith("[画像:")) and line.endswith("]"):
                    img_name = line.replace(old_image_prefix, "").replace("[画像:", "").replace("]", "").strip()
                    processed_lines.append(f"[image:{img_name}]")
                elif line.strip() == "\ufffc":
                    continue
                else:
                    processed_lines.append(line)
            span["text"] = "\n".join(processed_lines)
            
        return spans

    def insert_image_block(self, text_widget, img_filename, width=DEFAULT_IMAGE_WIDTH):
        img_path = os.path.join(IMAGES_DIR, img_filename)
        if not os.path.exists(img_path):
            text_widget.insert(tk.INSERT, f"[画像が見つかりません: {img_filename}]\n")
            return

        try:
            pil_img = load_resized_image(img_path, width)
            if pil_img is None:
                text_widget.insert(tk.INSERT, f"[画像の描画失敗: {img_filename}]\n")
                return

            tk_img = ImageTk.PhotoImage(pil_img)
            self.keep_alive_images.append(tk_img)

            marker = image_marker_text(img_filename, width)
            text_widget.insert(tk.INSERT, f"{marker}\n", ("image_marker",))
            text_widget.image_create(tk.INSERT, image=tk_img)
            text_widget.insert(tk.INSERT, "\n\n")
        except Exception as e:
            text_widget.insert(tk.INSERT, f"[画像の描画失敗: {img_filename}]\n")
            log_error("画像の描画に失敗しました。", e)

    def render_note_content(self, spans_or_string):
        """保存データをエディタに復元し、画像をインライン表示する。"""
        self.editor.configure(state="normal")
        self.editor.delete("1.0", "end")
        self.keep_alive_images.clear()
        
        if isinstance(spans_or_string, str):
            spans = [{"text": spans_or_string, "color": "default", "size": DEFAULT_FONT_SIZE, "bold": False, "underline": False}]
        else:
            spans = spans_or_string
            
        text_widget = self.editor._textbox
        
        for span in spans:
            text = span.get("text", "")
            color = span.get("color", "default")
            size = span.get("size", DEFAULT_FONT_SIZE)
            bold = span.get("bold", False)
            underline = span.get("underline", False)
            
            color_tag = f"color_{color}"
            size_tag = self.font_tag_name(size, bold)
            text_tags = (color_tag, size_tag, "underline") if underline else (color_tag, size_tag)
            
            lines = text.split("\n")
            for idx, line in enumerate(lines):
                image_marker = parse_image_marker(line)
                if image_marker:
                    img_filename, image_width = image_marker
                    self.insert_image_block(text_widget, img_filename, image_width)
                else:
                    start_pos = text_widget.index(tk.INSERT)
                    text_widget.insert(tk.INSERT, line)
                    end_pos = text_widget.index(tk.INSERT)
                    
                    for tag in text_tags:
                        text_widget.tag_add(tag, start_pos, end_pos)
                    
                    if idx < len(lines) - 1:
                        start_nl = text_widget.index(tk.INSERT)
                        text_widget.insert(tk.INSERT, "\n")
                        end_nl = text_widget.index(tk.INSERT)
                        for tag in text_tags:
                            text_widget.tag_add(tag, start_nl, end_nl)

    # ==========================================
    # 6. リスト更新 ＆ ノート読込・保存
    # ==========================================

