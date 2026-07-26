# カタノリ ロボット顔 PCシミュレーター ガイド

## 1. 概要
`firmware/core`（標準C++14のコアロジック）を Windows PC 上で動かす Win32 API / GDI ベースの軽量シミュレーターです。もとは実機到着前の開発用でしたが、実機が完成した今の役割は次の2つです。

- **顔の確認** — `firmware/core` は実機とシミュレーターで**同じソースを共有**しています（コピーではありません。→ 5章）。ここに映る顔は実機のOLEDと同一です。
- **バックエンドの試験台** — `simulator/wrapper.py` は実機と同じURL・同じプロトコルで Durable Object へ接続します。プロンプト・つなぎ言葉・声・時刻注入といったサーバー側の変更は、**実機へ焼かずにここで確かめられます**。

### ここでは確かめられないもの
I2S のスレーブ設定、ReSpeaker Lite のハードウェアAEC、Wi-Fiプロビジョニング、Usrボタン、起動時ノイズ。いずれも実機でしか出ません。シミュレーターをこれらの「双子」にする計画は**ありません**（労力に対して返りが薄いため）。

---

## 2. 開発環境のセットアップ (Windows)
ビルドには `g++` (C++14対応) が必要です。

### 推奨環境: w64devkit / MinGW-w64
1. **w64devkit** または **MinGW-w64** をダウンロードして展開します。
2. 展開先の `bin` ディレクトリを環境変数 `PATH` に追加します。
3. コマンドプロンプト等で `g++ --version` を実行し、正常に認識されることを確認します。

---

## 3. ビルド手順
リポジトリルートで `simulator\build.bat` を実行します。

```cmd
simulator\build.bat
```

ビルドが成功すると、`simulator\katanori_sim.exe` が生成されます。

PATH に g++ を通していない場合は、PowerShell で前置してから実行します。

```powershell
$env:PATH = "C:\Users\shingo\w64devkit\bin;" + $env:PATH; cmd /c simulator\build.bat
```

---

## 4. 実行と操作方法

### 4.1 顔だけ見る
`simulator\katanori_sim.exe` を直接実行すると 1024x512 のウィンドウが開きます。

| キー | 動作 |
|---|---|
| `1` | イベント注入: `WAKE_WORD` (IDLE -> LISTEN) |
| `2` | イベント注入: `SPEECH_END` (LISTEN -> THINK) |
| `3` | イベント注入: `RESPONSE_READY` (THINK -> SPEAK) |
| `4` | イベント注入: `SPEECH_DONE` (SPEAK -> IDLE) |
| `Space` | 押下中、マイク入力レベル (0.2〜1.0) を擬似振動注入 |
| `ESC` | シミュレーター終了 |

### 4.2 会話する（ラッパー経由）

```cmd
python simulator\wrapper.py
```

`wrapper.py` がシミュレーターを子プロセスとして起動し、PCのマイク・スピーカーと Durable Object への接続を担当します。会話は**シミュレーターの窓**で `1`（話し始める）→ `2`（話し終わり）。別窓のモニターGUIに接続状態・マイクレベル・聞き取り・応答・遅延が出ます。

必要なもの: `pyaudio`, `websockets`。

---

## 5. 実機との関係

### 5.1 コアは共有されている（コピーではない）
`firmware/core` と `firmware/hal` は**両方のビルドが同じファイルを直接コンパイル**します。コピーは作りません。

- シミュレーター: `simulator/build.bat` が `firmware/core/*.cpp` をコンパイル対象に列挙
- 実機: `firmware/esp32/platformio.ini` の `build_src_filter = +<../../core/*.cpp>`

**`firmware/core` にファイルを足したら、build.bat にも追記が必要です**（PlatformIO 側はワイルドカードなので自動で拾われます。片側だけに入って気づかれない、という事故が過去に起きています）。

`IHal` の実装は2つあります。シミュレーターが `simulator/win32/main_win32.cpp` の `Win32Hal`、実機が `firmware/esp32/src/main.cpp` の `Esp32Hal` です。

### 5.2 プロトコルも揃えてある
`wrapper.py` は実機（`firmware/esp32/src/NetLink.h` の `KATANORI_WS_PATH`）と同じ **PCMバイナリモード**で接続します。

```
wss://katanori-backend.tobira-sys.workers.dev/?voice=Achird&pcm=16000
```

- **バイナリフレーム = 生の16bit PCM**、**テキストフレーム = 制御JSON**、という取り決め。
  PCMの先頭バイトがたまたま `{` になることがあるため、中身を見て振り分ける方式は成立しません。
- 上り（マイク→DO）は生PCMをそのまま送ります。base64もJSONも組み立てません。
- 下り（DO→クライアント）は DO 側で 24kHz→16kHz のリサンプルと4KB分割まで済ませて届きます。
- つなぎ言葉は `{"_filler": "えーっと"}` が先に来て、直後に音源がバイナリで届きます。

DO は `?pcm=` を付けない**素通しモード**（Gemini の生JSON + base64）も受け付けますが、それだと実機が通る経路を一切踏まないため使いません。**変えないこと。**

### 5.3 シミュレーターが実機に追随していない点
意図的に追随させていません（1章の「確かめられないもの」を参照）。シミュレーター側の会話開始は `1` キーですが、実機は Usr ボタン（GPIO3）で開始/終了します。VAD・再生中のミュート・エコーガードの実装も両者で別物です。