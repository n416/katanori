/*
 * ============================================================================
 *  AudioIo - ReSpeaker Lite との I2S 音声入出力
 *
 *  DO側で base64/JSON/リサンプルを済ませてあるので、ここは
 *  「生PCMを読む / 生PCMを書く」だけに徹する。
 *
 *  再生は専用タスク + リングバッファで行う。Geminiは応答音声を実時間より
 *  ずっと速くまとめて送ってくるため、受信スレッドから直接 i2s_write すると
 *  DMAが空くまでブロックして OLED の描画が止まる。
 * ============================================================================
 */

#ifndef KATANORI_AUDIO_IO_H
#define KATANORI_AUDIO_IO_H

#include <Arduino.h>

// ReSpeaker Lite との I2S 結線 (Seeed公式の I2S サンプルと同じ)
//   I2S.setPins(8, 7, 43, 44) = (bclk, ws, dout, din)
#ifndef KATANORI_I2S_BCLK
#define KATANORI_I2S_BCLK 8   // D9
#endif
#ifndef KATANORI_I2S_WS
#define KATANORI_I2S_WS 7     // D8
#endif
#ifndef KATANORI_I2S_DOUT
#define KATANORI_I2S_DOUT 43  // D6  ESP32 -> ReSpeaker (スピーカー)
#endif
#ifndef KATANORI_I2S_DIN
#define KATANORI_I2S_DIN 44   // D7  ReSpeaker -> ESP32 (マイク)
#endif
// MCLK は公式サンプルが未使用のため既定で出さない。必要なら 9 (D10) を指定する。
#ifndef KATANORI_I2S_MCLK
#define KATANORI_I2S_MCLK -1
#endif

// ReSpeaker Lite の XMOS が I2S マスタ。ESP32 はスレーブで受ける。
// 実機での総当たり結果:
//   MASTER 各種      -> rms 17000超（自分のクロックで無意味なビットを読むだけ）
//   SLAVE/I2S/16bit  -> 32427 fps（32bitスロットを2回に割ってしまい壊れる）
//   SLAVE/I2S/32bit  -> 16213 fps = 16kHz ちょうど、無音時 rms 256  ★これが正解
#ifndef KATANORI_I2S_SLAVE
#define KATANORI_I2S_SLAVE 1
#endif

// スロット幅。XMOS は 32bit スロットで送ってくる（データは上位16bit）。
#ifndef KATANORI_I2S_BITS
#define KATANORI_I2S_BITS 32
#endif

// 0 = 標準I2S(1bit遅れ) / 1 = 左詰め(MSB)。機器が合わないと無音か雑音になる。
#ifndef KATANORI_I2S_MSB_FORMAT
#define KATANORI_I2S_MSB_FORMAT 0
#endif

// 機体の中を流れる音のレート。Gemini の入力仕様が 16kHz なのでここは動かさない。
// 呼び出し側（main.cpp / NetLink / WakeWatch）が見るのは常にこのレートである。
#ifndef KATANORI_AUDIO_RATE
#define KATANORI_AUDIO_RATE 16000
#endif

/*
 * ReSpeaker Lite の I2S ファームが動いているレート。
 *
 * 16kHz 版（v1.0.8 / v1.0.9）は 16000、48kHz 版（v1.1.0 ch0-asr_ch1-mww）は 48000。
 *
 * 🔴 AGC を外すために 48kHz 版へ移る（firmware/esp32/README.md「再生中の残留」）。
 * ch0 の取り出し口を選ぶ I2C コマンドは v1.1.0 にしか無く、16kHz の v1.1.0 は
 * factory 版しか配られていないため、公式手順で書ける 48kHz の DFU 版を使う。
 *
 * 48000 / 16000 = 3 の整数比なので、変換は AudioIo の中だけで済む。
 * 読むときは3サンプルを平均して1つにし、書くときは1つを3つへ伸ばす。
 * ⚠ 上の KATANORI_AUDIO_RATE との比は整数でなければならない。
 */
#ifndef KATANORI_XMOS_RATE
#define KATANORI_XMOS_RATE 16000
#endif

/*
 * マイクに掛ける固定のゲイン（倍）。
 *
 * 🔴 XMOS の AGC を外すと、AGC が担っていた増幅も無くなって感度が落ちる
 * （2026-09-21 実機: 普通の声が RMS 36 までしか入らず、かなり大きな声でないと
 * 検出線を越えなかった）。そのぶんをここで取り戻す。
 *
 * ⚠ AGC とは別物である。AGC は入力の大きさで倍率を変えるので、小さい残留エコーも
 * 引き上げて AEC を台無しにする。こちらは常に同じ倍率なので、**残留と声の比は
 * 変わらない**。AEC の効果はそのまま残る。
 *
 * 1 なら素通し（AGC が生きている 16kHz 版はこちら）。
 */
#ifndef KATANORI_MIC_GAIN
#define KATANORI_MIC_GAIN 1
#endif

// マイクのどちらのチャンネルを使うか。
// ch0-asr/ch1-mww ファームでは 0 = 音声認識向け、1 = ウェイクワード向け。
#ifndef KATANORI_MIC_CHANNEL
#define KATANORI_MIC_CHANNEL 0
#endif

namespace katanori {

class AudioIo {
public:
    /** I2Sを初期化し、再生タスクを起動する。 */
    bool begin();

    // --- 録音 ---
    void startRecording();
    void stopRecording();
    bool isRecording() const { return recording_; }

    /**
     * マイクから読めるぶんだけ読んでモノラル化する。ブロックしない。
     * @return 書き込んだサンプル数 (0 = まだ溜まっていない)
     */
    size_t readMic(int16_t* out, size_t maxSamples, int16_t* wakeOut = nullptr);
    // wakeOut: 同じサンプル数ぶん、呼び名の聞き分け用の音を書く（MicroWake.h）。
    // XMOS の ch1（mww 向け・取り出し口 1）を、32bit のまま 16 倍して 16bit に落としたもの。
    // 2026-09-22 の試験で、取り出し口 3 の ch0 より当たりが良かった。
    // ch1 は話しても RMS 40 前後と小さく、16bit に落としてから倍にすると細かさが消えるので、
    // 32bit の段で倍にする

    // --- 再生 ---
    /** 再生キューへ積む。実時間より速く届くのでバッファで吸収する。 */
    void play(const int16_t* pcm, size_t samples);
    /** 割り込み時: 未再生ぶんを破棄する。 */
    void stopPlayback();
    bool isPlaying() const;

    /** 直近のマイクピーク (0.0〜1.0)。顔の口パク・波形表示に使う。 */
    float micLevel() const { return micLevel_; }

    /** 再生音量 0.0〜1.0。ReSpeakerの出力はアンプ経由なので既定は控えめ。 */
    void setGain(float g);
    float gain() const { return gain_; }

    /**
     * ReSpeaker Lite の音声コーデック (TLV320AIC3204 @ 0x18) を直接ミュートする。
     *
     * 【なぜ必要か】ESP32-S3 の GPIO43 は UART0 の TX であり、同時に I2S DOUT
     * でもある。リセット直後、ROMブートローダが 115200bps で吐くブートログが
     * そのままオーディオとして増幅され、耳を痛めるレベルの轟音になる。
     * アプリが走る前の出来事なのでソフトでは防げない。
     *
     * ただし ESP32 がリセットされてもコーデックはリセットされない（別電源）。
     * そこで「普段はミュート、再生するときだけ解除」しておけば、
     * リセット時にはミュート状態が保持されていて音が出ない。
     */
    bool setOutputMute(bool mute);
    bool outputMuted() const { return muted_; }

    /** マイクの受け皿が一杯で捨てたサンプル数（読む側が 5 秒止まった）。 */
    uint32_t micDropped() const;

    /**
     * 読み取り用のタスクを止める／再開する（入れ子にしてよい）。
     * 診断のコマンドが I2S を直に読むあいだ、奪い合わないように止める。
     */
    void holdCapture(bool hold);

    /** マイクのゲインで振り切れたサンプル数（多いなら倍率を下げる）。 */
    uint32_t micClipped() const { return micClipped_; }

    /**
     * 最後にミュートを解いた時刻 [ms]。0 なら一度も解いていない。
     *
     * 🔴 解いた瞬間、コーデックの出力段にポップノイズが出る。これをマイクが
     * 拾うと Gemini が「人が喋った」と見なして、始めたばかりの応答を割り込みで
     * 捨てる（実機で 3回続けて再現。文字起こしは "Porra." "¿Cuál es?" など、
     * 短い雑音を無理に言葉にしたものだった）。スピーカーに出た音を参照して引く
     * AEC では消せないので、送る側でこの瞬間をまたぐ。
     */
    uint32_t unmutedAtMs() const { return unmutedAt_; }

    /**
     * コーデックの主要レジスタをダンプする。
     *
     * コーデックを設定しているのはXMOSであってESP32ではない。電源が一瞬落ちて
     * コーデックがリセットされると、I2Cは応答しI2Sのクロックも来ているのに
     * 音だけが出なくなり、ESP32を再起動しても復旧しない（XMOSが再設定するのは
     * 基板の電源投入時だけ）。それが起きたかどうかは、正常時とこの出力を
     * 見比べれば分かる。特にDACの電源(P0 0x3F)と出力ドライバ(P1 0x09)。
     */
    void dumpCodec() const;

    /**
     * コーデックの出力が生きているか（DACの電源ビットが立っているか）。
     *
     * 電源が一瞬落ちてコーデックがリセットされると、ここがfalseになる。
     * I2Cは応答しI2Sのクロックも来ているので、これを見ないと気づけない。
     * 読めなかったときは「生きている」扱いにする（I2Cの一時的な失敗で
     * 誤検出しないため。本当に死んでいれば次の周期で分かる）。
     */
    bool codecOutputAlive() const;

    void printStatus() const;

    /**
     * マイク単独テスト。指定時間ぶん読んで、ch0/ch1 それぞれの
     * ピークとRMSを出す。
     *   バイト数が0     -> クロックが回っていない（マスタ/スレーブ設定かピン）
     *   読めるが全部0   -> ReSpeaker側が音を出していない（ファームかマイク）
     *   片方だけ振れる  -> KATANORI_MIC_CHANNEL が逆
     */
    void micTest(uint32_t durationMs);

    /**
     * I2Sの設定を実行時に張り替える。書き込み直さずに条件を変えて試すため。
     * @param bits 16 または 32（スロット幅）
     */
    bool applyConfig(bool slave, bool msbFormat, int bits);
    int16_t applyMicGain(int16_t v);

    /**
     * マスタ/スレーブ × 標準I2S/左詰め × 16/32bit の全組み合わせを試し、
     * それぞれのマイク入力レベルを測って一覧にする。
     * 無音状態で実行すること。RMSが最も低い組み合わせが正解の候補。
     */
    void scanConfigs();

    /**
     * スピーカー単独テスト。正弦波を鳴らして出力経路だけを確かめる。
     * @param amplitude 0〜32767。既定は十分小さくしてある。
     *        ReSpeaker Lite の出力はアンプ経由なので、イヤホンを直結すると
     *        小さい値でも非常に大きな音になる。耳に着けたまま試さないこと。
     */
    void toneTest(uint32_t durationMs, int freqHz, int amplitude = 600);

private:
    static void playbackTask(void* arg);
    static void captureTask(void* arg);
    void runCapture();
    size_t captureFromI2s(int16_t* out, size_t maxSamples, int16_t* wakeOut, TickType_t wait);
    void runPlayback();

    /** 現在のスロット幅での1フレームのバイト数（ステレオ）。 */
    size_t frameBytes() const;
    /** モノラル16bitを左右へ複製してI2Sへ書く。32bitスロットなら上位へ載せる。 */
    void writeMono(const int16_t* mono, size_t samples, TickType_t wait);

    bool started_ = false;
    // 実行時に張り替えられる現在のI2S設定
    bool curSlave_ = KATANORI_I2S_SLAVE;
    bool curMsb_ = KATANORI_I2S_MSB_FORMAT;
    int curBits_ = 16;
    volatile bool recording_ = false;
    volatile float micLevel_ = 0.0f;
    // 既定音量。0.30で「大きすぎてびっくりした」（2026-08-05・実機で本人）ため
    // 控えめに置く。肩＝耳元数cmの装着位置が基準。上げるのは `vol` かつまみで。
    volatile float gain_ = 0.15f;
    // 48kHz のファームで 16kHz へ落とすときの持ち越し（readMic）
    uint32_t micClipped_ = 0;   // ゲインで振り切れたサンプル数
    int32_t decimAcc_ = 0;
    int64_t decimAccWake_ = 0;  // wakeOut 用（ch1 の 32bit 値を足す）
    int decimCount_ = 0;
    // 16kHz から 48kHz へ伸ばすときの前のサンプル（writeMono）
    int32_t upsamplePrev_ = 0;
    bool muted_ = true;   // 既定はミュート。起動時の轟音を防ぐため。
    uint32_t unmutedAt_ = 0;  // 最後にミュートを解いた時刻（ポップをまたぐため）

    // 統計 (デバッグ用)
    volatile uint32_t sentSamples_ = 0;
    volatile uint32_t playedSamples_ = 0;
    volatile uint32_t droppedSamples_ = 0;
};

extern AudioIo audioIo;

} // namespace katanori

#endif // KATANORI_AUDIO_IO_H
