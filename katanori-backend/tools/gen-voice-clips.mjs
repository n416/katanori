/*
 * ============================================================================
 *  ファームに焼き込むローカル音声を firmware/esp32/src/VoiceClips.h にまとめる。
 *
 *  サーバーに繋がる前・繋がらないときに鳴らす音なので、DO側には置けない。
 *  ファームのフラッシュに直接持たせる。
 *
 *  16kHz に落として持つ。実機のI2Sは16kHz固定なので、24kHzのまま置くと
 *  マイコン側でリサンプルが必要になるうえ、そのまま流すと低く遅い声になる。
 *
 *  声は会話と同じ Gemini Live で録り、耳で選んだ 1 本を入れる。
 *    1. node tools/live-takes.mjs WAKE_READY 3       # 候補を clips-takes/ に録る
 *    2. 聞いて選ぶ
 *    3. node tools/gen-voice-clips.mjs --wav WAKE_READY=clips-takes/wake_ready_2.wav
 *  --wav は何個でも並べてよい。指定しなかったクリップは、今の VoiceClips.h から写す
 *  （録るたびに抑揚が変わるので、聞き慣れた物は触らない）。
 *
 *  TTS のモデル（tts.mjs の synth）で作った声は、名前が同じ Achird でも会話の声と
 *  違い、2026-09-22 にユーザーから「カタノリの声じゃない」と言われた（live.mjs）。
 *
 *  生成物の VoiceClips.h はコミットする。書き込み前に `pio run` が要る。
 * ============================================================================
 */

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { CLIPS } from "./clip-list.mjs";
import { LIVE_MODEL } from "./live.mjs";
import { VOICE, trimSilence, downsample, msOf } from "./tts.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(ROOT, "..", "firmware", "esp32", "src", "VoiceClips.h");

/** 実機のI2Sレート。firmware/esp32/src/AudioIo.h の KATANORI_AUDIO_RATE と揃える。 */
const DEVICE_RATE = 16000;

/** --wav NAME=ファイル の並び。 */
const picks = new Map();
for (let i = 2; i < process.argv.length; i++) {
  if (process.argv[i] === "--wav") {
    const [name, file] = process.argv[++i].split("=");
    picks.set(name, resolve(ROOT, file));
  }
}
for (const name of picks.keys()) {
  if (!CLIPS.some((c) => c.name === name)) {
    throw new Error(`${name} は clip-list.mjs にありません`);
  }
}

/** 今の VoiceClips.h に入っているクリップ（--wav で替えない分をここから写す）。 */
function readExisting() {
  const map = new Map();
  if (!existsSync(OUT)) {
    return map;
  }
  const src = readFileSync(OUT, "utf8").replace(/\r\n/g, "\n");  // git が CRLF で置くことがある
  const re = /\/\*\* 「(.*?)」 (\d+)ms[^\n]*\n\s*static const int16_t (\w+)\[\] = \{([\s\S]*?)\n\};/g;
  for (const m of src.matchAll(re)) {
    const nums = m[4].split(/[,\s]+/).filter((x) => x !== "").map(Number);
    map.set(m[3], { text: m[1], ms: Number(m[2]), samples: Int16Array.from(nums) });
  }
  return map;
}

/** 16bit モノラルの WAV を読む。 */
function readWav(file) {
  const b = readFileSync(file);
  if (b.toString("ascii", 0, 4) !== "RIFF" || b.readUInt16LE(22) !== 1 || b.readUInt16LE(34) !== 16) {
    throw new Error(`${file} は 16bit モノラルの WAV ではありません`);
  }
  let off = 12;
  while (off < b.length) {
    const id = b.toString("ascii", off, off + 4);
    const size = b.readUInt32LE(off + 4);
    if (id === "data") {
      return { rate: b.readUInt32LE(24), pcm: b.subarray(off + 8, off + 8 + size) };
    }
    off += 8 + size;
  }
  throw new Error(`${file} に data がありません`);
}

const existing = readExisting();
const results = [];

for (const clip of CLIPS) {
  const file = picks.get(clip.name);
  if (!file) {
    const old = existing.get(clip.name);
    if (!old || old.text !== clip.text) {
      throw new Error(`${clip.name} は今の VoiceClips.h に無いか文言が違います。--wav で入れてください`);
    }
    console.log(`そのまま: ${clip.text} ${old.ms}ms`);
    results.push({ ...clip, samples: old.samples, ms: old.ms });
    continue;
  }
  const { rate, pcm } = readWav(file);
  // 前後の無音だけを落とす。語の間の無音は詰めない（間合いが変わると抑揚が崩れる）
  const d = downsample(trimSilence(Buffer.from(pcm)), rate, DEVICE_RATE);
  const samples = new Int16Array(d.buffer, d.byteOffset, d.byteLength >> 1);
  const ms = msOf(d, DEVICE_RATE);
  console.log(`入れる: ${clip.text} ${ms}ms ← ${file}`);
  results.push({ ...clip, samples, ms });
}

const totalKb = results.reduce((n, r) => n + r.samples.length * 2, 0) / 1024;
console.log(`\n合計 ${totalKb.toFixed(1)}KB（フラッシュを消費します）`);

/** int16 の並びを、1行16個ずつのC初期化子にする。 */
function toCArray(samples) {
  const lines = [];
  for (let i = 0; i < samples.length; i += 16) {
    const chunk = Array.from(samples.slice(i, i + 16)).join(",");
    lines.push(`    ${chunk},`);
  }
  return lines.join("\n");
}

const out = [
  "/*",
  " * 自動生成ファイル — 手で編集しないこと。",
  " *",
  " * 生成: cd katanori-backend && node tools/gen-voice-clips.mjs（手順はその頭）",
  ` * 声  : ${VOICE} / モデル: ${LIVE_MODEL}（会話と同じ Gemini Live で録った）`,
  ` * 形式: ${DEVICE_RATE}Hz 16bit モノラル（実機のI2Sと同じ。変換不要でそのまま play() へ）`,
  " *",
  " * サーバーに繋がる前・繋がらないときに鳴らす音。",
  " */",
  "",
  "#ifndef KATANORI_VOICE_CLIPS_H",
  "#define KATANORI_VOICE_CLIPS_H",
  "",
  "#include <Arduino.h>",
  "",
  "namespace katanori {",
  "namespace clips {",
  "",
  `constexpr uint32_t RATE = ${DEVICE_RATE};`,
  "",
];

for (const r of results) {
  out.push(
    `/** 「${r.text}」 ${r.ms}ms — ${r.comment} */`,
    `static const int16_t ${r.name}[] = {`,
    toCArray(r.samples),
    "};",
    `constexpr size_t ${r.name}_SAMPLES = sizeof(${r.name}) / sizeof(${r.name}[0]);`,
    ""
  );
}

out.push(
  "} // namespace clips",
  "} // namespace katanori",
  "",
  "#endif // KATANORI_VOICE_CLIPS_H",
  ""
);

writeFileSync(OUT, out.join("\n"), "utf8");
console.log(`${OUT} を書き出しました`);
