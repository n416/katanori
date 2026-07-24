# カタノリロボ シミュレーター 仕様

実機ハードウェアの動作をブラウザ上で模擬するReactシミュレーター。

## 実機構成（模擬対象）
- メインMCU: XIAO ESP32S3
- 音声DSP: ReSpeaker Lite (XMOS, AEC対応)
- ディスプレイ: 0.96" SSD1306 OLED (I2C, 128x64, addr 0x3C)
- スピーカー: 8Ω 2W パッシブ (ReSpeaker LiteのJST端子)
- 電源: ReSpeaker LiteのUSB-C 5V → ヘッダ経由でXIAO/OLED給電

## 成果物
`simulator.html` 1ファイルのみ。React 18 UMD + Babel Standalone をCDN (unpkg) から読み込む。ビルド不要でブラウザで直接開けること。

## 機能要件

### 1. OLED表示シミュレーション (最重要)
- 128x64のモノクロピクセルバッファを canvas に4倍スケールで描画（ピクセル感を出す。SSD1306風に黒背景+水色ピクセル）
- 5x7ドットフォント風でテキスト描画（英数カナは難しければ英数のみでOK、日本語はUI側の吹き出しで補完表示）
- 状態ごとの画面:
  - idle: 目（2つの丸/四角）がランダム間隔でまばたきするアニメーション
  - listening: マイクアイコン+波形アニメーション
  - thinking: "..." ドットアニメーション
  - speaking: 口パクアニメーション+応答テキストの横スクロール表示

### 2. 音声対話の状態機械
idle → (ウェイクワード) → listening → (発話入力) → thinking(1-2秒) → speaking → idle
- 「ウェイクワード」ボタンで listening へ
- テキスト入力欄でユーザー発話を模擬（Enterで送信）
- 応答は簡単なルールベース（挨拶、時刻、天気などの定型数パターン + それ以外はオウム返し風）
- speaking中は Web Speech API (speechSynthesis, ja-JP) で実際に読み上げ（ON/OFFトグル付き、使えない環境では無視）

### 3. ハードウェアパネル
- 各コンポーネント（XIAO ESP32S3 / ReSpeaker Lite / OLED / スピーカー / 5V電源）の状態インジケーター（電源LED、I2C接続、AEC有効など）
- 電源ON/OFFスイッチ（OFFでOLED消灯・操作不能）
- 音量スライダー

### 4. シリアルモニタ
- 画面下部にログ表示（タイムスタンプ付き、[BOOT] [I2C] [DSP] [STATE] [TTS] などのタグ、自動スクロール、最大200行）
- 電源ON時に実機風のブートログ（I2Cスキャンで0x3C検出、ReSpeaker init、AEC enabled等）

## UI/デザイン
- ダーク基調。左にロボット正面ビュー（OLED+スピーカーグリルを配したロボの顔っぽい筐体）、右にコントロール+ハードウェアパネル、下部にシリアルモニタ
- 日本語UI
