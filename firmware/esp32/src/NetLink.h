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
    /**
     * 受信を待たせる（true の間は ws.loop() を回さない）。
     * ソケットから読まなければ TCP の窓が埋まってサーバー側が送るのを待つ。再生キューが満杯に
     * 近いとき main loop が立てる（長い返事は実時間より速く届くので、捨てずに向こうで持たせる）。
     */
    void holdReceive(bool hold);

    // --- Wi-Fi 資格情報 (NVSへ永続化) ---
    //
    // 最新5件まで保存する（自宅とスマホテザリングの併用のため）。
    // 一覧は「新しい順」で持ち、6件目を登録すると最も古い1件が押し出される。
    // 接続に成功したSSIDも先頭へ繰り上がる（=よく使うものが残る）。

    /** SSIDを一覧の先頭に追加する。既存の同名SSIDは先頭へ移動（パスワード維持）。 */
    void setSsid(const char* ssid);
    /** 直前に setSsid したSSID（一覧の先頭）にパスワードを設定する。 */
    void setPassword(const char* pass);
    /** SSIDとパスワードをまとめて登録する（設定ポータル用）。 */
    void addCredential(const char* ssid, const char* pass);
    /** 指定SSIDを一覧から削除する。無ければ false。 */
    bool removeCredential(const char* ssid);
    /** 保存したWi-Fi設定を全て消す。 */
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

    /**
     * 保存済みのWi-Fiへ接続する。
     *
     * 2件以上あるときは先にスキャンし、見えている保存済みSSIDを電波の強い順に
     * 試す。スキャンに映らなかった保存分（名前を隠したAP）も最後に試す。
     * timeoutMs は「1候補あたり」の上限。駄目な候補は理由コードで数秒で
     * 打ち切られるので、全滅でも timeoutMs×件数 まで待つことは普通はない。
     */
    bool wifiConnect(uint32_t timeoutMs = 20000, WaitHook onWait = nullptr);

    /*
     * 直近の接続失敗の理由。
     *
     * status だけでは「パスワードが違う」と「電波が届いていない」を区別できず、
     * 切断理由コードを見るのが唯一の切り分けになる。どちらも再試行では直らない
     * ので、設定モードへ渡す判断と、画面に出す文言の選択に使う。
     */

    /** 直近の wifiConnect() で「パスワードが違う」候補が1つでもあったか。 */
    bool lastFailureWasAuth() const;
    /**
     * 直近の wifiConnect() で試した全候補が「電波に出ていない」だったか。
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
     * 完全に止めたい場合は wifiStop()。かつて「WIFI_OFF はI2S/コーデックを殺す」と
     * 記録していたが誤りで、単独では起きない（main.cpp の `powerWifiOff` を参照）。
     */
    void wifiDisconnect();

    /**
     * 無線を完全に止める（`esp_wifi_stop()` まで）。消費電流はこちらが小さい。
     *
     * 疑似電源OFFでここまで落とすかは main.cpp の `powerWifiOff`（既定 false）。
     * シリアル `wifistop` から直接叩ける（15秒は自動接続を止めて保持する）。
     */
    void wifiStop();

    bool wifiConnected() const;

    // --- WebSocket ---
    void wsConnect();
    /**
     * 次の接続で KATANORI_WS_PATH の後ろに足すクエリ（"&woke=sleep" など）。空で足さない。
     * サーバーは会話の始まり方を Gemini への指示に足す（katanori-backend の wokeInstruction）。
     */
    void setConnectTag(const char* tag) { connectTag_ = tag ? tag : ""; }
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
    String connectTag_;
    String wsPath_;  // beginSsl に渡した道。ライブラリが参照し続けるので保持する
    static constexpr int kMaxCreds = 5;

    struct Cred {
        String ssid;
        String pass;
    };

    /** 一覧全体をNVSへ書き戻す。 */
    void persist();
    /** 同名SSIDを先頭へ移動（無ければ先頭へ追加、あふれた最古は削除）。 */
    void upsertFront(const char* ssid);
    void moveToBack(const String& ssid);
    /** creds_[idx] へ1回だけ接続を試す。 */
    bool tryConnectOne(int idx, uint32_t timeoutMs, WaitHook onWait);

    Cred creds_[kMaxCreds]; // 新しい順
    int credCount_ = 0;

    // 直近の wifiConnect() の失敗内容の集計。候補が複数になったので、
    // 「どれか1つでパスワード誤り」「全候補が圏外」を区別して持つ。
    bool anyAuthFail_ = false;
    bool allNoAp_ = false;
};

extern NetLink netLink;

} // namespace katanori

#endif // KATANORI_NET_LINK_H
