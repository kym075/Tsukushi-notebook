import json
import queue
import random
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from app_logger import log_error


# ==========================================
# AIクイズ画面
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
        
        self.protocol("WM_DELETE_WINDOW", self.close_quiz)
        
        self.quiz_questions = []
        self.current_q_index = 0
        self.selected_ans_var = tk.IntVar(value=-1)
        self.score = 0
        self.generation_thread = None
        self.result_queue = queue.Queue(maxsize=1)
        self.result_poll_after_id = None
        api_key = self.parent.data.get("gemini_api_key", "")
        self.use_gemini_api = bool(api_key and self.parent.data.get("use_gemini_api", bool(api_key)))
        
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=25, pady=25)

        loading_text = (
            "Gemini APIでクイズを生成しています。\nしばらくお待ちください。"
            if self.use_gemini_api
            else "ローカルモードでクイズを生成しています。"
        )
        
        self.loading_label = ctk.CTkLabel(
            self.container, 
            text=loading_text,
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.loading_label.pack(expand=True)
        
        self.after(500, self.generate_quiz_data)

    def close_quiz(self):
        """クイズウィンドウを閉じる。"""
        try:
            self.grab_release()
        except tk.TclError:
            pass

        if self.result_poll_after_id is not None:
            try:
                self.after_cancel(self.result_poll_after_id)
            except tk.TclError:
                pass
            self.result_poll_after_id = None

        # ボタンイベント処理の完了後に破棄する。
        self.after(10, self.destroy)

    def generate_quiz_data(self):
        if self.generation_thread and self.generation_thread.is_alive():
            return

        self.generation_thread = threading.Thread(target=self.generate_quiz_data_worker, daemon=True)
        self.generation_thread.start()
        self.poll_quiz_result()

    def generate_quiz_data_worker(self):
        questions = self.build_quiz_questions()
        try:
            self.result_queue.put_nowait(questions)
        except queue.Full:
            pass

    def poll_quiz_result(self):
        try:
            questions = self.result_queue.get_nowait()
        except queue.Empty:
            if self.generation_thread and self.generation_thread.is_alive():
                try:
                    self.result_poll_after_id = self.after(100, self.poll_quiz_result)
                except tk.TclError:
                    self.result_poll_after_id = None
                return
            questions = []

        self.result_poll_after_id = None
        self.finish_quiz_generation(questions)

    def build_quiz_questions(self):
        api_key = self.parent.data.get("gemini_api_key", "")

        if api_key and self.use_gemini_api:
            try:
                questions = self.generate_gemini_quiz(api_key)
            except Exception as e:
                log_error("Gemini APIによるクイズ生成に失敗しました。ローカルモードに切り替えます。", e)
                questions = self.generate_mock_quiz()
        else:
            questions = self.generate_mock_quiz()

        return self.shuffle_quiz_choices(questions)

    def generate_gemini_quiz(self, api_key):
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise RuntimeError("google-generativeai がインストールされていません。") from exc

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = f"""
以下の学習メモを読み、理解度を確認するための3択問題を{self.num_questions}問作成してください。
同じ内容に偏りすぎないよう、出題する観点を適度に変えてください。

【問題文のルール】
- question は問題文だけにしてください。
- 問題文は、単独で読んでも自然に成立する文章にしてください。
- 「学習メモに記載されている」「メモによると」「本文中の」「以下の内容では」など、メモの存在を参照する表現は禁止です。
- 悪い例: 学習メモに記載されている「徳川家康」について正しい説明はどれですか？
- 良い例: 徳川家康について正しい説明はどれですか？

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

【学習メモ】
{self.note_content}
"""
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.8}
        )
        text = self.clean_json_response(response.text)
        return json.loads(text)

    def clean_json_response(self, text):
        text = text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1].strip()
            if text.startswith("json"):
                text = text[4:].strip()
        return text

    def shuffle_quiz_choices(self, questions):
        if not isinstance(questions, list):
            return []

        valid_questions = []
        for q in questions:
            if not isinstance(q, dict):
                continue

            choices = q.get("choices")
            answer_index = q.get("answer_index")
            if not isinstance(choices, list) or len(choices) < 3:
                continue
            if not isinstance(answer_index, int) or answer_index < 0 or answer_index >= len(choices):
                continue

            correct_ans = choices[answer_index]
            if len(choices) > 3:
                distractors = [choice for idx, choice in enumerate(choices) if idx != answer_index]
                choices = [correct_ans] + distractors[:2]
            else:
                choices = list(choices)
            random.shuffle(choices)
            q = {
                "question": q.get("question", ""),
                "choices": choices,
                "answer_index": choices.index(correct_ans),
                "explanation": q.get("explanation", "")
            }
            valid_questions.append(q)

        return valid_questions[:self.num_questions]

    def finish_quiz_generation(self, questions):
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return

        self.quiz_questions = questions

        try:
            if self.loading_label.winfo_exists():
                self.loading_label.pack_forget()
        except tk.TclError:
            return
        
        if self.quiz_questions:
            self.show_question()
        else:
            error_lbl = ctk.CTkLabel(
                self.container, 
                text="ローカルクイズを生成できませんでした。\n\n"
                     "【クイズを作成するためのメモの書き方例】\n"
                     "■ 重要語句 : その意味や説明\n"
                     "■ 公式名 → 公式の内容や解説\n"
                     "■ 英単語 【品詞】 日本語訳\n\n"
                     "上記のようにメモを書くと、ローカルモードでも3択問題を作成できます。\n"
                     "または、Gemini APIキーを設定すると、AIが内容を読み取って自動で問題を作成します。",
                font=ctk.CTkFont(size=14),
                justify="left"
            )
            error_lbl.pack(expand=True, pady=20)

    def generate_mock_quiz(self):
        """
        メモ内の語句や定義から、ローカルで3択クイズを作成する。
        """
        quiz_questions = []
        
        # メモ内の語句と定義を解析抽出する辞書
        # 例: {"用語": "説明", "公式名": "公式の内容"}
        definitions = {}
        
        lines = self.note_content.split("\n")
        for idx, raw_line in enumerate(lines):
            line = raw_line.strip()
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
                    
            # パターンC: ■ 単語 → 意味
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
                meaning = ""
                for next_line in lines[idx+1:]:
                    if next_line.strip() and not next_line.strip().startswith("■"):
                        meaning = next_line.strip()
                        break
                if term and meaning:
                    definitions[term] = meaning

        # 抽出できた重要語句から問題を作る。
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
            
            quiz_questions.append({
                "question": f"メモに書かれた『 {term} 』について、正しい説明または定義はどれですか？",
                "choices": choices,
                "answer_index": 0,
                "explanation": f"正解は『{meaning}』です。メモ内の記述をもとにしています。"
            })

        # 指定された問題数になるように調整（最大指定数）
        return quiz_questions[:self.num_questions]

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
            text="この答えで回答する",
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

        self.submit_btn.pack_forget()
        self.choices_frame.pack_forget()

        result_title = "正解です" if is_correct else "不正解です"
        result_color = "#2ecc71" if is_correct else "#e74c3c"
        
        explanation_box = ctk.CTkFrame(self.container, fg_color=("#eaeaea", "#2b2b2b"), border_width=1, border_color=result_color)
        explanation_box.pack(fill="x", pady=10)
        
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
            next_btn_text = "次の問題へ"
            next_cmd = self.next_question
        else:
            next_btn_text = "最終結果を見る"
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
            msg = "全問正解です。メモの内容をよく確認できています。"
            color = "#2ecc71"
        elif pct >= 60:
            msg = "一定の理解ができています。間違えた部分をメモで確認してください。"
            color = "#3498db"
        else:
            msg = "もう一度ノートを確認してから再実行してください。"
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
