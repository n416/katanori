# カタノリ ロボット顔ファームウェア — C++コアロジック + PCシミュレーター仕様

対象実機: XIAO ESP32S3 + OLED 128x64 (u8g2想定) + ReSpeaker Lite。
目的: 実機到着前に、実機へそのまま移植できるC++コアロジックをPC(Windows)上で開発・テストする。

## 絶対条件
- `firmware/core/` と `firmware/hal/` は **標準C++14のみ**。`Arduino.h`, `u8g2`, `Windows.h` 等への依存禁止。`<cstdint> <cmath> <algorithm>` 等の標準ヘッダのみ可。
- プラットフォーム依存コードは `firmware/esp32/`（参考スケルトン）と `simulator/win32/` にのみ置く。
- 全ファイル UTF-8、コメントは日本語可。

## ディレクトリ構成（このとおり作成）
```
firmware/
  core/
    DisplayBuffer.h / DisplayBuffer.cpp
    Face.h / Face.cpp
    StateMachine.h / StateMachine.cpp
    RobotCore.h / RobotCore.cpp
  hal/
    IHal.h
  esp32/
    main_esp32_skeleton.cpp   (参考実装。ビルド対象外の注記コメントを先頭に)
simulator/
  win32/
    main_win32.cpp
  wrapper.py                (追加: API通信・音声制御用Pythonラッパー)
  build.bat
docs/
  SIMULATOR.md
```

## firmware/core 仕様

### DisplayBuffer (128x64, 1bpp)
- `static constexpr int W=128, H=64;`
- 内部バッファ: `uint8_t buf[W*H/8]`（u8g2互換のページ形式でなくてよい。1byte=横8px、行優先で可。形式をヘッダにコメント明記）
- API: `clear()`, `setPixel(x,y,bool on)`, `getPixel(x,y)`, `fillRect(x,y,w,h,on)`, `drawRect`, `fillCircle(cx,cy,r,on)`, `drawHLine`, `drawVLine`, `const uint8_t* data() const`。範囲外は安全に無視。

### StateMachine
- `enum class RobotState { IDLE, LISTEN, THINK, SPEAK };`
- イベント駆動: `enum class RobotEvent { WAKE_WORD, SPEECH_END, RESPONSE_READY, SPEECH_DONE, TIMEOUT };`
- 遷移: IDLE --WAKE_WORD--> LISTEN --SPEECH_END--> THINK --RESPONSE_READY--> SPEAK --SPEECH_DONE--> IDLE。LISTEN/THINKでTIMEOUT→IDLE。
- `handleEvent(RobotEvent)`, `state()`, `timeInState()`（updateでdt加算）。不正イベントは無視。

### Face（目のアニメーション）
- 状態ごとの表情を `update(float dt, RobotState, float micLevel)` で時間発展させ `render(DisplayBuffer&)` で描画。
- IDLE: 大きめの丸目2つ。3〜6秒間隔のランダムまばたき（縦方向に潰れる補間）。ゆっくり視線が左右に揺れる。
- LISTEN: 目がやや大きくなり、micLevel(0..1)に応じて目の下に音量バー or 目がわずかに脈動。
- THINK: 目が細くなり、視線が上に。画面隅に回転するドット3つ（考え中表現）。
- SPEAK: micLevel（=出力音声レベルの代用）に応じて口（画面下部の矩形/波形）が開閉。目は通常。
- 状態遷移時は目のサイズ・位置を線形補間で0.2〜0.3秒かけて滑らかに変化させる（スナップ禁止）。
- 乱数は自前のxorshift等で実装（`<random>`可だが軽量に）。

### RobotCore（統合ファサード）
- `RobotCore(IHal&)`。`void tick()`: HALから時刻とmicLevelを取得→StateMachine/Face更新→DisplayBufferへ描画→`hal.flushDisplay(fb.data())`。
- `void injectEvent(RobotEvent)` を公開（シミュレーターのキー入力/実機の音声認識結果の両方から呼ぶ）。

## firmware/hal/IHal.h
```cpp
struct IHal {
  virtual ~IHal() = default;
  virtual uint32_t millis() = 0;
  virtual float getMicLevel() = 0;              // 0.0..1.0
  virtual void flushDisplay(const uint8_t* fb) = 0; // DisplayBuffer::data()形式
  virtual void log(const char* msg) = 0;
};
```
（必要ならメソッド追加可。ただし最小限に）

## simulator/win32/main_win32.cpp
- 純Win32 API + GDI のみ（外部ライブラリ禁止。リンクは -lgdi32 -luser32 のみ）。
- 128x64を**8倍拡大**した1024x512クライアント領域のウィンドウ。StretchDIBitsでフレームバッファを描画（ニアレストネイバー）。点灯色はシアン系(0,220,255)、消灯は黒に近い紺。
- 約60fpsループ（PeekMessage + Sleep(16)相当）。
- Win32HalクラスがIHalを実装: millis=GetTickCount、micLevelはキー操作から合成（下記）、flushDisplayは内部32bitピクセルバッファへ変換。
- キー操作（ウィンドウタイトルにも表示）:
  - `1`〜`4`: 直接 WAKE_WORD / SPEECH_END / RESPONSE_READY / SPEECH_DONE イベント注入
  - `Space`: 押下中 micLevel を0.2〜1.0でランダム振動（喋り/入力の模擬）、離すと0へ減衰
  - `ESC`: 終了
- コンソールにも状態遷移ログを出力（log実装）。
- **Pythonラッパーとの連携 (IPC)**:
  - キー操作等でイベントが発火した際、標準出力に `[EVENT] WAKE_WORD` などのトリガーを出力し、即座に `fflush(stdout)` します。
  - バックグラウンドで `stdin` を監視し、ラッパーからのコマンド（例: `CMD:SPEAK_START`）を受け取って状態遷移（口パクの開始など）を連動させます。

## simulator/build.bat
- `g++ -std=c++14 -O2` で firmware/core/*.cpp と simulator/win32/main_win32.cpp をコンパイル、`-lgdi32 -luser32 -mwindows` なし（コンソールログを見たいので -mwindows は付けない）。出力 `simulator\katanori_sim.exe`。
- g++ が見つからない場合のエラーメッセージ表示。

## firmware/esp32/main_esp32_skeleton.cpp
- 参考用。`#if 0 // 実機ビルド時にArduino環境へ移植` 等で囲うかコメント主体でよい。U8g2でflushDisplayを実装するEsp32Halの例と、setup/loopでRobotCore::tick()を回す形を示す。

## docs/SIMULATOR.md
- w64devkit等でg++を入れる手順、build.batの実行、キー操作一覧、実機移植の手順（core/halはそのままコピー、esp32ディレクトリのHALだけ実装）を記載。

## Pythonラッパー仕様 (wrapper.py)
C++シミュレーター側（`main_win32.cpp`）を純粋なWin32環境に保ち、Windows専用の複雑なネットワーク・音声処理を混入させないため、Gemini APIの双方向ストリーミング通信とPCのマイク/スピーカー制御は別プロセスのPythonスクリプトが担います。

*   **動作フロー**:
    1. `wrapper.py` が `subprocess` でコンパイル済みの `katanori_sim.exe` を起動し、その標準入出力（stdin/stdout）を監視・フックします。
    2. C++側でのキー操作により WAKE_WORD イベントが発生し、`stdout` に `[EVENT] WAKE_WORD` が出力されたのを確認すると、`pyaudio` を用いてマイク録音を開始し、Gemini APIへWebSocket接続を確立して音声を送信します。
    3. Gemini APIから音声ストリームを受信すると、スピーカーから再生しつつ、C++側の `stdin` に対して `CMD:SPEAK_START` コマンドを送ります。
    4. C++シミュレーターはコマンドを受けて `SPEAK` 状態に遷移し、顔（口パク）のアニメーションを開始します。再生完了後は `CMD:SPEAK_END` を受けて `IDLE` に戻ります。
