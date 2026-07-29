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

    /**
     * 接続の待ち中に呼ばれる関数。顔を描き続けるために使う。
     *
     * wifiConnect() は繋がるまで戻らない。渡さないと、その十数秒のあいだ
     * main loop ごと止まって画面が固まる（利用者からは故障に見える）。
     */
    using WaitHook = void (*)();

    bool wifiConnect(uint32_t timeoutMs = 20000, WaitHook onWait = nullptr);

    /*
     * 直近の接続失敗の理由。
     *
     * status だけでは「パスワードが違う」と「電波が届いていない」を区別できず、
     * 切断理由コードを見るのが唯一の切り分けになる。どちらも再試行では直らない
     * ので、設定モードへ渡す判断と、画面に出す文言の選択に使う。
     */

    /** 直近の切断理由が「パスワードが違う」を指しているか。 */
    bool lastFailureWasAuth() const;
    /**
     * 直近の切断理由が「そのSSIDが電波に出ていない」を指しているか。
     *
     * 引っ越し・ルーター交換で保存済みSSIDが消えた場合がこれ。スキャンで
     * 一覧を取って判断する手もあるが、名前を隠したAPが1つでも近くにあると
     * 「一覧に無い＝存在しない」と言えなくなる（実測でそうなった）。
     * 接続を試したうえでの理由コードのほうが確かで、しかも速い（約2.5秒）。
     */
    bool lastFailureWasNoAp() const;
    /**
     * APから離れる。無線そのもの（STAモード）は生かしたままにする。
     *
     * **WIFI_OFF まで落としてはいけない。** コーデックの設定が初期値へ飛び、
     * USBを抜き差しするまで音が戻らなくなる（2026-07-30 実測。ESP32の再起動では
     * 直らない ＝ 壊れているのはI2Sではなくコーデック）。詳細は main.cpp の
     * `powerWifiOff` と docs/TODO.md 2.5。
     */
    void wifiDisconnect();

    /**
     * 無線を完全に止める（`esp_wifi_stop()` まで）。消費電流はこちらが小さい。
     *
     * これでI2Sが巻き添えになるかどうかを確かめるための口。詳細は
     * wifiDisconnect() のコメントと docs/TODO.md 2.5。
     */
    void wifiStop();

    bool wifiConnected() const;

    // --- WebSocket ---
    void wsConnect();
    void wsDisconnect();
    bool wsConnected() const;
    /**
     * 音声を送り始めてよいか。
     *
     * WebSocketが繋がった時点ではまだ Gemini の setup が終わっておらず、
     * 送った音声は捨てられる。録音開始の判断はこちらを使うこと。
     */
    bool wsReady() const;

    /** 現在の状態をまとめてシリアルへ出す。 */
    void printStatus() const;

private:
    String ssid_;
    String pass_;
};

extern NetLink netLink;

} // namespace katanori

#endif // KATANORI_NET_LINK_H
