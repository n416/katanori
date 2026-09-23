/*
 * Console - シリアルモニタを Wi-Fi 越しにも出す。設計の説明は Console.h。
 *
 * このファイルの中の `Serial` だけは差し替えず、本物の USB シリアル（HWCDC）を指す。
 */

#define KATANORI_CONSOLE_IMPL
#include "Console.h"

#include <WiFi.h>
#include <esp_attr.h>
#include <esp_system.h>

namespace katanori {

Console console;

namespace {

WiFiServer server(KATANORI_CONSOLE_PORT);
WiFiClient client;
bool clientOpen = false;

// 合言葉の 1 行
char authLine[48];
size_t authLen = 0;
uint8_t authTries = 0;
// telnet の制御列（IAC = 0xFF で始まる 3 バイト）を読み捨てる残り
uint8_t iacSkip = 0;

// 出力の輪。printf は音声のタスクからも来るので、出し入れはロックの中で行う
constexpr size_t kOutSize = 8192;
uint8_t outBuf[kOutSize];
size_t outHead = 0;
size_t outTail = 0;
bool outDropped = false;
portMUX_TYPE outMux = portMUX_INITIALIZER_UNLOCKED;

// 入力の輪（main loop からしか触らない）
constexpr size_t kInSize = 256;
uint8_t inBuf[kInSize];
size_t inHead = 0;
size_t inTail = 0;

size_t inCount() {
    return (inHead + kInSize - inTail) % kInSize;
}

/*
 * ログの保存（2026-09-12・TODO A-4「ログの保存」）。
 * 流れたログの最後の約 3KB を、再起動をまたいで残るメモリ（RTC）に輪で書いておく。
 * 次の起動で取り出して `lastlog` で読める。勝手に再起動したときに「落ちる前に何が出ていたか」を
 * 後から見るため（2026-09-11 夜の再起動は理由が何も残っていなかった）。
 * ⚠ 電源そのものが落ちたとき（POWERON）は RTC も消えるので残らない。[STAT] は数が多く
 *    輪を押し流すので入れない。
 */
constexpr uint32_t kLogMagic = 0x4C4F4731; // "LOG1"
constexpr size_t kLogSize = 3072;
struct RtcLog {
    uint32_t magic;
    uint32_t head;
    uint32_t used;
    char buf[kLogSize];
};
RTC_NOINIT_ATTR RtcLog rtcLog;
char* prevLog = nullptr;
size_t prevLen = 0;

void rtcLogAppend(const uint8_t* buf, size_t n) {
    if (n >= 6 && memcmp(buf, "[STAT]", 6) == 0) {
        return;
    }
    for (size_t i = 0; i < n; ++i) {
        rtcLog.buf[rtcLog.head] = (char)buf[i];
        rtcLog.head = (rtcLog.head + 1) % kLogSize;
        if (rtcLog.used < kLogSize) {
            ++rtcLog.used;
        }
    }
}

void clearRings() {
    portENTER_CRITICAL(&outMux);
    outHead = outTail = 0;
    outDropped = false;
    portEXIT_CRITICAL(&outMux);
    inHead = inTail = 0;
}

} // namespace

void Console::begin(unsigned long baud) {
    Serial.begin(baud);
    // 前回のログを取り出してから輪を空にする（電源断のときは中身が不定なので捨てる）
    bool valid = esp_reset_reason() != ESP_RST_POWERON && rtcLog.magic == kLogMagic &&
                 rtcLog.head < kLogSize && rtcLog.used <= kLogSize;
    if (valid && rtcLog.used > 0) {
        prevLog = (char*)malloc(rtcLog.used + 1);
        if (prevLog) {
            size_t start = (rtcLog.head + kLogSize - rtcLog.used) % kLogSize;
            for (size_t i = 0; i < rtcLog.used; ++i) {
                prevLog[i] = rtcLog.buf[(start + i) % kLogSize];
            }
            prevLen = rtcLog.used;
            prevLog[prevLen] = '\0';
        }
    }
    portENTER_CRITICAL(&outMux);
    rtcLog.magic = kLogMagic;
    rtcLog.head = 0;
    rtcLog.used = 0;
    portEXIT_CRITICAL(&outMux);
}

void Console::printPreviousLog() {
    if (!prevLog) {
        console.println("[LOG] 前回のログは残っていません（電源が一度切れた・初めての起動など）");
        return;
    }
    console.printf("[LOG] ---- 前回の起動の最後の %u バイト ----\n", (unsigned)prevLen);
    // 今回の輪には入れない（入れると次に読んだとき前回と今回が混ざる）
    Serial.write((const uint8_t*)prevLog, prevLen);
    pushOut((const uint8_t*)prevLog, prevLen);
    console.println("\n[LOG] ---- ここまで ----");
}

Console::operator bool() const {
    return static_cast<bool>(Serial);
}

size_t Console::write(uint8_t c) {
    return write(&c, 1);
}

size_t Console::write(const uint8_t* buf, size_t n) {
    size_t written = Serial.write(buf, n);
    pushOut(buf, n);
    portENTER_CRITICAL(&outMux);
    rtcLogAppend(buf, n);
    portEXIT_CRITICAL(&outMux);
    return written ? written : n;
}

void Console::pushOut(const uint8_t* buf, size_t n) {
    if (!authed_) {
        return;
    }
    portENTER_CRITICAL(&outMux);
    for (size_t i = 0; i < n; ++i) {
        size_t next = (outHead + 1) % kOutSize;
        if (next == outTail) {
            outDropped = true;
            break;
        }
        outBuf[outHead] = buf[i];
        outHead = next;
    }
    portEXIT_CRITICAL(&outMux);
}

void Console::sendOut() {
    // 1 周回で送るのは 2KB まで。詰まっても main loop を長く止めない
    for (int round = 0; round < 4; ++round) {
        uint8_t chunk[512];
        size_t n = 0;
        bool dropped;
        portENTER_CRITICAL(&outMux);
        while (n < sizeof(chunk) && outTail != outHead) {
            chunk[n++] = outBuf[outTail];
            outTail = (outTail + 1) % kOutSize;
        }
        dropped = outDropped;
        outDropped = false;
        portEXIT_CRITICAL(&outMux);

        if (dropped) {
            client.print("\r\n[CON] (送りきれず、ここまでのログを一部捨てました)\r\n");
        }
        if (n == 0) {
            return;
        }
        client.write(chunk, n);
    }
}

void Console::takeInput() {
    while (client.available() > 0) {
        int b = client.read();
        if (b < 0) {
            break;
        }
        if (iacSkip > 0) {
            --iacSkip;
            continue;
        }
        if (b == 0xFF) {
            iacSkip = 2;
            continue;
        }

        if (!authed_) {
            if (b == '\r') {
                continue;
            }
            if (b != '\n') {
                if (authLen < sizeof(authLine) - 1) {
                    authLine[authLen++] = static_cast<char>(b);
                }
                continue;
            }
            authLine[authLen] = '\0';
            authLen = 0;
            if (strcmp(authLine, password_) == 0) {
                authed_ = true;
                client.print("OK\r\n");
                console.printf("[CON] Wi-Fi モニタが繋がりました（%s）\n",
                               client.remoteIP().toString().c_str());
            } else if (++authTries >= 3) {
                client.print("違います。切ります\r\n");
                client.stop();
                clientOpen = false;
                return;
            } else {
                client.print("違います。合言葉: ");
            }
            continue;
        }

        size_t next = (inHead + 1) % kInSize;
        if (next != inTail) { // あふれた分は捨てる（1 行 160 字の handleSerial より十分大きい）
            inBuf[inHead] = static_cast<uint8_t>(b);
            inHead = next;
        }
    }
}

void Console::loop() {
    if (WiFi.status() != WL_CONNECTED) {
        if (clientOpen) {
            client.stop();
            clientOpen = false;
            authed_ = false;
        }
        return;
    }

    if (!serverUp_) {
        server.begin();
        server.setNoDelay(true);
        serverUp_ = true;
        console.printf("[CON] Wi-Fi モニタの待受: %s port %d（最初に OTA と同じ合言葉を送る）\n",
                       WiFi.localIP().toString().c_str(), KATANORI_CONSOLE_PORT);
    }

    if (server.hasClient()) {
        WiFiClient incoming = server.available();
        if (clientOpen && client.connected()) {
            incoming.print("ほかの端末が使用中です\r\n");
            incoming.stop();
        } else {
            client = incoming;
            clientOpen = true;
            authed_ = false;
            authTries = 0;
            authLen = 0;
            iacSkip = 0;
            clearRings();
            client.print("katanori モニタ。合言葉: ");
        }
    }

    if (!clientOpen) {
        return;
    }
    if (!client.connected()) {
        bool was = authed_;
        authed_ = false;
        client.stop();
        clientOpen = false;
        if (was) {
            console.println("[CON] Wi-Fi モニタが切れました");
        }
        return;
    }
    takeInput();
    if (authed_ && clientOpen) {
        sendOut();
    }
}

void Console::suspend() {
    if (clientOpen) {
        client.stop();
        clientOpen = false;
    }
    authed_ = false;
    if (serverUp_) {
        server.end();
        serverUp_ = false;
    }
}

int Console::available() {
    int n = Serial.available();
    if (n > 0) {
        return n;
    }
    return static_cast<int>(inCount());
}

int Console::read() {
    if (Serial.available() > 0) {
        return Serial.read();
    }
    if (inTail == inHead) {
        return -1;
    }
    uint8_t b = inBuf[inTail];
    inTail = (inTail + 1) % kInSize;
    return b;
}

int Console::peek() {
    if (Serial.available() > 0) {
        return Serial.peek();
    }
    if (inTail == inHead) {
        return -1;
    }
    return inBuf[inTail];
}

void Console::flush() {
    Serial.flush();
}

} // namespace katanori
