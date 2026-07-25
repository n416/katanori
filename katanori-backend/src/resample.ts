/**
 * PCM のダウンサンプラ。
 *
 * Gemini Live API の応答は 24kHz、ReSpeaker Lite の I2S は 16kHz。
 * この変換を ESP32 側でやると音声バッファと CPU を圧迫するため、サーバで行う。
 *
 * 単純に間引くとナイキスト周波数(出力16kHzなら8kHz)を超える成分が折り返して
 * 金属的なノイズになるため、低域通過フィルタを通してから補間する。
 * フィルタの遅延線と読み出し位相はチャンクを跨いで保持する（リセットすると
 * チャンク境界でプチプチとしたクリックノイズが乗る）。
 */

/** 窓関数(ハミング)付き sinc による低域通過FIRの係数を作る。 */
function makeLowPassTaps(numTaps: number, cutoffNormalized: number): Float32Array {
  const taps = new Float32Array(numTaps);
  const mid = (numTaps - 1) / 2;
  let sum = 0;

  for (let i = 0; i < numTaps; i++) {
    const n = i - mid;
    // sinc
    const sinc = n === 0
      ? 2 * cutoffNormalized
      : Math.sin(2 * Math.PI * cutoffNormalized * n) / (Math.PI * n);
    // ハミング窓
    const window = 0.54 - 0.46 * Math.cos((2 * Math.PI * i) / (numTaps - 1));
    taps[i] = sinc * window;
    sum += taps[i];
  }

  // DCゲインを1に正規化
  for (let i = 0; i < numTaps; i++) {
    taps[i] /= sum;
  }
  return taps;
}

export class Downsampler {
  private readonly taps: Float32Array;
  private readonly delay: Float32Array;
  private delayPos = 0;

  /** 未消費のフィルタ済みサンプル。チャンク境界を跨いで補間するために保持する。 */
  private pending: number[] = [];
  /** pending 内の読み出し位置（小数）。 */
  private phase = 0;
  /** 入力1サンプルあたりの進み幅 = inRate / outRate。 */
  private readonly step: number;

  readonly inRate: number;
  readonly outRate: number;

  constructor(inRate: number, outRate: number, numTaps = 31) {
    this.inRate = inRate;
    this.outRate = outRate;
    this.step = inRate / outRate;

    // 出力のナイキスト周波数より少し下に遮断周波数を置く（余裕を持たせて 0.9 倍）
    const cutoffHz = Math.min(inRate, outRate) / 2 * 0.9;
    this.taps = makeLowPassTaps(numTaps, cutoffHz / inRate);
    this.delay = new Float32Array(numTaps);
  }

  /** FIR を1サンプル通す。 */
  private filterOne(x: number): number {
    const n = this.taps.length;
    this.delay[this.delayPos] = x;

    let acc = 0;
    let idx = this.delayPos;
    for (let k = 0; k < n; k++) {
      acc += this.taps[k] * this.delay[idx];
      idx = idx === 0 ? n - 1 : idx - 1;
    }

    this.delayPos = this.delayPos === n - 1 ? 0 : this.delayPos + 1;
    return acc;
  }

  /**
   * 16bit PCM を変換する。入出力ともリトルエンディアン。
   * 呼び出し間で状態を保持するので、同じストリームには同じインスタンスを使うこと。
   */
  process(input: Int16Array): Int16Array {
    for (let i = 0; i < input.length; i++) {
      this.pending.push(this.filterOne(input[i]));
    }

    const out: number[] = [];
    while (Math.floor(this.phase) + 1 < this.pending.length) {
      const i = Math.floor(this.phase);
      const frac = this.phase - i;
      const v = this.pending[i] + frac * (this.pending[i + 1] - this.pending[i]);

      // クリッピングガード
      out.push(v > 32767 ? 32767 : v < -32768 ? -32768 : v);
      this.phase += this.step;
    }

    // 消費済みのサンプルを捨てる
    const consumed = Math.floor(this.phase);
    if (consumed > 0) {
      this.pending.splice(0, consumed);
      this.phase -= consumed;
    }

    const result = new Int16Array(out.length);
    for (let i = 0; i < out.length; i++) {
      result[i] = out[i];
    }
    return result;
  }
}

/** Base64 -> Int16Array (リトルエンディアン)。 */
export function base64ToInt16(b64: string): Int16Array {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) {
    bytes[i] = bin.charCodeAt(i);
  }
  // 奇数バイトで終わっていたら末尾を落とす
  return new Int16Array(bytes.buffer, 0, bytes.length >> 1);
}

/** ArrayBuffer -> Base64。大きなバッファでスタックを溢れさせないよう分割する。 */
export function arrayBufferToBase64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  const CHUNK = 0x8000;
  let bin = "";
  for (let i = 0; i < bytes.length; i += CHUNK) {
    bin += String.fromCharCode(...bytes.subarray(i, i + CHUNK));
  }
  return btoa(bin);
}
