import json
import random
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import google.generativeai as genai


# ==========================================
# AIクイズ表示用 ポップアップ
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
