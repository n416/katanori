import { Downsampler, base64ToInt16, arrayBufferToBase64 } from "./resample";
import { FILLERS_B64, FILLER_INFO, FILLER_RATE, FILLER_VOICE } from "./fillers";

export interface Env {
  ROBOT_DO: DurableObjectNamespace;
  GEMINI_API_KEY: string;
}

/**
 * Gemini が受け付ける入力音声のレート。仕様で 16kHz 固定。
 * ReSpeaker Lite のマイクも 16kHz なので、入力方向の変換は不要。
 */
const GEMINI_INPUT_RATE = 16000;

/**
 * PCMモードで1フレームに詰める音声の最大バイト数。
 *
 * マイコン側の WebSocket ライブラリ (links2004/WebSockets) は
 * WEBSOCKETS_MAX_DATA_SIZE = 15KB を超えるフレームを受け取ると、
 * 中身を読まずに close(1009) で切断する。Geminiは1チャンクで
 * それを超える音声を送ってくることがあるため、ここで刻んでおく。
 * 4096バイト = 2048サンプル = 16kHzで128ms。
 */
const MAX_AUDIO_FRAME_BYTES = 4096;

/**
 * つなぎ言葉のデコード済みキャッシュ。
 *
 * 送信レートごとに1回だけ base64 デコードとリサンプルを済ませて使い回す。
 * DOインスタンスは接続をまたいで生きるので、モジュール変数に置いておけば
 * 2回目以降の会話では変換コストが完全に消える。
 */
const fillerCache = new Map<number, Int16Array[]>();

/** 指定レートのつなぎ言葉PCMを返す（初回だけ変換する）。 */
function fillersAt(rate: number): Int16Array[] {
  let cached = fillerCache.get(rate);
  if (cached) {
    return cached;
  }
  cached = FILLERS_B64.map((b64) => {
    const pcm = base64ToInt16(b64);
    if (rate === FILLER_RATE) {
      return pcm;
    }
    // Downsampler は連続ストリーム用に内部状態を持つ。つなぎ言葉ごとに
    // 使い捨てにして、前の語の尾が次の語へ混ざらないようにする。
    return new Downsampler(FILLER_RATE, rate).process(pcm);
  });
  fillerCache.set(rate, cached);
  return cached;
}

/**
 * 人格と、名前の誤認識を吸収するための指示。
 *
 * Gemini Live API には音声認識のヒント（phrase hints）を渡す手段がないため、
 * 「カタノリロボ」が誤って文字起こしされる問題はプロンプト側で吸収するしかない。
 * 実機で「加藤のいとこ」と認識された実例がある。
 */
const SYSTEM_INSTRUCTION = [
  "あなたは「カタノリロボ」という名前の小さなロボットです。",
  "親しみやすく、短く返答してください。",
  "",
  "【名前の聞き取りについて】",
  "音声認識の都合で、あなたの名前が次のように誤って文字起こしされることがあります。",
  "「加藤のいとこ」「加藤の従兄弟」「肩乗り」「片乗り」「カタノリ」「かたのり」",
  "「かた乗り」「方のり」など。",
  "これらが出てきたら、すべてあなたへの呼びかけだと解釈してください。",
  "聞き間違いを指摘したり名前を訂正したりせず、自然に応答を続けてください。",
].join("\n");

/**
 * 現在時刻を日本時間の読み上げやすい形にする。
 *
 * Cloudflare Workers の Date は常に UTC で動く。素の toString() を使うと
 * 9時間ずれた時刻を自信満々に喋る、注入しないより悪い状態になるので
 * timeZone を明示すること。
 *
 * 例: "2026年7月26日日曜日 14:35"
 */
function nowInJapan(): string {
  return new Intl.DateTimeFormat("ja-JP", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date());
}

/**
 * 人格の指示に、接続時点の日時を足したものを組み立てる。
 *
 * LLM は時計を持たないため、日付や時刻を聞かれると平然と嘘を答える。
 * 見守り用途（「お薬の時間だよ」等）では誤答が実害になるので、
 * セッション開始時に現在時刻を渡しておく。
 *
 * 注意: ここで渡した時刻はセッション開始時点で固定される。現状は
 * 会話が終わればすぐ切断される運用なのでズレは無視できるが、
 * 常時接続に戻すなら定期的な再注入が必要になる。
 */
function buildSystemInstruction(woke: string): string {
  return [
    SYSTEM_INSTRUCTION,
    ...wokeInstruction(woke),
    "",
    "【現在の日時】",
    `この会話が始まった時点の日本時間は ${nowInJapan()} です。`,
    "日付・曜日・時刻を聞かれたら、必ずこの情報をもとに答えてください。",
    "推測で別の日時を答えてはいけません。",
    "会話中はこの時刻から少しずつ時間が経っていると考えてください。",
    "挨拶をするときも、この時刻に合ったもの（朝・昼・夜）を選んでください。",
  ].join("\n");
}

/**
 * 会話の始まり方に合わせた指示（機体が ?woke= で伝える）。
 *
 * 眠っている間に呼ばれたとき、機体はつながるまでの間に自分の声で「ちょっと待ってね、
 * いま起きたところ」「ワイファイがつながったよ、あと少し」「おまたせ！」と言ってある
 * （firmware の VoiceClips.h）。Gemini はそれを知らないので、伝えないと挨拶を重ねる。
 * 🔒 ユーザー 2026-09-22「これがAIへのプロンプトにもつなげておかないといけない」。
 */
function wokeInstruction(woke: string): string[] {
  if (woke !== "sleep") {
    return [];
  }
  return [
    "",
    "【この会話の始まり方】",
    "あなたは眠っていたところを、名前を呼ばれて起きました。",
    "つながるまで待たせている間に、あなたはもう「ちょっと待ってね、いま起きたところ」",
    "「ワイファイがつながったよ、あと少し」のように言ってあり、待たせたときは「おまたせ！」も言ってあります。",
    "同じ挨拶やお詫びを繰り返さないでください。",
    "最初に届く音声は、待っている間に相手が話したものです。用件が入っていれば、それに答えてください。",
    // 「なあに？」と聞かせたら、「おまたせ！」の直後で同じ呼びかけが 2 回続いて違和感があった
    // （2026-09-22 ユーザー）。「おまたせ！」がもう「どうぞ」の合図になっている
    "あなたの名前しか入っていなければ、何も言わずに、相手が話し始めるのを待ってください。",
  ];
}

/** 上限を超えないよう分割して送る。 */
function sendAudioChunked(ws: WebSocket, pcm: Int16Array) {
  const maxSamples = MAX_AUDIO_FRAME_BYTES / 2;
  for (let off = 0; off < pcm.length; off += maxSamples) {
    ws.send(pcm.subarray(off, Math.min(off + maxSamples, pcm.length)));
  }
}

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
  /** 直前に鳴らしたつなぎ言葉。2回続けて同じものを選ばないため。 */
  lastFiller = -1;
  /** このセッションで Gemini に喋らせている声。つなぎ言葉の突き合わせに使う。 */
  voiceName = "";
  /** 会話の始まり方（?woke=）。wokeInstruction を参照。 */
  woke = "";

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
      // 既定値はつなぎ言葉を焼いた声に合わせる。ここを別の声にすると、
      // ?voice を付けないクライアントだけ本編とつなぎ言葉が別人になる。
      const voice = requestUrl.searchParams.get("voice") || FILLER_VOICE;
      this.voiceName = voice;
      this.woke = requestUrl.searchParams.get("woke") || "";

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

  /**
   * つなぎ言葉を鳴らす。
   *
   * 発話終了(audioStreamEnd)から Gemini の応答が返るまでは実測1.3秒あり、
   * その間ロボットは完全に沈黙する。会話としてはこの無音が一番不自然なので、
   * 「えーっと」を先に返して間を埋める。
   *
   * ここはDOなので、クライアントから audioStreamEnd が届いた時点で
   * ネットワーク往復ぶん(数十ms)だけで鳴らし始められる。音源は本編と同じ
   * 声で作ってあるため、別の何かが割り込んだようには聞こえない。
   *
   * @param pcmRate PCMモードの送信レート。0 なら素通しモード。
   */
  sendFiller(ws: WebSocket, pcmRate: number) {
    if (FILLERS_B64.length === 0) {
      return;
    }

    /*
     * 声が違うなら鳴らさない。
     *
     * 音源は FILLER_VOICE 固定で焼いてあるので、クライアントが ?voice= で別の
     * 声を指定してくると、つなぎ言葉だけ別人が喋る。沈黙のほうがまだ自然。
     * tuner.html で声を比べているときにこれが効く。
     */
    if (this.voiceName !== FILLER_VOICE) {
      return;
    }

    // 同じ語が続くと機械的に聞こえるので、直前と違うものを選ぶ
    let index = Math.floor(Math.random() * FILLERS_B64.length);
    if (index === this.lastFiller && FILLERS_B64.length > 1) {
      index = (index + 1) % FILLERS_B64.length;
    }
    this.lastFiller = index;

    const phrase = FILLER_INFO[index]?.phrase ?? "";

    try {
      if (pcmRate > 0) {
        // つなぎ言葉であることを先に知らせる。マイコンは今のところ無視するが、
        // 応答遅延の計測やログでこれを見分けられるようにしておく。
        ws.send(JSON.stringify({ _filler: phrase }));
        sendAudioChunked(ws, fillersAt(pcmRate)[index]);
        return;
      }

      // 素通しモード(wrapper.py / シミュレーター)は Gemini の生の形しか
      // 解釈しないので、同じ形に包んで渡す。レート変換も不要。
      ws.send(JSON.stringify({
        _filler: phrase,
        serverContent: {
          modelTurn: {
            parts: [{
              inlineData: {
                mimeType: `audio/pcm;rate=${FILLER_RATE}`,
                data: FILLERS_B64[index],
              },
            }],
          },
        },
      }));
    } catch (e) {
      // つなぎ言葉が出せなくても会話自体は続けられる。落とさない。
      console.error("Filler send error:", e);
    }
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
          // PCMモードでは「バイナリ=音声」をクライアントの唯一の判定基準にする。
          // JSONでないものもテキストで渡し、バイナリ枠を音声専用に保つ。
          // (PCMデータの先頭バイトがたまたま '{' になることは普通に起きるため、
          //  中身を覗いて振り分ける方式は成立しない)
          serverWs.send(text);
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
                sendAudioChunked(serverWs, out);
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

        // 発話終了の合図が通ったら、応答を待たずにつなぎ言葉を返す。
        // Gemini への転送を先に済ませてから鳴らすこと（応答生成の開始を
        // 1msでも遅らせない）。
        if (typeof event.data === "string" && event.data.includes("audioStreamEnd")) {
          this.sendFiller(serverWs, pcmMode ? pcmRate : 0);
        }
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
          parts: [{ text: buildSystemInstruction(this.woke) }]
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
