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
| 4 | 起動時ノイズ対策 | ⚠ ソフト側（コーデックのミュートゲート）は実機確認済み。ただし**製品として置くには不足** — 電池切れ・クラッシュで耳元に爆音が出る経路が残っており、対策はアナログ側の音圧上限（[firmware/esp32/README.md](firmware/esp32/README.md) の轟音の節） |
| 4 | 現在時刻の注入 | ✅ デプロイ済み |
| 4 | つなぎ言葉（応答待ちの間を埋める） | ✅ デプロイ済み |
| 4 | 起動後のWi-Fi自動接続 | ✅ 実機確認済み |
| 4 | 繋がらないことを画面と声で伝える | ✅ 実機確認済み |
| 4 | 起動アナウンス（焼き込み音声） | ✅ 実機確認済み（Wi-Fi接続の約1秒後に鳴る） |
| 4 | **音量つまみ（AS5600・非接触の絶対角度）** | ✅ **移行完了**（2026-08-02）。可変抵抗には戻さない。「回すとコーデックが死ぬ」は原因ごと部品が消えて解消（[docs/KNOB-ENCODER.md](docs/KNOB-ENCODER.md)） |
| 4 | OTA更新 | ✅ 実機確認済み（2026-08-03） |
| 4 | ミュートリレー（無通電で開） | ✅ 駆動8項目・接点 OL/0Ω 合格（2026-08-08）。⚠ **スピーカー線にはまだ入っていない**（[docs/POWER.md](docs/POWER.md) 3章） |
| 4 | ウェイクワード / QRペアリング | 未着手 |

### ハードウェア（いまここ）

🔒 **現フェーズは「最小単位で動かす」** — 1台が電源から会話・安全機構まで通ること。

| | 状態 |
|---|---|
| **ハブ基板** | ✅ **2026-08-18 実装完了**（図は赤0・黄0、全数テスターで導通確認）。⚠ **通電はまだ**（[docs/POWER.md](docs/POWER.md) 4章 ／ [hardware/parts/relay_board.html](hardware/parts/relay_board.html)） |
| **電池・電源** | 🔴 **いまの実機は電池で動いていない**（モバイルバッテリー給電）。PowerBoost とリポは未接続 |
| **リードスイッチ（電源断）** | 🔴 部品は手元。座は [hardware/frozen/v1-v4/knob_v5.scad](hardware/frozen/v1-v4/knob_v5.scad) に入っている（**未印刷**） |
| **つまみ** | ✅ v5 で設計完了（2026-08-19）。**未印刷**（v4 は実機で回らず捨てた） |
| **筐体** | 🔴 v2 を設計中。部品どうし・線ともに当たり 0（[docs/CASE-V2.md](docs/CASE-V2.md)） |

**残りの全量は [docs/TODO.md](docs/TODO.md) にフェーズ順で集約してある。**

Wi-Fi未設定の機体を渡せば、スマホでQRを読む → 設定画面が自動で開く → 設定 → 会話、
という流れが通ります。設定済みの機体は、電源を入れるだけで自動でWi-Fiへ繋ぎ、
ボタンを押した時点でサーバーへ接続します（シリアルコンソールは不要）。

## リポジトリ構成

```
firmware/
├── core/          純C++14のコアロジック。Arduino依存禁止。実機とシミュレーターで共有
│                  DisplayBuffer / StateMachine / Face / RobotCore
├── hal/           IHal.h（プラットフォーム抽象）
└── esp32/         実機ファームウェア（PlatformIO）   ★詳細は firmware/esp32/README.md
    └── src/       main.cpp / NetLink / AudioIo / Provisioning / RootCa.h

katanori-backend/  Cloudflare Worker + Durable Object  ★詳細は katanori-backend/README.md
└── src/           index.ts（中継とプロトコル）/ resample.ts（24k→16k）

simulator/         Windows用シミュレーター（Win32 GDI、外部lib不要）
├── win32/         main_win32.cpp
├── wrapper.py     PC上でマイク・スピーカー・DO接続を担うPythonラッパー
└── tuner.html     ロボットボイスの調整UI

hardware/          筐体・つまみ・基板モックの CAD（OpenSCAD）  ★直下は v5 の作業場
├── parts/         部品ライブラリ（parts.scad / respeaker_lite.scad / hub_board*.scad / relay_board.html）
├── icons/         刻印の元絵（SVG）と生成スクリプト
├── tools/         刷る前の検算（_stl_preflight.py / _stl_clean.py）
├── stl/           印刷した STL（刷るぞーが読む）／ print_log.jsonl 印刷の記録
├── ref/           実物の写真・ピン配置・データシート
├── sim/           MuJoCo の模型（m2_sorter/ ＝ M2 ねじ仕分けの機構、2026-09-07）
├── frozen/v1-v4/  🔒 凍結した v1〜v4 の .scad・検算・レンダー。読まない・触らない
└── frozen/v6/     v6（2026-09-12〜13・失敗）。歯車の機構と KiCad の板は次で使い回す。中身は frozen/v6/README.md

docs/manual/       組み立てマニュアル（assembly_v4.html と画像）
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
pio device monitor -e xiao_esp32s3 --port COM4   # ポートは pio device list で確認
```

ポート番号はPCごとに変わります（この機体は環境を移して COM4 → COM3 になりました）。
USBドライバは不要です（ネイティブUSBなので挿すだけで見えます）。

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

顔は実機と同じ `firmware/core` が描き、DOへの接続も実機と同じPCMバイナリモード
（`?voice=Achird&pcm=16000`）を使います。**バックエンドやプロンプトの変更は、
実機へ焼く前にここで確かめられます。** 一方 I2S・AEC・Wi-Fi は実機でしか出ません。
**詳細は [docs/SIMULATOR.md](docs/SIMULATOR.md)。**

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
| **スキャンでSSIDの有無は判定できない**（ステルスAPが1つでもあると「一覧に無い＝無い」が成立しない）。接続の切断理由コードを見るほうが速く確か | firmware/esp32/README.md |
| **I2Sへの直接書きは鳴らない**。再生タスクが無音を流し続ける方式のため、キュー経由以外はDMAの取り合いに負ける（beepがこれで壊れていた） | AudioIo.cpp の toneTest コメント |

## 未着手の一覧

会話は動くが、**自立ロボットとしての土台（電源・筐体・認証）がまだ空白**。
何が無いかは **[docs/TODO.md](docs/TODO.md)** に集約してある。
🔒 **A章＝現フェーズ（最小単位で動かす）／ B章＝人に渡す ／ C章＝フェーズ2（Stackchan）** の順で並ぶ。

## 次にやること

🔒 **いまはハードウェアの段である。ソフトの新機能は現フェーズに入っていない。**

1. **電池で動かす** — 現行機ではまだ一度もやっていない。稼働時間の実測はその後
2. **つまみ一式を `knob_v5.scad` で刷る** — ⚠ 先にリード用磁石の向きを確かめる（刷ってから間違いだと分かる形）
3. **筐体 v2 を出力できる形にする** — 蓋のツメの隙間と、会話ボタンの実測4つが未了

⚠ ハブ基板は 2026-08-18 に組み上がった。リードスイッチの距離は 2026-08-15 に測った（5mm）。

**その先（人に渡すため）**: 筐体 → 認証・費用の上限・QRペアリング → 実使用者テスト。
**フェーズ2**: 遠隔モジュール（Stackchan）を BLE で足す（[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)）。

⬜ **保留中**: 呼びかけ検知（ウェイクワード）は今もボタン起動＝レベル0のまま
（計画は [docs/WAKEUP.md](docs/WAKEUP.md)）。証明書の有効期限検証は
`CONFIG_MBEDTLS_HAVE_TIME_DATE` が無効で未検証だが、ピン留め済みなので実害は薄い。

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
- 🔴 **耳元の音圧に上限が無い。** 再生中にクラッシュ・電池切れ・ブラウンアウトが起きると、
  コーデックが解除のまま残り、次のリセットでROMブートログが耳道から数cmで増幅される
  （概算 105〜110dB SPL 台）。**「喋っている最中に電源を抜かない」は装着者に要求できない**
  ので、運用注意では塞げない。対策はソフトではなく**アナログ側の音圧上限**
  （[firmware/esp32/README.md](firmware/esp32/README.md) の「起動時の轟音とその対策」）。
