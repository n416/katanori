/*
 * XMOSファーム版数の読み取り — USB版かI2S版かを白黒付ける。
 *
 * 【根拠】公式例 xiao_i2c_get_register_value.ino:
 *   XMOSはI2Cアドレス 0x42。リソースID 0xF0・コマンド 0xD8 で
 *   版数3バイト (major.minor.patch) を返す。先頭1バイトはステータス。
 *
 * 【判定】1.x.y → I2S版 ／ 2.x.y → USB版 ／ ACKなし → それ自体が異常
 *
 * I2SもWi-Fiも触らない。I2C(D4=GPIO5 SDA / D5=GPIO6 SCL)だけ。音は出ない。
 */
#include <Arduino.h>
#include <Wire.h>

static const uint8_t kXmosAddr  = 0x42;
static const uint8_t kCodecAddr = 0x18;  // 対照。ここがACKすればバス自体は生きている

static void scanBus() {
    Serial.println("--- I2Cスキャン ---");
    int found = 0;
    for (uint8_t a = 1; a < 127; a++) {
        Wire.beginTransmission(a);
        if (Wire.endTransmission() == 0) {
            Serial.printf("  0x%02X ACK%s\n", a,
                          a == kXmosAddr ? "  ← XMOS制御" :
                          a == kCodecAddr ? "  ← コーデック(AIC3204)" : "");
            found++;
        }
    }
    if (found == 0) Serial.println("  応答なし（バスが沈黙）");
}

static void readVersion() {
    Serial.println("--- XMOS版数 (0x42 / 0xF0 0xD8) ---");
    Wire.beginTransmission(kXmosAddr);
    Wire.write((uint8_t)0xF0);   // リソースID
    Wire.write((uint8_t)0xD8);   // コマンド: バージョン
    Wire.write((uint8_t)4);      // 読み出し長 (ステータス1 + 版数3)
    const uint8_t err = Wire.endTransmission();
    if (err != 0) {
        Serial.printf("  書き込み失敗 (Wireエラー %u) — 0x42が居ない\n", err);
        return;
    }
    const uint8_t got = Wire.requestFrom(kXmosAddr, (uint8_t)4);
    uint8_t b[4] = { 0xFF, 0xFF, 0xFF, 0xFF };
    for (uint8_t i = 0; i < got && i < 4; i++) b[i] = Wire.read();
    Serial.printf("  生バイト: %u個 [%02X %02X %02X %02X]\n", got, b[0], b[1], b[2], b[3]);
    if (got == 4) {
        Serial.printf("  ステータス=%u  版数 %u.%u.%u\n", b[0], b[1], b[2], b[3]);
        if (b[1] == 1)      Serial.println("  ★ 1.x.y = I2S版");
        else if (b[1] == 2) Serial.println("  ★ 2.x.y = USB版");
        else                Serial.println("  ★ 想定外の値。生バイトをそのまま報告して");
    }
}

void setup() {
    Serial.begin(115200);
    delay(3000);
    Wire.begin(5, 6);  // D4=SDA / D5=SCL（本体ファームと同じ）
    Wire.setClock(100000);
    Serial.println();
    Serial.println("=== XMOSファーム版数の読み取り ===");
}

void loop() {
    scanBus();
    readVersion();
    Serial.println();
    delay(5000);
}
