/*
 * ============================================================================
 *  WakeWatch - マイクの控え（会話の頭の貯め）
 *
 *  マイクの音を常にリングへ貯めておき、会話の頭を遡って拾う。
 *
 *  🔒 ユーザー 2026-09-21「Gemini応答までの間に喋ったものも送ってほしい」
 *  「会話ボタンを押下した瞬間から保存しておいてほしい」。
 *  呼ばれてから、あるいはボタンを押してから、サーバーへ繋がって
 *  setupComplete が返るまでには間がある（Wi-Fi が切れていれば数秒）。
 *  その間に喋ったぶんをリングから拾い、繋がった時点でまとめて送る。
 *  呼ばれたときは呼び名の前まで遡る（「カタノリ、〇〇して」ごと届ける）。
 *
 *  呼び名の聞き分けは機体の中（MicroWake.h）。
 *  🔴 音声をクラウドへ出すのは、会話が始まってからだけ。待機中の音を垂れ流さない。
 * ============================================================================
 */

#ifndef KATANORI_WAKEWATCH_H
#define KATANORI_WAKEWATCH_H

#include <Arduino.h>

namespace katanori {

class WakeWatch {
public:
    /**
     * 遡れる長さ。
     *
     * 呼び名の頭を拾うだけなら 2 秒で足りるが、繋がるまでの貯めにも同じ
     * リングを使う。Wi-Fi が落ちていると再接続に数秒かかるので、長めに取る。
     */
    static constexpr uint32_t kRingMs = 12000;

    /** PSRAM にリングを取る。取れなければ false（見張りは動かさない）。 */
    bool begin();
    bool ready() const { return ring_ != nullptr; }

    /** マイクの生データ。待機中も会話中も、読んだものは全部ここへ流す。 */
    void feed(const int16_t* pcm, size_t n);

    /**
     * 会話の頭。ここから先は、繋がった時点でまとめて Gemini へ送る。
     *
     * 会話ボタンを押した瞬間と、呼びかけを見つけた瞬間に打つ。
     */
    void markTurn(uint32_t backMs = 0);
    bool hasTurn() const { return hasTurn_; }
    void clearTurn() { hasTurn_ = false; }

    /**
     * 貯めてある会話の頭から今までを NetLink へ流す。
     *
     * 繋がって setupComplete が返ったところで1回だけ呼ぶ。流し終えたら印は
     * 消えるので、以降は pumpMic がそのまま送る。
     *
     * 🔴 無音は詰めて送る。
     * 溜めたぶんを一括で流し込むと、Gemini は無音の長さを実時間として扱わない
     * （setup で silenceDurationMs=2000 を渡してあるのに、実機では 0.44秒 の
     * 無音で発話が切れた）。切れると、呼びかけへの応答を始めた直後に、待って
     * いる間の独り言が「割り込み」と判定されて応答ごと捨てられる。
     * 有声のところだけを継いで、ひと続きの発話として渡す。
     *
     * @param gateRms これを下回るフレームを無音とみなす（VAD の検出線）
     * @return 送ったサンプル数
     */
    uint32_t drainToNetLink(float gateRms);

    /** 無音として落としたサンプル数（直前の drain）。 */
    uint32_t lastTrimmedSamples() const { return trimmed_; }

private:
    int16_t* ring_ = nullptr;
    uint32_t ringLen_ = 0;
    volatile uint32_t wpos_ = 0;
    volatile uint32_t written_ = 0;   // 総書き込み数（位置の計算用）

    uint32_t turnAt_ = 0;             // 会話の頭
    bool hasTurn_ = false;

    uint32_t trimmed_ = 0;
};

extern WakeWatch wakeWatch;

} // namespace katanori

#endif // KATANORI_WAKEWATCH_H
