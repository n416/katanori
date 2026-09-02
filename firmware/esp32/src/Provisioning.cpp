#include "Provisioning.h"
#include "NetLink.h"

#include <WiFi.h>
#include <DNSServer.h>
#include <WebServer.h>
#include <Preferences.h>

namespace katanori {

namespace {

DNSServer dns;
WebServer http(80);

const IPAddress AP_IP(192, 168, 4, 1);
const IPAddress AP_MASK(255, 255, 255, 0);

/**
 * スキャン結果のキャッシュ。
 * キャプティブポータル検出のため端末は同じURLを何度も叩いてくる。
 * その都度 WiFi.scanNetworks() を回すと1回数秒かかり、ポータルが開く前に
 * 端末側がタイムアウトする。起動時に一度スキャンして使い回す。
 */
String cachedOptions;
uint32_t scannedAtMs = 0;

void refreshScan() {
    String opts;
    int n = WiFi.scanNetworks();
    for (int i = 0; i < n; ++i) {
        String ssid = WiFi.SSID(i);
        if (ssid.length() == 0) {
            continue;
        }
        opts += "<option value=\"" + ssid + "\">" + ssid;
        opts += " (" + String(WiFi.RSSI(i)) + "dBm)</option>";
    }
    WiFi.scanDelete();
    if (opts.length() == 0) {
        opts = F("<option value=\"\">見つかりませんでした</option>");
    }
    cachedOptions = opts;
    scannedAtMs = millis();
    Serial.printf("[PROV] スキャン完了: %d件\n", n);
}

/** 設定ページ。スマホ1画面で完結させ、余計な操作を挟まない。 */
String buildPage() {
    String html;
    html.reserve(4096);

    html += F(
        "<!doctype html><html lang=\"ja\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>カタノリロボ Wi-Fi設定</title><style>"
        "body{font-family:system-ui,sans-serif;margin:0;padding:20px;"
        "background:#101828;color:#e2e8f0;line-height:1.6}"
        "h1{font-size:20px;margin:0 0 4px}"
        "p.sub{color:#94a3b8;font-size:13px;margin:0 0 20px}"
        "label{display:block;margin:16px 0 6px;font-size:14px;color:#cbd5e1}"
        "select,input{width:100%;box-sizing:border-box;padding:12px;font-size:16px;"
        "border-radius:8px;border:1px solid #334155;background:#1e293b;color:#e2e8f0}"
        "button{width:100%;margin-top:24px;padding:14px;font-size:16px;font-weight:bold;"
        "border:0;border-radius:8px;background:#38bdf8;color:#0b1220}"
        "select:disabled,input:disabled,button:disabled{opacity:.4}"
        ".note{margin-top:20px;padding:12px;border-radius:8px;background:#1e293b;"
        "font-size:12px;color:#94a3b8}"
        "</style></head><body>"
        "<h1>カタノリロボ Wi-Fi設定</h1>"
        "<p class=\"sub\">おうちのWi-Fiを選んでパスワードを入れてください。</p>"
        "<form method=\"POST\" action=\"/save\">"
        "<label for=\"s\">Wi-Fiの名前</label><select id=\"s\" name=\"ssid\">");

    html += cachedOptions;

    html += F(
        "</select>"
        "<label for=\"p\">パスワード</label>"
        "<input id=\"p\" name=\"pass\" type=\"password\" autocomplete=\"off\" "
        "placeholder=\"8文字以上\">"
        "<button id=\"b\" type=\"submit\">保存して再起動</button></form>"
        // 再検索中はAPのビーコンが数秒止まり、スマホが一時的に切れる。
        // 一覧に目的のWi-Fiが無いときだけ使ってもらう。
        "<p style=\"text-align:center;margin-top:16px\">"
        "<a id=\"r\" href=\"/rescan\" style=\"color:#38bdf8;font-size:13px\">Wi-Fiを再検索"
        "</a><br><span style=\"color:#64748b;font-size:11px\">"
        "（数秒つながりが切れます）</span></p>"
        // 再検索を押したら入力を無効化する。検索中はサーバー側が数秒黙り、
        // ページ遷移も待たされる。その間に触れても保存されないし、
        // 完了時にはページが作り直されて入力は消える。触れないほうが正直。
        "<script>document.getElementById('r').addEventListener('click',function(){"
        "document.getElementById('s').disabled=true;"
        "document.getElementById('p').disabled=true;"
        "document.getElementById('b').disabled=true;"
        "this.textContent='さいけんさく中...';});</script>"
        "<div class=\"note\">"
        "この設定画面は暗号化されていません。設定が終わるとロボットは自動で再起動し、"
        "この画面は消えます。<br>"
        "ESP32は2.4GHz帯のみ対応です。5GHz専用のWi-Fiには接続できません。"
        "</div></body></html>");

    return html;
}

void sendPortal() {
    // キャッシュさせない。ポータル検出を毎回成立させるため。
    http.sendHeader("Cache-Control", "no-cache, no-store, must-revalidate");
    http.sendHeader("Pragma", "no-cache");
    http.send(200, "text/html; charset=utf-8", buildPage());
}

void handleRoot() {
    sendPortal();
}

void handleRescan() {
    refreshScan();
    http.sendHeader("Location", "/", true);
    http.send(302, "text/plain", "");
}

/**
 * キャプティブポータル検出。
 *
 * 302リダイレクトではなく「200 + ポータル本体」を返すのが確実。
 * AndroidもiOSも「期待した応答(204 や <SUCCESS>)が返ってこないこと」で
 * ポータルの存在を判定するため、中身のあるHTMLをそのまま返せば発火する。
 * リダイレクトだと端末によっては追随せず、ログイン画面が出ない。
 */
void handleNotFound() {
    sendPortal();
}

} // namespace

Provisioning provisioning;

bool Provisioning::begin() {
    if (active_) {
        return true;
    }

    // Wi-Fi接続用QRの標準形式。実機のスキャナで「ネットワーク名/タイプ」として
    // 正しく解釈されることを確認済み（S先・T先どちらの順序でも読めた）。
    snprintf(qrPayload_, sizeof(qrPayload_), "WIFI:T:nopass;S:%s;;", KATANORI_AP_SSID);

    // 【順序が重要】
    // 1. STAの接続・再接続を完全に止める
    //    再接続を試み続けているとチャンネルが動き、APが安定して電波に出られない。
    // 2. AP起動より先にスキャンを済ませる
    //    scanNetworks() は数秒チャンネルを掃くので、AP起動後に呼ぶと
    //    その間ビーコンが止まり、スマホのWi-Fi一覧に出てこない。
    // 3. 最後にAPを立てる
    WiFi.disconnect(false, false);
    WiFi.mode(WIFI_AP_STA); // APだけだと周囲のSSID一覧が取れないので AP_STA
    delay(200);

    refreshScan();

    WiFi.softAPConfig(AP_IP, AP_IP, AP_MASK);
    // パスワード無し = 開放AP。チャンネルは固定して安定させる。
    if (!WiFi.softAP(KATANORI_AP_SSID, nullptr, /*channel=*/1,
                     /*hidden=*/0, /*max_connection=*/4)) {
        Serial.println("[PROV] APの起動に失敗しました");
        return false;
    }
    delay(300); // ビーコンが出るまで少し待つ

    Serial.printf("[PROV] AP状態: SSID=\"%s\" IP=%s ch=%d mode=%d\n",
                  WiFi.softAPSSID().c_str(),
                  WiFi.softAPIP().toString().c_str(),
                  WiFi.channel(), WiFi.getMode());

    // 全問い合わせに自分のIPを返す。これでスマホが自動的に設定画面を開く。
    dns.setErrorReplyCode(DNSReplyCode::NoError);
    dns.start(53, "*", AP_IP);

    http.on("/", handleRoot);
    http.on("/rescan", handleRescan);

    // 端末がポータル検出に使う既知のURL。明示的に拾っておく。
    http.on("/generate_204", sendPortal);          // Android
    http.on("/gen_204", sendPortal);               // Android
    http.on("/hotspot-detect.html", sendPortal);   // iOS / macOS
    http.on("/library/test/success.html", sendPortal); // iOS
    http.on("/connecttest.txt", sendPortal);       // Windows
    http.on("/ncsi.txt", sendPortal);              // Windows
    http.on("/redirect", sendPortal);              // Windows
    http.on("/canonical.html", sendPortal);        // Firefox
    http.on("/save", HTTP_POST, [this]() {
        String ssid = http.arg("ssid");
        String pass = http.arg("pass");

        if (ssid.length() == 0) {
            http.send(200, "text/html; charset=utf-8",
                      F("<meta charset=\"utf-8\"><body style=\"font-family:sans-serif;padding:20px\">"
                        "<h2>Wi-Fiが選ばれていません</h2><a href=\"/\">戻る</a></body>"));
            return;
        }

        // 追加保存（最新5件まで）。前の設定は消さないので、自宅とテザリングの
        // 併用ができる。同じSSIDを選び直した場合はパスワードが更新される。
        netLink.addCredential(ssid.c_str(), pass.c_str());

        // 「設定した直後」の印。再起動をまたぐのでNVSに置く。次の接続成功時に
        // 「ワイファイにつながりました」を鳴らして、入れたパスワードが
        // 合っていたことを声で伝える（main.cpp の noteWifiUp が消費する）。
        Preferences p;
        p.begin("katanori", false);
        p.putBool("provok", true);
        p.end();

        http.send(200, "text/html; charset=utf-8",
                  F("<meta charset=\"utf-8\"><body style=\"font-family:sans-serif;padding:20px;"
                    "background:#101828;color:#e2e8f0\">"
                    "<h2>保存しました</h2>"
                    "<p>ロボットを再起動します。しばらくお待ちください。</p>"
                    "<p style=\"color:#94a3b8;font-size:13px\">"
                    "うまく繋がらないときは、ロボットのボタンを3秒押すとこの画面に戻れます。</p>"
                    "</body>"));

        phase_ = Phase::SAVED;
        savedAtMs_ = millis();
        Serial.printf("[PROV] 設定を受信しました SSID=\"%s\"\n", ssid.c_str());
    });
    http.onNotFound(handleNotFound);
    http.begin();

    active_ = true;
    phase_ = Phase::WAITING;
    Serial.printf("[PROV] 設定モード開始  SSID=\"%s\"  IP=%s\n",
                  KATANORI_AP_SSID, AP_IP.toString().c_str());
    Serial.printf("[PROV] QR: %s\n", qrPayload_);
    return true;
}

void Provisioning::loop() {
    if (!active_) {
        return;
    }
    dns.processNextRequest();
    http.handleClient();

    if (phase_ == Phase::SAVED) {
        // ブラウザへ応答を返し切ってから再起動する
        if (millis() - savedAtMs_ > 2000) {
            Serial.println("[PROV] 再起動します");
            Serial.flush();
            delay(100);
            ESP.restart();
        }
        return;
    }

    // スマホが繋がったかどうかを画面に反映する
    phase_ = (WiFi.softAPgetStationNum() > 0) ? Phase::CONNECTED : Phase::WAITING;
}

void Provisioning::stop() {
    if (!active_) {
        return;
    }
    http.stop();
    dns.stop();
    WiFi.softAPdisconnect(true);
    WiFi.mode(WIFI_STA);
    active_ = false;
    Serial.println("[PROV] 設定モードを終了しました");
}

IPAddress Provisioning::apIp() const {
    return AP_IP;
}

const char* Provisioning::statusText() const {
    switch (phase_) {
    case Phase::WAITING:   return "接続をまっています";
    case Phase::CONNECTED: return "せつぞく中です";
    case Phase::SAVED:     return "さいきどうします";
    }
    return "";
}

} // namespace katanori
