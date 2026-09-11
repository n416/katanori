/*
 * ============================================================================
 *  BootLog - なぜ再起動したのかを残す（2026-09-11 追加）
 *
 *  きっかけ: 2026-09-11 夜、ユーザーが寝ている間に「カタノリ、起動しました」が
 *  5〜15 分おきに鳴っていた（同居人の話）。あの声は起動のたびに 1 回だけなので、
 *  ESP32 が勝手にリセットを繰り返していたことになる。だが理由がどこにも残っておらず、
 *  電池が切れた後では何も分からなかった。
 *
 *  残すもの:
 *   - 起動時に ESP32 が報告するリセットの理由（電圧低下・パニック・ウォッチドッグ・電源断…）
 *   - 動いている間、1 秒ごとに「その時の様子」をリセットで消えないメモリ（RTC）へ書く。
 *     次の起動でそれを読めば「落ちる直前、何をしていたか」が分かる。
 *     ⚠ 電源そのものが落ちたとき（POWERON）は RTC も消えるので、直前の様子は残らない。
 *     それ自体が「5V が本当に切れた」という手がかりになる。
 *   - 起動ごとに上の 2 つを NVS へ 10 回ぶん貯める。シリアル `boots` で一覧。
 * ============================================================================
 */

#ifndef KATANORI_BOOT_LOG_H
#define KATANORI_BOOT_LOG_H

#include <Arduino.h>

namespace katanori {
namespace bootlog {

/** 今の段階。1 秒ごとの記録に入れる。 */
enum Stage : uint8_t {
    kAwake = 0,
    kDim = 1,
    kAsleep = 2,
    kKnobOff = 3,
    kProvisioning = 4,
};

/** setup() の早いうちに 1 回。前回の理由と直前の様子を出し、NVS の履歴に足す。 */
void begin();

/** main loop から毎回呼ぶ（実際に書くのは 1 秒に 1 回）。 */
void tick(Stage stage, bool conversation, bool wifi, float batVolts, float batMa, bool batValid);

/** `boots` の表示。新しい順。 */
void printHistory();

} // namespace bootlog
} // namespace katanori

#endif // KATANORI_BOOT_LOG_H
