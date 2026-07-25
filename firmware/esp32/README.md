# カタノリロボ 実機ファームウェア (XIAO ESP32S3)

`firmware/core` / `firmware/hal` のコアロジックを実機で動かすための PlatformIO プロジェクトです。
コアはシミュレーターと**同一のソースを共有**しています（コピーを作らないこと）。

## 段階

| Stage | 内容 | 状態 |
|---|---|---|
| 1 | OLEDに顔を表示（I2Cスキャン・状態遷移の目視確認） | ✅ 実機で表示確認済み (2026-07-26) |
| 2 | Wi-Fi + WSS で Durable Object へ接続 | 未着手 |
| 3 | I2S 音声の送受信（ReSpeaker Lite 経由） | 未着手 |
| 4 | ウェイクワード / つなぎ言葉 / Wi-Fiプロビジョニング | 未着手 |

## 構成

```
firmware/
├── core/          ← シミュレーターと共有（Arduino依存禁止・純C++14）
├── hal/           ← IHal インターフェース
└── esp32/         ← このPlatformIOプロジェクト
    ├── platformio.ini
    └── src/main.cpp   ← 唯一の実機依存コード（Esp32Hal + setup/loop）
```

`platformio.ini` の `build_src_filter` で `../../core/*.cpp` をビルド対象に加えているため、
コア側を修正すると実機ビルドにもそのまま反映されます。

## 配線（実機で確認済み）

XIAO ESP32S3 を ReSpeaker Lite に直挿しした構成。OLED は ReSpeaker Lite が使っている
I2Cバス（D4/D5）に相乗りさせる。**このバスにはプルアップが既に載っている**ため追加不要。

| OLEDのピン | XIAO | GPIO |
|---|---|---|
| `VCC` | 3V3（右側ヘッダ上から3本目） | — |
| `GND` | GND（右側ヘッダ上から2本目） | — |
| `SCL` | D5（左側ヘッダ上から6本目） | 6 |
| `SDA` | D4（左側ヘッダ上から5本目） | 5 |

```
          ┌──[USB-C]──┐
   D0 ────┤           ├──── 5V
   D1 ────┤           ├──── GND
   D2 ────┤           ├──── 3V3
   D3 ────┤           ├──── D10
   D4 ────┤           ├──── D9      D4 = SDA (GPIO5)
   D5 ────┤           ├──── D8      D5 = SCL (GPIO6)
   D6 ────┤           ├──── D7
          └───────────┘
```

注意点:

- **VCC は 5V ではなく 3V3 に繋ぐこと。** 5Vを与えるとモジュール側のプルアップが
  I2Cラインを5Vへ引き上げ、ESP32の入力定格を超える。
- 使用しているOLEDモジュールのシルクは **`VCC GND SCL SDA`** の順で、一般的な
  `VCC GND SDA SCL` とは SCL/SDA が逆。並び順の記憶で挿すと入れ替わる。
- 起動時にOLEDが繋がっていないと初期化コマンド列がパネルに届かない。配線を直した後は
  リセットするか、シリアルで `r` を打って再初期化すること。

I2Cスキャンでは ReSpeaker Lite 側のデバイスが `0x18` に、OLEDが `0x3C` に見える。
両方出れば配線は正常。

## セットアップ

PlatformIO Core をインストールします（VS Code拡張版でも可）。

```bash
pip install -U platformio
```

## ビルドと書き込み

XIAO ESP32S3 を USB-C で PC に接続してから、このディレクトリで実行します。

```bash
pio run -e xiao_esp32s3 -t upload
```

書き込み後、シリアルモニタを開きます。

```bash
pio device monitor -e xiao_esp32s3
```

### 書き込みできない場合（ブートローダーモード）

XIAO ESP32S3 の **BOOT ボタンを押しながら RESET**（または BOOT を押しながらUSB接続）すると
ダウンロードモードに入ります。COMポートが見えない場合はこれを試してください。

## 動作確認（Stage 1 の完了条件）

1. シリアルに `[I2C] device found at 0x3C` が出る → **配線OK**
2. OLED に目が表示され、数秒おきにまばたきする → **描画OK**
3. シリアルモニタから `1` `2` `3` `4` を送ると顔が変化する → **状態機械OK**

| 入力 | イベント | 遷移 |
|---|---|---|
| `1` / BOOTボタン | `WAKE_WORD` | IDLE → LISTEN |
| `2` | `SPEECH_END` | LISTEN → THINK |
| `3` | `RESPONSE_READY` | THINK → SPEAK |
| `4` | `SPEECH_DONE` | SPEAK → IDLE |

シミュレーターのキー操作と同じ割り当てです。
`wrapper.py` が送る `CMD:SPEAK_START` / `CMD:SPEAK_END` も受理します。

### 診断コマンド

ネイティブUSB CDC のため、`upload` 直後のブートログはモニタを開く前に流れてしまいます。
以下のコマンドで後からいつでも同じ情報を取れます。

| 入力 | 内容 |
|---|---|
| `s` | I2Cバスを再スキャン（配線確認） |
| `a` | D0〜D10 の全ピン組み合わせを I2C として叩き、OLED(0x3C/0x3D)がどのピンに繋がっているかを探索 |
| `vN` | D`N` ピンの電圧を測る（簡易電圧計）。例 `v0` |
| `gN` | D`N` ピンが GND に導通しているか見る（簡易導通チェッカー）。例 `g1` |
| `t` | OLED自己診断パターンを5秒表示（`DisplayBuffer` を通さず U8g2 直描画） |
| `i` | チップ・メモリ・I2Cピン設定を再表示 |
| `?` | ヘルプ |

`t` は**画面が出ない原因を二分する**ためのものです。

- `t` で枠と `KATANORI SELFTEST` が見える → 配線とOLED初期化はOK。原因は `DisplayBuffer` → U8g2 の転送側
- `t` でも真っ暗 → 配線・I2Cアドレス・給電のいずれかの問題

同じ理由で、起動直後にも自動でこのパターンを5秒表示します。

### テスター代わりの使い方

`vN` / `gN` はテスターが手元にないときに ESP32 自身を簡易計測器として使うためのものです。
調べたい点から D`N` ピンへジャンパーを1本渡して実行します。

- `v` は ADC で電圧を読みます。**入力は 3.3V まで。5V の点に繋ぐとピンが壊れます**
- `g` は内部プルアップを有効にして読むだけ。LOW なら GND に導通しています
- ADC非対応のため `v` は D6 / D7 では使えません（D0〜D5、D8〜D10 を使うこと）

## トラブルシューティング

| 症状 | 対処 |
|---|---|
| 画面が真っ暗 | まず `t` で自己診断。それも真っ暗なら配線側、パターンが出るなら転送側の問題 |
| `[I2C] no devices found` | SDA/SCL/VCC/GND の配線と OLED への給電を確認。ソフトの問題ではありません |
| 画像が横に2ピクセルずれる / 端が回り込む | コントローラが SSD1306 ではなく **SH1106** の可能性。`U8G2_SH1106_128X64_NONAME_F_HW_I2C` に差し替える |
| `0x3C` ではなく `0x3D` が見つかる | `platformio.ini` の `build_flags` に `-DKATANORI_OLED_ADDR=0x3D` を追加 |
| I2Cピンが違う | 同様に `-DKATANORI_I2C_SDA=<n> -DKATANORI_I2C_SCL=<n>` を追加 |
| 顔が8ピクセル単位で左右反転する | `-DKATANORI_DISPLAY_BIT_REVERSE=1` を追加（MSB/LSB順の差異を吸収） |
| `PSRAM が見えていません` | `board_build.arduino.memory_type = qio_opi` が効いているか確認。Stage 3 で必須 |
| シリアルに何も出ない | ネイティブUSBのため、モニタを開き直すか RESET を一度押す |

## Stage 3 に向けたメモ

- `Esp32Hal::getMicLevel()` は現在ダミーのLFO（`KATANORI_FAKE_MIC`）。I2S入力の実測ピークに差し替える。
- Gemini の応答は 24kHz、ReSpeaker Lite の I2S は 16kHz。**リサンプルは DO 側でやる**方が実機は楽。
- base64+JSON は ESP32 には重いため、DO にバイナリフレーム受け口を追加してから着手すること。
- スピーカー出力は ESP32 → I2S → ReSpeaker Lite の DAC 経由にする（AECを効かせるため）。

`main_esp32_skeleton.cpp` は移植前の参考コード（`#if 0`）で、`src/main.cpp` に置き換わっています。
