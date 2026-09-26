import os
# 強制將目前程式所在的資料夾加入系統 PATH，讓 audio-separator 完美抓到 ffmpeg.exe
os.environ["PATH"] += os.pathsep + os.path.dirname(os.path.abspath(__file__))

import subprocess
import traceback
import torch
import queue
import threading
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from audio_separator.separator import Separator

class StdoutRedirector:
    """用來攔截終端機輸出與錯誤，同步傳遞到佇列中"""
    def __init__(self, q):
        self.q = q
        self.terminal = sys.__stdout__

    def write(self, message):
        self.terminal.write(message)
        if message:
            self.q.put(message)

    def flush(self):
        self.terminal.flush()

class KaraokeApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("850x880")
        self.root.minsize(700, 780)

        # 多國語言字典設定 (繁體中文、简体中文、English、日本語、한국어)
        self.texts = {
            "繁體中文": {
                "title": "AI 人聲分離與多軌重組系統",
                "lang_label": "語言 / Language:",
                "group1": " 1. 選擇檔案 (支援多選音訊或影片) ",
                "btn_select": "選擇檔案...",
                "no_file": "尚未選擇任何檔案",
                "file_selected": "已選擇 {} 個檔案",
                "group2": " 2. 模型與輸出參數設定 ",
                "model_label": "選擇 AI 模型:",
                "fmt_label": "音訊格式:",
                "sr_label": "取樣率:",
                "out_opts": "輸出項目勾選:",
                "chk_original": "輸出原音 (Original)",
                "chk_vocals": "輸出人聲 (Vocals)",
                "chk_inst": "輸出伴奏 (Instrumental)",
                "chk_video": "輸出多軌影片 (含原音/伴奏/人聲)",
                "group3": " 3. 執行控制 ",
                "btn_run": "開始執行處理",
                "btn_open": "開啟輸出資料夾",
                "group4": " 4. 即時 CMD 日誌與進度回報 ",
                "init_log": "系統就緒。請點選上方按鈕選擇音訊或影片檔案...\n",
                "device_msg": "目前運行裝置: {}",
                "prep_audio": "[{}/{}] 正在處理音訊格式 ({})...",
                "load_model": "[{}/{}] 正在載入 AI 模型 ({}) 並執行分離...",
                "multi_track": "[{}/{}] 正在進行多軌影音重組...",
                "video_success": "多軌影片建立成功: {}",
                "video_fail": "❌ 影片重組失敗:\n{}",
                "all_done": "\n🎉 全部處理完成！所有勾選的項目已儲存至 downloads 資料夾。\n",
                "done_title": "完成",
                "done_msg": "批次處理已全部完成！",
                "err_title": "錯誤",
                "err_no_file": "請先選擇至少一個音訊或影片檔案！",
                "err_general": "\n❌ 發生錯誤:\n{}"
            },
            "简体中文": {
                "title": "AI 人声分离与多轨重组系统",
                "lang_label": "语言 / Language:",
                "group1": " 1. 选择文件 (支持多选音频或视频) ",
                "btn_select": "选择文件...",
                "no_file": "尚未选择任何文件",
                "file_selected": "已选择 {} 个文件",
                "group2": " 2. 模型与输出参数设定 ",
                "model_label": "选择 AI 模型:",
                "fmt_label": "音频格式:",
                "sr_label": "采样率:",
                "out_opts": "输出项目勾选:",
                "chk_original": "输出原音 (Original)",
                "chk_vocals": "输出人声 (Vocals)",
                "chk_inst": "输出伴奏 (Instrumental)",
                "chk_video": "输出多轨视频 (含原音/伴奏/人声)",
                "group3": " 3. 执行控制 ",
                "btn_run": "开始执行处理",
                "btn_open": "打开输出文件夹",
                "group4": " 4. 实时 CMD 日志与进度回报 ",
                "init_log": "系统就绪。请点击上方按钮选择音频或视频文件...\n",
                "device_msg": "当前运行设备: {}",
                "prep_audio": "[{}/{}] 正在处理音频格式 ({})...",
                "load_model": "[{}/{}] 正在加载 AI 模型 ({}) 并执行分离...",
                "multi_track": "[{}/{}] 正在进行多轨影音重组...",
                "video_success": "多轨视频创建成功: {}",
                "video_fail": "❌ 视频重组失败:\n{}",
                "all_done": "\n🎉 全部处理完成！所有勾选的项目已保存至 downloads 文件夹。\n",
                "done_title": "完成",
                "done_msg": "批次处理已全部完成！",
                "err_title": "错误",
                "err_no_file": "请先选择至少一个音频或视频文件！",
                "err_general": "\n❌ 发生错误:\n{}"
            },
            "English": {
                "title": "AI Vocal Separation & Multi-Track Recombination System",
                "lang_label": "Language:",
                "group1": " 1. Select Files (Supports multiple audio/video files) ",
                "btn_select": "Select Files...",
                "no_file": "No files selected yet",
                "file_selected": "Selected {} file(s)",
                "group2": " 2. Model & Output Settings ",
                "model_label": "Select AI Model:",
                "fmt_label": "Audio Format:",
                "sr_label": "Sample Rate:",
                "out_opts": "Output Options:",
                "chk_original": "Original Audio",
                "chk_vocals": "Vocals",
                "chk_inst": "Instrumental",
                "chk_video": "Multi-Track Video (Original/Inst/Vocals)",
                "group3": " 3. Execution Control ",
                "btn_run": "Start Processing",
                "btn_open": "Open Output Folder",
                "group4": " 4. Real-time CMD Logs & Progress ",
                "init_log": "System ready. Please click the button above to select audio or video files...\n",
                "device_msg": "Running Device: {}",
                "prep_audio": "[{}/{}] Processing audio format ({})...",
                "load_model": "[{}/{}] Loading AI model ({}) and separating...",
                "multi_track": "[{}/{}] Recombining multi-track video...",
                "video_success": "Multi-track video created successfully: {}",
                "video_fail": "❌ Video recombination failed:\n{}",
                "all_done": "\n🎉 All processing complete! Checked items have been saved to the downloads folder.\n",
                "done_title": "Completed",
                "done_msg": "Batch processing is fully completed!",
                "err_title": "Error",
                "err_no_file": "Please select at least one audio or video file first!",
                "err_general": "\n❌ Error occurred:\n{}"
            },
            "日本語": {
                "title": "AI ボーカル分離・マルチトラック再構築システム",
                "lang_label": "言語 / Language:",
                "group1": " 1. ファイルを選択 (複数選択可) ",
                "btn_select": "ファイルを選択...",
                "no_file": "ファイルが選択されていません",
                "file_selected": "{} 個のファイルを選択しました",
                "group2": " 2. モデルと出力設定 ",
                "model_label": "AI モデル選択:",
                "fmt_label": "音声フォーマット:",
                "sr_label": "サンプリングレート:",
                "out_opts": "出力項目の選択:",
                "chk_original": "オリジナル音声 (Original)",
                "chk_vocals": "ボーカル (Vocals)",
                "chk_inst": "伴奏 (Instrumental)",
                "chk_video": "マルチトラック動画 (オリジナル/伴奏/ボーカル)",
                "group3": " 3. 実行コントロール ",
                "btn_run": "処理開始",
                "btn_open": "出力フォルダを開く",
                "group4": " 4. リアルタイムログと進捗 ",
                "init_log": "システム準備完了。上のボタンを押して音声または動画ファイルを選択してください...\n",
                "device_msg": "実行デバイス: {}",
                "prep_audio": "[{}/{}] 音声フォーマットを処理中 ({})...",
                "load_model": "[{}/{}] AI モデル ({}) を読み込んで分離中...",
                "multi_track": "[{}/{}] マルチトラック動画を再構築中...",
                "video_success": "マルチトラック動画の作成に成功しました: {}",
                "video_fail": "❌ 動画の再構築に失敗しました:\n{}",
                "all_done": "\n🎉 すべての処理が完了しました！選択した項目は downloads フォルダに保存されました。\n",
                "done_title": "完了",
                "done_msg": "一括処理がすべて完了しました！",
                "err_title": "エラー",
                "err_no_file": "まず1つ以上の音声または動画ファイルを選択してください！",
                "err_general": "\n❌ エラーが発生しました:\n{}"
            },
            "한국어": {
                "title": "AI 보컬 분리 및 멀티트랙 재조합 시스템",
                "lang_label": "언어 / Language:",
                "group1": " 1. 파일 선택 (오디오/비디오 다중 선택 지원) ",
                "btn_select": "파일 선택...",
                "no_file": "선택된 파일이 없습니다",
                "file_selected": "{}개 파일 선택됨",
                "group2": " 2. 모델 및 출력 설정 ",
                "model_label": "AI 모델 선택:",
                "fmt_label": "오디오 형식:",
                "sr_label": "샘플레이트:",
                "out_opts": "출력 항목 선택:",
                "chk_original": "원본 오디오 (Original)",
                "chk_vocals": "보컬 (Vocals)",
                "chk_inst": "반주 (Instrumental)",
                "chk_video": "멀티트랙 비디오 (원본/반주/보컬)",
                "group3": " 3. 실행 제어 ",
                "btn_run": "처리 시작",
                "btn_open": "출력 폴더 열기",
                "group4": " 4. 실시간 로그 및 진행 상황 ",
                "init_log": "시스템 준비 완료. 상단의 버튼을 눌러 오디오 또는 비디오 파일을 선택하세요...\n",
                "device_msg": "현재 실행 장치: {}",
                "prep_audio": "[{}/{}] 오디오 형식 처리 중 ({})...",
                "load_model": "[{}/{}] AI 모델 ({}) 로드 및 분리 중...",
                "multi_track": "[{}/{}] 멀티트랙 비디오 재조합 중...",
                "video_success": "멀티트랙 비디오 생성 성공: {}",
                "video_fail": "❌ 비디오 재조합 실패:\n{}",
                "all_done": "\n🎉 모든 처리가 완료되었습니다! 선택한 항목이 downloads 폴더에 저장되었습니다.\n",
                "done_title": "완료",
                "done_msg": "일괄 처리가 모두 완료되었습니다!",
                "err_title": "오류",
                "err_no_file": "먼저 하나 이상의 오디오 또는 비디오 파일을 선택하세요!",
                "err_general": "\n❌ 오류 발생:\n{}"
            }
        }

        self.selected_files = []
        self.log_queue = queue.Queue()

        # 僅保留兩個高效模型
        self.model_mapping = {
            "melband_roformer_inst_v2 (For Instrumental)": "melband_roformer_inst_v2.ckpt",
            "model_bs_roformer_ep_317_sdr_12.9755 (For Vocal)": "model_bs_roformer_ep_317_sdr_12.9755.ckpt"
        }

        self.create_widgets()
        self.root.after(100, self.process_log_queue)

    def get_text(self, key):
        lang = self.combo_lang.get() if hasattr(self, 'combo_lang') else "繁體中文"
        if lang not in self.texts:
            lang = "繁體中文"
        return self.texts[lang].get(key, key)

    def update_ui_texts(self, event=None):
        self.root.title(self.get_text("title"))
        self.lbl_lang.config(text=self.get_text("lang_label"))
        self.frame_top.config(text=self.get_text("group1"))
        self.btn_select.config(text=self.get_text("btn_select"))
        if not self.selected_files:
            self.lbl_file_count.config(text=self.get_text("no_file"))
        else:
            self.lbl_file_count.config(text=self.get_text("file_selected").format(len(self.selected_files)))
        
        self.frame_config.config(text=self.get_text("group2"))
        self.lbl_model_sel.config(text=self.get_text("model_label"))
        self.lbl_fmt.config(text=self.get_text("fmt_label"))
        self.lbl_sr.config(text=self.get_text("sr_label"))
        self.lbl_opts.config(text=self.get_text("out_opts"))
        self.chk_original_btn.config(text=self.get_text("chk_original"))
        self.chk_vocals_btn.config(text=self.get_text("chk_vocals"))
        self.chk_inst_btn.config(text=self.get_text("chk_inst"))
        self.chk_video_btn.config(text=self.get_text("chk_video"))
        
        self.frame_mid.config(text=self.get_text("group3"))
        self.btn_run.config(text=self.get_text("btn_run"))
        self.btn_open.config(text=self.get_text("btn_open"))
        
        self.frame_log.config(text=self.get_text("group4"))

    def create_widgets(self):
        frame_lang = tk.Frame(self.root)
        frame_lang.pack(fill="x", padx=15, pady=(10, 0))

        self.lbl_lang = tk.Label(frame_lang, text=self.get_text("lang_label"), font=("Microsoft JhengHei", 9, "bold"))
        self.lbl_lang.pack(side="left", padx=(0, 5))

        self.combo_lang = ttk.Combobox(frame_lang, values=["繁體中文", "简体中文", "English", "日本語", "한국어"], width=12, state="readonly")
        self.combo_lang.set("繁體中文")
        self.combo_lang.pack(side="left")
        self.combo_lang.bind("<<ComboboxSelected>>", self.update_ui_texts)

        # 1. 選擇檔案區塊
        self.frame_top = tk.LabelFrame(self.root, text=self.get_text("group1"), font=("Microsoft JhengHei", 10, "bold"), padx=10, pady=10)
        self.frame_top.pack(fill="x", padx=15, pady=8)

        self.btn_select = tk.Button(self.frame_top, text=self.get_text("btn_select"), font=("Microsoft JhengHei", 10), command=self.select_files, width=15, bg="#007ACC", fg="white", relief="raised")
        self.btn_select.pack(side="left", padx=5)

        self.lbl_file_count = tk.Label(self.frame_top, text=self.get_text("no_file"), font=("Microsoft JhengHei", 10), fg="gray")
        self.lbl_file_count.pack(side="left", padx=10)

        # 2. 設定區塊 (模型選擇 + 格式設定)
        self.frame_config = tk.LabelFrame(self.root, text=self.get_text("group2"), font=("Microsoft JhengHei", 10, "bold"), padx=10, pady=10)
        self.frame_config.pack(fill="x", padx=15, pady=5)

        # 模型下拉選單列
        model_row = tk.Frame(self.frame_config)
        model_row.pack(fill="x", pady=5)
        
        self.lbl_model_sel = tk.Label(model_row, text=self.get_text("model_label"), font=("Microsoft JhengHei", 9, "bold"))
        self.lbl_model_sel.pack(side="left", padx=(0, 5))

        self.combo_model = ttk.Combobox(model_row, values=list(self.model_mapping.keys()), width=48, state="readonly")
        self.combo_model.set("melband_roformer_inst_v2 (For Instrumental)")
        self.combo_model.pack(side="left", padx=(0, 10))

        # 格式設定列
        sub_frame = tk.Frame(self.frame_config)
        sub_frame.pack(fill="x", pady=5)

        self.lbl_fmt = tk.Label(sub_frame, text=self.get_text("fmt_label"), font=("Microsoft JhengHei", 9))
        self.lbl_fmt.pack(side="left", padx=(0, 5))
        self.combo_fmt = ttk.Combobox(sub_frame, values=["Source", "mp3", "wav", "flac"], width=8, state="readonly")
        self.combo_fmt.set("Source")
        self.combo_fmt.pack(side="left", padx=(0, 20))

        self.lbl_sr = tk.Label(sub_frame, text=self.get_text("sr_label"), font=("Microsoft JhengHei", 9))
        self.lbl_sr.pack(side="left", padx=(0, 5))
        self.combo_sr = ttk.Combobox(sub_frame, values=["Source", "44100", "48000"], width=8, state="readonly")
        self.combo_sr.set("Source")
        self.combo_sr.pack(side="left", padx=(0, 20))

        # 勾選項目列
        chk_frame = tk.Frame(self.frame_config)
        chk_frame.pack(fill="x", pady=(5, 0))

        self.lbl_opts = tk.Label(chk_frame, text=self.get_text("out_opts"), font=("Microsoft JhengHei", 9, "bold"))
        self.lbl_opts.pack(side="left", padx=(0, 10))

        self.chk_original_var = tk.BooleanVar(value=False)
        self.chk_vocals_var = tk.BooleanVar(value=True)
        self.chk_inst_var = tk.BooleanVar(value=True)
        self.chk_video_var = tk.BooleanVar(value=True)

        self.chk_original_btn = tk.Checkbutton(chk_frame, text=self.get_text("chk_original"), variable=self.chk_original_var, font=("Microsoft JhengHei", 9))
        self.chk_original_btn.pack(side="left", padx=5)
        self.chk_vocals_btn = tk.Checkbutton(chk_frame, text=self.get_text("chk_vocals"), variable=self.chk_vocals_var, font=("Microsoft JhengHei", 9))
        self.chk_vocals_btn.pack(side="left", padx=5)
        self.chk_inst_btn = tk.Checkbutton(chk_frame, text=self.get_text("chk_inst"), variable=self.chk_inst_var, font=("Microsoft JhengHei", 9))
        self.chk_inst_btn.pack(side="left", padx=5)
        self.chk_video_btn = tk.Checkbutton(chk_frame, text=self.get_text("chk_video"), variable=self.chk_video_var, font=("Microsoft JhengHei", 9))
        self.chk_video_btn.pack(side="left", padx=5)

        # 3. 執行控制區塊
        self.frame_mid = tk.LabelFrame(self.root, text=self.get_text("group3"), font=("Microsoft JhengHei", 10, "bold"), padx=10, pady=10)
        self.frame_mid.pack(fill="x", padx=15, pady=5)

        self.btn_run = tk.Button(self.frame_mid, text=self.get_text("btn_run"), font=("Microsoft JhengHei", 11, "bold"), command=self.start_thread, bg="#28A745", fg="white", width=22, height=1, relief="raised")
        self.btn_run.pack(side="left", padx=5)

        self.btn_open = tk.Button(self.frame_mid, text=self.get_text("btn_open"), font=("Microsoft JhengHei", 10), command=self.open_downloads_folder, width=18, relief="raised")
        self.btn_open.pack(side="right", padx=5)

        # 4. 日誌區塊
        self.frame_log = tk.LabelFrame(self.root, text=self.get_text("group4"), font=("Microsoft JhengHei", 10, "bold"), padx=10, pady=10)
        self.frame_log.pack(fill="both", expand=True, padx=15, pady=8)

        self.log_text = scrolledtext.ScrolledText(self.frame_log, wrap=tk.WORD, font=("Consolas", 9), bg="#1E1E1E", fg="#00FF00")
        self.log_text.pack(fill="both", expand=True)
        self.log_text.insert(tk.END, self.get_text("init_log"))

        self.root.title(self.get_text("title"))

    def select_files(self):
        files = filedialog.askopenfilenames(
            title="Select audio or video files",
            filetypes=[
                ("Media Files", "*.mp3 *.wav *.flac *.m4a *.mp4 *.mkv *.avi *.mov *.webm"),
                ("All Files", "*.*")
            ]
        )
        if files:
            self.selected_files = list(files)
            self.lbl_file_count.config(text=self.get_text("file_selected").format(len(self.selected_files)), fg="blue")
            self.log(f"Loaded {len(self.selected_files)} files.\n")

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def process_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if '\r' in msg:
                    sub_msgs = msg.split('\r')
                    for idx, sub in enumerate(sub_msgs):
                        if idx > 0:
                            try:
                                self.log_text.delete("end-1l linestart", "end-1c")
                            except Exception:
                                pass
                        if sub:
                            self.log_text.insert(tk.END, sub)
                else:
                    self.log_text.insert(tk.END, msg)
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(100, self.process_log_queue)

    def open_downloads_folder(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        downloads_dir = os.path.join(base_dir, "downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        os.startfile(downloads_dir)

    def start_thread(self):
        if not self.selected_files:
            messagebox.showerror(self.get_text("err_title"), self.get_text("err_no_file"))
            return
        
        self.btn_run.config(state="disabled", bg="gray")
        threading.Thread(target=self.run_process, daemon=True).start()

    def run_process(self):
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        redirector = StdoutRedirector(self.log_queue)
        sys.stdout = redirector
        sys.stderr = redirector

        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.log(self.get_text("device_msg").format(device.upper()) + "\n")

            base_dir = os.path.dirname(os.path.abspath(__file__))
            models_dir = os.path.join(base_dir, "models")
            downloads_dir = os.path.join(base_dir, "downloads")
            os.makedirs(models_dir, exist_ok=True)
            os.makedirs(downloads_dir, exist_ok=True)

            selected_display_name = self.combo_model.get()
            target_model_file = self.model_mapping.get(selected_display_name, "melband_roformer_inst_v2.ckpt")

            selected_fmt = self.combo_fmt.get()
            output_format = selected_fmt if selected_fmt != "Source" else "mp3"
            
            selected_sr = self.combo_sr.get()
            target_sr = selected_sr if selected_sr != "Source" else "44100"

            do_original = self.chk_original_var.get()
            do_vocals = self.chk_vocals_var.get()
            do_inst = self.chk_inst_var.get()
            do_video = self.chk_video_var.get()

            total = len(self.selected_files)

            for i, file_path in enumerate(self.selected_files):
                file_name = os.path.basename(file_path)
                base_name = os.path.splitext(file_name)[0]
                
                vocal_path = None
                inst_path = None
                original_path = None

                # 1. 處理原音 (Original)
                if do_original:
                    self.log(f"\n[{i+1}/{total}] Processing Original Audio...")
                    orig_ext = output_format if selected_fmt != "Source" else "mp3"
                    original_path = os.path.join(downloads_dir, f"{base_name}(Original).{orig_ext}")
                    orig_cmd = ["ffmpeg", "-y", "-i", file_path, "-vn", "-ar", target_sr, original_path]
                    subprocess.run(orig_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                need_ai = do_vocals or do_inst or do_video

                if need_ai:
                    self.log(f"\n{self.get_text('prep_audio').format(i+1, total, file_name)}\n")
                    temp_wav_path = os.path.join(downloads_dir, f"{base_name}_temp_input.wav")
                    conv_cmd = ["ffmpeg", "-y", "-i", file_path, "-vn", "-acodec", "pcm_s16le", "-ar", target_sr, temp_wav_path]
                    subprocess.run(conv_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                    separator_input = temp_wav_path if os.path.exists(temp_wav_path) else file_path

                    self.log(self.get_text('load_model').format(i+1, total, selected_display_name) + "\n")
                    
                    separator = Separator(
                        model_file_dir=models_dir,
                        output_dir=downloads_dir,
                        output_format=output_format,
                        normalization_threshold=0.9
                    )
                    separator.load_model(target_model_file)

                    separated_files = separator.separate(separator_input)

                    if os.path.exists(temp_wav_path):
                        os.remove(temp_wav_path)

                    # 重新命名與項目收集（支援 instrumental, other, accompaniment）
                    for f in separated_files:
                        full_f_path = os.path.join(downloads_dir, os.path.basename(f))
                        ext = os.path.splitext(full_f_path)[1]
                        
                        if "Vocals" in f or "vocals" in f:
                            target_vocal = os.path.join(downloads_dir, f"{base_name}(Vocals){ext}")
                            if os.path.exists(full_f_path):
                                if os.path.exists(target_vocal): os.remove(target_vocal)
                                os.rename(full_f_path, target_vocal)
                                vocal_path = target_vocal
                        elif any(keyword in f.lower() for keyword in ["instrumental", "other", "accompaniment"]):
                            target_inst = os.path.join(downloads_dir, f"{base_name}(Instrumental){ext}")
                            if os.path.exists(full_f_path):
                                if os.path.exists(target_inst): os.remove(target_inst)
                                os.rename(full_f_path, target_inst)
                                inst_path = target_inst

                    # 多軌影片重組
                    is_video_file = file_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm'))
                    if do_video and is_video_file and inst_path and vocal_path:
                        self.log(f"\n{self.get_text('multi_track').format(i+1, total)}\n")
                        output_mkv = os.path.join(downloads_dir, f"{base_name}(Multi-Track).mkv")

                        cmd = [
                            "ffmpeg", "-y",
                            "-i", file_path,
                            "-i", inst_path,
                            "-i", vocal_path,
                            "-map", "0:v?",
                            "-map", "0:a?",
                            "-map", "1:a:0",
                            "-map", "2:a:0",
                            "-metadata:s:a:0", "title=Original Audio",
                            "-metadata:s:a:1", "title=Instrumental",
                            "-metadata:s:a:2", "title=Vocals",
                            "-c:v", "copy",
                            "-c:a", "aac",
                            output_mkv
                        ]
                        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        if res.returncode == 0 and os.path.exists(output_mkv):
                            self.log(self.get_text("video_success").format(os.path.basename(output_mkv)) + "\n")
                        else:
                            err_msg = res.stderr.decode('utf-8', errors='ignore')
                            self.log(self.get_text("video_fail").format(err_msg) + "\n")

                    if vocal_path and not do_vocals:
                        if os.path.exists(vocal_path):
                            os.remove(vocal_path)
                    if inst_path and not do_inst:
                        if os.path.exists(inst_path):
                            os.remove(inst_path)

            self.log(self.get_text("all_done"))
            messagebox.showinfo(self.get_text("done_title"), self.get_text("done_msg"))

        except Exception as e:
            err_detail = traceback.format_exc()
            self.log(self.get_text("err_general").format(err_detail) + "\n")
            messagebox.showerror(self.get_text("err_title"), str(e))
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self.btn_run.config(state="normal", bg="#28A745")

if __name__ == "__main__":
    root = tk.Tk()
    app = KaraokeApp(root)
    root.mainloop()