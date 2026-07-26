/*
 * ============================================================================
 *  Provisioning - APモード + キャプティブポータルによる Wi-Fi 設定
 *
 *  仕様書3章。初回起動時（Wi-Fi未設定時）に自身がアクセスポイントとなり、
 *  スマホから設定画面を開いて自宅のWi-Fi情報を入力してもらう。
 *
 *  保存先は NetLink と同じ NVS。設定を受け取ったら再起動して通常モードで繋ぐ。
 *
 *  【承知のうえの割り切り】設定用APは開放（暗号化なし）で、ページもHTTP。
 *  つまり入力されたWi-Fiパスワードは設定中の数分間、近くの第三者から
 *  傍受されうる。市販IoT機器でも一般的な方式だが、これは弱点である。
 * ============================================================================
 */

#ifndef KATANORI_PROVISIONING_H
#define KATANORI_PROVISIONING_H

#include <Arduino.h>
#include <IPAddress.h>

// 設定用APの名前。QRに載せる文字列長がQRの誤り訂正レベルを左右する。
//   "katanori-setup" -> 32バイト -> Version2 は誤り訂正L のみ
//   "katanori"       -> 26バイト -> Version2 で誤り訂正M が使える（読み取りに有利）
// 実機でスキャンが不安定なら短いほうへ切り替える。
#ifndef KATANORI_AP_SSID
#define KATANORI_AP_SSID "katanori-setup"
#endif

namespace katanori {

class Provisioning {
public:
    enum class Phase {
        WAITING,   // AP起動済み、スマホの接続待ち
        CONNECTED, // スマホが繋がった
        SAVED,     // 設定を受け取った（まもなく再起動）
    };

    /** APとDNS、Webサーバを起動する。 */
    bool begin();
    /** DNSとHTTPのポンプ。main loop から毎回呼ぶ。 */
    void loop();
    void stop();

    bool active() const { return active_; }
    Phase phase() const { return phase_; }

    const char* apSsid() const { return KATANORI_AP_SSID; }
    IPAddress apIp() const;

    /** スマホのカメラで読ませるWi-Fi接続用QRの中身。 */
    const char* wifiQrPayload() const { return qrPayload_; }

    /** 画面に出す1行のステータス。 */
    const char* statusText() const;

private:
    bool active_ = false;
    Phase phase_ = Phase::WAITING;
    uint32_t savedAtMs_ = 0;
    char qrPayload_[64] = {0};
};

extern Provisioning provisioning;

} // namespace katanori

#endif // KATANORI_PROVISIONING_H
