/*
 * ============================================================================
 *  TTSで音声を作るための共通処理。
 *
 *  つなぎ言葉(gen-fillers.mjs / サーバー側)と、起動アナウンス
 *  (gen-voice-clips.mjs / ファーム側)の両方から使う。
 *
 *  声名をここに1つだけ置くのが主目的。以前、生成側とクライアント側で別々に
 *  声名を持っていたために「つなぎ言葉だけ別人が喋る」状態になった。
 * ============================================================================
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

/*
 * 実機が要求している声。
 *
 * 出所はDOの既定値ではなくクライアント側。変えるならこの2か所と揃えること:
 *   firmware/esp32/src/NetLink.h  KATANORI_WS_PATH  (?voice=...)
 *   simulator/wrapper.py          WS_URL
 */
export const VOICE = "Achird";

/** TTSの出力は常に 24kHz 16bit モノラル PCM。 */
export const TTS_RATE = 24000;

export const MODEL = "models/gemini-3.1-flash-tts-preview";

/** .dev.vars から APIキーを読む（gitignore済み）。 */
export function apiKey() {
  const text = readFileSync(join(ROOT, ".dev.vars"), "utf8");
  const m = /GEMINI_API_KEY\s*=\s*"?([^"\s]+)"?/.exec(text);
  if (!m) {
    throw new Error(".dev.vars に GEMINI_API_KEY が見つかりません");
  }
  return m[1];
}

/** 1文を合成して生のPCM(24kHz)を返す。 */
export async function synth(key, text, { voice = VOICE, style = "" } = {}) {
  const url = `https://generativelanguage.googleapis.com/v1beta/${MODEL}:generateContent?key=${key}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contents: [{ parts: [{ text: style + text }] }],
      generationConfig: {
        responseModalities: ["AUDIO"],
        speechConfig: {
          voiceConfig: { prebuiltVoiceConfig: { voiceName: voice } },
        },
      },
    }),
  });

  if (!res.ok) {
    throw new Error(`TTS failed (${res.status}): ${(await res.text()).slice(0, 300)}`);
  }

  const json = await res.json();
  const inline = json?.candidates?.[0]?.content?.parts?.[0]?.inlineData;
  if (!inline?.data) {
    throw new Error(`音声が返りませんでした: ${JSON.stringify(json).slice(0, 300)}`);
  }
  return Buffer.from(inline.data, "base64");
}

/**
 * 前後の無音を落とす。
 *
 * TTS は語の前後に数百msの余白を付けてくる。放っておくと、鳴らしたい音の前に
 * 無言の間が入る。
 */
export function trimSilence(buf, thresholdAbs = 350, padMs = 30) {
  const pcm = new Int16Array(buf.buffer, buf.byteOffset, buf.byteLength >> 1);
  let start = 0;
  let end = pcm.length - 1;
  while (start < pcm.length && Math.abs(pcm[start]) < thresholdAbs) start++;
  while (end > start && Math.abs(pcm[end]) < thresholdAbs) end--;
  if (start >= end) {
    return buf; // 全部無音なら諦めてそのまま返す（異常時に気づけるように）
  }
  const pad = Math.floor((TTS_RATE * padMs) / 1000);
  start = Math.max(0, start - pad);
  end = Math.min(pcm.length - 1, end + pad);
  const out = pcm.slice(start, end + 1);
  return Buffer.from(out.buffer, out.byteOffset, out.byteLength);
}

/**
 * 語の途中に空いた長い無音を詰める。
 *
 * TTS は「えーっと」を「えー」…320ms無音…「っと」のように返してくることが
 * ある。trimSilence は端しか削らないので、放っておくと音の真ん中に無音が残る。
 * 区間ごとに切り出すと語が半分になるため、無音そのものを短くして両方の音節を残す。
 */
export function collapseGaps(buf, thresholdAbs = 350, maxGapMs = 120) {
  const pcm = new Int16Array(buf.buffer, buf.byteOffset, buf.byteLength >> 1);
  const maxGap = Math.floor((TTS_RATE * maxGapMs) / 1000);
  const out = [];
  let run = 0; // 直近の連続した無音サンプル数

  for (let i = 0; i < pcm.length; i++) {
    if (Math.abs(pcm[i]) < thresholdAbs) {
      run++;
      // 上限までは残す。無音を完全に削ると音節が繋がって別の語に聞こえる。
      if (run <= maxGap) {
        out.push(pcm[i]);
      }
    } else {
      run = 0;
      out.push(pcm[i]);
    }
  }

  const arr = Int16Array.from(out);
  return Buffer.from(arr.buffer, arr.byteOffset, arr.byteLength);
}

/**
 * 話速を factor 倍にする（サンプルを間引く線形補間）。
 * レートは変わらないので、そのぶん音程も上がる。x1.6で7半音上がり別人になる。
 */
export function speedUp(buf, factor) {
  const src = new Int16Array(buf.buffer, buf.byteOffset, buf.byteLength >> 1);
  const outLen = Math.floor(src.length / factor);
  const out = new Int16Array(outLen);
  for (let i = 0; i < outLen; i++) {
    const pos = i * factor;
    const i0 = Math.floor(pos);
    const i1 = Math.min(i0 + 1, src.length - 1);
    const t = pos - i0;
    out[i] = Math.round(src[i0] * (1 - t) + src[i1] * t);
  }
  return Buffer.from(out.buffer, out.byteOffset, out.byteLength);
}

/** 末尾をぶつ切りにするとプツッと鳴るのでフェードアウトさせる。 */
export function truncate(buf, maxSamples, fadeMs = 40) {
  const pcm = new Int16Array(buf.buffer, buf.byteOffset, buf.byteLength >> 1);
  const out = pcm.slice(0, maxSamples);
  const fade = Math.min(Math.floor((TTS_RATE * fadeMs) / 1000), out.length);
  for (let i = 0; i < fade; i++) {
    const idx = out.length - fade + i;
    out[idx] = Math.round(out[idx] * (1 - i / fade));
  }
  return Buffer.from(out.buffer, out.byteOffset, out.byteLength);
}

export const msOf = (buf, rate = TTS_RATE) =>
  Math.round((buf.byteLength / 2 / rate) * 1000);

/**
 * 24kHz から実機のI2S(16kHz)へ落とす。
 *
 * 単純な間引きでは 8kHz を超える成分が折り返して金属的なノイズになる。
 * src/resample.ts (DO側) と同じ考えで、ハミング窓付き sinc の低域通過FIRを
 * 通してから線形補間する。こちらはオフライン処理なので、チャンク跨ぎの
 * 状態保持は不要でタップ数も多く取れる。
 */
export function downsample(buf, fromRate = TTS_RATE, toRate = 16000) {
  const src = new Int16Array(buf.buffer, buf.byteOffset, buf.byteLength >> 1);
  if (fromRate === toRate) {
    return buf;
  }

  // 出力側のナイキストより少し下で切る
  const cutoff = 0.45 * toRate;
  const taps = 63;
  const half = (taps - 1) / 2;
  const fir = new Float64Array(taps);
  let sum = 0;
  for (let i = 0; i < taps; i++) {
    const n = i - half;
    const x = (2 * Math.PI * cutoff * n) / fromRate;
    const sinc = n === 0 ? 1 : Math.sin(x) / x;
    const window = 0.54 - 0.46 * Math.cos((2 * Math.PI * i) / (taps - 1));
    fir[i] = sinc * window;
    sum += fir[i];
  }
  for (let i = 0; i < taps; i++) {
    fir[i] /= sum; // 直流利得を1に正規化（音量が変わらないように）
  }

  // 低域通過
  const lp = new Float64Array(src.length);
  for (let i = 0; i < src.length; i++) {
    let acc = 0;
    for (let k = 0; k < taps; k++) {
      const j = i + k - half;
      if (j >= 0 && j < src.length) {
        acc += src[j] * fir[k];
      }
    }
    lp[i] = acc;
  }

  // 線形補間で間引く
  const step = fromRate / toRate;
  const outLen = Math.floor(src.length / step);
  const out = new Int16Array(outLen);
  for (let i = 0; i < outLen; i++) {
    const pos = i * step;
    const i0 = Math.floor(pos);
    const i1 = Math.min(i0 + 1, src.length - 1);
    const t = pos - i0;
    const v = Math.round(lp[i0] * (1 - t) + lp[i1] * t);
    out[i] = v > 32767 ? 32767 : v < -32768 ? -32768 : v;
  }
  return Buffer.from(out.buffer, out.byteOffset, out.byteLength);
}
