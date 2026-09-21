/*
 * ============================================================================
 *  MicroWake - 機体の中で呼び名「カタノリ」を聞き分ける（microWakeWord）
 *
 *  ESPHome の micro_wake_word と同じ部品・同じ前処理で動かす（lib/ の tflite-micro・
 *  esp-nn・esp-micro-speech-features）。試験は mww_test/ で済んでいて、機体と PC の
 *  確からしさが一致することを確かめてある（2026-09-22）。
 *
 *  聞かせるのは XMOS の ch1 を 16 倍にした音（AudioIo::readMic の第 3 引数）。
 *  2026-09-22 の試験で、取り出し口 3 の ch0 より当たりが良かった（4 回中 4 回）。
 *
 *  モデルとしきい値は WakeModel.h。モデルを替えるときはそちらだけ差し替える。
 * ============================================================================
 */

#ifndef KATANORI_MICRO_WAKE_H
#define KATANORI_MICRO_WAKE_H

#include <Arduino.h>

namespace katanori {

class MicroWake {
public:
    /** モデルと前処理を用意する。内部 RAM を約 31KB 取る。 */
    bool begin();
    bool ready() const { return ready_; }

    /** 状態を初期化する。見張りを始めるたびに呼ぶ（前の音を引きずらない）。 */
    void reset();

    /**
     * 16kHz の音を流す。呼び名を聞いたら true を返す。
     * 判定は直近 5 回の確からしさの平均がしきい値を越えたか（ESPHome と同じ）。
     */
    bool feed(const int16_t* pcm, size_t n);

    /** 直近の確からしさの 5 回平均の最大（0〜1）。ログ用。reset で 0 に戻る。 */
    float peak() const { return peak_; }

    /** 1 回の推論にかかった時間の平均 [us]。 */
    uint32_t avgInvokeUs() const { return invokes_ ? (uint32_t)(invokeUs_ / invokes_) : 0; }

private:
    bool ready_ = false;
    float peak_ = 0.0f;
    uint64_t invokeUs_ = 0;
    uint32_t invokes_ = 0;
};

extern MicroWake microWake;

} // namespace katanori

#endif // KATANORI_MICRO_WAKE_H
