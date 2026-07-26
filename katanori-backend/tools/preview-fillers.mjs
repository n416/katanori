/*
 * ============================================================================
 *  src/fillers.ts に入っているつなぎ言葉を WAV に書き出して耳で確かめる。
 *
 *  デプロイしてから「思ってた音と違う」となるのが一番手戻りが大きいので、
 *  実機に載せる前にここで聴く。TTSは呼ばない（fillers.ts の中身そのもの）。
 *
 *  使い方:
 *    node tools/preview-fillers.mjs [出力先ディレクトリ]
 * ============================================================================
 */

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT_DIR = process.argv[2] ?? join(ROOT, "fillers-preview");

// fillers.ts は自動生成でフォーマットが固定なので、TSをビルドせず正規表現で読む。
const src = readFileSync(join(ROOT, "src", "fillers.ts"), "utf8");

const rate = Number(/export const FILLER_RATE = (\d+);/.exec(src)?.[1]);
if (!rate) {
  throw new Error("FILLER_RATE を読めません");
}

// `export const` まで込みで当てること。コメント中にも識別子が出てくるので、
// 名前だけを頼りにすると宣言ではなくコメントに当たる。
const infoBlock = /export const FILLER_INFO[^=]*=\s*\[([\s\S]*?)\n\];/.exec(src)?.[1] ?? "";
const phrases = [...infoBlock.matchAll(/phrase:\s*"((?:[^"\\]|\\.)*)"/g)]
  .map((m) => JSON.parse(`"${m[1]}"`));

const b64Block = /export const FILLERS_B64[^=]*=\s*\[([\s\S]*?)\n\];/.exec(src)?.[1] ?? "";
const b64s = [...b64Block.matchAll(/"([A-Za-z0-9+/=]+)"/g)].map((m) => m[1]);

if (b64s.length === 0) {
  throw new Error("FILLERS_B64 を読めません");
}

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

b64s.forEach((b64, i) => {
  const pcm = Buffer.from(b64, "base64");
  const samples = new Int16Array(pcm.buffer, pcm.byteOffset, pcm.byteLength >> 1);

  let sum = 0;
  let peak = 0;
  for (const s of samples) {
    sum += s * s;
    peak = Math.max(peak, Math.abs(s));
  }
  const rms = Math.sqrt(sum / samples.length);
  const ms = Math.round((samples.length / rate) * 1000);

  const name = `filler${i}.wav`;
  writeFileSync(join(OUT_DIR, name), toWav(pcm, rate));
  console.log(
    `${name}  "${phrases[i] ?? "?"}"  ${ms}ms  rms=${rms.toFixed(0)} peak=${peak}`
  );
});

console.log(`\n${OUT_DIR} に書き出しました (${rate}Hz モノラル)`);
