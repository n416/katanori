#include "NetLink.h"

#include <WiFi.h>
#include <Preferences.h>
#include <WebSocketsClient.h>

#include "RootCa.h"
#include "Console.h" // 最後に置く（Serial を Wi-Fi モニタへも流す差し替え。Console.h）

namespace katanori {

namespace {

Preferences prefs;
WebSocketsClient ws;

const char* kPrefNamespace = "katanori";
// 旧形式（1件だけ保存）のキー。読み出せたら新形式へ移行して消す。
const char* kKeyLegacySsid = "ssid";
const char* kKeyLegacyPass = "pass";
// 新形式: 件数 + スロット別キー "s0".."s4" / "p0".."p4"（新しい順）
const char* kKeyCredCount = "wifin";

void slotKeys(int i, char* sk, char* pk) {
    snprintf(sk, 8, "s%d", i);
    snprintf(pk, 8, "p%d", i);
}

// 「張りにいっている / 張っている」状態か。
// ライブラリは既定で自動再接続するが、DOはクライアント接続と同時にGeminiへ
// 繋ぐため、放置すると再接続のたびにGeminiのセッションを消費してしまう。
// このフラグが false の間は ws.loop() を回さないことで自動再接続を止める。
bool wantConnected = false;
bool connected = false;
uint32_t connectStartedMs = 0;

// Geminiの setupComplete を受け取ったか。
// WebSocketが繋がっただけでは音声を送っても捨てられる。録音を始めてよいかの
// 判断はこちらを見ること。
bool geminiReady = false;

NetLink::AudioSink audioSink = nullptr;
NetLink::ControlSink controlSink = nullptr;

// 制御JSONを NUL 終端して渡すための作業領域。
// 音声はバイナリで来るので、テキスト側が巨大になることはない。
constexpr size_t CONTROL_BUF = 1024;
char controlBuf[CONTROL_BUF];

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

uint8_t lastReason = 0;

/**
 * これ以上待っても結果が変わらない切断理由か。
 *
 * 接続待ちを打ち切ってよいかの判断だけに使う。「なぜ駄目だったか」の分類は
 * 呼び出し側（lastFailureWasAuth / lastFailureWasNoAp）が別に行う。
 */
bool isConclusiveFailure(uint8_t r) {
    switch (r) {
    case 15:  // 4WAY_HANDSHAKE_TIMEOUT
    case 23:  // 802_1X_AUTH_FAILED
    case 24:  // CIPHER_SUITE_REJECTED
    case 201: // NO_AP_FOUND
    case 202: // AUTH_FAIL
    case 204: // HANDSHAKE_TIMEOUT
        return true;
    default:
        return false;
    }
}

void onWifiEvent(arduino_event_id_t event, arduino_event_info_t info) {
    if (event == ARDUINO_EVENT_WIFI_STA_DISCONNECTED) {
        uint8_t r = info.wifi_sta_disconnected.reason;
        if (r != lastReason) {
            lastReason = r;
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

void handleControl(const uint8_t* payload, size_t length) {
    if (contains(payload, length, "setupComplete")) {
        geminiReady = true;
        Serial.println("[WS] ★ setupComplete 受信 — Geminiまで疎通しました");
    }

    size_t n = length < CONTROL_BUF - 1 ? length : CONTROL_BUF - 1;
    memcpy(controlBuf, payload, n);
    controlBuf[n] = '\0';

    Serial.printf("[WS] %s%s\n", controlBuf, length > n ? " ..." : "");

    if (controlSink != nullptr) {
        controlSink(controlBuf);
    }
}

// 受信統計。音声が本当に届いているのかを切り分けるため。
uint32_t binFrames = 0;
uint32_t binBytes = 0;
uint32_t textFrames = 0;

void onWsEvent(WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
    case WStype_CONNECTED:
        connected = true;
        geminiReady = false; // setupComplete はこの後に来る
        binFrames = 0;
        binBytes = 0;
        textFrames = 0;
        Serial.printf("[WS] 接続しました (%.1f秒)\n",
                      (millis() - connectStartedMs) / 1000.0f);
        Serial.println("[WS] Geminiの setupComplete を待っています...");
        break;

    case WStype_DISCONNECTED:
        if (connected || wantConnected) {
            Serial.printf("[WS] 切断されました  受信: BIN %u件/%uB  TEXT %u件  "
                          "wifi=%d heap=%uB\n",
                          binFrames, binBytes, textFrames,
                          WiFi.status(), ESP.getFreeHeap());
#if !KATANORI_TLS_INSECURE
            // 一度も繋がらないまま切れた場合、TLS検証の失敗が最有力。
            // 沈黙のまま繋がらないと原因が分からなくなるので明示する。
            if (!connected) {
                Serial.println("[WS] 一度も接続できていません。TLS証明書の検証に");
                Serial.println("[WS] 失敗した可能性があります。接続先が発行元CAを変更した");
                Serial.println("[WS] 場合は src/RootCa.h の更新が必要です。");
                Serial.println("[WS] 暫定回避: build_flags に -DKATANORI_TLS_INSECURE=1");
            }
#endif
        }
        connected = false;
        geminiReady = false;
        // 自動再接続を止める (Geminiのセッション浪費を防ぐ)
        if (wantConnected) {
            wantConnected = false;
            ws.disconnect();
            Serial.println("[WS] 再接続はしません。もう一度繋ぐには 'c' を打ってください");
        }
        break;

    // PCMモードでは バイナリ=音声 / テキスト=制御 に分離されている。
    // ただしDOの _debug や、素通しになった非JSONはバイナリで来る場合があるので、
    // 先頭が '{' ならJSONとして扱う。
    case WStype_BIN: {
        ++binFrames;
        binBytes += length;
        if (binFrames <= 5) {
            Serial.printf("[WS] BIN #%u %uB\n", binFrames, (unsigned)length);
        }
        // PCMモードではバイナリは必ず音声。中身を覗いて振り分けてはいけない。
        // PCMデータの先頭バイトがたまたま '{' (0x7B) になることは普通に起きる。
        // 実機で1フレーム誤判定して音が欠けた。DO側で制御は必ずテキストにしてある。
        if (audioSink != nullptr) {
            audioSink(reinterpret_cast<const int16_t*>(payload), length / 2);
        }
        break;
    }

    case WStype_TEXT:
        ++textFrames;
        handleControl(payload, length);
        break;

    // 大きなメッセージが分割されて届く場合。ここに落ちていると音声が
    // まったく処理されないので、検出できるようにしておく。
    case WStype_FRAGMENT_TEXT_START:
    case WStype_FRAGMENT_BIN_START:
    case WStype_FRAGMENT:
    case WStype_FRAGMENT_FIN:
        Serial.printf("[WS] !! 分割フレーム(type=%d, %uB) — 未対応です\n",
                      (int)type, (unsigned)length);
        break;

    case WStype_PING:
    case WStype_PONG:
        break;

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
    // 移行の書き込みがあり得るので read-write で開く
    if (!prefs.begin(kPrefNamespace, /* readOnly= */ false)) {
        Serial.println("[NET] !! NVSを開けませんでした。Wi-Fi設定を読めません");
    }

    credCount_ = 0;
    int n = prefs.getInt(kKeyCredCount, 0);
    Serial.printf("[NET] NVS読込: 件数キー=%d\n", n);
    if (n > kMaxCreds) {
        n = kMaxCreds;
    }
    char sk[8], pk[8];
    for (int i = 0; i < n; ++i) {
        slotKeys(i, sk, pk);
        String s = prefs.getString(sk, "");
        if (s.length() == 0) {
            continue;
        }
        creds_[credCount_].ssid = s;
        creds_[credCount_].pass = prefs.getString(pk, "");
        ++credCount_;
    }

    // 旧形式（ssid/pass 1件だけ）からの移行。既存の機体を設定し直させないため。
    if (credCount_ == 0 && prefs.isKey(kKeyLegacySsid)) {
        String s = prefs.getString(kKeyLegacySsid, "");
        if (s.length() > 0) {
            creds_[0].ssid = s;
            creds_[0].pass = prefs.getString(kKeyLegacyPass, "");
            credCount_ = 1;
            slotKeys(0, sk, pk);
            prefs.putInt(kKeyCredCount, 1);
            prefs.putString(sk, creds_[0].ssid);
            prefs.putString(pk, creds_[0].pass);
            Serial.printf("[NET] 旧形式のWi-Fi設定を移行しました: \"%s\"\n", s.c_str());
        }
        prefs.remove(kKeyLegacySsid);
        prefs.remove(kKeyLegacyPass);
    }
    prefs.end();

    WiFi.mode(WIFI_STA);
    WiFi.onEvent(onWifiEvent);
    ws.onEvent(onWsEvent);

    if (hasCredentials()) {
        Serial.printf("[NET] 保存済みのWi-Fi設定: %d件（最新: \"%s\"）\n",
                      credCount_, creds_[0].ssid.c_str());
    } else {
        Serial.println("[NET] Wi-Fi未設定です。'ssid <名前>' と 'pass <パスワード>' で設定してください");
    }
}

void NetLink::loop() {
    if (!wantConnected) {
        return;
    }
    // 応答音声は 4KB × 100フレーム規模がまとめて届く。OLEDの全面転送(約29ms)で
    // main loop が止まる間に受信バッファが埋まるため、1周あたり複数回まわして
    // 取りこぼしを防ぐ。
    for (int i = 0; i < 8; ++i) {
        ws.loop();
    }
}

void NetLink::setAudioSink(AudioSink fn) {
    audioSink = fn;
}

void NetLink::setControlSink(ControlSink fn) {
    controlSink = fn;
}

bool NetLink::sendAudio(const int16_t* pcm, size_t samples) {
    if (!connected || samples == 0) {
        return false;
    }
    return ws.sendBIN(reinterpret_cast<const uint8_t*>(pcm), samples * sizeof(int16_t));
}

bool NetLink::sendControl(const char* json) {
    if (!connected) {
        return false;
    }
    return ws.sendTXT(json);
}

void NetLink::persist() {
    if (!prefs.begin(kPrefNamespace, false)) {
        // 静かに失敗すると「保存したのに毎回設定を求められる」形で現れ、
        // 原因がNVSだと分からなくなる。必ず声を上げる。
        Serial.println("[NET] !! NVSを開けませんでした。Wi-Fi設定を保存できません");
        return;
    }
    prefs.putInt(kKeyCredCount, credCount_);
    char sk[8], pk[8];
    for (int i = 0; i < kMaxCreds; ++i) {
        slotKeys(i, sk, pk);
        if (i < credCount_) {
            if (prefs.putString(sk, creds_[i].ssid) == 0 ||
                (creds_[i].pass.length() > 0 && prefs.putString(pk, creds_[i].pass) == 0)) {
                Serial.printf("[NET] !! \"%s\" のNVS書き込みに失敗しました\n",
                              creds_[i].ssid.c_str());
            }
            if (creds_[i].pass.length() == 0) {
                prefs.putString(pk, ""); // 開放APはパスワード空も正しい値
            }
        } else {
            // 減った枠は消す。古い中身が残っていると件数を増やしたときに化けて出る
            // （無いキーの remove は log_e を吐くので isKey で黙らせる）
            if (prefs.isKey(sk)) {
                prefs.remove(sk);
            }
            if (prefs.isKey(pk)) {
                prefs.remove(pk);
            }
        }
    }

    // 書けたつもりで消えているのが最悪なので、その場で読み返して確かめる
    int back = prefs.getInt(kKeyCredCount, -1);
    slotKeys(0, sk, pk);
    String s0 = credCount_ > 0 ? prefs.getString(sk, "") : String();
    prefs.end();
    if (back != credCount_ || (credCount_ > 0 && s0 != creds_[0].ssid)) {
        Serial.printf("[NET] !! 保存の読み返しが一致しません (件数 %d/%d, 先頭 \"%s\")\n",
                      back, credCount_, s0.c_str());
    }
}

/**
 * 一覧の一番下へ下げる（もう一度試しても繋がらなかった候補）。
 * 下にあるものほど、新しい SSID を足したときに枠から追い出される。
 */
void NetLink::moveToBack(const String& ssid) {
    int found = -1;
    for (int i = 0; i < credCount_; ++i) {
        if (creds_[i].ssid == ssid) {
            found = i;
            break;
        }
    }
    if (found < 0 || found == credCount_ - 1) {
        return;
    }
    const Cred moved = creds_[found];
    for (int i = found; i < credCount_ - 1; ++i) {
        creds_[i] = creds_[i + 1];
    }
    creds_[credCount_ - 1] = moved;
}

void NetLink::upsertFront(const char* ssid) {
    int found = -1;
    for (int i = 0; i < credCount_; ++i) {
        if (creds_[i].ssid == ssid) {
            found = i;
            break;
        }
    }
    if (found == 0) {
        return; // すでに先頭
    }

    Cred moved;
    if (found > 0) {
        moved = creds_[found];
    } else {
        moved.ssid = ssid;
        if (credCount_ == kMaxCreds) {
            Serial.printf("[NET] 保存枠が一杯のため最も古い \"%s\" を消しました\n",
                          creds_[kMaxCreds - 1].ssid.c_str());
        }
    }

    // found より前（見つからなければ末尾まで）を1つずつ後ろへずらして先頭を空ける
    int shiftFrom = (found > 0) ? found
                                : ((credCount_ < kMaxCreds) ? credCount_ : kMaxCreds - 1);
    for (int i = shiftFrom; i > 0; --i) {
        creds_[i] = creds_[i - 1];
    }
    creds_[0] = moved;
    if (found < 0 && credCount_ < kMaxCreds) {
        ++credCount_;
    }
}

void NetLink::setSsid(const char* ssid) {
    upsertFront(ssid);
    persist();
    Serial.printf("[NET] SSIDを保存しました: \"%s\" (%d/%d件)\n",
                  ssid, credCount_, kMaxCreds);
    if (creds_[0].pass.length() == 0) {
        Serial.println("[NET] 続けて 'pass <パスワード>' を設定してください");
    }
}

void NetLink::setPassword(const char* pass) {
    if (credCount_ == 0) {
        Serial.println("[NET] 先に 'ssid <名前>' でSSIDを設定してください");
        return;
    }
    creds_[0].pass = pass;
    persist();
    // パスワードは表示しない
    Serial.printf("[NET] \"%s\" のパスワードを保存しました (%d文字)\n",
                  creds_[0].ssid.c_str(), creds_[0].pass.length());
}

void NetLink::addCredential(const char* ssid, const char* pass) {
    upsertFront(ssid);
    creds_[0].pass = pass;
    persist();
    Serial.printf("[NET] Wi-Fi設定を保存しました: \"%s\" (%d/%d件)\n",
                  ssid, credCount_, kMaxCreds);
}

bool NetLink::removeCredential(const char* ssid) {
    for (int i = 0; i < credCount_; ++i) {
        if (creds_[i].ssid != ssid) {
            continue;
        }
        for (int j = i; j < credCount_ - 1; ++j) {
            creds_[j] = creds_[j + 1];
        }
        --credCount_;
        creds_[credCount_] = Cred();
        persist();
        Serial.printf("[NET] \"%s\" を削除しました（残り%d件）\n", ssid, credCount_);
        return true;
    }
    Serial.printf("[NET] \"%s\" は保存されていません（'n' で一覧）\n", ssid);
    return false;
}

void NetLink::clearCredentials() {
    for (int i = 0; i < kMaxCreds; ++i) {
        creds_[i] = Cred();
    }
    credCount_ = 0;
    prefs.begin(kPrefNamespace, false);
    prefs.clear();
    prefs.end();
    Serial.println("[NET] Wi-Fi設定をすべて消去しました");
}

bool NetLink::hasCredentials() const {
    return credCount_ > 0;
}

bool NetLink::wifiConnected() const {
    return WiFi.status() == WL_CONNECTED;
}

bool NetLink::wsReady() const {
    return connected && geminiReady;
}

bool NetLink::lastFailureWasAuth() const {
    return anyAuthFail_;
}

bool NetLink::lastFailureWasNoAp() const {
    return allNoAp_;
}

/** 切断理由が「パスワードが違う」を指しているか。 */
static bool reasonIsAuth(uint8_t r) {
    switch (r) {
    case 15:  // 4WAY_HANDSHAKE_TIMEOUT (ほぼパスワード誤り)
    case 23:  // 802_1X_AUTH_FAILED
    case 24:  // CIPHER_SUITE_REJECTED
    case 202: // AUTH_FAIL
        return true;
    // 204 (HANDSHAKE_TIMEOUT) はここに入れない。電波が弱いだけでも出るため、
    // これで「パスワードが違う」と断じると、繋がるはずの機体を設定モードへ
    // 落としてしまう。204は普通の再試行に任せる。
    default:
        return false;
    }
}

bool NetLink::tryConnectOne(int idx, uint32_t timeoutMs, WaitHook onWait) {
    const Cred& c = creds_[idx];
    Serial.printf("[NET] \"%s\" へ接続します...\n", c.ssid.c_str());
    lastReason = 0;
    WiFi.begin(c.ssid.c_str(), c.pass.c_str());

    uint32_t start = millis();
    while (WiFi.status() != WL_CONNECTED && (millis() - start) < timeoutMs) {
        /*
         * 結果が変わらないと分かった時点で待つのをやめる。
         *
         * 201=APが見つからない / 202,15=認証に失敗 / 204=ハンドシェイク不成立。
         * どれもタイムアウトまで待ったところで結論は同じで、その十数秒がまるごと
         * 「顔は出ているのに何も起きない時間」になる。理由コードは数秒で来る。
         */
        if (isConclusiveFailure(lastReason)) {
            Serial.printf("[NET] 待っても変わらないと判断して打ち切ります（理由 %u %s）\n",
                          lastReason, disconnectReasonName(lastReason));
            break;
        }
        // 待っているあいだも呼び出し側に制御を戻す（顔を止めないため）
        if (onWait != nullptr) {
            onWait();
        }
        delay(20);
    }

    if (!wifiConnected()) {
        int st = WiFi.status();
        Serial.printf("[NET] \"%s\" に接続できませんでした: %s (status=%d)\n",
                      c.ssid.c_str(), wifiStatusName(st), st);
        if (c.pass.length() > 0 && c.pass.length() < 8) {
            Serial.printf("[NET] !! パスワードが%d文字です。WPA/WPA2/WPA3のパスフレーズは\n",
                          c.pass.length());
            Serial.println("[NET]    8〜63文字と規格で決まっており、これでは接続できません。");
        }
        if (lastReason != 0) {
            Serial.printf("[NET] 切断理由: %u %s\n",
                          lastReason, disconnectReasonName(lastReason));
        }
        return false;
    }

    Serial.printf("[NET] 接続しました  SSID=\"%s\"  IP=%s  RSSI=%ddBm  (%.1f秒)\n",
                  c.ssid.c_str(), WiFi.localIP().toString().c_str(), WiFi.RSSI(),
                  (millis() - start) / 1000.0f);
    return true;
}

bool NetLink::wifiConnect(uint32_t timeoutMs, WaitHook onWait) {
    if (!hasCredentials()) {
        Serial.println("[NET] SSIDが未設定です。'ssid <名前>' から設定してください");
        return false;
    }

    // 設定モードのAPが残っているとSTA側の接続が不安定になる。確実にSTAへ戻す。
    if (WiFi.getMode() != WIFI_STA) {
        Serial.printf("[NET] WiFiモードを %d から STA へ戻します\n", WiFi.getMode());
        WiFi.softAPdisconnect(true);
        WiFi.mode(WIFI_STA);
        delay(100);
    }
    if (wifiConnected()) {
        Serial.println("[NET] すでに接続済みです");
        return true;
    }

    // --- 試す順番を決める ---
    // 1件だけならスキャンの数秒がまるごと無駄なので、直接試す。
    // 2件以上なら先にスキャンし、見えている保存済みSSIDを電波の強い順へ。
    // 見えなかった保存分も捨てない（名前を隠したAPはスキャンに映らないため）。
    int order[kMaxCreds];
    for (int i = 0; i < credCount_; ++i) {
        order[i] = i;
    }

    if (credCount_ >= 2) {
        WiFi.disconnect(false, false); // 再接続の試行中はスキャンが失敗する

        // 起動直後やdisconnect直後はスキャンを開始できず -2 が返る（実機で確認。
        // 'scan' コマンドにも同じ知見がある）。少し置いてから、駄目なら1回だけやり直す。
        // 🔴 2 回（0.2 秒・0.5 秒待ち）では起動直後に毎回 -2 のままだった（2026-09-22 実機）。
        // 見えるかどうか分からないまま保存順に総当たりすると、件数が多いほど繋がる候補に
        // たどり着くのが遅れる。待ちを延ばしながら 5 回まで試す
        static const int kScanWaitMs[] = {200, 500, 1000, 1500, 2000};
        int n = WIFI_SCAN_FAILED;
        int attempt = 0;
        for (; attempt < 5 && n < 0; ++attempt) {
            for (int t = 0; t < kScanWaitMs[attempt]; t += 20) {
                if (onWait != nullptr) {
                    onWait();
                }
                delay(20);
            }
            WiFi.scanDelete();
            // 同期スキャンは数秒ブロックして顔が固まるので、非同期で回して待つ
            WiFi.scanNetworks(/* async= */ true);
            uint32_t scanStart = millis();
            while ((n = WiFi.scanComplete()) == WIFI_SCAN_RUNNING &&
                   (millis() - scanStart) < 8000) {
                if (onWait != nullptr) {
                    onWait();
                }
                delay(20);
            }
        }

        if (n >= 0 && attempt > 1) {
            Serial.printf("[NET] スキャンは %d 回目で通りました\n", attempt);
        }
        if (n > 0) {
            int rssi[kMaxCreds];
            for (int i = 0; i < credCount_; ++i) {
                rssi[i] = -1000; // 見えていない印
            }
            for (int i = 0; i < n; ++i) {
                for (int k = 0; k < credCount_; ++k) {
                    if (WiFi.SSID(i) == creds_[k].ssid && WiFi.RSSI(i) > rssi[k]) {
                        rssi[k] = WiFi.RSSI(i);
                    }
                }
            }
            // 見えているものをRSSI降順で前へ（同値・不可視は保存順=新しい順を保つ）
            for (int i = 1; i < credCount_; ++i) {
                int o = order[i];
                int j = i;
                while (j > 0 && rssi[order[j - 1]] < rssi[o]) {
                    order[j] = order[j - 1];
                    --j;
                }
                order[j] = o;
            }
            for (int i = 0; i < credCount_; ++i) {
                int k = order[i];
                if (rssi[k] > -1000) {
                    Serial.printf("[NET] 候補%d: \"%s\" (%ddBm)\n",
                                  i + 1, creds_[k].ssid.c_str(), rssi[k]);
                } else {
                    Serial.printf("[NET] 候補%d: \"%s\" (スキャンに映らず。隠れAPなら繋がる)\n",
                                  i + 1, creds_[k].ssid.c_str());
                }
            }
        } else {
            Serial.printf("[NET] スキャンできなかったため保存の新しい順に試します (戻り値 %d)\n", n);
        }
        WiFi.scanDelete();
    }

    // --- 順に試す ---
    anyAuthFail_ = false;
    allNoAp_ = true;
    // もう一度試しても繋がらなかった候補。どれかに繋がったら一番下へ下げる
    // （ユーザー 2026-09-22「失敗してるなら順位下げるんじゃないの？」）
    String failed[kMaxCreds];
    int nFailed = 0;
    for (int i = 0; i < credCount_; ++i) {
        if (i > 0) {
            WiFi.disconnect(false, false); // 前候補の再接続試行を確実に止めてから
            delay(100);
        }
        bool ok = tryConnectOne(order[i], timeoutMs, onWait);
        if (!ok && (lastReason == 15 || lastReason == 202 || lastReason == 204)) {
            // ハンドシェイク不成立は「パスワード誤り」と「再起動直後のタイミング」の
            // 両方で出る（実機で正しいパスワードでも初回に理由15を確認）。
            // 1回で結論を出さず、同じ候補をもう一度だけ試す。
            // 🔴 202 AUTH_FAIL も同じ（2026-09-22 実機: 書き込み直後の起動で毎回 1 回目だけ
            // 202 で弾かれ、見えない残りの候補を試して 5 秒待った 2 周目に 0.6 秒で繋がっていた）
            Serial.println("[NET] ハンドシェイク不成立。同じ設定でもう一度だけ試します");
            WiFi.disconnect(false, false);
            for (int t = 0; t < 300; t += 20) {
                if (onWait != nullptr) {
                    onWait();
                }
                delay(20);
            }
            ok = tryConnectOne(order[i], timeoutMs, onWait);
        }
        if (ok) {
            // 繋がったSSIDを「最新」へ繰り上げる。次回はスキャン前でもこれが先頭。
            // その手前で繋がらなかった候補は一番下へ下げる。
            // ⚠ 起動直後の一時的な弾かれ（1 回目の 202 など）は、上のもう一度で繋がるので下げない
            const String ssid = creds_[order[i]].ssid;
            const bool moveUp = order[i] != 0;
            if (moveUp) {
                upsertFront(ssid.c_str());
            }
            for (int f = 0; f < nFailed; ++f) {
                moveToBack(failed[f]);
                Serial.printf("[NET] 繋がらなかった \"%s\" を一覧の一番下へ下げました\n", failed[f].c_str());
            }
            if (moveUp || nFailed > 0) {
                persist();
            }
            return true;
        }
        failed[nFailed++] = creds_[order[i]].ssid;
        if (reasonIsAuth(lastReason)) {
            anyAuthFail_ = true;
        }
        if (lastReason != 201) { // NO_AP_FOUND 以外が1つでもあれば「全滅=圏外」ではない
            allNoAp_ = false;
        }
    }

    Serial.printf("[NET] 保存済みの%d件すべてに接続できませんでした\n", credCount_);
    Serial.println("[NET]   'scan' で該当SSIDが見えているか確認してください");
    Serial.println("[NET]   ESP32は2.4GHz帯のみです。5GHz専用のSSIDには繋がりません");
    return false;
}

void NetLink::scan() {
    Serial.println("[NET] 2.4GHz帯をスキャンします...");

    // ESP32は WiFi.begin() が失敗すると内部で再接続を繰り返す。その最中は
    // スキャンを開始できず -2 (SCAN_FAILED) が返る。先に接続試行を止める。
    if (WiFi.status() != WL_CONNECTED) {
        WiFi.disconnect(false, false); // 電源は落とさず、保存設定も消さない
        delay(200);
    }
    WiFi.scanDelete(); // 前回の結果が残っていると次のスキャンが失敗することがある

    int n = WiFi.scanNetworks();
    if (n == WIFI_SCAN_FAILED) {
        // 一度で駄目でも、少し待てば通ることが多い
        delay(500);
        WiFi.scanDelete();
        n = WiFi.scanNetworks();
    }

    // 負の値は「APが無い」ではなく「スキャンが失敗/実行中」。
    // ここを 0 と同一視していると、電波の問題と誤診する。
    if (n < 0) {
        Serial.printf("[NET] スキャンできませんでした (戻り値 %d: %s)\n", n,
                      n == WIFI_SCAN_RUNNING ? "実行中" :
                      n == WIFI_SCAN_FAILED  ? "失敗" : "不明");
        Serial.printf("[NET]   WiFi.mode=%d  status=%d\n", WiFi.getMode(), WiFi.status());
        Serial.println("[NET]   APモードが残っている可能性があります。'R' で再起動するか、");
        Serial.println("[NET]   USBを抜き差しして電源から入れ直してください。");
        WiFi.scanDelete();
        return;
    }
    if (n == 0) {
        Serial.println("[NET] APが1つも見つかりませんでした（アンテナの接続を確認してください）");
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
        bool isSaved = false;
        for (int k = 0; k < credCount_; ++k) {
            if (WiFi.SSID(i) == creds_[k].ssid) {
                isSaved = true;
                break;
            }
        }
        Serial.printf("  %s %-32s ch%-3d %4ddBm  %s\n",
                      isSaved ? "->" : "  ",
                      WiFi.SSID(i).c_str(), WiFi.channel(i), WiFi.RSSI(i), enc);
    }
    WiFi.scanDelete();

    if (credCount_ > 0) {
        Serial.println("[NET] 保存済みのSSIDが上の一覧に -> 付きで居れば電波は届いています");
    }
}

void NetLink::wifiDisconnect() {
    wsDisconnect();
    WiFi.disconnect();
    Serial.println("[NET] Wi-Fiを切断しました");
}

void NetLink::wifiStop() {
    wsDisconnect();
    WiFi.disconnect(false, false); // 電源は落とさず、保存設定も消さない
    WiFi.mode(WIFI_OFF);           // ここで esp_wifi_stop() が走る
    Serial.println("[NET] 無線を完全に止めました (WIFI_OFF)");
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

    wantConnected = true;
    connectStartedMs = millis();

#if KATANORI_TLS_INSECURE
    // 緊急用の逃げ道。CAを更新するまでの一時しのぎ以外で使わないこと。
    Serial.println("[WS] !! 警告: TLSサーバ証明書を検証していません");
    ws.beginSSL(KATANORI_WS_HOST, KATANORI_WS_PORT, KATANORI_WS_PATH);
#else
    // ルートCAを検証する。接続できなくなった場合、まず疑うべきは
    // 接続先が発行元CAを変更したこと（RootCa.h のコメント参照）。
    ws.beginSslWithCA(KATANORI_WS_HOST, KATANORI_WS_PORT, KATANORI_WS_PATH,
                      KATANORI_ROOT_CA_PEM);
#endif
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
    // パスワードは出さないが、桁数は出す。設定モードで空や誤りを保存してしまった
    // 場合に「保存されているつもりだった」を見抜けるようにするため。
    if (credCount_ == 0) {
        Serial.println("  Wi-Fi設定 : (未設定)");
    } else {
        Serial.printf("  Wi-Fi設定 : %d/%d件（新しい順）\n", credCount_, kMaxCreds);
        for (int i = 0; i < credCount_; ++i) {
            bool inUse = wifiConnected() && WiFi.SSID() == creds_[i].ssid;
            Serial.printf("   %s %d. \"%s\" (パスワード %d文字)\n",
                          inUse ? "->" : "  ", i + 1,
                          creds_[i].ssid.c_str(), creds_[i].pass.length());
        }
    }
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
