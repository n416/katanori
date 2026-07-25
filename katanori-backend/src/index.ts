import { Downsampler, base64ToInt16, arrayBufferToBase64 } from "./resample";

export interface Env {
  ROBOT_DO: DurableObjectNamespace;
  GEMINI_API_KEY: string;
}

/**
 * Gemini が受け付ける入力音声のレート。仕様で 16kHz 固定。
 * ReSpeaker Lite のマイクも 16kHz なので、入力方向の変換は不要。
 */
const GEMINI_INPUT_RATE = 16000;

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    try {
      if (request.headers.get("Upgrade") === "websocket") {
        const id = env.ROBOT_DO.idFromName("robot-1");
        const stub = env.ROBOT_DO.get(id);
        return await stub.fetch(request);
      }
      return new Response("Katanori DO Server is running.", { status: 200 });
    } catch (e: any) {
      return new Response(`Main Worker Error: ${e.message}`, { status: 500 });
    }
  }
};

/**
 * PCMモードで、クライアント(マイコン)へ送る価値のないメッセージか。
 * 帯域とパース負荷を無駄にしないために落とす。
 * turnComplete / interrupted / 文字起こし などが残っていれば当然送る。
 */
function shouldDropForDevice(msg: any): boolean {
  const keys = Object.keys(msg ?? {});
  if (keys.length === 0) {
    return true;
  }

  // セッション再開ハンドル。Geminiが数秒おきに送ってくるが、ESP32は
  // 再開機能を使わないので捨てる（実測で20秒に13件届いていた）
  if (keys.length === 1 && keys[0] === "sessionResumptionUpdate") {
    return true;
  }

  // 音声を抜いた結果、あるいは元から中身が空だったもの
  if (keys.length === 1 && keys[0] === "serverContent") {
    return Object.keys(msg.serverContent ?? {}).length === 0;
  }

  return false;
}

export class RobotDO implements DurableObject {
  state: DurableObjectState;
  env: Env;
  clientWs: WebSocket | null = null;
  geminiWs: WebSocket | null = null;

  constructor(state: DurableObjectState, env: Env) {
    this.state = state;
    this.env = env;
  }

  async fetch(request: Request): Promise<Response> {
    try {
      const webSocketPair = new WebSocketPair();
      const client = Object.values(webSocketPair)[0];
      const server = Object.values(webSocketPair)[1];

      server.accept();
      this.clientWs = server;
      
      const requestUrl = new URL(request.url);
      const voice = requestUrl.searchParams.get("voice") || "Aoede";

      // ?pcm=<レート> を付けたクライアントは「生PCMバイナリ」でやり取りする。
      // 付けなければ従来どおり Gemini のメッセージを素通しする (wrapper.py 互換)。
      const pcmParam = requestUrl.searchParams.get("pcm");
      let pcmRate = 0;
      if (pcmParam !== null) {
        const parsed = parseInt(pcmParam, 10);
        pcmRate = Number.isFinite(parsed) && parsed >= 8000 && parsed <= 48000
          ? parsed
          : GEMINI_INPUT_RATE;
      }

      this.connectToGemini(server, voice, pcmRate).catch(e => {
        console.error("Gemini connection error:", e);
      });

      return new Response(null, {
        status: 101,
        webSocket: client
      });
    } catch (e: any) {
      return new Response(`DO Fetch Error: ${e.message}`, { status: 500 });
    }
  }

  dbg(ws: WebSocket, msg: string) {
    console.log("[DO]", msg);
    try { ws.send(JSON.stringify({ _debug: msg })); } catch {}
  }

  async connectToGemini(serverWs: WebSocket, voiceName: string, pcmRate: number) {
    const pcmMode = pcmRate > 0;
    this.dbg(serverWs, `DO fetch ok, connecting to Gemini with voice: ${voiceName}...`);
    if (pcmMode) {
      this.dbg(serverWs, `PCM mode: audio as binary frames @${pcmRate}Hz`);
    }

    if (!this.env.GEMINI_API_KEY) {
      this.dbg(serverWs, "ERROR: No GEMINI_API_KEY set.");
      return;
    }

    const url = `https://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key=${this.env.GEMINI_API_KEY}`;

    let res: Response;
    try {
      res = await fetch(url, {
        headers: { "Upgrade": "websocket" }
      });
    } catch (e: any) {
      this.dbg(serverWs, `ERROR: fetch to Gemini threw: ${e.message}`);
      return;
    }

    if (res.status !== 101) {
      const body = await res.text();
      this.dbg(serverWs, `ERROR: Gemini upgrade failed: status=${res.status} body=${body.slice(0, 300)}`);
      return;
    }

    const geminiWs = res.webSocket;
    if (!geminiWs) {
      this.dbg(serverWs, "ERROR: res.webSocket is null");
      return;
    }

    this.geminiWs = geminiWs;

    // Gemini -> Client
    //
    // 素通しモード: Gemini のメッセージをそのまま流す (wrapper.py が使う)。
    // PCMモード  : 音声だけを取り出して 16bit PCM のバイナリフレームで送り、
    //              残りの制御情報をテキストJSONで送る。ESP32側は
    //              「バイナリ=音声 / テキスト=制御」だけを見ればよくなる。
    let downsampler: Downsampler | null = null;

    geminiWs.addEventListener("message", (event) => {
      try {
        if (!pcmMode) {
          const preview = typeof event.data === "string"
            ? event.data.slice(0, 200)
            : `<binary ${(event.data as ArrayBuffer).byteLength} bytes>`;
          console.log("[DO] Gemini -> client:", preview);
          serverWs.send(event.data);
          return;
        }

        // Gemini はバイナリフレームで返してくる場合がある (中身はJSONテキスト)
        const text = typeof event.data === "string"
          ? event.data
          : new TextDecoder().decode(event.data as ArrayBuffer);

        let msg: any;
        try {
          msg = JSON.parse(text);
        } catch {
          serverWs.send(event.data); // JSONでないものはそのまま渡す
          return;
        }

        const parts = msg?.serverContent?.modelTurn?.parts;

        if (Array.isArray(parts)) {
          const remaining: any[] = [];

          for (const part of parts) {
            const inline = part?.inlineData;
            const mime: string = inline?.mimeType ?? "";

            if (inline?.data && mime.startsWith("audio/pcm")) {
              // mimeType から実際のレートを読む (24000決め打ちにしない)
              const m = /rate=(\d+)/.exec(mime);
              const srcRate = m ? parseInt(m[1], 10) : 24000;

              const pcm = base64ToInt16(inline.data);

              // .buffer ではなくビューを渡す。base64が奇数バイトで終わった場合に
              // .buffer だと末尾の余分な1バイトまで送ってしまう。
              let out: Int16Array;
              if (srcRate === pcmRate) {
                out = pcm; // 変換不要
              } else {
                if (!downsampler || downsampler.inRate !== srcRate) {
                  downsampler = new Downsampler(srcRate, pcmRate);
                }
                out = downsampler.process(pcm);
              }

              // 極小のチャンクではリサンプル後に0サンプルになることがある。
              // 長さ0のフレームはマイコンを無駄に起こすだけなので送らない。
              if (out.length > 0) {
                serverWs.send(out);
              }
            } else {
              remaining.push(part);
            }
          }

          if (remaining.length > 0) {
            msg.serverContent.modelTurn.parts = remaining;
          } else {
            delete msg.serverContent.modelTurn;
          }
        }

        if (shouldDropForDevice(msg)) {
          return;
        }
        serverWs.send(JSON.stringify(msg));
      } catch (e) {
        console.error("Forward to client error:", e);
      }
    });

    geminiWs.addEventListener("close", (event) => {
      this.dbg(serverWs, `Gemini closed: code=${event.code} reason=${event.reason}`);
      serverWs.close(1011, `Gemini closed: ${event.code} ${event.reason}`.slice(0, 120));
    });

    geminiWs.addEventListener("error", (event: any) => {
      this.dbg(serverWs, `Gemini ws error: ${event?.message ?? String(event)}`);
    });

    // Client -> Gemini
    //
    // PCMモードでは「バイナリフレーム = 生の16kHz PCM」と解釈して、
    // Gemini が要求する realtimeInput.audio の形に包み直す。
    // 制御メッセージ (audioStreamEnd など) はテキストで送ってもらい素通しする。
    // これで ESP32 側は base64 も JSON 組み立ても一切やらなくて済む。
    serverWs.addEventListener("message", (event) => {
      try {
        if (pcmMode && typeof event.data !== "string") {
          const b64 = arrayBufferToBase64(event.data as ArrayBuffer);
          geminiWs.send(JSON.stringify({
            realtimeInput: {
              audio: {
                mimeType: `audio/pcm;rate=${GEMINI_INPUT_RATE}`,
                data: b64,
              },
            },
          }));
          return;
        }
        geminiWs.send(event.data);
      } catch (e) {
        console.error("Forward to Gemini error:", e);
      }
    });

    serverWs.addEventListener("close", (event) => {
      console.log(`[DO] Client closed: code=${event.code} reason=${event.reason}`);
      geminiWs.close();
    });

    geminiWs.accept();
    this.dbg(serverWs, "Connected to Gemini, sending setup...");

    const setupMsg = {
      setup: {
        // gemini-2.5-flash-native-audio-preview-12-2025 (遅延~1.9s) から変更。
        // 実測で発話終了→応答開始が1.3sに短縮。previewモデルのため廃止時は
        // native-audio-latest へ戻すこと(その場合クライアントは旧mediaChunks形式も可)
        model: "models/gemini-3.1-flash-live-preview",
        systemInstruction: {
          parts: [{ text: "あなたはカタノリロボです。親しみやすく短い返答をしてください。" }]
        },
        generationConfig: {
          responseModalities: ["AUDIO"],
          speechConfig: {
            voiceConfig: {
              prebuiltVoiceConfig: {
                voiceName: voiceName
              }
            }
          }
        },
        // クライアント側デバッグ表示用: Geminiが聞き取った内容と応答内容の文字起こし
        inputAudioTranscription: {},
        outputAudioTranscription: {},
        // 自動VADを鈍らせる: 文間の休止で発話終了と誤判定→応答開始→続きの音声で
        // interrupted になり会話が破綻するため。発話終了はクライアントの
        // audioStreamEnd で即時確定するので沈黙2秒待ちのデメリットは実質ない
        realtimeInputConfig: {
          automaticActivityDetection: {
            endOfSpeechSensitivity: "END_SENSITIVITY_LOW",
            silenceDurationMs: 2000
          }
        }
      }
    };
    geminiWs.send(JSON.stringify(setupMsg));
  }
}
