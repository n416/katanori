import sys
import os
import subprocess
import threading
import queue
import time
import asyncio
import json
import base64
import collections
import pyaudio
import websockets
import array
import math

# Windowsのコンソール/リダイレクト先がcp932でも絵文字ログで落ちないようにする
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SIM_EXE = os.path.join(os.path.dirname(__file__), "katanori_sim.exe")
WS_URL = "wss://katanori-backend.tobira-sys.workers.dev/?voice=Achird"

# PyAudio 設定 (16bit, Mono)
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000        # マイク入力 (Gemini Live APIの入力仕様)
OUT_RATE = 24000    # スピーカー出力 (Geminiの返答は audio/pcm;rate=24000)
CHUNK = 1024

# 会話が途切れてからセッションを閉じるまでの秒数。
# Geminiは無通信のセッションを約2分で一方的に切る(実測2.09分)ため、
# それより十分短くして「切られる」前に「自分から閉じる」
SESSION_IDLE_CLOSE_SEC = 45

class WrapperApp:
    def __init__(self):
        self.process = None
        self.event_queue = queue.Queue()
        self.audio_queue = asyncio.Queue()
        self.play_queue = queue.Queue()
        self.p = pyaudio.PyAudio()
        self.stream_in = None
        self.stream_out = None
        self.is_recording = False
        self.is_playing = False
        self.loop = None
        self.ws = None
        self.session_task = None       # 会話中だけ張るWSセッション
        self.setup_event = None        # setupComplete待ち (これ以前に送った音声は取りこぼされる)
        self.idle_close_handle = None  # 無通信でセッションを閉じるタイマー

        # --- モニター用の状態 ---
        self.conn_status = "未接続"
        self.gemini_ready = False
        self.mic_level = 0.0          # 直近のマイクピーク (0.0〜1.0)
        self.turn_sent_chunks = 0     # このターンで送信したチャンク数
        self.turn_sent_bytes = 0
        self.dropped_chunks = 0       # エコーガードで破棄したチャンク数
        self.recv_chunks = 0
        self.recv_bytes = 0
        self.turn_active = False      # Geminiの応答音声を受信中か
        self.t_stream_end = None      # audioStreamEnd送信時刻 (応答遅延の実測用)
        self.input_text = ""          # Geminiが聞き取った内容 (inputTranscription)
        self.output_text = ""         # Geminiの応答内容 (outputTranscription)
        self.log_lines = collections.deque(maxlen=200)

        # ロボットボイス設定（本格的なマイコン用アルゴリズム）
        self.enable_robot_voice = False  # 遅延検証のため一時的にOFF
        self.pitch_ratio = 1.10      # ピッチ倍率（声の高さ。1.0以上で高く、小型ロボット風に）
        self.comb_feedback = 0.75    # 金属共鳴の強さ（0.0〜0.9）

        # ピッチシフター用リングバッファ
        self.delay_buf = array.array('h', [0] * 48000)
        self.wr_idx = 0
        self.phase = 0.0

        # 簡易GUI (後でC++移植時に調整)
        self.grain_size_ms = 44.0

    # ---------------------------------------------------------------
    # ログ (コンソール + モニターGUI 両方へ)
    # ---------------------------------------------------------------
    def log(self, msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(f"[WRAPPER] {msg}")
        self.log_lines.append(line)

    def sim_cmd(self, cmd):
        try:
            self.process.stdin.write((cmd + "\n").encode())
            self.process.stdin.flush()
        except Exception:
            pass

    # ---------------------------------------------------------------
    # C++ シミュレーター
    # ---------------------------------------------------------------
    def start_sim(self):
        if not os.path.exists(SIM_EXE):
            print(f"[Error] {SIM_EXE} が見つかりません。先にビルドしてください。")
            sys.exit(1)
        self.process = subprocess.Popen(
            SIM_EXE, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, bufsize=0
        )
        threading.Thread(target=self.monitor_sim, daemon=True).start()
        threading.Thread(target=self.handle_events, daemon=True).start()
        threading.Thread(target=self.playback_worker, daemon=True).start()

    def monitor_sim(self):
        """C++からのstdoutを監視"""
        for line in iter(self.process.stdout.readline, b''):
            decoded = line.decode('utf-8', errors='replace').strip()
            # 口パクイベントの定型ログはラッパー側で表示するので抑制
            if "Event Injected (via stdin)" in decoded:
                continue
            if decoded:
                print(f"[C++ SIM] {decoded}")
            if "[EVENT] WAKE_WORD" in decoded:
                self.event_queue.put("WAKE_WORD")
            elif "[EVENT] SPEECH_END" in decoded:
                self.event_queue.put("SPEECH_END")
            elif "[EVENT] FREQ_UP" in decoded:
                self.event_queue.put("FREQ_UP")
            elif "[EVENT] FREQ_DOWN" in decoded:
                self.event_queue.put("FREQ_DOWN")
            elif "[EVENT] BIT_UP" in decoded:
                self.event_queue.put("BIT_UP")
            elif "[EVENT] BIT_DOWN" in decoded:
                self.event_queue.put("BIT_DOWN")

    def handle_events(self):
        """イベントキューを処理して録音開始・終了を制御"""
        while True:
            event = self.event_queue.get()
            if event == "WAKE_WORD":
                self.turn_sent_chunks = 0
                self.turn_sent_bytes = 0
                self.dropped_chunks = 0
                self.input_text = ""
                # 先に接続を始める。setup(実測約0.6秒)は発話中に裏で終わるので待たない
                if self.loop:
                    asyncio.run_coroutine_threadsafe(self.on_wake_word(), self.loop)
                self.log("🎙 録音開始（マイク→DO送信）")
                self.start_recording()
            elif event == "SPEECH_END":
                self.stop_recording()
                sent_sec = self.turn_sent_bytes / (RATE * 2)
                self.log(f"⏹ 録音終了（送信: {self.turn_sent_chunks}チャンク / {sent_sec:.1f}秒）")
                if self.loop:
                    asyncio.run_coroutine_threadsafe(self.send_end_signal(), self.loop)
            elif event in ["FREQ_UP", "FREQ_DOWN", "BIT_UP", "BIT_DOWN"]:
                # チューニング機能 (十字キー)
                if event == "FREQ_UP": self.pitch_ratio = min(2.5, self.pitch_ratio + 0.1)
                elif event == "FREQ_DOWN": self.pitch_ratio = max(0.5, self.pitch_ratio - 0.1)
                elif event == "BIT_UP": self.comb_feedback = min(0.9, self.comb_feedback + 0.1)
                elif event == "BIT_DOWN": self.comb_feedback = max(0.0, self.comb_feedback - 0.1)
                self.log(f"⚙️ pitch_ratio = {self.pitch_ratio:.1f}, comb_feedback = {self.comb_feedback:.1f}")

    # ---------------------------------------------------------------
    # 録音
    # ---------------------------------------------------------------
    def start_recording(self):
        if self.stream_in is None:
            self.stream_in = self.p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                                         input=True, frames_per_buffer=CHUNK,
                                         stream_callback=self.audio_callback)
        self.is_recording = True
        self.stream_in.start_stream()

    def stop_recording(self):
        self.is_recording = False
        if self.stream_in:
            self.stream_in.stop_stream()
        self.mic_level = 0.0

    def audio_callback(self, in_data, frame_count, time_info, status):
        """マイクからの音声コールバック。非同期キューへ渡す"""
        samples = array.array('h', in_data)
        peak = 0
        for s in samples:
            a = -s if s < 0 else s
            if a > peak: peak = a
        self.mic_level = peak / 32768.0

        if self.is_recording and self.loop:
            if self.is_playing:
                # エコーガード: スピーカー再生中はマイク音声を送らない
                # (Geminiが自分の声で割り込み(interrupted)判定するのを防ぐ)
                self.dropped_chunks += 1
            else:
                self.loop.call_soon_threadsafe(self.audio_queue.put_nowait, in_data)
        return (None, pyaudio.paContinue)

    # ---------------------------------------------------------------
    # ロボットボイスDSP
    # ---------------------------------------------------------------
    def apply_robot_dsp(self, audio_data: bytes) -> bytes:
        """マイコン移植を前提とした本格ロボットボイスDSP
        (タイムドメイン・ピッチシフター + コムフィルター)"""
        in_samples = array.array('h', audio_data)
        out_samples = array.array('h', [0] * len(in_samples))

        buf_len = len(self.delay_buf)
        # 3msディレイ (コムフィルタ用: 24000 * 0.003 = 72)
        delay_ms_samples = int(OUT_RATE * 0.003)

        # ピッチシフト用最大ディレイ
        max_delay = int(OUT_RATE * (self.grain_size_ms / 1000.0))
        if max_delay < 10: max_delay = 10

        # 1サンプルあたりの位相増分
        phase_inc = 0.0
        if self.pitch_ratio != 1.0:
            phase_inc = (1.0 - self.pitch_ratio) / max_delay

        for i in range(len(in_samples)):
            # 1. リングバッファへ書き込み
            self.delay_buf[self.wr_idx] = in_samples[i]

            # LFO更新
            self.phase += phase_inc
            if self.phase >= 1.0: self.phase -= 1.0
            elif self.phase < 0.0: self.phase += 1.0

            # 2つの位相 (180度反転)
            phase1 = self.phase
            phase2 = self.phase + 0.5
            if phase2 >= 1.0: phase2 -= 1.0

            d1 = phase1 * max_delay
            d2 = phase2 * max_delay

            # 三角窓
            w1 = 1.0 - abs(2.0 * phase1 - 1.0)
            w2 = 1.0 - abs(2.0 * phase2 - 1.0)

            # ポインタ1
            rd1 = self.wr_idx - d1
            if rd1 < 0: rd1 += buf_len
            idx1_0 = int(rd1)
            idx1_1 = (idx1_0 + 1) % buf_len
            frac1 = rd1 - idx1_0
            s1 = self.delay_buf[idx1_0] + frac1 * (self.delay_buf[idx1_1] - self.delay_buf[idx1_0])

            # ポインタ2
            rd2 = self.wr_idx - d2
            if rd2 < 0: rd2 += buf_len
            idx2_0 = int(rd2)
            idx2_1 = (idx2_0 + 1) % buf_len
            frac2 = rd2 - idx2_0
            s2 = self.delay_buf[idx2_0] + frac2 * (self.delay_buf[idx2_1] - self.delay_buf[idx2_0])

            # クロスフェード
            val = s1 * w1 + s2 * w2

            # コムフィルター (ショートディレイでメタリック共鳴を付加)
            if i >= delay_ms_samples:
                val = val + out_samples[i - delay_ms_samples] * self.comb_feedback

            # クリッピングガード
            if val > 32767: val = 32767
            elif val < -32768: val = -32768

            out_samples[i] = int(val)
            self.wr_idx = (self.wr_idx + 1) % buf_len

        if hasattr(out_samples, 'tobytes'):
            return out_samples.tobytes()
        return out_samples.tostring()

    # ---------------------------------------------------------------
    # 再生 (専用スレッド: WS受信ループをブロックしないため)
    # ---------------------------------------------------------------
    def playback_worker(self):
        while True:
            kind, data = self.play_queue.get()
            if kind == "START":
                self.is_playing = True
                self.sim_cmd("CMD:SPEAK_START")
            elif kind == "END":
                self.is_playing = False
                self.sim_cmd("CMD:SPEAK_END")
            elif kind == "DATA":
                self.play_audio(data)

    def reset_turn_state(self):
        """切断時など: 再生中フラグが残るとエコーガードがマイクを止め続けるため必ず解除する"""
        if self.turn_active or self.is_playing:
            self.clear_playback()
        self.turn_active = False

    def clear_playback(self):
        """割り込み時: 未再生の音声を破棄する"""
        try:
            while True:
                self.play_queue.get_nowait()
        except queue.Empty:
            pass
        self.play_queue.put(("END", None))

    def play_audio(self, data):
        """スピーカーからの再生"""
        if self.enable_robot_voice:
            data = self.apply_robot_dsp(data)

        if self.stream_out is None:
            self.stream_out = self.p.open(format=FORMAT, channels=CHANNELS, rate=OUT_RATE, output=True)
        self.stream_out.write(data)

    # ---------------------------------------------------------------
    # WebSocket
    # ---------------------------------------------------------------
    async def send_end_signal(self):
        """マイク停止をGeminiに伝える。audioStreamEnd で音声ストリーム終了を
        明示すると自動VADが発話終了を確定して返答生成が始まる。
        注意: clientContent+turnComplete はVADが発話中と認識していると
        無視されてハングするため使わないこと (2026-07-25の障害で確定済み)"""
        if not self.ws:
            self.log("⚠️ 未接続のため audioStreamEnd を送れません。「1」から録音し直してください")
            return
        # 録音停止直前にキューへ入った音声を先に送り切る (最大2秒)
        deadline = time.time() + 2.0
        while not self.audio_queue.empty() and time.time() < deadline:
            await asyncio.sleep(0.05)
        try:
            await self.ws.send(json.dumps({"realtimeInput": {"audioStreamEnd": True}}))
            self.t_stream_end = time.time()
            self.log("➡ audioStreamEnd 送信（Geminiの応答待ち）")
        except Exception as e:
            self.log(f"⚠️ audioStreamEnd送信エラー: {e}")

    # ---------------------------------------------------------------
    # セッション管理 (会話するときだけ接続する)
    #   Geminiは無通信のセッションを約2分で切るので常時接続は成立しない。
    #   「1」キーで張り、会話が途切れたら自分から閉じる。
    # ---------------------------------------------------------------
    async def on_wake_word(self):
        self.cancel_idle_close()
        if self.session_task and not self.session_task.done():
            return  # 会話継続中: 既存セッションを再利用して文脈を保つ
        self.drain_audio_queue()  # 前セッションの切れ端を持ち込まない
        self.setup_event = asyncio.Event()
        self.session_task = asyncio.create_task(self.run_session())

    async def run_session(self):
        self.conn_status = "接続中..."
        self.log("🔗 セッション開始（DOへ接続）")
        t0 = time.time()
        try:
            async with websockets.connect(WS_URL) as ws:
                self.ws = ws
                self.conn_status = "接続済"
                send_task = asyncio.create_task(self.ws_sender(ws))
                recv_task = asyncio.create_task(self.ws_receiver(ws))
                done, pending = await asyncio.wait(
                    [send_task, recv_task], return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                for task in done:
                    # 例外を回収しないと "Task exception was never retrieved" が
                    # 標準エラーに出る。切断自体は正常系なので黙って捨てる
                    if not task.cancelled():
                        exc = task.exception()
                        if exc and not isinstance(exc, websockets.ConnectionClosed):
                            self.log(f"⚠️ セッション内エラー: {exc}")
        except Exception as e:
            self.log(f"⚠️ 接続エラー: {e}")
        finally:
            self.ws = None
            self.gemini_ready = False
            self.conn_status = "未接続"
            self.reset_turn_state()
            self.cancel_idle_close()
            self.log(f"🔌 セッション終了（{time.time() - t0:.0f}秒）。次の「1」で再接続します。")

    def schedule_idle_close(self):
        """やりとりが途切れたら自分から閉じる (Geminiに切られる前に)"""
        self.cancel_idle_close()
        if self.loop:
            self.idle_close_handle = self.loop.call_later(
                SESSION_IDLE_CLOSE_SEC,
                lambda: asyncio.ensure_future(self.close_session())
            )

    def cancel_idle_close(self):
        if self.idle_close_handle:
            self.idle_close_handle.cancel()
            self.idle_close_handle = None

    async def close_session(self):
        self.idle_close_handle = None
        if self.ws:
            self.log(f"💤 {SESSION_IDLE_CLOSE_SEC}秒やりとりが無いのでセッションを閉じます")
            try:
                await self.ws.close()
            except Exception:
                pass

    def drain_audio_queue(self):
        try:
            while True:
                self.audio_queue.get_nowait()
        except asyncio.QueueEmpty:
            pass

    async def ws_sender(self, ws):
        """オーディオキューの音声をGemini仕様のJSONに包んで送信"""
        # setupComplete前に送るとGemini側で取りこぼされる。待つ間の音声は
        # キューに溜まるので、発話の頭は欠けない
        await self.setup_event.wait()
        while True:
            data = await self.audio_queue.get()
            # Gemini Live API 新形式 (gemini-3.1-flash-live は旧mediaChunksを拒否する)
            payload = {
                "realtimeInput": {
                    "audio": {
                        "mimeType": "audio/pcm;rate=16000",
                        "data": base64.b64encode(data).decode('utf-8')
                    }
                }
            }
            try:
                await ws.send(json.dumps(payload))
                self.turn_sent_chunks += 1
                self.turn_sent_bytes += len(data)
            except Exception:
                break # 再接続へ

    async def ws_receiver(self, ws):
        """DO(Gemini)からの返答を受信してパース"""
        async for message in ws:
            try:
                msg = json.loads(message)
            except Exception:
                continue
            try:
                # DOからのデバッグ情報 (接続エラー等はここに出る)
                if "_debug" in msg:
                    self.log(f"[DO] {msg['_debug']}")
                    continue

                # Geminiからのセットアップ完了通知
                if "setupComplete" in msg:
                    self.gemini_ready = True
                    if self.setup_event:
                        self.setup_event.set()
                    self.log("✅ Gemini セットアップ完了（音声の送信を開始）")
                    continue

                sc = msg.get("serverContent")
                if sc is None:
                    continue

                # 割り込み検知 (マイクがスピーカー音や雑音を拾った場合ここに来る)
                if sc.get("interrupted"):
                    self.log("🚫 Geminiが割り込みを検知（応答を中断。マイクが音を拾った可能性）")
                    self.clear_playback()
                    self.turn_active = False
                    continue

                # 文字起こし (何が聞こえたか / 何を話しているか)
                it = sc.get("inputTranscription", {}).get("text")
                if it:
                    self.input_text += it
                ot = sc.get("outputTranscription", {}).get("text")
                if ot:
                    self.output_text += ot

                model_turn = sc.get("modelTurn")
                if model_turn:
                    for part in model_turn.get("parts", []):
                        if "inlineData" in part:
                            audio_data = base64.b64decode(part["inlineData"]["data"])
                            if not self.turn_active:
                                self.turn_active = True
                                self.recv_chunks = 0
                                self.recv_bytes = 0
                                self.output_text = ""
                                if self.t_stream_end:
                                    self.log(f"⏱ 発話終了→応答開始 {time.time() - self.t_stream_end:.2f}秒")
                                    self.t_stream_end = None
                                self.log("🔊 応答音声の受信・再生を開始")
                                self.play_queue.put(("START", None))
                            self.recv_chunks += 1
                            self.recv_bytes += len(audio_data)
                            self.play_queue.put(("DATA", audio_data))
                        elif "text" in part:
                            self.log(f"[GEMINI TEXT] {part['text']}")

                if sc.get("turnComplete"):
                    if self.input_text.strip():
                        self.log(f"👂 Geminiの聞き取り: 「{self.input_text.strip()}」")
                    else:
                        self.log("👂 Geminiの聞き取り: (なし — 音声が届いていない可能性)")
                    if self.output_text.strip():
                        self.log(f"🗣 Geminiの応答: 「{self.output_text.strip()}」")
                    if self.turn_active:
                        recv_sec = self.recv_bytes / (OUT_RATE * 2)
                        self.log(f"✅ ターン完了（応答音声: {self.recv_chunks}チャンク / {recv_sec:.1f}秒）")
                        self.turn_active = False
                        self.play_queue.put(("END", None))
                    else:
                        self.log("✅ ターン完了（応答音声なし）")
                    # 会話が続くなら次のWAKE_WORDでキャンセルされる
                    self.schedule_idle_close()

            except Exception as e:
                self.log(f"⚠️ 受信処理エラー: {e}")

    # ---------------------------------------------------------------
    # モニターGUI (Tkinter / 別スレッド)
    # ---------------------------------------------------------------
    def start_gui(self):
        threading.Thread(target=self.gui_loop, daemon=True).start()

    def gui_loop(self):
        try:
            import tkinter as tk
        except ImportError:
            self.log("⚠️ tkinterが無いためモニターGUIは無効です")
            return

        root = tk.Tk()
        root.title("Katanori Audio Monitor")
        root.geometry("560x480")
        root.configure(bg="#101828")

        FG = "#e2e8f0"
        DIM = "#94a3b8"
        BG = "#101828"
        FONT = ("Meiryo UI", 10)

        def row(label_text):
            f = tk.Frame(root, bg=BG)
            f.pack(fill="x", padx=10, pady=2)
            tk.Label(f, text=label_text, width=10, anchor="w", bg=BG, fg=DIM, font=FONT).pack(side="left")
            v = tk.Label(f, text="", anchor="w", bg=BG, fg=FG, font=FONT, justify="left")
            v.pack(side="left", fill="x", expand=True)
            return v

        conn_v = row("接続")
        state_v = row("状態")

        # マイクレベルバー
        f = tk.Frame(root, bg=BG)
        f.pack(fill="x", padx=10, pady=2)
        tk.Label(f, text="マイク", width=10, anchor="w", bg=BG, fg=DIM, font=FONT).pack(side="left")
        level_canvas = tk.Canvas(f, height=18, bg="#1e293b", highlightthickness=0)
        level_canvas.pack(side="left", fill="x", expand=True)

        sent_v = row("送信")
        recv_v = row("受信")

        def text_row(label_text):
            f = tk.Frame(root, bg=BG)
            f.pack(fill="x", padx=10, pady=2)
            tk.Label(f, text=label_text, width=10, anchor="nw", bg=BG, fg=DIM, font=FONT).pack(side="left", anchor="n")
            v = tk.Label(f, text="", anchor="w", bg=BG, fg=FG, font=FONT,
                         justify="left", wraplength=420)
            v.pack(side="left", fill="x", expand=True)
            return v

        heard_v = text_row("聞き取り")
        reply_v = text_row("応答")

        tk.Label(root, text="イベントログ", anchor="w", bg=BG, fg=DIM, font=FONT).pack(fill="x", padx=10, pady=(8, 0))
        log_text = tk.Text(root, height=10, bg="#0b1220", fg="#cbd5e1",
                           font=("Consolas", 9), state="disabled", wrap="none")
        log_text.pack(fill="both", expand=True, padx=10, pady=(2, 10))

        last_log_len = [0]

        def refresh():
            if self.ws:
                gem = "✅ Gemini準備OK" if self.gemini_ready else "⏳ Gemini待ち"
                conn_v.config(text=f"{self.conn_status} / {gem}")
            else:
                conn_v.config(text=f"{self.conn_status}（会話するときだけ接続します）")

            if self.is_playing and self.is_recording:
                state_v.config(text="🔊 再生中（マイク送信は一時停止＝エコーガード）", fg="#fbbf24")
            elif self.is_playing:
                state_v.config(text="🔊 再生中", fg="#38bdf8")
            elif self.is_recording:
                state_v.config(text="🎙 録音中（DOへ送信中）", fg="#4ade80")
            elif self.ws:
                state_v.config(text="💬 セッション接続中（無通信が続けば自動で閉じます）", fg="#a78bfa")
            else:
                state_v.config(text="待機（シミュレーター窓で 1=話す開始 / 2=話す終了）", fg=FG)

            # マイクレベル
            level_canvas.delete("all")
            w = level_canvas.winfo_width()
            h = 18
            lv = self.mic_level
            color = "#ef4444" if lv > 0.9 else ("#4ade80" if self.is_recording else "#64748b")
            level_canvas.create_rectangle(0, 0, int(w * lv), h, fill=color, width=0)
            level_canvas.create_text(w - 4, h // 2, text=f"{lv:.2f}", anchor="e", fill="#e2e8f0", font=("Consolas", 8))

            sent_sec = self.turn_sent_bytes / (RATE * 2)
            drop = f"  (エコーガード破棄: {self.dropped_chunks})" if self.dropped_chunks else ""
            sent_v.config(text=f"{self.turn_sent_chunks} チャンク / {sent_sec:.1f} 秒{drop}")

            recv_sec = self.recv_bytes / (OUT_RATE * 2)
            recv_v.config(text=f"{self.recv_chunks} チャンク / {recv_sec:.1f} 秒")

            heard_v.config(text=self.input_text.strip() or "—")
            reply_v.config(text=self.output_text.strip() or "—")

            if len(self.log_lines) != last_log_len[0]:
                last_log_len[0] = len(self.log_lines)
                log_text.config(state="normal")
                log_text.delete("1.0", "end")
                log_text.insert("1.0", "\n".join(self.log_lines))
                log_text.see("end")
                log_text.config(state="disabled")

            root.after(100, refresh)

        refresh()
        root.mainloop()

async def main():
    app = WrapperApp()
    app.loop = asyncio.get_running_loop()
    app.start_sim()
    app.start_gui()
    app.log("待機中。シミュレーター窓で「1」を押すと接続して録音を開始します。")
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n[WRAPPER] 終了します。")
    finally:
        await app.close_session()
        if app.process:
            app.process.terminate()
            app.process.wait()

if __name__ == "__main__":
    asyncio.run(main())
