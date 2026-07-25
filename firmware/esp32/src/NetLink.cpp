#include "NetLink.h"

#include <WiFi.h>
#include <Preferences.h>
#include <WebSocketsClient.h>

namespace katanori {

namespace {

Preferences prefs;
WebSocketsClient ws;

const char* kPrefNamespace = "katanori";
const char* kKeySsid = "ssid";
const char* kKeyPass = "pass";

// 「張りにいっている / 張っている」状態か。
// ライブラリは既定で自動再接続するが、DOはクライアント接続と同時にGeminiへ
// 繋ぐため、放置すると再接続のたびにGeminiのセッションを消費してしまう。
// このフラグが false の間は ws.loop() を回さないことで自動再接続を止める。
bool wantConnected = false;
bool connected = false;
uint32_t connectStartedMs = 0;

/** wl_status_t を読める名前にする。数値だけ出しても原因が分からないため。 */
const char* wifiStatusName(int s) {
    switch (s) {
    case WL_IDLE_STATUS:     return "IDLE (待機中)";
    case WL_NO_SSID_AVAIL:   return "NO_SSID_AVAIL (SSIDが見つからない)";
    case WL_SCAN_COMPLETED:  return "SCAN_COMPLETED";
    case WL_CONNECTED:       return "CONNECTED (接続済み)";
    case WL_CONNECT_FAILED:  return "CONNECT_FAILED (認証失敗)";
    case WL_CONNECTION_LOST: return "CONNECTION_LOST (接続喪失)";
    case WL_DISCONNECTED:    return "DISCONNECTED (切断/認証拒否)";
    default:                 return "UNKNOWN";
    }
}

/**
 * 切断理由コード。status だけでは「パスワード誤り」と「電波が弱い」を
 * 区別できないため、これを見るのが唯一の確実な切り分けになる。
 */
const char* disconnectReasonName(uint8_t r) {
    switch (r) {
    case 2:   return "AUTH_EXPIRE (認証の期限切れ)";
    case 4:   return "ASSOC_EXPIRE";
    case 15:  return "4WAY_HANDSHAKE_TIMEOUT (ほぼパスワード誤り)";
    case 16:  return "GROUP_KEY_UPDATE_TIMEOUT";
    case 23:  return "802_1X_AUTH_FAILED";
    case 24:  return "CIPHER_SUITE_REJECTED (暗号方式の不一致)";
    case 200: return "BEACON_TIMEOUT (電波が届いていない)";
    case 201: return "NO_AP_FOUND (APを見つけられない=電波が弱い)";
    case 202: return "AUTH_FAIL (認証失敗=パスワード誤り)";
    case 203: return "ASSOC_FAIL (アソシエーション失敗)";
    case 204: return "HANDSHAKE_TIMEOUT (パスワード誤りか電波が弱い)";
    default:  return "";
    }
}

uint8_t lastDisconnectReason = 0;

void onWifiEvent(arduino_event_id_t event, arduino_event_info_t info) {
    if (event == ARDUINO_EVENT_WIFI_STA_DISCONNECTED) {
        uint8_t r = info.wifi_sta_disconnected.reason;
        if (r != lastDisconnectReason) {
            lastDisconnectReason = r;
            Serial.printf("[NET] 切断理由: %u %s\n", r, disconnectReasonName(r));
        }
    }
}

/** 受信テキストにマーカーが含まれるかを見るだけの軽量チェック。
 *  Stage 2 では JSON パーサを積まない (音声を扱う Stage 3 で検討する)。 */
bool contains(const uint8_t* payload, size_t length, const char* needle) {
    if (payload == nullptr || length == 0) {
        return false;
    }
    size_t nLen = strlen(needle);
    if (nLen == 0 || length < nLen) {
        return false;
    }
    for (size_t i = 0; i + nLen <= length; ++i) {
        if (memcmp(payload + i, needle, nLen) == 0) {
            return true;
        }
    }
    return false;
}

void onWsEvent(WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
    case WStype_CONNECTED:
        connected = true;
        Serial.printf("[WS] 接続しました (%.1f秒)\n",
                      (millis() - connectStartedMs) / 1000.0f);
        Serial.println("[WS] Geminiの setupComplete を待っています...");
        break;

    case WStype_DISCONNECTED:
        if (connected || wantConnected) {
            Serial.println("[WS] 切断されました");
        }
        connected = false;
        // 自動再接続を止める (Geminiのセッション浪費を防ぐ)
        if (wantConnected) {
            wantConnected = false;
            ws.disconnect();
            Serial.println("[WS] 再接続はしません。もう一度繋ぐには 'c' を打ってください");
        }
        break;

    // Gemini Live API は応答を「バイナリフレーム」で返してくる。中身はJSONテキスト。
    // (wrapper.py では Python の websockets が bytes/str を透過的に扱うため
    //  気づかなかったが、実機では両方を同じように読む必要がある)
    case WStype_TEXT:
    case WStype_BIN: {
        const char* kind = (type == WStype_TEXT) ? "TEXT" : "BIN";

        if (contains(payload, length, "setupComplete")) {
            Serial.println("[WS] ★ setupComplete 受信 — Geminiまで疎通しました");
        }
        // DOが送ってくるデバッグ情報 (Gemini側のエラーはここに出る)
        size_t preview = length < 300 ? length : 300;
        Serial.printf("[WS] %s %ubytes: %.*s%s\n",
                      kind, (unsigned)length, (int)preview, (const char*)payload,
                      length > preview ? " ..." : "");
        break;
    }

    case WStype_ERROR:
        Serial.printf("[WS] エラー: %.*s\n", (int)length, (const char*)payload);
        break;

    default:
        break;
    }
}

} // namespace

NetLink netLink;

void NetLink::begin() {
    prefs.begin(kPrefNamespace, /* readOnly= */ true);
    ssid_ = prefs.getString(kKeySsid, "");
    pass_ = prefs.getString(kKeyPass, "");
    prefs.end();

    WiFi.mode(WIFI_STA);
    WiFi.onEvent(onWifiEvent);
    ws.onEvent(onWsEvent);

    if (hasCredentials()) {
        Serial.printf("[NET] 保存済みのWi-Fi設定: SSID=\"%s\"\n", ssid_.c_str());
    } else {
        Serial.println("[NET] Wi-Fi未設定です。'ssid <名前>' と 'pass <パスワード>' で設定してください");
    }
}

void NetLink::loop() {
    if (wantConnected) {
        ws.loop();
    }
}

void NetLink::setSsid(const char* ssid) {
    ssid_ = ssid;
    prefs.begin(kPrefNamespace, false);
    prefs.putString(kKeySsid, ssid_);
    prefs.end();
    Serial.printf("[NET] SSIDを保存しました: \"%s\"\n", ssid_.c_str());
}

void NetLink::setPassword(const char* pass) {
    pass_ = pass;
    prefs.begin(kPrefNamespace, false);
    prefs.putString(kKeyPass, pass_);
    prefs.end();
    // パスワードは表示しない
    Serial.printf("[NET] パスワードを保存しました (%d文字)\n", pass_.length());
}

void NetLink::clearCredentials() {
    ssid_ = "";
    pass_ = "";
    prefs.begin(kPrefNamespace, false);
    prefs.clear();
    prefs.end();
    Serial.println("[NET] Wi-Fi設定を消去しました");
}

bool NetLink::hasCredentials() const {
    return ssid_.length() > 0;
}

bool NetLink::wifiConnected() const {
    return WiFi.status() == WL_CONNECTED;
}

bool NetLink::wifiConnect(uint32_t timeoutMs) {
    if (!hasCredentials()) {
        Serial.println("[NET] SSIDが未設定です。'ssid <名前>' から設定してください");
        return false;
    }
    if (wifiConnected()) {
        Serial.println("[NET] すでに接続済みです");
        return true;
    }

    Serial.printf("[NET] \"%s\" へ接続します...\n", ssid_.c_str());
    lastDisconnectReason = 0;
    WiFi.begin(ssid_.c_str(), pass_.c_str());

    uint32_t start = millis();
    while (WiFi.status() != WL_CONNECTED && (millis() - start) < timeoutMs) {
        delay(200);
    }

    if (!wifiConnected()) {
        int st = WiFi.status();
        Serial.printf("[NET] 接続できませんでした: %s (status=%d)\n", wifiStatusName(st), st);
        if (pass_.length() > 0 && pass_.length() < 8) {
            Serial.printf("[NET] !! パスワードが%d文字です。WPA/WPA2/WPA3のパスフレーズは\n",
                          pass_.length());
            Serial.println("[NET]    8〜63文字と規格で決まっており、これでは接続できません。");
        }
        if (lastDisconnectReason != 0) {
            Serial.printf("[NET] 切断理由: %u %s\n",
                          lastDisconnectReason, disconnectReasonName(lastDisconnectReason));
        }
        Serial.println("[NET]   'scan' で該当SSIDが見えているか確認してください");
        Serial.println("[NET]   ESP32は2.4GHz帯のみです。5GHz専用のSSIDには繋がりません");
        return false;
    }

    Serial.printf("[NET] 接続しました  IP=%s  RSSI=%ddBm  (%.1f秒)\n",
                  WiFi.localIP().toString().c_str(), WiFi.RSSI(),
                  (millis() - start) / 1000.0f);
    return true;
}

void NetLink::scan() {
    Serial.println("[NET] 2.4GHz帯をスキャンします...");
    int n = WiFi.scanNetworks();
    if (n <= 0) {
        Serial.println("[NET] APが1つも見つかりませんでした");
        WiFi.scanDelete();
        return;
    }

    Serial.printf("[NET] %d件:\n", n);
    for (int i = 0; i < n; ++i) {
        const char* enc;
        switch (WiFi.encryptionType(i)) {
        case WIFI_AUTH_OPEN:            enc = "OPEN"; break;
        case WIFI_AUTH_WEP:             enc = "WEP"; break;
        case WIFI_AUTH_WPA_PSK:         enc = "WPA"; break;
        case WIFI_AUTH_WPA2_PSK:        enc = "WPA2"; break;
        case WIFI_AUTH_WPA_WPA2_PSK:    enc = "WPA/WPA2"; break;
        case WIFI_AUTH_WPA3_PSK:        enc = "WPA3"; break;
        case WIFI_AUTH_WPA2_WPA3_PSK:   enc = "WPA2/WPA3"; break;
        default:                        enc = "?"; break;
        }
        bool isTarget = (ssid_.length() > 0 && WiFi.SSID(i) == ssid_);
        Serial.printf("  %s %-32s ch%-3d %4ddBm  %s\n",
                      isTarget ? "->" : "  ",
                      WiFi.SSID(i).c_str(), WiFi.channel(i), WiFi.RSSI(i), enc);
    }
    WiFi.scanDelete();

    if (ssid_.length() > 0) {
        Serial.printf("[NET] 設定中のSSID \"%s\" が上の一覧に -> 付きで居れば電波は届いています\n",
                      ssid_.c_str());
    }
}

void NetLink::wifiDisconnect() {
    wsDisconnect();
    WiFi.disconnect();
    Serial.println("[NET] Wi-Fiを切断しました");
}

void NetLink::wsConnect() {
    if (!wifiConnected()) {
        Serial.println("[WS] 先にWi-Fiへ接続してください ('wifi')");
        return;
    }
    if (wantConnected) {
        Serial.println("[WS] すでに接続処理中です");
        return;
    }

    Serial.printf("[WS] wss://%s:%d%s へ接続します\n",
                  KATANORI_WS_HOST, KATANORI_WS_PORT, KATANORI_WS_PATH);

    // TODO(Stage 4): サーバ証明書を検証していない。fingerprint に NULL を渡すと
    // ライブラリ内部で setInsecure() が呼ばれ、中間者攻撃を検出できなくなる。
    // 出荷前に beginSslWithCA() でルート証明書を渡すか、証明書バンドルを積むこと。
    Serial.println("[WS] !! 警告: TLSサーバ証明書を検証していません (Stage 2の暫定実装)");

    wantConnected = true;
    connectStartedMs = millis();
    ws.beginSSL(KATANORI_WS_HOST, KATANORI_WS_PORT, KATANORI_WS_PATH);
}

void NetLink::wsDisconnect() {
    if (!wantConnected && !connected) {
        return;
    }
    wantConnected = false;
    connected = false;
    ws.disconnect();
    Serial.println("[WS] 切断しました");
}

bool NetLink::wsConnected() const {
    return connected;
}

void NetLink::printStatus() const {
    Serial.println("--- ネットワーク状態 ---");
    Serial.printf("  Wi-Fi設定 : %s\n",
                  hasCredentials() ? ssid_.c_str() : "(未設定)");
    if (wifiConnected()) {
        Serial.printf("  Wi-Fi     : 接続中  IP=%s  RSSI=%ddBm\n",
                      WiFi.localIP().toString().c_str(), WiFi.RSSI());
    } else {
        Serial.printf("  Wi-Fi     : 未接続 (status=%d)\n", WiFi.status());
    }
    Serial.printf("  WebSocket : %s\n",
                  connected ? "接続中" : (wantConnected ? "接続処理中" : "未接続"));
    Serial.printf("  接続先    : wss://%s%s\n", KATANORI_WS_HOST, KATANORI_WS_PATH);
    Serial.printf("  空きヒープ: %uB\n", ESP.getFreeHeap());
    Serial.println("------------------------");
}

} // namespace katanori
