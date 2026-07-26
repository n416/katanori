/*
 * ============================================================================
 *  firmware/esp32/src/VoiceClips.h に焼き込まれた音声を WAV に書き出して聴く。
 *
 *  TTSは呼ばない（ヘッダの中身そのもの）。実機に書き込むのは30秒かかるので、
 *  「思っていた音と違う」はここで気づきたい。
 *
 *  使い方:
 *    cd katanori-backend
 *    node tools/preview-clips.mjs [出力先ディレクトリ]
 * ============================================================================
 */

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const HEADER = join(ROOT, "..", "firmware", "esp32", "src", "VoiceClips.h");
const OUT_DIR = process.argv[2] ?? join(ROOT, "clips-preview");

const src = readFileSync(HEADER, "utf8");

const rate = Number(/constexpr uint32_t RATE = (\d+);/.exec(src)?.[1]);
if (!rate) {
  throw new Error("RATE を読めません");
}

/*
 * 各クリップは
 *   /** 「文言」 1705ms — 説明 *\/
 *   static const int16_t NAME[] = { ... };
 * の形で並んでいる。`static const int16_t` まで込みで当てること
 * （名前だけを頼りにすると、直後の _SAMPLES の行にも当たる）。
 */
const re = /\/\*\* 「(.*?)」 (\d+)ms[^\n]*\n\s*static const int16_t (\w+)\[\] = \{([\s\S]*?)\n\};/g;

/** 16bitモノラルPCMに WAV ヘッダを付ける。 */
function toWav(pcm, sampleRate) {
  const header = Buffer.alloc(44);
  header.write("RIFF", 0);
  header.writeUInt32LE(36 + pcm.length, 4);
  header.write("WAVE", 8);
  header.write("fmt ", 12);
  header.writeUInt32LE(16, 16);        // fmtチャンクの長さ
  header.writeUInt16LE(1, 20);         // PCM
  header.writeUInt16LE(1, 22);         // モノラル
  header.writeUInt32LE(sampleRate, 24);
  header.writeUInt32LE(sampleRate * 2, 28); // バイト/秒
  header.writeUInt16LE(2, 32);         // ブロックアライン
  header.writeUInt16LE(16, 34);        // ビット深度
  header.write("data", 36);
  header.writeUInt32LE(pcm.length, 40);
  return Buffer.concat([header, pcm]);
}

mkdirSync(OUT_DIR, { recursive: true });

let found = 0;
for (const m of src.matchAll(re)) {
  const [, text, ms, name, body] = m;
  const values = body.split(",").map((s) => s.trim()).filter((s) => s.length > 0);
  const pcm = new Int16Array(values.length);
  for (let i = 0; i < values.length; i++) {
    pcm[i] = Number(values[i]);
  }

  let peak = 0;
  let sum = 0;
  for (const s of pcm) {
    peak = Math.max(peak, Math.abs(s));
    sum += s * s;
  }
  const rms = Math.sqrt(sum / pcm.length);

  const file = `${name.toLowerCase()}.wav`;
  writeFileSync(join(OUT_DIR, file), toWav(Buffer.from(pcm.buffer), rate));
  console.log(
    `${file}  「${text}」  ${Math.round((pcm.length / rate) * 1000)}ms ` +
    `(ヘッダ表記 ${ms}ms)  rms=${rms.toFixed(0)} peak=${peak}`
  );
  ++found;
}

if (found === 0) {
  throw new Error("クリップが1つも読めませんでした（VoiceClips.h の形式が変わった可能性）");
}

console.log(`\n${OUT_DIR} に書き出しました (${rate}Hz モノラル)`);
