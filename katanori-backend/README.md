# katanori-backend

カタノリロボと Gemini Live API を中継する Cloudflare Worker + Durable Object。

エンドポイント: `wss://katanori-backend.tobira-sys.workers.dev/`

## クエリパラメータ

| 名前 | 既定 | 内容 |
|---|---|---|
| `voice` | `Aoede` | Gemini の音声名 |
| `pcm` | （なし） | **PCMモード**を有効にし、クライアントへ返す音声のサンプルレートを指定する |

## 2つのモード

`pcm` を付けるかどうかで、クライアントとの間のプロトコルが変わります。
Gemini との間のやり取りは両モードで同じです。

### 素通しモード（`pcm` なし）

Gemini のメッセージをそのまま流します。クライアントが base64 と JSON を自前で扱います。
**`simulator/wrapper.py` がこのモードを使います。** 従来の挙動から一切変わりません。

### PCMモード（`pcm=16000` など）

マイコン向けのモードです。ESP32 が base64 も JSON の組み立ても行わずに済むよう、
**音声をバイナリフレーム、制御をテキストフレーム**に分離します。

```
ESP32 --[バイナリ: 生PCM 16kHz]--> DO --[base64+JSON]--> Gemini
ESP32 <-[バイナリ: 生PCM 指定kHz]- DO <-[base64+JSON]-- Gemini
ESP32 <--[テキスト: 制御JSON]----- DO
```

| 方向 | フレーム種別 | 中身 |
|---|---|---|
| クライアント → DO | バイナリ | 生の 16bit PCM・16kHz・リトルエンディアン。DOが `realtimeInput.audio` に包み直す |
| クライアント → DO | テキスト | 制御JSON（`audioStreamEnd` など）。Geminiへ素通し |
| DO → クライアント | バイナリ | 生の 16bit PCM。`pcm` で指定したレートへ変換済み |
| DO → クライアント | テキスト | `setupComplete` / `turnComplete` / `interrupted` / 文字起こし など。**音声は除去済み** |

音声を抜いた結果が空になったメッセージは送りません（帯域とマイコンのパース負荷の節約）。

### 実装上の要点

- **Gemini はバイナリフレームでも返してくる**（中身はJSONテキスト）。両方を同じように
  パースする必要がある。実機で確認済み。
- Gemini の出力レートは `mimeType` の `rate=` から読む（24000決め打ちにしない）。
  指定レートと一致すれば変換をスキップする。
- Gemini の入力は **16kHz 固定**。ReSpeaker Lite のマイクも 16kHz なので入力方向の変換は不要。

## リサンプラ

`src/resample.ts`。Gemini の応答(24kHz)を ReSpeaker Lite の I2S(16kHz)へ落とす。
単純な間引きでは 8kHz を超える成分が折り返して金属的なノイズになるため、
ハミング窓付き sinc の低域通過FIR(31タップ)を通してから線形補間する。

FIRの遅延線と読み出し位相はチャンクを跨いで保持する。リセットするとチャンク境界に
クリックノイズが乗るため。

検証済みの実測値（24000→16000）:

| 項目 | 結果 |
|---|---|
| 出力サンプル数 | 期待値と誤差0 |
| 440Hz の振幅保持（通過帯域） | 比 0.998 |
| 10kHz の減衰（阻止帯域） | -83dB |
| 331サンプル刻みと一括処理の差 | 0 |

## 開発

```bash
npm install
npm run dev      # wrangler dev
npm run deploy   # wrangler deploy
```

`GEMINI_API_KEY` はシークレットとして設定すること。

```bash
npx wrangler secret put GEMINI_API_KEY
```
