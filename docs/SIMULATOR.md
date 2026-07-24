# カタノリ ロボット顔 PCシミュレーター ガイド

## 1. 概要
実機（XIAO ESP32S3 + OLED 128x64 + ReSpeaker Lite）の到着前に、標準C++14で作成されたコアロジックを Windows PC上で開発・テストするための Win32 API / GDIベースの軽量シミュレーターです。

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

---

## 4. シミュレーターの実行と操作方法

`simulator\katanori_sim.exe` を実行すると 1024x512 のウィンドウが開きます。

### キー操作一覧
| キー | 動作 |
|---|---|
| `1` | イベント注入: `WAKE_WORD` (IDLE -> LISTEN) |
| `2` | イベント注入: `SPEECH_END` (LISTEN -> THINK) |
| `3` | イベント注入: `RESPONSE_READY` (THINK -> SPEAK) |
| `4` | イベント注入: `SPEECH_DONE` (SPEAK -> IDLE) |
| `Space` | 押下中、マイク入力レベル (0.2〜1.0) を擬似振動注入 |
| `ESC` | シミュレーター終了 |

---

## 5. 実機 (ESP32S3) への移植ガイド

`firmware/core` および `firmware/hal` ディレクトリ配下のコードはプラットフォーム独立（標準C++14のみ）のため、そのまま ESP32 プロジェクトにコピーして使用できます。

1. **`firmware/core/` および `firmware/hal/` をコピー**
   ESP32用プロジェクト（Arduino IDE / PlatformIO / ESP-IDF）にそのまま配置します。

2. **`IHal` の実機実装**
   `firmware/esp32/main_esp32_skeleton.cpp` を参考に、U8g2ライブラリおよび音声処理ライブラリを呼び出す `Esp32Hal` を実装します。
   - `millis()`: `::millis()` を返却
   - `getMicLevel()`: ReSpeaker Lite / ADC の信号レベル (0.0f〜1.0f) を返却
   - `flushDisplay()`: `DisplayBuffer::data()` (128x64 1bpp) を U8g2 バッファへ描画

3. **`RobotCore::tick()` の呼び出し**
   `setup()` で初期化し、`loop()` の周期処理内で `robotCore.tick()` を実行します。