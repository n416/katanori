/*
 * BootLog - なぜ再起動したのかを残す。設計の説明は BootLog.h。
 */

#include "BootLog.h"

#include <Preferences.h>
#include <esp_attr.h>
#include <esp_system.h>
#include "Console.h" // 最後に置く（Serial を Wi-Fi モニタへも流す差し替え。Console.h）

namespace katanori {
namespace bootlog {

namespace {

constexpr uint32_t kMagic = 0x4B544E31; // "KTN1"
constexpr int kHistory = 10;

/** 1 秒ごとの様子。リセット（電源断以外）をまたいで残る。 */
struct Snapshot {
    uint32_t magic;
    uint32_t uptimeSec;
    uint16_t batMv;      // 0 = 読めていない
    int16_t batMa;       // ＋が放電
    uint16_t heapMinKb;  // 起動してからの空きメモリの最小
    uint8_t stage;
    uint8_t flags;       // bit0 = 会話中 / bit1 = Wi-Fi 接続中
};

RTC_NOINIT_ATTR Snapshot rtcSnap;

/** NVS に貯める 1 回ぶん。 */
struct Entry {
    uint8_t reason;      // esp_reset_reason_t
    uint8_t stage;       // 0xFF = 直前の様子なし（電源断など）
    uint8_t flags;
    uint8_t pad;
    uint16_t batMv;
    int16_t batMa;
    uint16_t heapMinKb;
    uint16_t pad2;
    uint32_t uptimeSec;
};

uint32_t bootCount = 0;

const char* reasonName(uint8_t r) {
    switch (r) {
    case ESP_RST_POWERON:   return "電源投入（5Vが一度切れた）";
    case ESP_RST_EXT:       return "外部リセット";
    case ESP_RST_SW:        return "ソフトから再起動（OTA・reboot など）";
    case ESP_RST_PANIC:     return "パニック（ファームが落ちた）";
    case ESP_RST_INT_WDT:   return "割り込みウォッチドッグ";
    case ESP_RST_TASK_WDT:  return "タスクウォッチドッグ";
    case ESP_RST_WDT:       return "ウォッチドッグ";
    case ESP_RST_DEEPSLEEP: return "deep sleep から";
    case ESP_RST_BROWNOUT:  return "電圧低下（ブラウンアウト）";
    case ESP_RST_SDIO:      return "SDIO";
    default:                return "不明";
    }
}

const char* stageName(uint8_t s) {
    switch (s) {
    case kAwake:        return "起きている";
    case kDim:          return "画面を暗く";
    case kAsleep:       return "待機スリープ";
    case kKnobOff:      return "つまみOFF";
    case kProvisioning: return "Wi-Fi設定";
    default:            return "?";
    }
}

void printEntry(const char* head, const Entry& e) {
    if (e.stage == 0xFF) {
        Serial.printf("%s 理由=%s（直前の様子は残っていない）\n", head, reasonName(e.reason));
        return;
    }
    char bat[32];
    if (e.batMv) {
        snprintf(bat, sizeof(bat), "電池 %.2fV %dmA", e.batMv / 1000.0f, e.batMa);
    } else {
        snprintf(bat, sizeof(bat), "電池 読めず");
    }
    Serial.printf("%s 理由=%s ／ 直前: 起動から%u秒・%s%s%s・%s・空きメモリ最小 %uKB\n",
                  head, reasonName(e.reason), (unsigned)e.uptimeSec, stageName(e.stage),
                  (e.flags & 1) ? "・会話中" : "", (e.flags & 2) ? "・Wi-Fi接続中" : "",
                  bat, (unsigned)e.heapMinKb);
}

} // namespace

void begin() {
    Entry e = {};
    e.reason = (uint8_t)esp_reset_reason();
    // 電源断では RTC も消えて中身は不定。magic が合っても信じない
    bool snapValid = (rtcSnap.magic == kMagic) && e.reason != ESP_RST_POWERON;
    if (snapValid) {
        e.stage = rtcSnap.stage;
        e.flags = rtcSnap.flags;
        e.batMv = rtcSnap.batMv;
        e.batMa = rtcSnap.batMa;
        e.heapMinKb = rtcSnap.heapMinKb;
        e.uptimeSec = rtcSnap.uptimeSec;
    } else {
        e.stage = 0xFF;
    }
    rtcSnap = {};
    rtcSnap.magic = kMagic;

    Preferences prefs;
    prefs.begin("boot", false);
    bootCount = prefs.getUInt("count", 0) + 1;
    prefs.putUInt("count", bootCount);
    Entry hist[kHistory] = {};
    prefs.getBytes("hist", hist, sizeof(hist));
    memmove(&hist[1], &hist[0], sizeof(Entry) * (kHistory - 1)); // 先頭が最新
    hist[0] = e;
    prefs.putBytes("hist", hist, sizeof(hist));
    prefs.end();

    char head[40];
    snprintf(head, sizeof(head), "[BOOT] %u回目の起動。前回:", (unsigned)bootCount);
    printEntry(head, e);
}

void tick(Stage stage, bool conversation, bool wifi, float batVolts, float batMa, bool batValid) {
    static uint32_t lastMs = 0;
    uint32_t now = millis();
    if ((now - lastMs) < 1000) {
        return;
    }
    lastMs = now;
    rtcSnap.magic = kMagic;
    rtcSnap.uptimeSec = now / 1000;
    rtcSnap.stage = stage;
    rtcSnap.flags = (conversation ? 1 : 0) | (wifi ? 2 : 0);
    rtcSnap.batMv = batValid ? (uint16_t)(batVolts * 1000.0f) : 0;
    rtcSnap.batMa = batValid ? (int16_t)batMa : 0;
    rtcSnap.heapMinKb = (uint16_t)(ESP.getMinFreeHeap() / 1024);
}

void printHistory() {
    Preferences prefs;
    prefs.begin("boot", true);
    uint32_t count = prefs.getUInt("count", 0);
    Entry hist[kHistory] = {};
    size_t got = prefs.getBytes("hist", hist, sizeof(hist));
    prefs.end();
    Serial.printf("[BOOT] 起動は通算%u回。新しい順に最大%d回ぶん:\n", (unsigned)count, kHistory);
    int shown = (int)(got / sizeof(Entry));
    for (int i = 0; i < shown && i < (int)count; ++i) {
        char head[24];
        snprintf(head, sizeof(head), "[BOOT]  %u回目:", (unsigned)(count - i));
        printEntry(head, hist[i]);
    }
}

} // namespace bootlog
} // namespace katanori
