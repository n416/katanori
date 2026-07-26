/*
 * ============================================================================
 *  つなぎ言葉（フィラー）の音声を生成して src/fillers.ts を作り直す。
 *
 *  発話終了から応答開始までの実測1.3秒を埋めるための音。本編と同じ声で
 *  喋らせないと「別の何かが割り込んだ」ように聞こえるため、Live API が
 *  使っているのと同じ voiceName を TTS にも渡している。
 *
 *  使い方:
 *    cd katanori-backend
 *    node tools/gen-fillers.mjs [声名]
 *
 *  APIキーは .dev.vars から読む（gitignore済み）。生成物の fillers.ts は
 *  コミットする。デプロイのたびに叩く必要はなく、文言や声を変えたいときだけ。
 * ============================================================================
 */

import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import {
  VOICE as DEFAULT_VOICE,
  TTS_RATE,
  MODEL,
  apiKey,
  synth,
  trimSilence,
  collapseGaps,
  speedUp,
  truncate,
  msOf,
} from "./tts.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

/*
 * 声は tts.mjs に集約してある（実機が要求している声）。ここで上書きするのは
 * 声を比べたいときだけ。
 *
 * 一度これで間違えている: src/index.ts の既定値(Aoede)を見て合わせたつもりが、
 * 実機は firmware/esp32/src/NetLink.h の `?voice=Achird` を投げていたので
 * 本編とつなぎ言葉が別人になった。
 */
const VOICE = process.argv[2] ?? DEFAULT_VOICE;

// TTS の出力は 24kHz PCM。Live API の応答と同じレートなので、DO 側は
// 既存の Downsampler をそのまま通せる（クライアントが要求したレートへ落ちる）。

/*
 * 文言。
 *
 * 「なるほど」「わかった」のような相づちは内容を理解した体になるので使わない。
 * まだ何も分かっていない時点で鳴る音なので、中身に踏み込まない語だけにする。
 */
const PHRASES = [
  "えーっと",
  "うーんと",
  "そうだねぇ",
  "ちょっと待ってね",
];

/*
 * 読み上げの雰囲気。
 *
 * 「やわらかく」「考えごとをしながら」と頼むと母音を伸ばして1.6〜2.3秒かかり、
 * 埋めたい間（1.3秒）より長くなって本編の応答を遅らせる。早口を明示すること。
 */
const STYLE = "小さくて親しみやすいロボットのつぶやき。伸ばさずに、さらっと早口で、ごく短く言ってください: ";

/*
 * つなぎ言葉が本編の応答より長いと、間を埋めるどころか応答を待たせてしまう。
 * 実測の応答開始は1.3秒なので、その手前で必ず終わらせる。
 *
 * ただし長すぎるからと末尾を切ると語の途中でぶつ切りになる。まず話速を詰めて
 * 収め、それでも入らないぶんだけ切る（実際には切らずに収まる）。
 */
const TARGET_MS = 1100;
const MAX_MS = 1250;
// これ以上詰めると声が甲高くなって別人になる。
const MAX_SPEEDUP = 1.6;

/*
 * 短すぎる出力を弾くための下限。
 *
 * TTS は同じ文言でも実行ごとに結果が変わり、298ms（語として聞き取れない）を
 * 返してきたことがある。検証せずに焼き込むと、そのまま実機で鳴って原因調査に
 * 逆戻りするので、下限を割ったら作り直す。
 */
const MIN_MS = 500;
const MAX_ATTEMPTS = 4;

/*
 * 話速を上げると音程も一緒に上がる（サンプルを間引く方式なので）。x1.6 では
 * 7半音上がって別人になり、本編と声が違うという一番避けたい状態になる。
 *
 * TTS の長さは実行ごとにばらつくので、詰めが要らない短い回が出るまで振り直す。
 */
const MAX_NATURAL_SPEEDUP = 1.25;

const key = apiKey();
const entries = [];

/** 1回合成して、鳴らせる形（無音除去・間詰め・話速・上限）まで整える。 */
async function makeOne(phrase) {
  const raw = await synth(key, phrase, { voice: VOICE, style: STYLE });
  const rawMs = msOf(raw);
  let pcm = collapseGaps(trimSilence(raw));
  const trimmedMs = msOf(pcm);

  // 長い場合はまず話速で詰める。切るのは最後の手段。
  let speed = 1;
  if (trimmedMs > TARGET_MS) {
    speed = Math.min(trimmedMs / TARGET_MS, MAX_SPEEDUP);
    pcm = speedUp(pcm, speed);
  }

  const maxSamples = Math.floor((TTS_RATE * MAX_MS) / 1000);
  let capped = false;
  if (pcm.byteLength / 2 > maxSamples) {
    pcm = truncate(pcm, maxSamples);
    capped = true;
  }

  const notes = [
    `TTS ${rawMs}ms → 整形後 ${trimmedMs}ms`,
    speed > 1 ? `話速 x${speed.toFixed(2)}` : "話速そのまま",
    capped ? "上限で切詰" : null,
  ].filter(Boolean);

  return { pcm, ms: msOf(pcm), speed, notes };
}

for (const phrase of PHRASES) {
  process.stdout.write(`生成中: ${phrase} ... `);

  /*
   * 短すぎる回・詰めすぎになった回は捨てて振り直す。同じ文言でも結果が変わる
   * ので、たいてい数回で「そのままの話速で1.3秒に収まる回」が出る。
   */
  const cands = [];
  let attempt = 0;
  for (; attempt < MAX_ATTEMPTS; attempt++) {
    const cand = await makeOne(phrase);
    cands.push(cand);
    if (cand.ms >= MIN_MS && cand.speed <= MAX_NATURAL_SPEEDUP) {
      break;
    }
    process.stdout.write(
      cand.ms < MIN_MS
        ? `[${cand.ms}msと短い→再生成] `
        : `[話速x${cand.speed.toFixed(2)}は詰めすぎ→再生成] `
    );
  }

  // 聞き取れる長さがあるものの中から、いちばん音程をいじらずに済むものを採る。
  const usable = cands.filter((c) => c.ms >= MIN_MS);
  if (usable.length === 0) {
    // 全滅なら文言かSTYLEの問題。黙って通すと実機で気づくことになる。
    const longest = Math.max(...cands.map((c) => c.ms));
    throw new Error(
      `"${phrase}" が ${cands.length}回とも ${MIN_MS}ms 未満でした（最長 ${longest}ms）。` +
      `文言か STYLE を見直してください。`
    );
  }
  const best = usable.reduce((a, b) => (b.speed < a.speed ? b : a));

  if (cands.length > 1) {
    best.notes.push(`${cands.length}回振って採用`);
  }
  console.log(`${best.ms}ms (${(best.pcm.byteLength / 1024).toFixed(1)}KB) — ${best.notes.join(" / ")}`);
  entries.push({ phrase, ms: best.ms, b64: best.pcm.toString("base64") });
}

const total = entries.reduce((n, e) => n + e.b64.length, 0);
console.log(`\n合計 base64 ${(total / 1024).toFixed(1)}KB`);

const lines = [
  "/*",
  " * 自動生成ファイル — 手で編集しないこと。",
  " *",
  " * 生成: node tools/gen-fillers.mjs",
  ` * 声  : ${VOICE} / モデル: ${MODEL}`,
  ` * 形式: ${TTS_RATE}Hz 16bit モノラル PCM を base64 にしたもの`,
  " *",
  " * 発話終了から応答開始までの1.3秒を埋めるつなぎ言葉。",
  " */",
  "",
  `export const FILLER_RATE = ${TTS_RATE};`,
  "",
  "/**",
  " * この音源を作った声。",
  " *",
  " * クライアントが別の声を要求してきたとき、つなぎ言葉だけ声が変わるのを",
  " * 避けるために DO 側で突き合わせる。",
  " */",
  `export const FILLER_VOICE = ${JSON.stringify(VOICE)};`,
  "",
  "/** 文言と長さ（ログ・確認用）。FILLERS_B64 と同じ順序。 */",
  "export const FILLER_INFO: ReadonlyArray<{ phrase: string; ms: number }> = [",
  ...entries.map((e) => `  { phrase: ${JSON.stringify(e.phrase)}, ms: ${e.ms} },`),
  "];",
  "",
  "export const FILLERS_B64: ReadonlyArray<string> = [",
  ...entries.map((e) => `  ${JSON.stringify(e.b64)},`),
  "];",
  "",
];

mkdirSync(join(ROOT, "src"), { recursive: true });
writeFileSync(join(ROOT, "src", "fillers.ts"), lines.join("\n"), "utf8");
console.log("src/fillers.ts を書き出しました");
