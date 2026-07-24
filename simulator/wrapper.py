import sys
import os
import subprocess
import threading
import queue
import time
import asyncio
import json
import base64
import pyaudio
import websockets

SIM_EXE = os.path.join(os.path.dirname(__file__), "katanori_sim.exe")
WS_URL = "wss://katanori-backend.tobira-sys.workers.dev"

# PyAudio 設定 (16bit, Mono)
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000        # マイク入力 (Gemini Live APIの入力仕様)
OUT_RATE = 24000    # スピーカー出力 (Geminiの返答は audio/pcm;rate=24000)
CHUNK = 1024

class WrapperApp:
    def __init__(self):
        self.process = None
        self.event_queue = queue.Queue()
        self.audio_queue = asyncio.Queue()
        self.p = pyaudio.PyAudio()
        self.stream_in = None
        self.stream_out = None
        self.is_recording = False
        self.loop = None
        self.ws = None

    def start_sim(self):
        if not os.path.exists(SIM_EXE):
            print(f"[Error] {SIM_EXE} が見つかりません。先にビルドしてください。")
            sys.exit(1)
        # C++シミュレーター起動
        self.process = subprocess.Popen(
            SIM_EXE, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, bufsize=1
        )
        # 監視スレッド開始
        threading.Thread(target=self.monitor_sim, daemon=True).start()
        threading.Thread(target=self.handle_events, daemon=True).start()

    def monitor_sim(self):
        """C++からのstdoutを監視"""
        for line in iter(self.process.stdout.readline, b''):
            decoded = line.decode('utf-8', errors='replace').strip()
            print(f"[C++ SIM] {decoded}")
            if "[EVENT] WAKE_WORD" in decoded:
                self.event_queue.put("WAKE_WORD")
            elif "[EVENT] SPEECH_END" in decoded:
                self.event_queue.put("SPEECH_END")

    def handle_events(self):
        """イベントキューを処理して録音開始・終了を制御"""
        while True:
            event = self.event_queue.get()
            if event == "WAKE_WORD":
                print("[WRAPPER] 🎙️ マイク録音を開始します (DOへ送信)...")
                self.start_recording()
            elif event == "SPEECH_END":
                print("[WRAPPER] ⏹️ 録音終了 (DOへ完了通知)...")
                self.stop_recording()
                if self.loop:
                    asyncio.run_coroutine_threadsafe(self.send_end_signal(), self.loop)

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

    def audio_callback(self, in_data, frame_count, time_info, status):
        """マイクからの音声コールバック。非同期キューへ渡す"""
        if self.is_recording and self.loop:
            self.loop.call_soon_threadsafe(self.audio_queue.put_nowait, in_data)
        return (None, pyaudio.paContinue)

    def play_audio(self, data):
        """スピーカーからの再生"""
        if self.stream_out is None:
            self.stream_out = self.p.open(format=FORMAT, channels=CHANNELS, rate=OUT_RATE, output=True)
        self.stream_out.write(data)

    async def send_end_signal(self):
        """録音終了のシグナルをDOに送る"""
        if self.ws:
            # Gemini Live API に「ユーザーのターンが終わった（返答を生成してよい）」ことを伝えるシグナル
            payload = {
                "clientContent": {
                    "turns": [{"role": "user", "parts": []}],
                    "turnComplete": True
                }
            }
            try:
                await self.ws.send(json.dumps(payload))
            except Exception as e:
                print(f"[WRAPPER] 通知エラー: {e}")

    async def run_websocket(self):
        """Durable Objects との WebSocket 通信メインループ"""
        self.loop = asyncio.get_running_loop()
        print(f"[WRAPPER] DOサーバー ({WS_URL}) に接続中...")
        while True:
            try:
                async with websockets.connect(WS_URL) as ws:
                    self.ws = ws
                    print("[WRAPPER] ✅ DOサーバーに接続完了。")
                    
                    # 送受信タスクを並行実行 (どちらかが終了=切断とみなし、もう片方を止めて再接続へ)
                    send_task = asyncio.create_task(self.ws_sender(ws))
                    recv_task = asyncio.create_task(self.ws_receiver(ws))
                    done, pending = await asyncio.wait(
                        [send_task, recv_task], return_when=asyncio.FIRST_COMPLETED
                    )
                    for task in pending:
                        task.cancel()
                    print("[WRAPPER] ⚠️ 接続が切れました。3秒後に再接続します...")
                    await asyncio.sleep(3)
            except Exception as e:
                print(f"[WRAPPER] ⚠️ WebSocket接続エラー: {e}. 3秒後に再接続します...")
                await asyncio.sleep(3)

    async def ws_sender(self, ws):
        """オーディオキューの音声をGemini仕様のJSONに包んで送信"""
        while True:
            data = await self.audio_queue.get()
            # Gemini Multimodal Live API のフォーマット
            payload = {
                "realtimeInput": {
                    "mediaChunks": [{
                        "mimeType": "audio/pcm;rate=16000",
                        "data": base64.b64encode(data).decode('utf-8')
                    }]
                }
            }
            try:
                await ws.send(json.dumps(payload))
            except Exception:
                break # 再接続へ

    async def ws_receiver(self, ws):
        """DO(Gemini)からの返答を受信してパース"""
        async for message in ws:
            try:
                msg = json.loads(message)
                # デバッグ用にGeminiから来た生メッセージ（先頭200文字）を出力
                print(f"[GEMINI RAW] {message[:200]}")
                
                # Geminiからのセットアップ完了通知
                if "setupComplete" in msg:
                    print("[WRAPPER] ✅ Gemini API セットアップ完了")
                    continue
                
                # Geminiからのコンテンツ返答
                if "serverContent" in msg:
                    model_turn = msg["serverContent"].get("modelTurn")
                    if model_turn:
                        for part in model_turn.get("parts", []):
                            if "inlineData" in part:
                                print("[WRAPPER] 🔊 音声を受信しました。スピーカーで再生します...")
                                # 口パク開始
                                self.process.stdin.write(b"CMD:SPEAK_START\n")
                                self.process.stdin.flush()
                                
                                # 再生
                                audio_data = base64.b64decode(part["inlineData"]["data"])
                                self.play_audio(audio_data)
                                
                                # 口パク終了
                                self.process.stdin.write(b"CMD:SPEAK_END\n")
                                self.process.stdin.flush()
                            elif "text" in part:
                                print(f"[GEMINI TEXT] {part['text']}")
                                
            except Exception as e:
                print(f"[WRAPPER] 受信エラー: {e}")

async def main():
    app = WrapperApp()
    app.start_sim()
    try:
        await app.run_websocket()
    except KeyboardInterrupt:
        print("\n[WRAPPER] 終了します。")
    finally:
        if app.process:
            app.process.terminate()
            app.process.wait()

if __name__ == "__main__":
    asyncio.run(main())
