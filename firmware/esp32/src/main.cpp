/*
 * ============================================================================
 *  カタノリロボ 実機ファームウェア (XIAO ESP32S3 + SSD1306 OLED)
 *
 *  Stage 1: 「顔が出る」まで
 *    - I2Cスキャンで OLED の実在を確認 (配線チェック)
 *    - firmware/core の RobotCore を実機で回して OLED に顔を描画
 *    - シリアル / BOOTボタンから状態遷移イベントを注入して目視確認
 *
 *  音声(I2S)・Wi-Fi・WebSocket は Stage 2 以降で追加する。
 *  このファイルが唯一の「実機依存コード」であり、firmware/core は
 *  シミュレーターとまったく同じソースを共有している。
 * ============================================================================
 */

#include <Arduino.h>
#include <Wire.h>
#include <U8g2lib.h>

#include "IHal.h"
#include "RobotCore.h"
#include "NetLink.h"
#include "AudioIo.h"

// ---------------------------------------------------------------------------
// ボード設定
// ---------------------------------------------------------------------------

// XIAO ESP32S3 の I2C: D4 = GPIO5 (SDA) / D5 = GPIO6 (SCL)
// ReSpeaker Lite に直挿しした場合は Grove I2C コネクタがこの2本に出ている。
#ifndef KATANORI_I2C_SDA
#define KATANORI_I2C_SDA 5
#endif
#ifndef KATANORI_I2C_SCL
#define KATANORI_I2C_SCL 6
#endif

// SSD1306 のI2Cアドレス (7bit)。基板によっては 0x3D の個体もある。
#ifndef KATANORI_OLED_ADDR
#define KATANORI_OLED_ADDR 0x3C
#endif

// XIAO ESP32S3 の BOOT ボタン (押下でLOW)
#ifndef KATANORI_BOOT_BUTTON
#define KATANORI_BOOT_BUTTON 0
#endif

// XIAO ESP32S3 のユーザーLED (GPIO21)。アクティブLOW = LOWで点灯。
// 未設定のままだと点きっぱなしで眩しいので起動時に明示的に消す。
// 仕様書では「通信中のステータス表示」に使う予定なので Stage 2 で点灯制御を入れる。
#ifndef KATANORI_USER_LED
#define KATANORI_USER_LED 21
#endif

// 描画レート。128x64 の全面転送は 400kHz I2C で約23ms かかるため、
// 20FPS(50ms)がこの構成の実用上限。上げたい場合は I2C を 1MHz にする。
static constexpr uint32_t FRAME_INTERVAL_MS = 50;
// 音声受信中はこちらへ落とす（描画がCPUを占有して受信を落とすのを防ぐ）
static constexpr uint32_t FRAME_INTERVAL_SLOW_MS = 120;

// DisplayBuffer は MSB(0x80)=左ピクセル。U8g2 の drawBitmap() は U8glib互換の
// MSB-first なのでそのまま渡せる。万一 8ピクセル単位で左右反転して見えたら
// この定義を 1 にして XBM(LSB-first)へ変換する経路へ切り替える。
#ifndef KATANORI_DISPLAY_BIT_REVERSE
#define KATANORI_DISPLAY_BIT_REVERSE 0
#endif

// ---------------------------------------------------------------------------
// グローバル
// ---------------------------------------------------------------------------

static U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, /* reset= */ U8X8_PIN_NONE);

#if KATANORI_DISPLAY_BIT_REVERSE
static uint8_t reverseByte(uint8_t b) {
    b = static_cast<uint8_t>((b & 0xF0) >> 4 | (b & 0x0F) << 4);
    b = static_cast<uint8_t>((b & 0xCC) >> 2 | (b & 0x33) << 2);
    b = static_cast<uint8_t>((b & 0xAA) >> 1 | (b & 0x55) << 1);
    return b;
}
#endif

class Esp32Hal : public katanori::IHal {
public:
    uint32_t millis() override {
        return ::millis();
    }

    float getMicLevel() override {
        return katanori::audioIo.micLevel();
    }

    void flushDisplay(const uint8_t* fb) override {
        u8g2.clearBuffer();
#if KATANORI_DISPLAY_BIT_REVERSE
        static uint8_t xbm[katanori::DisplayBuffer::BUFFER_SIZE];
        for (size_t i = 0; i < katanori::DisplayBuffer::BUFFER_SIZE; ++i) {
            xbm[i] = reverseByte(fb[i]);
        }
        u8g2.drawXBM(0, 0, katanori::DisplayBuffer::W, katanori::DisplayBuffer::H, xbm);
#else
        u8g2.drawBitmap(0, 0,
                        katanori::DisplayBuffer::W / 8,
                        katanori::DisplayBuffer::H,
                        fb);
#endif
        u8g2.sendBuffer();
    }

    void log(const char* msg) override {
        Serial.println(msg);
    }
};

static Esp32Hal hal;
static katanori::RobotCore robot(hal);

// ---------------------------------------------------------------------------
// 対話フロー
//
// wrapper.py が確立した手順をそのまま実機へ移したもの:
//   ウェイクワード -> 録音してDOへ送る -> audioStreamEnd で発話終了を確定
//   -> 応答音声を再生 -> turnComplete + 再生完了で IDLE へ戻る
// ---------------------------------------------------------------------------

// 応答音声の受信中か（顔をSPEAKにするため）
static bool speaking = false;
// Geminiがターンを終えたか。再生キューが空になるまで IDLE には戻らない。
static bool turnComplete = false;
// audioStreamEnd を送った時刻（応答遅延の実測用）
static uint32_t streamEndMs = 0;

/**
 * 状態機械を目的の状態まで歩かせる。
 *
 * StateMachine は IDLE -> LISTEN -> THINK -> SPEAK の一本道で、途中の
 * イベントを飛ばせない。一方 Gemini は自前のVADで勝手にターンを進めるため、
 * こちらの状態と食い違う（例: LISTENが10秒でタイムアウトしてIDLEに戻った後に
 * 応答音声が届く）。顔を実際の会話に追従させるため、必要なイベントを
 * 順に注入して追いつかせる。
 */
static void driveTo(katanori::RobotState target) {
    for (int guard = 0; guard < 4 && robot.state() != target; ++guard) {
        switch (robot.state()) {
        case katanori::RobotState::IDLE:
            robot.injectEvent(katanori::RobotEvent::WAKE_WORD);
            break;
        case katanori::RobotState::LISTEN:
            robot.injectEvent(katanori::RobotEvent::SPEECH_END);
            break;
        case katanori::RobotState::THINK:
            robot.injectEvent(katanori::RobotEvent::RESPONSE_READY);
            break;
        case katanori::RobotState::SPEAK:
            robot.injectEvent(katanori::RobotEvent::SPEECH_DONE);
            break;
        }
    }
}

/** DOから届いた生PCM。そのまま再生キューへ積むだけ。 */
static void onAudio(const int16_t* pcm, size_t samples) {
    if (!speaking) {
        speaking = true;
        turnComplete = false;
        if (streamEndMs != 0) {
            Serial.printf("[TURN] 発話終了 -> 応答開始 %.2f秒\n",
                          (millis() - streamEndMs) / 1000.0f);
            streamEndMs = 0;
        }
        driveTo(katanori::RobotState::SPEAK);
    }
    katanori::audioIo.play(pcm, samples);
}

/** DOから届いた制御JSON。パーサは積まず、必要な語だけ拾う。 */
static void onControl(const char* json) {
    // 割り込み: マイクがスピーカー音を拾うと Gemini がこれを返す。
    // 未再生ぶんを捨てないと、古い応答が延々と流れ続ける。
    if (strstr(json, "\"interrupted\"") != nullptr) {
        Serial.println("[TURN] 割り込み検知 — 再生を中断します");
        katanori::audioIo.stopPlayback();
        speaking = false;
        turnComplete = false;
        robot.injectEvent(katanori::RobotEvent::SPEECH_DONE);
        return;
    }
    if (strstr(json, "\"turnComplete\"") != nullptr) {
        turnComplete = true;
    }

    // GeminiのVADをそのまま顔に反映する。ボタンを押さなくても
    // 喋り始め・喋り終わりで表情が変わる。
    if (strstr(json, "\"speechState\":\"SPEECH\"") != nullptr) {
        if (!speaking) {
            driveTo(katanori::RobotState::LISTEN);
        }
    } else if (strstr(json, "\"speechState\":\"NON_SPEECH\"") != nullptr) {
        if (!speaking && robot.state() == katanori::RobotState::LISTEN) {
            robot.injectEvent(katanori::RobotEvent::SPEECH_END); // -> THINK
        }
    }
}

/** ウェイクワード相当。接続してから録音を始める。 */
static void startTurn() {
    if (!katanori::netLink.wsConnected()) {
        Serial.println("[TURN] 未接続です。'wifi' と 'c' で繋いでください");
        return;
    }
    streamEndMs = 0;
    katanori::audioIo.startRecording();
    robot.injectEvent(katanori::RobotEvent::WAKE_WORD);
    Serial.println("[TURN] 録音開始（'2' または BOOTボタンで終了）");
}

/** 発話終了。audioStreamEnd を送ると Gemini が応答生成を始める。 */
static void endTurn() {
    if (!katanori::audioIo.isRecording()) {
        return;
    }
    katanori::audioIo.stopRecording();
    robot.injectEvent(katanori::RobotEvent::SPEECH_END);

    // clientContent+turnComplete はVADが発話中と認識していると無視されて
    // ハングする。audioStreamEnd を使うこと（wrapper.py で確定済みの知見）
    if (katanori::netLink.sendControl("{\"realtimeInput\":{\"audioStreamEnd\":true}}")) {
        streamEndMs = millis();
        Serial.println("[TURN] audioStreamEnd 送信（応答待ち）");
    }
}

/** マイクを読んでDOへ送る。main loop から毎回呼ぶ。 */
static void pumpMic() {
    static int16_t buf[512];

    if (!katanori::audioIo.isRecording()) {
        return;
    }
    size_t n = katanori::audioIo.readMic(buf, sizeof(buf) / sizeof(buf[0]));
    if (n == 0) {
        return;
    }

    // エコーガード: 再生中はマイクを送らない。
    // 送ると自分の声で Gemini が割り込み判定して会話が破綻する。
    // (ReSpeaker Lite のハードウェアAECが効けば不要になるはずの暫定措置)
    if (katanori::audioIo.isPlaying()) {
        return;
    }
    katanori::netLink.sendAudio(buf, n);
}

/** ターンの終了判定。Geminiが喋り終え、再生キューも空になったら IDLE へ。 */
static void pumpTurnState() {
    if (speaking && turnComplete && !katanori::audioIo.isPlaying()) {
        speaking = false;
        turnComplete = false;
        driveTo(katanori::RobotState::IDLE);
        Serial.println("[TURN] 応答の再生が完了しました");
    }
}

// ---------------------------------------------------------------------------
// ヘルパー
// ---------------------------------------------------------------------------

static const char* stateName(katanori::RobotState s) {
    switch (s) {
    case katanori::RobotState::IDLE:   return "IDLE";
    case katanori::RobotState::LISTEN: return "LISTEN";
    case katanori::RobotState::THINK:  return "THINK";
    case katanori::RobotState::SPEAK:  return "SPEAK";
    }
    return "?";
}

/** チップ・メモリ情報。ブート時に取りこぼしても 'i' で再表示できる。 */
static void printBootInfo() {
    Serial.printf("[INFO] chip=%s rev=%d cores=%d cpu=%dMHz\n",
                  ESP.getChipModel(), ESP.getChipRevision(),
                  ESP.getChipCores(), getCpuFrequencyMhz());
    Serial.printf("[INFO] flash=%uKB heap=%uKB psram=%uKB\n",
                  ESP.getFlashChipSize() / 1024,
                  ESP.getHeapSize() / 1024,
                  ESP.getPsramSize() / 1024);
    Serial.printf("[INFO] I2C SDA=GPIO%d SCL=GPIO%d  OLED addr=0x%02X\n",
                  KATANORI_I2C_SDA, KATANORI_I2C_SCL, KATANORI_OLED_ADDR);

    if (ESP.getPsramSize() == 0) {
        // Stage 3 の音声バッファ + TLS で必ず効いてくるのでここで警告しておく
        Serial.println("[INFO] !! PSRAM が見えていません。platformio.ini の");
        Serial.println("[INFO]    board_build.arduino.memory_type = qio_opi を確認してください。");
    }
}

/**
 * I2Cバスを総なめして応答するアドレスを列挙する。
 * 「配線が正しいか」を最初に切り分けるための最重要ログ。
 * ここで 0x3C が出なければソフトの問題ではなく配線か電源の問題。
 */
static bool scanI2c() {
    bool foundOled = false;
    int count = 0;

    Serial.println("[I2C] scanning bus...");
    for (uint8_t addr = 1; addr < 127; ++addr) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0) {
            Serial.printf("[I2C]   device found at 0x%02X\n", addr);
            ++count;
            if (addr == KATANORI_OLED_ADDR) {
                foundOled = true;
            }
        }
    }

    if (count == 0) {
        Serial.println("[I2C] !! no devices found.");
        Serial.println("[I2C]    SDA/SCL/VCC/GND の配線と、OLEDへの給電を確認してください。");
    } else if (!foundOled) {
        Serial.printf("[I2C] !! 0x%02X (OLED) が見つかりません。上の一覧のアドレスを\n",
                      KATANORI_OLED_ADDR);
        Serial.println("[I2C]    KATANORI_OLED_ADDR に指定し直してください (0x3D の個体があります)。");
    }
    return foundOled;
}

/** D番号 -> GPIO番号 (XIAO ESP32S3)。範囲外は -1。 */
static int gpioForD(int d) {
    static const int kMap[] = { 1, 2, 3, 4, 5, 6, 43, 44, 7, 8, 9 }; // D0..D10
    if (d < 0 || d > 10) {
        return -1;
    }
    return kMap[d];
}

/**
 * 簡易電圧計。テスターが無い環境で「そこに電気が来ているか」を判定するために
 * ESP32 の ADC を使う。測りたい点から指定ピンへジャンパーを1本渡して実行する。
 *
 * 【重要】入力は 3.3V まで。5V の点を繋ぐとピンが壊れる。
 */
static void measureVoltage(int d) {
    int gpio = gpioForD(d);
    if (gpio < 0) {
        Serial.println("[MEAS] D0〜D10 で指定してください (例: v0)");
        return;
    }
    if (gpio == 43 || gpio == 44) {
        Serial.printf("[MEAS] D%d(GPIO%d) はADC非対応です。D0〜D5 か D8〜D10 を使ってください。\n",
                      d, gpio);
        return;
    }

    uint32_t mv = analogReadMilliVolts(gpio);
    Serial.printf("[MEAS] D%d(GPIO%d) = %u mV", d, gpio, mv);
    if (mv < 200) {
        Serial.println("  -> 電圧が来ていません（未接続 / 給電なし）");
    } else if (mv > 2800) {
        Serial.println("  -> 3.3V級。給電OK");
    } else {
        Serial.println("  -> 中途半端な電圧。接触不良かプルアップ経由の可能性");
    }

    // I2Cピンを測った場合はバスを張り直す
    if (gpio == KATANORI_I2C_SDA || gpio == KATANORI_I2C_SCL) {
        Wire.end();
        Wire.begin(KATANORI_I2C_SDA, KATANORI_I2C_SCL, 400000);
        Serial.println("[MEAS] I2Cバスを再初期化しました");
    }
}

/**
 * 簡易導通チェッカー。内部プルアップを有効にして読むだけ。
 * GND に落ちていれば LOW、浮いていれば HIGH。
 * 「GNDがちゃんと繋がっているか」はADCでは測れないのでこちらで見る。
 */
static void testGround(int d) {
    int gpio = gpioForD(d);
    if (gpio < 0) {
        Serial.println("[MEAS] D0〜D10 で指定してください (例: g1)");
        return;
    }

    pinMode(gpio, INPUT_PULLUP);
    delay(5);
    bool low = (digitalRead(gpio) == LOW);
    Serial.printf("[MEAS] D%d(GPIO%d) GND導通: %s\n", d, gpio,
                  low ? "あり (LOW)  -> GNDに繋がっています"
                      : "なし (HIGH) -> 浮いています");

    if (gpio == KATANORI_I2C_SDA || gpio == KATANORI_I2C_SCL) {
        Wire.end();
        Wire.begin(KATANORI_I2C_SDA, KATANORI_I2C_SCL, 400000);
        Serial.println("[MEAS] I2Cバスを再初期化しました");
    }
}

/**
 * XIAO ESP32S3 の外部ピン D0..D10 の全組み合わせを I2C として叩き、
 * SSD1306 (0x3C / 0x3D) がぶら下がっているピンペアを探す。
 *
 * 「どのピンに繋いだか分からない / 繋いだつもりのピンと違う」を潰すための最終手段。
 * VCC と GND さえ正しければ、SDA/SCL がどこであっても必ず見つかる。
 * 逆にここで何も出なければ、原因は信号線ではなく給電かモジュール故障に絞られる。
 */
static void sweepI2cPins() {
    struct PinDef { const char* name; int gpio; };
    static const PinDef pins[] = {
        {"D0",  1}, {"D1",  2}, {"D2",  3}, {"D3",  4}, {"D4",  5}, {"D5",  6},
        {"D6", 43}, {"D7", 44}, {"D8",  7}, {"D9",  8}, {"D10", 9},
    };
    const size_t n = sizeof(pins) / sizeof(pins[0]);

    Serial.println("[SWEEP] D0..D10 の全組み合わせで 0x3C / 0x3D を探索します...");
    int hits = 0;

    for (size_t s = 0; s < n; ++s) {
        for (size_t c = 0; c < n; ++c) {
            if (s == c) {
                continue;
            }
            Wire.end();
            if (!Wire.begin(pins[s].gpio, pins[c].gpio, 100000)) {
                continue;
            }
            for (uint8_t addr = 0x3C; addr <= 0x3D; ++addr) {
                Wire.beginTransmission(addr);
                if (Wire.endTransmission() == 0) {
                    Serial.printf("[SWEEP] >>> HIT  SDA=%s(GPIO%d)  SCL=%s(GPIO%d)  addr=0x%02X\n",
                                  pins[s].name, pins[s].gpio,
                                  pins[c].name, pins[c].gpio, addr);
                    ++hits;
                }
            }
        }
    }

    // 元のバス設定へ戻す
    Wire.end();
    Wire.begin(KATANORI_I2C_SDA, KATANORI_I2C_SCL, 400000);

    if (hits == 0) {
        Serial.println("[SWEEP] 見つかりませんでした。信号線ではなく給電側の問題です。");
        Serial.println("[SWEEP]   - OLED の VCC-GND 間の電圧を測ってください (3.3V か 5V が出ているか)");
        Serial.println("[SWEEP]   - ブレッドボードの電源レールに給電されているか");
        Serial.println("[SWEEP]   - モジュール自体の故障");
    } else {
        Serial.printf("[SWEEP] %d件ヒットしました。platformio.ini の build_flags に\n", hits);
        Serial.println("[SWEEP]   -DKATANORI_I2C_SDA=<GPIO番号> -DKATANORI_I2C_SCL=<GPIO番号>");
        Serial.println("[SWEEP] を追加して書き込み直してください。");
    }
}

/**
 * OLEDの自己診断。DisplayBuffer を一切通さず U8g2 の描画関数だけで
 * 枠・塗り・文字を出す。
 *   ここで何か見える  -> 配線とOLED初期化はOK。問題は DisplayBuffer の転送側
 *   ここでも真っ暗    -> 配線 / I2Cアドレス / 給電の問題
 * この二分岐が Stage 1 のデバッグで一番効く。
 */
static uint32_t selfTestUntilMs = 0;

static void runSelfTest() {
    Serial.println("[TEST] 自己診断パターンを5秒表示します (U8g2直描画)");
    u8g2.clearBuffer();
    u8g2.drawFrame(0, 0, 128, 64);
    u8g2.drawBox(6, 6, 18, 18);
    u8g2.drawLine(0, 63, 127, 0);
    u8g2.setFont(u8g2_font_6x10_tf);
    u8g2.drawStr(34, 26, "KATANORI");
    u8g2.drawStr(34, 40, "SELFTEST");
    u8g2.sendBuffer();
    selfTestUntilMs = millis() + 5000;
}

static void printHelp() {
    Serial.println("---------------------------------------------");
    Serial.println(" 会話");
    Serial.println("   1 : 話し始める（録音開始してDOへ送る）");
    Serial.println("   2 : 話し終わる（audioStreamEnd を送って応答を待つ）");
    Serial.println("   au  : 音声の状態を表示");
    Serial.println("   mic : マイク単独テスト(5秒) ch0/ch1のレベルを測る");
    Serial.println("   vol <0-100> : 再生音量（既定35）");
    Serial.println("   beep : スピーカー単独テスト(440Hzを1秒, 振幅600)");
    Serial.println("   beep2: 同上だが振幅4000 ※イヤホンを耳に着けないこと");
    Serial.println("   scan2: I2S設定の総当たり（無音状態で実行）");
    Serial.println("   i2s <m|s> <i2s|msb> <16|32> : I2S設定を実行時に切替");
    Serial.println(" 顔の状態を直接いじる（音声なしの確認用）");
    Serial.println("   3 : RESPONSE_READY (THINK  -> SPEAK)");
    Serial.println("   4 : SPEECH_DONE    (SPEAK  -> IDLE)");
    Serial.println("   s : I2Cバスを再スキャン");
    Serial.println("   a : D0..D10 の全ピン組み合わせでOLEDを探索");
    Serial.println("   vN: D<N>ピンの電圧を測る    (例: v0)  ※入力は3.3Vまで");
    Serial.println("   gN: D<N>ピンのGND導通を見る (例: g1)");
    Serial.println("   l : ユーザーLEDの点灯/消灯を切り替え");
    Serial.println("   r : OLEDを再初期化（配線を直した後に使う）");
    Serial.println("   R : ソフトウェア再起動");
    Serial.println("   t : OLED自己診断パターンを表示");
    Serial.println("   i : ブート情報を再表示");
    Serial.println("   ? : このヘルプ");
    Serial.println(" BOOTボタン: WAKE_WORD を注入");
    Serial.println("--- ネットワーク ---------------------------");
    Serial.println("   ssid <名前>       : Wi-Fi の SSID を保存");
    Serial.println("   pass <パスワード> : Wi-Fi のパスワードを保存");
    Serial.println("   forget            : 保存したWi-Fi設定を消去");
    Serial.println("   scan              : 周囲のAPを一覧表示");
    Serial.println("   wifi              : Wi-Fiへ接続");
    Serial.println("   wifioff           : Wi-Fiを切断");
    Serial.println("   c                 : Durable Object へ WebSocket 接続");
    Serial.println("   d                 : WebSocket を切断");
    Serial.println("   n                 : ネットワーク状態を表示");
    Serial.println("---------------------------------------------");
}

/**
 * シリアルからのイベント注入。
 * wrapper.py が使っている "CMD:SPEAK_START" / "CMD:SPEAK_END" も受理しておく。
 * Stage 3 で PC 側ラッパーを実機に向けて動作確認する際にそのまま使えるため。
 */
static void handleSerial() {
    // SSIDとパスワードを受け取るため余裕を持たせる
    static char line[160];
    static size_t len = 0;

    while (Serial.available() > 0) {
        char c = static_cast<char>(Serial.read());

        if (c == '\r') {
            continue;
        }
        if (c != '\n') {
            if (len < sizeof(line) - 1) {
                line[len++] = c;
            }
            continue;
        }

        line[len] = '\0';
        len = 0;

        if (strcmp(line, "1") == 0) {
            startTurn();
        } else if (strcmp(line, "2") == 0) {
            endTurn();
        } else if (strcmp(line, "3") == 0) {
            robot.injectEvent(katanori::RobotEvent::RESPONSE_READY);
        } else if (strcmp(line, "4") == 0) {
            robot.injectEvent(katanori::RobotEvent::SPEECH_DONE);
        } else if (strcmp(line, "CMD:SPEAK_START") == 0) {
            robot.injectEvent(katanori::RobotEvent::RESPONSE_READY);
        } else if (strcmp(line, "CMD:SPEAK_END") == 0) {
            robot.injectEvent(katanori::RobotEvent::SPEECH_DONE);

        // --- ネットワーク (単文字コマンドより先に判定すること) ---
        } else if (strncmp(line, "ssid ", 5) == 0) {
            katanori::netLink.setSsid(line + 5);
        } else if (strncmp(line, "pass ", 5) == 0) {
            katanori::netLink.setPassword(line + 5);
        } else if (strcmp(line, "forget") == 0) {
            katanori::netLink.clearCredentials();
        } else if (strcmp(line, "scan") == 0) {
            katanori::netLink.scan();
        } else if (strcmp(line, "wifi") == 0) {
            katanori::netLink.wifiConnect();
        } else if (strcmp(line, "wifioff") == 0) {
            katanori::netLink.wifiDisconnect();
        } else if (strcmp(line, "c") == 0) {
            katanori::netLink.wsConnect();
        } else if (strcmp(line, "d") == 0) {
            katanori::netLink.wsDisconnect();
        } else if (strcmp(line, "n") == 0) {
            katanori::netLink.printStatus();
        } else if (strcmp(line, "au") == 0) {
            katanori::audioIo.printStatus();
        } else if (strcmp(line, "mic") == 0) {
            katanori::audioIo.micTest(5000);
        } else if (strcmp(line, "beep") == 0) {
            katanori::audioIo.toneTest(1000, 440, 600);
        } else if (strcmp(line, "beep2") == 0) {
            katanori::audioIo.toneTest(1000, 440, 4000);
        } else if (strncmp(line, "vol ", 4) == 0) {
            katanori::audioIo.setGain(atoi(line + 4) / 100.0f);
        } else if (strcmp(line, "scan2") == 0) {
            katanori::audioIo.scanConfigs();
        } else if (strncmp(line, "i2s ", 4) == 0) {
            // 例: "i2s s msb 32"  (master/slave, i2s/msb, 16/32)
            bool slave = (line[4] == 's');
            bool msb = (strstr(line, "msb") != nullptr);
            int bits = (strstr(line, "32") != nullptr) ? 32 : 16;
            if (katanori::audioIo.applyConfig(slave, msb, bits)) {
                Serial.printf("[I2S] %s / %s / %dbit に切り替えました\n",
                              slave ? "SLAVE" : "MASTER", msb ? "MSB" : "標準I2S", bits);
            }

        } else if (strcmp(line, "s") == 0) {
            scanI2c();
        } else if (strcmp(line, "a") == 0) {
            sweepI2cPins();
        } else if (strcmp(line, "r") == 0) {
            // 起動時にOLEDが繋がっていなかった場合、初期化コマンド列がパネルに
            // 届いていない。配線を直した後にリセットボタンを押さずやり直すための口。
            Serial.println("[OLED] 再初期化します");
            if (u8g2.begin()) {
                Serial.println("[OLED] SSD1306 init ok");
            } else {
                Serial.println("[OLED] !! init failed");
            }
            u8g2.setBusClock(400000);
            runSelfTest();
        } else if (strcmp(line, "R") == 0) {
            Serial.println("[SYS] 再起動します");
            Serial.flush();
            delay(50);
            ESP.restart();
        } else if (strcmp(line, "l") == 0) {
            static bool ledOn = false;
            ledOn = !ledOn;
            digitalWrite(KATANORI_USER_LED, ledOn ? LOW : HIGH);
            Serial.printf("[LED] ユーザーLED(GPIO%d) = %s\n",
                          KATANORI_USER_LED, ledOn ? "点灯" : "消灯");
        } else if (line[0] == 'v' && isdigit((unsigned char)line[1])) {
            measureVoltage(atoi(line + 1));
        } else if (line[0] == 'g' && isdigit((unsigned char)line[1])) {
            testGround(atoi(line + 1));
        } else if (strcmp(line, "t") == 0) {
            runSelfTest();
        } else if (strcmp(line, "i") == 0) {
            printBootInfo();
        } else if (line[0] == '?') {
            printHelp();
        } else if (line[0] != '\0') {
            Serial.printf("[CMD] unknown: \"%s\"  ('?' でヘルプ)\n", line);
        }
    }
}

/** BOOTボタン: 立ち下がりで WAKE_WORD を注入 (30msデバウンス) */
static void handleButton() {
    static bool lastPressed = false;
    static uint32_t lastChangeMs = 0;

    bool pressed = (digitalRead(KATANORI_BOOT_BUTTON) == LOW);
    uint32_t now = millis();

    if (pressed != lastPressed && (now - lastChangeMs) > 30) {
        lastChangeMs = now;
        lastPressed = pressed;
        if (pressed) {
            // 押すたびに 話し始め / 話し終わり を切り替える。
            // Stage 4 でウェイクワード検出に置き換える。
            if (katanori::audioIo.isRecording()) {
                Serial.println("[BTN] BOOT -> 発話終了");
                endTurn();
            } else {
                Serial.println("[BTN] BOOT -> 発話開始");
                startTurn();
            }
        }
    }
}

// ---------------------------------------------------------------------------
// setup / loop
// ---------------------------------------------------------------------------

void setup() {
    Serial.begin(115200);

    // ネイティブUSB CDC はホストが開くまで出力が捨てられる。
    // ブートログを取りこぼさないよう最大3秒待つ (未接続でも先へ進む)。
    uint32_t t0 = millis();
    while (!Serial && (millis() - t0) < 3000) {
        delay(10);
    }

    Serial.println();
    Serial.println("=============================================");
    Serial.println(" katanori firmware - Stage 1 (face only)");
    Serial.println("=============================================");
    printBootInfo();

    pinMode(KATANORI_BOOT_BUTTON, INPUT_PULLUP);

    // ユーザーLEDを消灯 (アクティブLOWなのでHIGHで消える)
    pinMode(KATANORI_USER_LED, OUTPUT);
    digitalWrite(KATANORI_USER_LED, HIGH);

    // U8g2 が内部で呼ぶ Wire.begin() は既定ピンを使うため、
    // 先に setPins() でピンを確定させておく。
    Wire.setPins(KATANORI_I2C_SDA, KATANORI_I2C_SCL);
    Wire.begin();
    Wire.setClock(400000);
    Serial.printf("[I2C] SDA=GPIO%d SCL=GPIO%d @400kHz\n",
                  KATANORI_I2C_SDA, KATANORI_I2C_SCL);

    bool oledOk = scanI2c();

    u8g2.setI2CAddress(KATANORI_OLED_ADDR << 1);
    u8g2.setBusClock(400000);
    if (u8g2.begin()) {
        Serial.println("[OLED] SSD1306 init ok");
    } else {
        Serial.println("[OLED] !! init failed");
    }
    if (!oledOk) {
        Serial.println("[OLED] (I2Cスキャンで見つからなかったため描画されない可能性があります)");
    }

    katanori::netLink.begin();
    katanori::netLink.setAudioSink(onAudio);
    katanori::netLink.setControlSink(onControl);

    if (!katanori::audioIo.begin()) {
        Serial.println("[I2S] !! 音声の初期化に失敗しました。顔の表示だけ動きます");
    }

    printHelp();

    // 起動直後は自己診断パターンを出す。ネイティブUSB CDC ではブートログが
    // モニタ接続前に流れてしまうため、「電源を入れたら画面に何か出る」ことを
    // ログに頼らず目視できるようにしておく。
    runSelfTest();

    Serial.println("[BOOT] ready. 自己診断の後、顔が表示されれば Stage 1 完了です。");
}

void loop() {
    handleSerial();
    handleButton();
    katanori::netLink.loop();
    pumpMic();
    pumpTurnState();

    // 仕様書どおり、内蔵LEDを通信中のステータス表示に使う
    static bool lastWsState = false;
    bool wsNow = katanori::netLink.wsConnected();
    if (wsNow != lastWsState) {
        lastWsState = wsNow;
        digitalWrite(KATANORI_USER_LED, wsNow ? LOW : HIGH); // アクティブLOW
    }

    static uint32_t lastFrameMs = 0;
    static uint32_t lastStatMs = 0;
    static uint32_t frameCount = 0;
    static katanori::RobotState lastState = katanori::RobotState::IDLE;

    uint32_t now = millis();

    // 自己診断パターン表示中は顔の描画で上書きしない
    if (static_cast<int32_t>(now - selfTestUntilMs) < 0) {
        delay(1);
        return;
    }

    // 応答音声の受信中は描画を間引く。OLEDの全面転送は約29msブロックするので、
    // 20FPSのままだと時間の半分以上を描画に取られて受信が追いつかない。
    uint32_t interval = katanori::audioIo.isPlaying() ? FRAME_INTERVAL_SLOW_MS
                                                      : FRAME_INTERVAL_MS;
    if ((now - lastFrameMs) >= interval) {
        lastFrameMs = now;
        robot.tick();
        ++frameCount;

        katanori::RobotState s = robot.state();
        if (s != lastState) {
            Serial.printf("[STATE] %s -> %s\n", stateName(lastState), stateName(s));
            lastState = s;
        }
    }

    // 5秒ごとの生存確認。描画が固まっていないか / メモリが減り続けていないかを見る
    if ((now - lastStatMs) >= 5000) {
        Serial.printf("[STAT] state=%s fps=%.1f heap=%uB\n",
                      stateName(robot.state()),
                      frameCount * 1000.0f / (now - lastStatMs),
                      ESP.getFreeHeap());
        lastStatMs = now;
        frameCount = 0;
    }

    delay(1);
}
