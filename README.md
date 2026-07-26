# katanori（カタノリロボ）

Gemini Live API と音声で対話する小型ロボット。**実機で会話が成立する状態まで到達済み**（2026-07-26）。

```
[ユーザーの声]
   ↓ マイク
ReSpeaker Lite (XMOS XU316, ハードウェアAEC)
   ↓ I2S
XIAO ESP32S3 ── OLED 128x64（顔の表示）
   ↓ WebSocket over TLS
Cloudflare Durable Object（中継・音声変換）
   ↓
Gemini Live API（音声in / 音声out）
```

## 現在の状態

| 段階 | 内容 | 状態 |
|---|---|---|
| 1 | OLEDに顔を表示 | ✅ 実機確認済み |
| 2 | Wi-Fi + WSS で Durable Object へ接続 | ✅ 実機確認済み |
| 2.5 | DOのPCMモード・サーバ側リサンプル | ✅ デプロイ済み |
| 3 | I2S音声の送受信 | ✅ **実機で会話成立** |
| 4 | TLS証明書の検証 | ✅ 実機確認済み |
| 4 | Wi-Fiプロビジョニング（キャプティブポータル） | ✅ 実機確認済み |
| 4 | 起動時ノイズ対策 | ✅ 実機確認済み |
| 4 | 現在時刻の注入 | ✅ デプロイ済み |
| 4 | つなぎ言葉（応答待ちの間を埋める） | ✅ デプロイ済み |
| 4 | 起動後のWi-Fi自動接続 | ⏳ ビルド済み・実機未確認 |
| 4 | 起動アナウンス（焼き込み音声） | ⏳ ビルド済み・実機未確認 |
| 4 | ウェイクワード / QRペアリング | 未着手 |

Wi-Fi未設定の機体を渡せば、スマホでQRを読む → 設定画面が自動で開く → 設定 → 会話、
という流れが通ります。設定済みの機体は、電源を入れるだけで自動でWi-Fiへ繋ぎ、
ボタンを押した時点でサーバーへ接続します（シリアルコンソールは不要）。

## リポジトリ構成

```
firmware/
├── core/          純C++14のコアロジック。Arduino依存禁止。実機とシミュレーターで共有
│                  DisplayBuffer / StateMachine / Face / RobotCore / RobotDsp
├── hal/           IHal.h（プラットフォーム抽象）
└── esp32/         実機ファームウェア（PlatformIO）   ★詳細は firmware/esp32/README.md
    └── src/       main.cpp / NetLink / AudioIo / Provisioning / RootCa.h

katanori-backend/  Cloudflare Worker + Durable Object  ★詳細は katanori-backend/README.md
└── src/           index.ts（中継とプロトコル）/ resample.ts（24k→16k）

simulator/         Windows用シミュレーター（Win32 GDI、外部lib不要）
├── win32/         main_win32.cpp
├── wrapper.py     PC上でマイク・スピーカー・DO接続を担うPythonラッパー
└── tuner.html     ロボットボイスの調整UI

docs/SIMULATOR.md  シミュレーターのビルドと使い方
SPEC.md            シミュレーターの仕様
SPEC_SIM.md        同上（詳細）
仕様書.md           yorisoi-care-app との統合仕様（全体構想）
```

## 動かし方

### 実機

```bash
cd firmware/esp32
pio run -e xiao_esp32s3 -t upload
pio device monitor -e xiao_esp32s3 --port COM4
```

シリアルで `?` を打つとコマンド一覧が出ます。会話は `wifi` → `c` → `1`（喋る）。
**詳細・配線・トラブルシューティングは [firmware/esp32/README.md](firmware/esp32/README.md)。**

### バックエンド

```bash
cd katanori-backend
npm install
npm run deploy
```

**プロトコルの詳細は [katanori-backend/README.md](katanori-backend/README.md)。**

### シミュレーター（PC単体で顔と会話を試す）

```bash
# w64devkit を PATH に前置してから
simulator\build.bat
python simulator\wrapper.py
```

## 実機で判明した重要な事実

公式ドキュメントに書かれておらず、実機で踏んで初めて分かったものです。
**同じ罠を二度踏まないよう、詳細は各READMEに記録してあります。**

| 事実 | 詳細 |
|---|---|
| I2Sは **ESP32がスレーブ・32bitスロット**（公式サンプルはマスタ・16bit） | firmware/esp32/README.md |
| XIAO ESP32S3 は**外付けアンテナ必須**（未接続でRSSIが40dB悪化） | 同上 |
| **GPIO43 = UART0 TX = I2S DOUT**。リセット時のブートログが轟音になる | 同上 |
| WebSocketライブラリは **15KB超のフレームで無言切断**（DO側で4KBに刻む） | katanori-backend/README.md |
| Geminiの応答は**バイナリフレーム**で届く（中身はJSON） | 同上 |
| プロビジョニングは **STA停止→スキャン→AP起動** の順でないとAPが電波に出ない | firmware/esp32/README.md |

## 次にやること（優先度順）

1. **ウェイクワード** — 今はボタン起動。**判定はESP32側で自前に実装するしかない**
   （2026-07-26に確認。ReSpeaker の `ch0-asr/ch1-mww` ファームはウェイクワードを
   検出せず、外部エンジン向けの音声を出すだけ。しかもDFU版は48kHzで現構成と合わない）。
   実機ファームの書き換えは不要で、既存の16kHz ch0 の音声で作れる。
   詳細は firmware/esp32/README.md の訂正を参照。
2. **証明書の有効期限検証** — `CONFIG_MBEDTLS_HAVE_TIME_DATE` が無効のため未検証。
   有効にするにはフレームワークの再ビルドが必要。ピン留め済みなので実害は薄い。
3. **QRコードでのペアリング** — 仕様書3章。DO側にアカウントと個体番号の管理が必要で、
   現状の DO は `robot-1` 固定。ここだけ規模が大きく、コードより先に仕様を決める作業。

### 済んだもの

- **時刻の注入**（2026-07-26）— LLMは時計を持たず、聞かれると嘘の日時を答えていた。
  DO側で接続時に日本時間を systemInstruction へ埋める（`buildSystemInstruction()`）。
  Workers の `Date` は常にUTCなので `timeZone: "Asia/Tokyo"` の明示が必須。
- **つなぎ言葉**（2026-07-26）— 応答までの1.3秒の沈黙を埋める。DO側で完結し、
  ファームの変更は不要（`audioStreamEnd` を受けた時点で音声を先に返す）。
  音源は `katanori-backend/tools/gen-fillers.mjs` でTTS生成し `src/fillers.ts` に格納。
  **声名は実機が要求している `Achird` に合わせること**（DO既定値の `Aoede` で焼いて
  別人になった経緯あり）。詳細は katanori-backend/README.md。

## 既知の弱点

- **設定用APは開放（暗号化なし）でページもHTTP。** 入力されたWi-Fiパスワードは
  設定中の数分間、近くの第三者から傍受されうる。市販IoT機器でも一般的な方式だが弱点。
- **ルートCAをピン留めしている。** 接続先が発行元CAを変更すると繋がらなくなる。
  更新手順は `firmware/esp32/src/RootCa.h` のコメント参照。
- **再生中にクラッシュするとリセット時に轟音が出る。** 完全に潰すならスピーカー線に
  物理スイッチ。
