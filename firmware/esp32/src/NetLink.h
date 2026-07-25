/*
 * ============================================================================
 *  NetLink - Wi-Fi と Durable Object への WebSocket 接続
 *
 *  Stage 2: 音声はまだ流さない。接続してGeminiの setupComplete が返るまでを
 *  シリアルログで検証するための層。
 *
 *  設計方針:
 *   - Wi-Fi 資格情報は NVS(Preferences) に保存する。ソースにもgitにも残さない。
 *   - WebSocket は「使うときだけ張る」。DOはクライアント接続と同時にGeminiへ
 *     繋ぎにいくため、常時接続や自動再接続はGeminiのセッションを浪費する。
 *     (wrapper.py が実測で確認した挙動: 無通信のセッションは約2分で切られる)
 * ============================================================================
 */

#ifndef KATANORI_NET_LINK_H
#define KATANORI_NET_LINK_H

#include <Arduino.h>

// 接続先。既にデプロイ済みの Cloudflare Durable Object。
#ifndef KATANORI_WS_HOST
#define KATANORI_WS_HOST "katanori-backend.tobira-sys.workers.dev"
#endif
#ifndef KATANORI_WS_PORT
#define KATANORI_WS_PORT 443
#endif
// 1にするとTLSサーバ証明書を検証しない。ピン留めしたCAが古くなって
// 接続できなくなったときの緊急避難用で、常用してはいけない。
#ifndef KATANORI_TLS_INSECURE
#define KATANORI_TLS_INSECURE 0
#endif

// ?pcm=16000 で「音声=バイナリ / 制御=テキスト」モードになる。
// base64もJSON組み立ても不要になり、24k->16k変換もDO側で済ませてくれる。
#ifndef KATANORI_WS_PATH
#define KATANORI_WS_PATH "/?voice=Achird&pcm=16000"
#endif

namespace katanori {

class NetLink {
public:
    /** DOから届いた音声（生PCM）。バイナリフレームで来る。 */
    using AudioSink = void (*)(const int16_t* pcm, size_t samples);
    /** DOから届いた制御JSON（文字列, NUL終端済み）。 */
    using ControlSink = void (*)(const char* json);

    /** NVSから資格情報を読み出す。接続はしない。 */
    void begin();

    void setAudioSink(AudioSink fn);
    void setControlSink(ControlSink fn);

    /** 録音した生PCMをバイナリフレームで送る。 */
    bool sendAudio(const int16_t* pcm, size_t samples);
    /** 制御JSONをテキストフレームで送る（DOはGeminiへ素通しする）。 */
    bool sendControl(const char* json);

    /** WebSocketのポンプ。loop() から毎回呼ぶこと。 */
    void loop();

    // --- Wi-Fi 資格情報 (NVSへ永続化) ---
    void setSsid(const char* ssid);
    void setPassword(const char* pass);
    void clearCredentials();
    bool hasCredentials() const;

    // --- Wi-Fi ---
    /** 周囲のAPを一覧表示する。SSIDの綴りと電波の有無を切り分ける。 */
    void scan();

    bool wifiConnect(uint32_t timeoutMs = 20000);
    void wifiDisconnect();
    bool wifiConnected() const;

    // --- WebSocket ---
    void wsConnect();
    void wsDisconnect();
    bool wsConnected() const;

    /** 現在の状態をまとめてシリアルへ出す。 */
    void printStatus() const;

private:
    String ssid_;
    String pass_;
};

extern NetLink netLink;

} // namespace katanori

#endif // KATANORI_NET_LINK_H
