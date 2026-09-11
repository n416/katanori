/*
 * ============================================================================
 *  Battery - 電池の電圧と電流を INA226 で読む（docs/POWER.md 6章）
 *
 *  INA226 は電池と PowerBoost のあいだに直列に入っている。そこに入れたときだけ
 *  「バス電圧」が電池電圧そのものになるので、1個で消費電流と電池残量の両方が読める。
 *
 *  ✅ アドレスは 0x44（2026-09-02 実機。0x40 ではない）。
 *  ✅ シャントは刻印 R010 ＝ 10mΩ（2026-08-24 着荷時）。
 *  ⚠ 電流の向き（どちらの端が INPUT か）は図面読みのままで、実機で確かめていない
 *     （POWER.md「電源の 4 穴の極性」）。逆なら符号が反転するだけで壊れはしないので、
 *     シリアル `batflip` で反転して NVS に保存する。
 *
 *  読むのはシャント電圧とバス電圧の 2 本だけ。電流はシャント電圧 ÷ 10mΩ で自分で
 *  出すので、校正レジスタ（CAL）は書かない。分解能は 0.25mA、上限は ±8.19A。
 *
 *  I2C のバスは OLED・AS5600・コーデック・XMOS と共用なので、読みに行くのは
 *  変換が終わったとき（CVRF）だけにして、無駄な転送を撃たない。
 * ============================================================================
 */

#ifndef KATANORI_BATTERY_H
#define KATANORI_BATTERY_H

#include <Arduino.h>

#ifndef KATANORI_INA_ADDR
#define KATANORI_INA_ADDR 0x44
#endif
// シャント抵抗（mΩ）。モジュールの刻印 R010。
#ifndef KATANORI_INA_SHUNT_MOHM
#define KATANORI_INA_SHUNT_MOHM 10
#endif
// 電流の向きの既定。1 で反転。実行時の `batflip` はこれの上に NVS で重ねる。
#ifndef KATANORI_INA_INVERT
#define KATANORI_INA_INVERT 0
#endif
// 残量の目安を出すときに、電流ぶんの電圧降下を足し戻す抵抗（mΩ）。
// ⚠ 実測していない仮定。1000mAh のリポの内部抵抗＋JST・延長線でこの桁と置いた。
//    スピーカーが鳴るたびに % が跳ねるなら大きく、放電の途中で逆に跳ねるなら小さくする。
#ifndef KATANORI_BAT_RINT_MOHM
#define KATANORI_BAT_RINT_MOHM 150
#endif
// 「電池が少ない」とみなす電圧（mV・上の補正後）。PowerBoost の LBO は 3.2V で落ちる。
#ifndef KATANORI_BAT_LOW_MV
#define KATANORI_BAT_LOW_MV 3500
#endif

namespace katanori {

class Battery {
public:
    /**
     * INA226 を探して設定する。setup() から 1 回（Wire は初期化済みであること）。
     * 見つからない／別の石が居るときは false で、以後 loop() は何もしない。
     * `bat` を打つと探し直す。
     */
    bool begin(bool verbose = true);

    /** main loop から毎回呼ぶ。実際にバスを叩くのは 50ms に 1 回まで。 */
    void loop();

    bool present() const { return present_; }
    /** 一度でも値が取れたか。 */
    bool hasReading() const { return haveSample_; }

    /** 電池の電圧 [V]。 */
    float volts() const { return volts_; }
    /** 電流 [mA]。＋が放電（電池から機体へ）、−が充電。 */
    float milliamps() const { return mA_; }
    bool charging() const { return mA_ < -kIdleBandMa; }
    /** 電池が繋がっているか（2.5V 未満は繋がっていないとみる）。 */
    bool connected() const { return haveSample_ && volts_ >= 2.5f; }

    /**
     * 残量の目安 [%]。読めていなければ -1。
     *
     * 電流ぶんの降下を足し戻した電圧を 30 秒でならし、リポの開放電圧の
     * 一般的な曲線に当てている。**電池ごとの実測ではない。**充電中は高めに出る。
     */
    int percent() const;
    bool low() const { return low_; }

    /** 起動（または `batreset`）からの積算 [mAh]。 */
    float dischargedMah() const { return outMah_; }
    float chargedMah() const { return inMah_; }

    void resetStats();
    /** 電流の向きを反転して NVS に保存する（`batflip`）。 */
    void toggleSign();
    /** 定期ログの間隔 [秒]。0 で止める。 */
    void setLogInterval(uint32_t sec);
    uint32_t logInterval() const { return logEverySec_; }

    /** `bat` の表示。 */
    void printStatus();

private:
    static constexpr float kIdleBandMa = 5.0f; // これより小さい電流は向きを言わない

    bool readReg(uint8_t reg, uint16_t& out);
    bool writeReg(uint8_t reg, uint16_t value);
    void onSample(float volts, float mA, uint32_t now);
    void printLine(const char* tag);
    void noteFailure();

    bool present_ = false;
    bool inverted_ = KATANORI_INA_INVERT != 0;
    uint8_t failures_ = 0;
    uint32_t lastPollMs_ = 0;

    bool haveSample_ = false;
    uint32_t lastSampleMs_ = 0;
    float volts_ = 0.0f;
    float mA_ = 0.0f;
    float restVolts_ = 0.0f; // 降下を足し戻して 30 秒でならした電圧
    bool low_ = false;

    float outMah_ = 0.0f;
    float inMah_ = 0.0f;

    // 定期ログ 1 回ぶんの窓
    uint32_t logEverySec_ = 60;
    uint32_t lastLogMs_ = 0;
    double winMaMs_ = 0.0;
    uint32_t winMs_ = 0;
    float winMin_ = 0.0f;
    float winMax_ = 0.0f;
    bool winHas_ = false;
};

extern Battery battery;

} // namespace katanori

#endif // KATANORI_BATTERY_H
