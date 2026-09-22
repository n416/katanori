/*
 * ============================================================================
 *  焼き込む声の候補を、会話と同じ Gemini Live で何本か録る（live.mjs）。
 *
 *  使い方:
 *    cd katanori-backend
 *    node tools/live-takes.mjs WAKE_READY 3        # clips-takes/wake_ready_1.wav 〜 _3.wav
 *
 *  録るたびに抑揚が変わるので、何本か録って耳で選ぶ。選んだ 1 本を
 *  node tools/gen-voice-clips.mjs --wav WAKE_READY=clips-takes/wake_ready_2.wav で入れる。
 *  台詞は gen-voice-clips.mjs の CLIPS から引く。
 * ============================================================================
 */

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { CLIPS } from "./clip-list.mjs";
import { LIVE_RATE, liveSay, makeRequest, normLine } from "./live.mjs";
import { apiKey, msOf } from "./tts.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(ROOT, "clips-takes");

const name = process.argv[2];
const count = Number(process.argv[3] ?? 3);
const clip = CLIPS.find((c) => c.name === name);
if (!clip) {
  throw new Error(`${name} は CLIPS にありません: ${CLIPS.map((c) => c.name).join(", ")}`);
}

/** 16bit モノラルの PCM に WAV の頭を付ける。 */
function toWav(pcm, rate) {
  const h = Buffer.alloc(44);
  h.write("RIFF", 0);
  h.writeUInt32LE(36 + pcm.length, 4);
  h.write("WAVE", 8);
  h.write("fmt ", 12);
  h.writeUInt32LE(16, 16);
  h.writeUInt16LE(1, 20);
  h.writeUInt16LE(1, 22);
  h.writeUInt32LE(rate, 24);
  h.writeUInt32LE(rate * 2, 28);
  h.writeUInt16LE(2, 32);
  h.writeUInt16LE(16, 34);
  h.write("data", 36);
  h.writeUInt32LE(pcm.length, 40);
  return Buffer.concat([h, pcm]);
}

mkdirSync(OUT, { recursive: true });
const key = apiKey();
const request = await makeRequest(key, clip.text);

let got = 0;
for (let attempt = 0; got < count && attempt < count * 4; attempt++) {
  const { pcm, transcript, heard } = await liveSay(key, request);
  if (normLine(transcript) !== normLine(clip.text)) {
    console.log(`  違う返事なので録り直し: 「${transcript}」（聞き取り: ${heard}）`);
    continue;
  }
  got++;
  const file = join(OUT, `${name.toLowerCase()}_${got}.wav`);
  writeFileSync(file, toWav(pcm, LIVE_RATE));
  console.log(`${file}  ${msOf(pcm, LIVE_RATE)}ms  「${transcript}」`);
}
if (got < count) {
  console.log(`${count} 本のうち ${got} 本しか台詞どおりに言いませんでした`);
}
