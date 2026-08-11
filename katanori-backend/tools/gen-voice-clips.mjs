/*
 * ============================================================================
 *  ファームに焼き込むローカル音声を生成して
 *  firmware/esp32/src/VoiceClips.h を作り直す。
 *
 *  サーバーに繋がる前・繋がらないときに鳴らす音なので、DO側には置けない。
 *  ファームのフラッシュに直接持たせる。
 *
 *  16kHz に落として持つ。実機のI2Sは16kHz固定なので、24kHzのまま置くと
 *  マイコン側でリサンプルが必要になるうえ、そのまま流すと低く遅い声になる。
 *
 *  使い方:
 *    cd katanori-backend
 *    node tools/gen-voice-clips.mjs
 *
 *  声は tts.mjs に集約（実機が要求している声と同じでなければならない）。
 *  生成物の VoiceClips.h はコミットする。書き込み前に `pio run` が要る。
 * ============================================================================
 */

import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import {
  VOICE,
  TTS_RATE,
  MODEL,
  apiKey,
  synth,
  trimSilence,
  collapseGaps,
  downsample,
  msOf,
} from "./tts.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(ROOT, "..", "firmware", "esp32", "src", "VoiceClips.h");

/** 実機のI2Sレート。firmware/esp32/src/AudioIo.h の KATANORI_AUDIO_RATE と揃える。 */
const DEVICE_RATE = 16000;

/*
 * 読み上げの雰囲気。
 *
 * 「明るく」と頼むと元気に叫ぶような読み方になり、置いてある家電としては
 * うるさい。一方でつなぎ言葉のような「つぶやき」にすると聞き取れない
 * （こちらは伝えるための音）。落ち着いた話し方で、はっきりだけ残す。
 *
 * 語尾に「！」を付けるとそれだけでテンションが上がるので付けないこと。
 */
const STYLE = "小さくて親しみやすいロボットの声で、落ち着いて、やわらかく、はっきりと、短く言ってください。大きな声を出さないでください: ";

/*
 * 焼き込む音声。
 *
 * C の識別子になるので name は英大文字。増やすぶんだけフラッシュを食う
 * （16kHz 16bit モノラルで 1秒 = 32KB）。
 */
const CLIPS = [
  {
    name: "BOOT_READY",
    text: "カタノリ、起動しました",
    comment: "Wi-Fiに繋がって会話できる状態になったとき",
  },
  {
    name: "PROV_NEEDED",
    text: "ワイファイの設定をしてください",
    comment: "Wi-Fi設定モードに入ったとき（未設定・繋がらない・手動で入った）",
  },
  {
    name: "WIFI_OK",
    text: "ワイファイにつながりました",
    comment: "設定モードで保存したWi-Fiへの初回接続に成功したとき（パスワードが合っていた合図）",
  },
];

/*
 * 短すぎる出力を弾くための下限。
 *
 * TTS は同じ文言でも実行ごとに長さが変わり、語の一部しか返さないことがある。
 * 検証せずに焼き込むと、書き込んで電源を入れるまで気づけない。
 */
const MIN_MS = 700;
const MAX_ATTEMPTS = 4;

const key = apiKey();
const results = [];

for (const clip of CLIPS) {
  process.stdout.write(`生成中: ${clip.text} ... `);

  let best = null;
  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
    const raw = await synth(key, clip.text, { style: STYLE });
    // 話速はいじらない。アナウンスは長さの制約が無いので、音程を触る理由がない。
    const shaped = collapseGaps(trimSilence(raw));
    const cand = { pcm: downsample(shaped, TTS_RATE, DEVICE_RATE), rawMs: msOf(raw) };
    cand.ms = msOf(cand.pcm, DEVICE_RATE);

    if (!best || cand.ms > best.ms) {
      best = cand;
    }
    if (cand.ms >= MIN_MS) {
      best = cand;
      break;
    }
    process.stdout.write(`[${cand.ms}msと短い→再生成] `);
  }

  if (best.ms < MIN_MS) {
    throw new Error(
      `"${clip.text}" が ${MAX_ATTEMPTS}回とも ${MIN_MS}ms 未満でした（最長 ${best.ms}ms）。` +
      `文言か STYLE を見直してください。`
    );
  }

  const samples = new Int16Array(best.pcm.buffer, best.pcm.byteOffset, best.pcm.byteLength >> 1);
  let peak = 0;
  for (const s of samples) {
    peak = Math.max(peak, Math.abs(s));
  }
  console.log(`${best.ms}ms (${(best.pcm.byteLength / 1024).toFixed(1)}KB) peak=${peak}`);
  results.push({ ...clip, samples, ms: best.ms });
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
  " * 生成: cd katanori-backend && node tools/gen-voice-clips.mjs",
  ` * 声  : ${VOICE} / モデル: ${MODEL}`,
  ` * 形式: ${DEVICE_RATE}Hz 16bit モノラル（実機のI2Sと同じ。変換不要でそのまま play() へ）`,
  " *",
  " * サーバーに繋がる前・繋がらないときに鳴らす音。DO側のつなぎ言葉とは",
  " * 別物だが、同じ声で作ってある。",
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
