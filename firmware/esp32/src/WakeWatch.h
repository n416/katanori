/*
 * ============================================================================
 *  WakeWatch - マイクの控え（呼びかけの見張り + 会話の頭の貯め）
 *
 *  マイクの音を常にリングへ貯めておき、2つの用途に使う。
 *
 *  1. 呼びかけの見張り
 *     VAD が「装着者が喋った」と判断した区間だけを POST /wake へ送り、
 *     文字起こしに呼び名が入っていれば会話を始める。決まった語を機体に
 *     覚えさせる方式は採らない（呼び名を変えられなくなる・docs/WAKEUP.md）。
 *
 *  2. 会話の頭の貯め
 *     🔒 ユーザー 2026-09-21「Gemini応答までの間に喋ったものも送ってほしい」
 *     「会話ボタンを押下した瞬間から保存しておいてほしい」。
 *     呼びかけを見つけてから、あるいはボタンを押してから、サーバーへ繋がって
 *     setupComplete が返るまでには間がある（Wi-Fi が切れていれば数秒）。
 *     その間に喋ったぶんをリングから拾い、繋がった時点でまとめて送る。
 *
 *  🔴 音声をクラウドへ出すのは、VAD を通った区間と、会話が始まってからだけ。
 *  待機中の音を垂れ流さない。
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
     * 呼びかけの頭（VAD_ATTACK_MS = 96ms ぶん過ぎている）を拾うだけなら
     * 1秒で足りるが、繋がるまでの貯めにも同じリングを使う。Wi-Fi が落ちて
     * いると再接続に数秒かかるので、長めに取る。
     */
    static constexpr uint32_t kRingMs = 12000;

    /**
     * 呼びかけ判定に1回で送る上限。
     *
     * 呼び名は文頭近くに来る（「カタノリ、おはよう」「ねえカタノリ」）ので、
     * 頭から4秒あれば照合できる。送った量がそのまま文字起こしの費用になる。
     */
    static constexpr uint32_t kMaxSendMs = 4000;

    /** PSRAM にリングを取る。取れなければ false（見張りは動かさない）。 */
    bool begin();
    bool ready() const { return ring_ != nullptr; }

    /** マイクの生データ。待機中も会話中も、読んだものは全部ここへ流す。 */
    void feed(const int16_t* pcm, size_t n);

    /**
     * VAD が発話の開始を認めた。呼びかけ判定はここから遡って送る。
     *
     * 🔴 遡る量は、ひとつ手前の区間が丸ごと入る長さにする。
     * 「カタノリ、聞こえてる?」のように呼び名のあとに間が空くと、VAD は
     * VAD_RELEASE_MS（0.5秒）で区間を切るので、呼び名と本文が別の区間になる。
     * 判定に送られるのは後ろの区間なので、200ms しか遡らないと呼び名が
     * まるごと外れる（実機で「聞こえてる?聞こえてるかな?」だけが届いた）。
     * 呼び名の発話 0.7秒 ＋ 区切りの無音 0.5秒 ＝ 1.2秒 に余裕を足して 1.5秒。
     *
     * @param backMs 何ms 遡るか
     */
    void markSegment(uint32_t backMs = 1500);

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

    /**
     * 呼びかけ判定を別タスクで始める。すぐ戻る。
     *
     * ⚠ ここで待つと main loop が止まり、返事を待つ1〜2秒のあいだマイクが
     * 読まれない。ユーザーの「Gemini応答までの間に喋ったものも送ってほしい」に
     * 反するので、送信はタスクへ出して、その間も feed() を続ける。
     *
     * @param name 照合する呼び名（カタカナ）
     * @return 始められたら true（すでに走っていれば false）
     */
    bool submitAsync(const char* name);

    /** 判定が走っている最中か。 */
    bool busy() const { return busy_; }

    /**
     * 判定の結果を受け取る。走っていない・まだ終わっていなければ false。
     * 1回受け取ると消える。
     */
    bool takeResult(bool& woke, String& text);

    /** 最後の判定にかかった時間 [ms]。 */
    uint32_t lastElapsedMs() const { return lastMs_; }

    /**
     * 直前の判定の「言葉ではない確率」（whisper の no_speech_prob の最大値）。
     * 空なら取れていない。雑音を呼び名と読み違えていないかを見る。
     */
    const String& lastNoSpeech() const { return noSpeech_; }

private:
    static void taskEntry(void* arg);
    void runSubmit();

    int16_t* ring_ = nullptr;
    uint32_t ringLen_ = 0;
    volatile uint32_t wpos_ = 0;
    volatile uint32_t written_ = 0;   // 総書き込み数（位置の計算用）

    uint32_t segAt_ = 0;              // 呼びかけ区間の頭
    bool hasSeg_ = false;
    uint32_t turnAt_ = 0;             // 会話の頭
    bool hasTurn_ = false;

    // 送信タスクとのやりとり
    volatile bool busy_ = false;
    volatile bool done_ = false;
    bool woke_ = false;
    String text_;
    String noSpeech_;
    String name_;
    uint8_t* payload_ = nullptr;      // タスクへ渡す一続きのPCM
    size_t payloadBytes_ = 0;
    uint32_t lastMs_ = 0;
    uint32_t trimmed_ = 0;
};

extern WakeWatch wakeWatch;

} // namespace katanori

#endif // KATANORI_WAKEWATCH_H
