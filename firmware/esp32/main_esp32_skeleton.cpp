/*
 * ============================================================================
 * [参考実装] ESP32S3 + U8g2 + ReSpeaker Lite 用スケルトン
 * NOTE: このファイルは実機移植時の参考コードです。PCシミュレータービルドには含まれません。
 * ============================================================================
 */

#if 0 // 実機ビルド時に Arduino IDE または PlatformIO 環境へ移植して有効化してください

#include <Arduino.h>
#include <U8g2lib.h>
#include "IHal.h"
#include "RobotCore.h"

// OLED インスタンス例 (I2C SSD1306 128x64)
U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, /* reset=*/ U8X8_PIN_NONE);

class Esp32Hal : public katanori::IHal {
public:
    Esp32Hal() {}

    uint32_t millis() override {
        return ::millis();
    }

    float getMicLevel() override {
        // ReSpeaker Lite や ADC から音量を取得して 0.0f ~ 1.0f に正規化
        return 0.0f;
    }

    void flushDisplay(const uint8_t* fb) override {
        // 128x64 モノクロビットマップを描画
        u8g2.clearBuffer();
        u8g2.drawXBM(0, 0, 128, 64, fb); // ※ビット順序の変換が必要な場合があります
        u8g2.sendBuffer();
    }

    void log(const char* msg) override {
        Serial.println(msg);
    }
};

static Esp32Hal hal;
static katanori::RobotCore robot(hal);

void setup() {
    Serial.begin(115200);
    u8g2.begin();
    hal.log("Esp32Hal initialized.");
}

void loop() {
    robot.tick();
    delay(10);
}

#endif