/*
 * Settings - 利用者が変えられる設定と、その設定ページ。設計の説明は Settings.h。
 */

#include "Settings.h"

#include <Preferences.h>
#include <WebServer.h>
#include <WiFi.h>

#include "Provisioning.h"
#include "Console.h" // 最後に置く（Serial を Wi-Fi モニタへも流す差し替え。Console.h）

namespace katanori {

Settings settings;

namespace {

// Wi-Fi 設定モードの WebServer（Provisioning.cpp）も 80 番を使う。同時には開かない
WebServer settingsHttp(80);

constexpr uint8_t kContrast[Settings::kBrightLevels] = {0x04, 0x20, 0x50, 0x90, 0xCF};
constexpr uint16_t kSleepMin[Settings::kSleepOptions] = {0, 1, 3, 5, 10};

void handleRoot() {
    String h;
    h.reserve(2600);
    h += F("<!doctype html><html lang=ja><head><meta charset=utf-8>"
           "<meta name=viewport content='width=device-width,initial-scale=1'>"
           "<title>カタノリの設定</title><style>"
           "body{font-family:sans-serif;margin:0;padding:20px;background:#f4f4f2;color:#222}"
           "h1{font-size:20px;margin:0 0 16px}"
           "fieldset{border:0;background:#fff;border-radius:10px;padding:14px 16px;margin:0 0 14px}"
           "legend{font-weight:bold;padding:0;margin-bottom:8px;float:left;width:100%}"
           "label{display:inline-block;margin:6px 14px 6px 0;font-size:17px}"
           "input{transform:scale(1.3);margin-right:6px}"
           "button{font-size:18px;padding:10px 28px;border-radius:8px;border:0;background:#2a6df4;color:#fff}"
           ".ok{background:#dff3df;border-radius:8px;padding:8px 12px;margin-bottom:14px}"
           "</style></head><body><h1>カタノリの設定</h1>");
    if (settingsHttp.hasArg("saved")) {
        h += F("<div class=ok>保存しました。機体にもう効いています。</div>");
    }
    h += F("<form method=post action=/save>");

    h += F("<fieldset><legend>画面の明るさ</legend>");
    for (uint8_t lv = 1; lv <= Settings::kBrightLevels; ++lv) {
        h += "<label><input type=radio name=b value=" + String(lv) +
             (settings.brightness() == lv ? " checked" : "") + ">" + String(lv) + "</label>";
    }
    h += F("<div style='font-size:13px;color:#666;clear:both'>1 がいちばん暗い</div></fieldset>");

    h += F("<fieldset><legend>眠るまでの時間（触らないでいると画面と無線を止める）</legend>");
    for (uint8_t i = 0; i < Settings::kSleepOptions; ++i) {
        String name = kSleepMin[i] == 0 ? String("眠らない") : String(kSleepMin[i]) + "分";
        h += "<label><input type=radio name=s value=" + String(i) +
             (settings.sleepIndex() == i ? " checked" : "") + ">" + name + "</label>";
    }
    h += F("</fieldset>");

    h += F("<fieldset><legend>起動の声（「カタノリ、起動しました」）</legend>");
    h += String("<label><input type=radio name=v value=1") + (settings.bootVoice() ? " checked" : "") +
         ">鳴らす</label>";
    h += String("<label><input type=radio name=v value=0") + (settings.bootVoice() ? "" : " checked") +
         ">鳴らさない</label></fieldset>";

    h += F("<button type=submit>保存</button></form>"
           "<p style='font-size:13px;color:#666'>機体のメニュー（会話ボタンを長押し）からも同じ設定を変えられます。</p>"
           "</body></html>");
    settingsHttp.send(200, "text/html; charset=utf-8", h);
}

void handleSave() {
    if (settingsHttp.hasArg("b")) {
        settings.setBrightness((uint8_t)settingsHttp.arg("b").toInt());
    }
    if (settingsHttp.hasArg("s")) {
        settings.setSleepIndex((uint8_t)settingsHttp.arg("s").toInt());
    }
    if (settingsHttp.hasArg("v")) {
        settings.setBootVoice(settingsHttp.arg("v").toInt() != 0);
    }
    Serial.printf("[CFG] 設定ページから保存しました（%s）\n",
                  settingsHttp.client().remoteIP().toString().c_str());
    settingsHttp.sendHeader("Location", "/?saved=1");
    settingsHttp.send(303);
}

} // namespace

uint8_t Settings::contrastFor(uint8_t level) {
    if (level < 1) level = 1;
    if (level > kBrightLevels) level = kBrightLevels;
    return kContrast[level - 1];
}

uint16_t Settings::sleepMinutesAt(uint8_t idx) {
    return idx < kSleepOptions ? kSleepMin[idx] : kSleepMin[2];
}

void Settings::begin() {
    Preferences p;
    p.begin("cfg", true);
    bright_ = p.getUChar("bright", kBrightLevels);
    sleepIdx_ = p.getUChar("sleep", 2);
    bootVoice_ = p.getUChar("voice", 1) != 0;
    p.end();
    if (bright_ < 1 || bright_ > kBrightLevels) bright_ = kBrightLevels;
    if (sleepIdx_ >= kSleepOptions) sleepIdx_ = 2;
    print();
}

void Settings::save(const char* key, uint8_t v) {
    Preferences p;
    p.begin("cfg", false);
    p.putUChar(key, v);
    p.end();
}

void Settings::changed() {
    print();
    if (onChange_) {
        onChange_();
    }
}

void Settings::setBrightness(uint8_t level) {
    if (level < 1 || level > kBrightLevels || level == bright_) return;
    bright_ = level;
    save("bright", level);
    changed();
}

void Settings::setSleepIndex(uint8_t idx) {
    if (idx >= kSleepOptions || idx == sleepIdx_) return;
    sleepIdx_ = idx;
    save("sleep", idx);
    changed();
}

void Settings::setBootVoice(bool on) {
    if (on == bootVoice_) return;
    bootVoice_ = on;
    save("voice", on ? 1 : 0);
    changed();
}

void Settings::print() const {
    uint16_t m = sleepMinutesAt(sleepIdx_);
    Serial.printf("[CFG] 明るさ %u/5（0x%02X）・眠るまで %s・起動の声 %s\n",
                  bright_, contrast(), m ? (String(m) + "分").c_str() : "眠らない",
                  bootVoice_ ? "鳴らす" : "鳴らさない");
}

void Settings::webLoop() {
    bool ready = WiFi.status() == WL_CONNECTED && !provisioning.active();
    if (!ready) {
        if (webUp_ && provisioning.active()) {
            webSuspend();
        }
        return;
    }
    if (!webUp_) {
        static bool routed = false; // 張り直しのたびに登録すると同じ口が重なる
        if (!routed) {
            routed = true;
            settingsHttp.on("/", HTTP_GET, handleRoot);
            settingsHttp.on("/save", HTTP_POST, handleSave);
            settingsHttp.onNotFound([]() { settingsHttp.send(404, "text/plain", "not found"); });
        }
        settingsHttp.begin();
        webUp_ = true;
        Serial.printf("[CFG] 設定ページ: http://katanori.local/ （http://%s/）\n",
                      WiFi.localIP().toString().c_str());
    }
    settingsHttp.handleClient();
}

void Settings::webSuspend() {
    if (!webUp_) return;
    settingsHttp.stop();
    webUp_ = false;
}

} // namespace katanori
