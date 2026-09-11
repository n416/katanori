/*
 * Battery - INA226 の読み出し。設計の説明は Battery.h。
 */

#include "Battery.h"

#include <Preferences.h>
#include <Wire.h>
#include "Console.h" // 最後に置く（Serial を Wi-Fi モニタへも流す差し替え。Console.h）

namespace katanori {

Battery battery;

namespace {

// INA226 のレジスタ（TI データシート SBOS547）
constexpr uint8_t kRegConfig = 0x00;
constexpr uint8_t kRegShunt = 0x01;   // 符号付き・1LSB = 2.5µV
constexpr uint8_t kRegBus = 0x02;     // 1LSB = 1.25mV
constexpr uint8_t kRegMaskEn = 0x06;  // bit3 = CVRF（変換完了。読むと落ちる）
constexpr uint8_t kRegMfgId = 0xFE;   // 0x5449 ("TI")
constexpr uint8_t kRegDieId = 0xFF;   // 上位12bit = 0x226

/*
 * 設定レジスタ。
 *   AVG=64（011）・VBUSCT=1.1ms（100）・VSHCT=1.1ms（100）・MODE=シャントとバスを連続（111）
 *   → 1 回の変換が 64 × (1.1 + 1.1) ≒ 141ms。
 *
 * 64 回ならすのは、読みに行く回数を減らしてバスを空けるため。代わりに
 * 141ms より短い山は均される。スピーカーの瞬間の山を見るならここを減らす。
 */
constexpr uint16_t kConfig = 0x4000 | (0x3 << 9) | (0x4 << 6) | (0x4 << 3) | 0x7;

constexpr uint32_t kPollMs = 50;
constexpr uint8_t kFailuresToGiveUp = 10;
/** 残量の目安に使う電圧のならし時間。スピーカーの山で % が跳ねないようにする。 */
constexpr float kRestTauMs = 30000.0f;

/*
 * リポ 1 セルの開放電圧と残量の対応（一般的な曲線。この電池での実測ではない）。
 * 電圧の高い順。間は直線で補う。
 */
struct OcvPoint { uint16_t mv; uint8_t pct; };
constexpr OcvPoint kOcv[] = {
    {4200, 100}, {4150, 95}, {4110, 90}, {4080, 85}, {4020, 80}, {3980, 75},
    {3950, 70},  {3910, 65}, {3870, 60}, {3850, 55}, {3840, 50}, {3820, 45},
    {3800, 40},  {3790, 35}, {3770, 30}, {3750, 25}, {3730, 20}, {3710, 15},
    {3690, 10},  {3610, 5},  {3270, 0},
};

int ocvToPercent(float volts) {
    float mv = volts * 1000.0f;
    constexpr size_t n = sizeof(kOcv) / sizeof(kOcv[0]);
    if (mv >= kOcv[0].mv) {
        return 100;
    }
    if (mv <= kOcv[n - 1].mv) {
        return 0;
    }
    for (size_t i = 1; i < n; ++i) {
        if (mv >= kOcv[i].mv) {
            const OcvPoint& hi = kOcv[i - 1];
            const OcvPoint& lo = kOcv[i];
            float t = (mv - lo.mv) / float(hi.mv - lo.mv);
            return int(lo.pct + t * (hi.pct - lo.pct) + 0.5f);
        }
    }
    return 0;
}

const char* directionWord(float mA) {
    if (mA > 5.0f) return "放電";
    if (mA < -5.0f) return "充電";
    return "ほぼ0";
}

} // namespace

bool Battery::readReg(uint8_t reg, uint16_t& out) {
    Wire.beginTransmission(KATANORI_INA_ADDR);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) {
        return false;
    }
    if (Wire.requestFrom((uint8_t)KATANORI_INA_ADDR, (uint8_t)2) != 2) {
        return false;
    }
    uint16_t hi = Wire.read();
    uint16_t lo = Wire.read();
    out = (uint16_t)((hi << 8) | lo);
    return true;
}

bool Battery::writeReg(uint8_t reg, uint16_t value) {
    Wire.beginTransmission(KATANORI_INA_ADDR);
    Wire.write(reg);
    Wire.write((uint8_t)(value >> 8));
    Wire.write((uint8_t)(value & 0xFF));
    return Wire.endTransmission() == 0;
}

bool Battery::begin(bool verbose) {
    present_ = false;
    failures_ = 0;

    Preferences prefs;
    prefs.begin("bat", true);
    bool flip = prefs.getBool("flip", false);
    prefs.end();
    inverted_ = (KATANORI_INA_INVERT != 0) != flip;

    uint16_t mfg = 0;
    uint16_t die = 0;
    if (!readReg(kRegMfgId, mfg)) {
        if (verbose) {
            Serial.printf("[BAT] INA226(0x%02X) が応答しません。電池の値は読めません\n",
                          KATANORI_INA_ADDR);
            Serial.println("[BAT]   's' で 0x44 が出るか確認。出ないなら INA の口（GND・3V3・SCL・SDA）");
        }
        return false;
    }
    readReg(kRegDieId, die);
    // 0x44 には他の石も居られる。型番を確かめずに電流として読むと、別物の数字を
    // 電池の値として出すことになる。
    if (mfg != 0x5449 || (die >> 4) != 0x226) {
        Serial.printf("[BAT] !! 0x%02X は INA226 ではありません（製造者ID=0x%04X 型番ID=0x%04X。"
                      "期待値 0x5449 / 0x226x）\n",
                      KATANORI_INA_ADDR, mfg, die);
        return false;
    }

    uint16_t readBack = 0;
    if (!writeReg(kRegConfig, kConfig) || !readReg(kRegConfig, readBack) ||
        readBack != kConfig) {
        Serial.printf("[BAT] !! INA226 の設定が書けませんでした（書いた 0x%04X / 読めた 0x%04X）\n",
                      kConfig, readBack);
        return false;
    }

    present_ = true;
    haveSample_ = false;
    lastPollMs_ = millis();
    lastLogMs_ = millis();
    Serial.printf("[BAT] INA226(0x%02X) を見つけました。シャント %dmΩ・141ms ごとに読みます%s\n",
                  KATANORI_INA_ADDR, KATANORI_INA_SHUNT_MOHM,
                  inverted_ ? "（電流の向きは反転設定）" : "");
    return true;
}

void Battery::noteFailure() {
    if (++failures_ < kFailuresToGiveUp) {
        return;
    }
    // 1 回の失敗では騒がない（バスは OLED の全面転送と共用で混んでいる）。
    // 続くようなら線が外れたとみて読みを止める。`bat` で探し直せる。
    present_ = false;
    failures_ = 0;
    Serial.println("[BAT] !! INA226 が続けて応答しません。読みを止めます（'bat' で探し直し）");
}

void Battery::loop() {
    if (!present_) {
        return;
    }
    uint32_t now = millis();
    if ((now - lastPollMs_) < kPollMs) {
        return;
    }
    lastPollMs_ = now;

    uint16_t maskEn = 0;
    if (!readReg(kRegMaskEn, maskEn)) {
        noteFailure();
        return;
    }
    if ((maskEn & 0x0008) == 0) {
        failures_ = 0;
        return; // まだ次の変換が終わっていない
    }

    uint16_t shuntRaw = 0;
    uint16_t busRaw = 0;
    if (!readReg(kRegShunt, shuntRaw) || !readReg(kRegBus, busRaw)) {
        noteFailure();
        return;
    }
    failures_ = 0;

    // I = Vshunt / R = raw × 2.5µV / (R[mΩ] × 1mΩ) = raw × 2.5 / R[mΩ]  [mA]
    float mA = (int16_t)shuntRaw * 2.5f / (float)KATANORI_INA_SHUNT_MOHM;
    if (inverted_) {
        mA = -mA;
    }
    float volts = busRaw * 1.25e-3f;
    onSample(volts, mA, now);

    if (logEverySec_ != 0 && (now - lastLogMs_) >= logEverySec_ * 1000u) {
        printLine("[BAT]");
    }
}

void Battery::onSample(float volts, float mA, uint32_t now) {
    float compensated = volts + mA * 1e-3f * (KATANORI_BAT_RINT_MOHM * 1e-3f);

    if (haveSample_) {
        uint32_t dt = now - lastSampleMs_;
        // ループが長く止まった後（Wi-Fi の接続待ち・OTA）も、その間は直前の電流が
        // 続いていたとみなして積む。ただし 1 分を超える穴は数えない。
        if (dt > 60000u) {
            dt = 60000u;
        }
        double mAh = (double)mA * dt / 3.6e6;
        if (mAh >= 0) {
            outMah_ += (float)mAh;
        } else {
            inMah_ += (float)-mAh;
        }
        winMaMs_ += (double)mA * dt;
        winMs_ += dt;

        float a = dt / kRestTauMs;
        if (a > 1.0f) {
            a = 1.0f;
        }
        restVolts_ += (compensated - restVolts_) * a;
    } else {
        restVolts_ = compensated;
        haveSample_ = true;
    }
    lastSampleMs_ = now;
    volts_ = volts;
    mA_ = mA;

    if (!winHas_) {
        winMin_ = winMax_ = mA;
        winHas_ = true;
    } else {
        if (mA < winMin_) winMin_ = mA;
        if (mA > winMax_) winMax_ = mA;
    }

    // 2.5V 未満はリポの保護回路が切る電圧より下なので、電池が繋がっていない
    // （USB 給電の机上）とみる。ここで「少ない」と言うのは誤報になる。
    if (!connected()) {
        low_ = false;
        return;
    }

    // 少ないかどうかは、ならした電圧で決める。0.1V の戻り幅でバタつかせない。
    bool wasLow = low_;
    float lowV = KATANORI_BAT_LOW_MV * 1e-3f;
    low_ = low_ ? (restVolts_ < lowV + 0.1f) : (restVolts_ < lowV);
    if (low_ != wasLow) {
        Serial.printf("[BAT] %s（ならした電圧 %.3fV・しきい値 %.2fV）\n",
                      low_ ? "!! 電池が少なくなりました" : "電池の残量が戻りました",
                      restVolts_, lowV);
    }
}

int Battery::percent() const {
    if (!haveSample_ || !connected()) {
        return -1;
    }
    return ocvToPercent(restVolts_);
}

void Battery::printLine(const char* tag) {
    lastLogMs_ = millis();
    if (!haveSample_) {
        Serial.printf("%s まだ値がありません\n", tag);
        return;
    }
    float avg = winMs_ ? (float)(winMaMs_ / winMs_) : mA_;
    char pct[16];
    if (connected()) {
        snprintf(pct, sizeof(pct), "目安 %d%%", percent());
    } else {
        snprintf(pct, sizeof(pct), "電池なし");
    }
    Serial.printf("%s %.3fV %s %.1fmA | 平均 %.1f 最小 %.1f 最大 %.1f mA（%u秒） | "
                  "%s | 積算 放電 %.1fmAh 充電 %.1fmAh\n",
                  tag, volts_, directionWord(mA_), fabsf(mA_), avg, winMin_, winMax_,
                  (unsigned)(winMs_ / 1000), pct, outMah_, inMah_);
    winMaMs_ = 0.0;
    winMs_ = 0;
    winHas_ = false;
}

void Battery::printStatus() {
    if (!present_) {
        Serial.println("[BAT] INA226 を探し直します");
        begin(true);
        return;
    }
    if (!haveSample_) {
        Serial.println("[BAT] まだ最初の変換が終わっていません（141ms 待って打ち直し）");
        return;
    }
    if (!connected()) {
        Serial.printf("[BAT] 電池が繋がっていません（バス %.3fV）。電流 %.1fmA\n", volts_, mA_);
        return;
    }
    Serial.printf("[BAT] 電池 %.3fV  %s %.1fmA（%.2fW）  残量の目安 %d%%%s\n",
                  volts_, directionWord(mA_), fabsf(mA_), volts_ * fabsf(mA_) * 1e-3f,
                  percent(), low_ ? "  ★少ない" : "");
    Serial.printf("[BAT]   目安の元の電圧 %.3fV（降下 %dmΩ ぶん足し戻して30秒でならした値）\n",
                  restVolts_, KATANORI_BAT_RINT_MOHM);
    Serial.printf("[BAT]   積算: 放電 %.1fmAh / 充電 %.1fmAh（'batreset' で0から）\n",
                  outMah_, inMah_);
    Serial.printf("[BAT]   向き: %s。USB を挿していないのに「充電」と出るなら 'batflip'\n",
                  inverted_ ? "反転" : "標準");
    Serial.printf("[BAT]   定期ログ: %s\n", logEverySec_ ? "動作中" : "停止中（'batlog <秒>'）");
}

void Battery::resetStats() {
    outMah_ = 0.0f;
    inMah_ = 0.0f;
    winMaMs_ = 0.0;
    winMs_ = 0;
    winHas_ = false;
    lastLogMs_ = millis();
    Serial.println("[BAT] 積算と最小・最大を 0 から数え直します");
}

void Battery::toggleSign() {
    Preferences prefs;
    prefs.begin("bat", false);
    bool flip = !prefs.getBool("flip", false);
    prefs.putBool("flip", flip);
    prefs.end();
    inverted_ = (KATANORI_INA_INVERT != 0) != flip;
    // 向きを変える前の積算は、放電と充電が入れ替わっていて意味が無い
    outMah_ = 0.0f;
    inMah_ = 0.0f;
    winHas_ = false;
    winMaMs_ = 0.0;
    winMs_ = 0;
    Serial.printf("[BAT] 電流の向きを%sにして保存しました（積算は 0 に戻しました）\n",
                  inverted_ ? "反転" : "標準");
}

void Battery::setLogInterval(uint32_t sec) {
    logEverySec_ = sec;
    lastLogMs_ = millis();
    winHas_ = false;
    winMaMs_ = 0.0;
    winMs_ = 0;
    if (sec == 0) {
        Serial.println("[BAT] 定期ログを止めました");
    } else {
        Serial.printf("[BAT] %u秒ごとに 1 行出します\n", (unsigned)sec);
    }
}

} // namespace katanori
