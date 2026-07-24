export interface Env {
  ROBOT_DO: DurableObjectNamespace;
  GEMINI_API_KEY: string;
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
      
      this.connectToGemini(server).catch(e => {
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

  async connectToGemini(serverWs: WebSocket) {
    this.dbg(serverWs, "DO fetch ok, connecting to Gemini...");

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
    geminiWs.addEventListener("message", (event) => {
      try {
        const preview = typeof event.data === "string"
          ? event.data.slice(0, 200)
          : `<binary ${ (event.data as ArrayBuffer).byteLength } bytes>`;
        console.log("[DO] Gemini -> client:", preview);
        serverWs.send(event.data);
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
    serverWs.addEventListener("message", (event) => {
      try {
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
        model: "models/gemini-2.5-flash-native-audio-preview-12-2025",
        systemInstruction: {
          parts: [{ text: "あなたはカタノリロボです。親しみやすく短い返答をしてください。" }]
        },
        generationConfig: {
          responseModalities: ["AUDIO"]
        }
      }
    };
    geminiWs.send(JSON.stringify(setupMsg));
  }
}
