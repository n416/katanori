/*
 * ============================================================================
 *  会話と同じ Gemini Live に台詞を言わせて、その声を録る。
 *
 *  TTS のモデル（tts.mjs）は、声の名前が同じ Achird でも、会話の声（Live）とは
 *  声の質が違う。2026-09-22 に TTS で作った段階の声は、ユーザーに「カタノリの声
 *  じゃない」と言われた。会話の合間に鳴らす声は、会話と同じ所から録る。
 *
 *  🔴 頼みは声で渡す。文字で「この文を言って」と渡すと、Live は読み上げの調子になり、
 *  「外国人が日本語を話しているみたい」になった（2026-09-22 ユーザー。「ちょっと」の
 *  所からもうなまる）。言語を ja-JP に指定しても、場面を添えても直らなかった。
 *  会話と同じく、話しかけた声への返事として言わせると自然になる。
 *
 *  頼みの声は TTS で作る（聞かせるだけで、録る物には入らない）。
 *  モデルと声は src/index.ts の setup と揃えること。
 * ============================================================================
 */

import WebSocket from "ws";

import { VOICE, TTS_RATE, synth, trimSilence, downsample } from "./tts.mjs";

/** src/index.ts の setup.model と同じ。 */
export const LIVE_MODEL = "models/gemini-3.1-flash-live-preview";
/** Live が返す音のレート。 */
export const LIVE_RATE = 24000;
/** Live に聞かせる音のレート（src/index.ts の GEMINI_INPUT_RATE）。 */
const INPUT_RATE = 16000;

const URL =
  "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key=";

/** src/index.ts の SYSTEM_INSTRUCTION の冒頭と同じ人格。 */
const INSTRUCTION = [
  "あなたは「カタノリロボ」という名前の小さなロボットです。",
  "親しみやすく、短く返答してください。",
  // 頼まれた言葉に返事をしてしまうので足す（「おまたせ」に「待ってたよ！」と返した）
  "セリフの練習を頼まれたら、そのセリフだけを、いつもの話し方でそのまま言ってください。セリフに返事をしたり、付け足したりしないでください。",
].join("\n");

/** 台詞の比べ方。句読点と空白を無視し、Wi-Fi の表記ゆれを吸収する。 */
/** 文字起こしが漢字で返る語（台詞に出てくるものだけ）。 */
const KANJI = [["お待たせ", "おまたせ"], ["待って", "まって"], ["今", "いま"], ["起きた", "おきた"],
  ["繋が", "つなが"], ["少し", "すこし"], ["起動", "きどう"], ["設定", "せってい"]];
const toHira = (x) => x.replace(/[ァ-ヶ]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0x60));
export const normLine = (x) => {
  let t = x.replace(/[\s、。！!？?「」]/g, "").replace(/Wi-?Fi/gi, "ワイファイ");
  for (const [k, v] of KANJI) t = t.split(k).join(v);
  return toHira(t);
};

/** 頼みの声（16kHz）。後ろに 0.5 秒の無音を付ける（語尾を切らない）。 */
export async function makeRequest(key, text) {
  // TTS は前半を「読み方の指示」と受け取り、台詞だけを声にしていた（Live の聞き取りが台詞だけだった）。
  // 文を丸ごと読むよう、読み方の指示を別に付ける
  const raw = await synth(key, `セリフの練習をしよう。次のセリフを、いつもの話し方で言ってみて。「${text}」`, {
    style: "次の文を、最初から最後まで全部、友達に話しかけるように読み上げてください: ",
  });
  return Buffer.concat([downsample(trimSilence(raw), TTS_RATE, INPUT_RATE), Buffer.alloc(INPUT_RATE * 2 * 0.5)]);
}

/**
 * 頼みの声を聞かせて、返ってきた声を録る。
 * 24kHz の PCM（Buffer）と、Live の返事の文字起こし・頼みの聞き取りを返す。
 */
export function liveSay(key, request, { voice = VOICE, timeoutMs = 40000 } = {}) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(URL + key);
    const chunks = [];
    let transcript = "";
    let heard = "";
    const timer = setTimeout(() => {
      ws.close();
      reject(new Error(`Live が ${timeoutMs}ms で返事をしませんでした`));
    }, timeoutMs);

    ws.on("open", () => {
      ws.send(
        JSON.stringify({
          setup: {
            model: LIVE_MODEL,
            systemInstruction: { parts: [{ text: INSTRUCTION }] },
            generationConfig: {
              responseModalities: ["AUDIO"],
              speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: voice } } },
            },
            inputAudioTranscription: {},
            outputAudioTranscription: {},
            // 自動の区切りは切る。頼みの途中の間（台詞の「。」のあと）で話し終わりと判断され、
            // 台詞だけに返事をされた（2026-09-22「おはよー！ゆっくりでいいよ」）
            realtimeInputConfig: { automaticActivityDetection: { disabled: true } },
          },
        })
      );
    });

    ws.on("message", (data) => {
      let msg;
      try {
        msg = JSON.parse(data.toString());
      } catch {
        return;
      }
      if (msg.setupComplete) {
        ws.send(JSON.stringify({ realtimeInput: { activityStart: {} } }));
        for (let i = 0; i < request.length; i += 4096) {
          ws.send(JSON.stringify({
            realtimeInput: {
              audio: { mimeType: `audio/pcm;rate=${INPUT_RATE}`, data: request.subarray(i, i + 4096).toString("base64") },
            },
          }));
        }
        ws.send(JSON.stringify({ realtimeInput: { activityEnd: {} } }));
        return;
      }
      const sc = msg.serverContent;
      if (!sc) {
        return;
      }
      for (const p of sc.modelTurn?.parts ?? []) {
        if (p.inlineData?.data) {
          chunks.push(Buffer.from(p.inlineData.data, "base64"));
        }
      }
      if (sc.outputTranscription?.text) {
        transcript += sc.outputTranscription.text;
      }
      if (sc.inputTranscription?.text) {
        heard += sc.inputTranscription.text;
      }
      if (sc.turnComplete) {
        clearTimeout(timer);
        ws.close();
        resolve({ pcm: Buffer.concat(chunks), transcript, heard });
      }
    });

    ws.on("error", (e) => {
      clearTimeout(timer);
      reject(e);
    });
  });
}
