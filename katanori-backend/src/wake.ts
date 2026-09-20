/*
 * ============================================================================
 *  wake.ts - 呼びかけ判定（POST /wake）
 *
 *  機体が VAD で「装着者が喋った」と判断した区間だけを送ってくる。ここで
 *  Workers AI の whisper で文字にし、呼び名が入っているかだけを返す。
 *
 *  Durable Object は通さない。状態を持たないうえ、DO は accept した接続が
 *  繋がっている間ずっと duration 課金されるため、待機のために張っておけない
 *  （1台を24時間繋ぐと有料プランの無料枠 400,000 GB-s の8割を食う）。
 *
 *  呼び名の正は機体側（NVS）にある。ブラウザの設定ページ http://katanori.local/
 *  で登録し、機体がリクエストごとに `?name=` で送ってくる。ここには持たない。
 * ============================================================================
 */

import { arrayBufferToBase64 } from "./resample";

/** 呼び名の既定。ユーザーが設定していないときはこれで判定する。 */
export const DEFAULT_WAKE_NAME = "カタノリ";

/** 機体が送ってくる音声のレート。ReSpeaker Lite のマイクと同じ。 */
const WAKE_INPUT_RATE = 16000;

/**
 * 受け付ける音声の上限バイト数。
 *
 * 機体が送るのは VAD の1区間で、上限は VAD_MAX_SEGMENT_MS = 10秒
 * （main.cpp）。16kHz・16bit・モノラルで 320,000 バイト。倍を上限にしておく。
 */
const MAX_WAKE_BYTES = 640000;

/**
 * 生PCMに WAV のヘッダを被せる。
 *
 * 機体が送ってくるのはヘッダの無い 16bit リトルエンディアンの生PCMだが、
 * Workers AI の whisper は音声ファイルとして受け取る。44バイト足すだけで
 * WAV になるので、ここで被せる（再エンコードはしない）。
 */
function wrapWav(pcm: ArrayBuffer, rate: number): ArrayBuffer {
  const out = new ArrayBuffer(44 + pcm.byteLength);
  const view = new DataView(out);
  const ascii = (off: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i));
  };
  ascii(0, "RIFF");
  view.setUint32(4, 36 + pcm.byteLength, true);
  ascii(8, "WAVE");
  ascii(12, "fmt ");
  view.setUint32(16, 16, true);          // fmt チャンクの大きさ
  view.setUint16(20, 1, true);           // 1 = PCM（無圧縮）
  view.setUint16(22, 1, true);           // モノラル
  view.setUint32(24, rate, true);
  view.setUint32(28, rate * 2, true);    // バイト毎秒 = レート × 2バイト
  view.setUint16(32, 2, true);           // ブロック境界 = 2バイト
  view.setUint16(34, 16, true);          // 1サンプル16bit
  ascii(36, "data");
  view.setUint32(40, pcm.byteLength, true);
  new Uint8Array(out, 44).set(new Uint8Array(pcm));
  return out;
}

/**
 * 突き合わせ用に整える。
 *
 * whisper の出力は表記が揺れる。同じ「カタノリ」でも、ひらがなで返ることも
 * 句読点や空白が挟まることもある（過去には「カタノリロボ」が「加藤のいとこ」と
 * 出た記録もある）。呼び名をカタカナに限っているのは、ここで読みだけを見て
 * 比べられるようにするため。
 *
 * ⚠ 漢字で返されたぶんは救えない。読みへ戻す手段がないため、initial_prompt で
 * 呼び名を先に見せて、その表記で出させるほうで対処する。
 */
export function normalizeForMatch(s: string): string {
  return s
    .replace(/[ぁ-ゖ]/g, (ch) =>
      String.fromCharCode(ch.charCodeAt(0) + 0x60)) // ひらがな → カタカナ
    .replace(/[ｦ-ﾝ]/g, (ch) =>
      String.fromCharCode(ch.charCodeAt(0) - 0xFF66 + 0x30A2)) // 半角カナ（粗い）
    .replace(/[\s、。，．・！？!?「」『』()（）]/g, "")
    .toUpperCase();
}

/** 文字起こしの中に呼び名があるか。 */
export function containsName(text: string, name: string): boolean {
  const n = normalizeForMatch(name);
  return n.length > 0 && normalizeForMatch(text).includes(n);
}

/**
 * POST /wake?name=カタノリ
 *   本体: ヘッダ無しの 16kHz・16bit・モノラルの生PCM
 *   返り: {"text": "...", "wake": true, "name": "カタノリ", "ms": 1234}
 */
export async function handleWake(request: Request, env: { AI: any }): Promise<Response> {
  const url = new URL(request.url);
  const name = (url.searchParams.get("name") || DEFAULT_WAKE_NAME).trim();
  const rate = Number(url.searchParams.get("rate") || WAKE_INPUT_RATE);

  const pcm = await request.arrayBuffer();
  if (pcm.byteLength === 0) {
    return json({ error: "音声が空です" }, 400);
  }
  if (pcm.byteLength > MAX_WAKE_BYTES) {
    return json({ error: `音声が大きすぎます (${pcm.byteLength}バイト)` }, 413);
  }

  const started = Date.now();
  try {
    const res = await env.AI.run("@cf/openai/whisper-large-v3-turbo", {
      audio: arrayBufferToBase64(wrapWav(pcm, rate)),
      language: "ja",
      task: "transcribe",
      // 呼び名を先に見せて、その表記で出させる。漢字に化けると照合できない
      initial_prompt: name,
      // 繰り返しの幻聴を抑える（無音に近い区間で効く）
      condition_on_previous_text: false,
      // 探索を1本に絞る。ここで見たいのは呼び名が入っているかだけで、
      // 文章の正確さは要らない。実機で判定に 2.7〜6.1秒 かかっていて、
      // 呼ばれてから会話が始まるまでの待ちに直結する
      beam_size: 1,
    });

    const text: string = (res?.text ?? "").trim();
    return json({
      text,
      wake: containsName(text, name),
      name,
      ms: Date.now() - started,
      bytes: pcm.byteLength,
      // 空で返ったときの切り分け用。音声そのものが届いていないのか、
      // 届いたが言葉として拾えなかったのかを分ける
      info: res?.transcription_info ?? null,
      words: res?.word_count ?? null,
    });
  } catch (e: any) {
    return json({ error: `文字起こしに失敗: ${e?.message ?? e}` }, 502);
  }
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}
