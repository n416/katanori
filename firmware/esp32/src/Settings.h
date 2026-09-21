/*
 * ============================================================================
 *  Settings - 利用者が変えられる設定（2026-09-11 追加）
 *
 *  🔒 ユーザー 2026-09-11: 変えたいのは「画面の明るさ」「眠るまでの時間」「起動の声」。
 *  🔒 同 2026-09-12「（つまみの 100% をゲイン 0.70 で頭打ちにしているなら）設定追加しておこうよ」:
 *     音量の上限（おんりょうMAX）。ただし天井はファームの KATANORI_KNOB_MAX_GAIN（0.70）のままで、
 *     設定で選べるのはそこから下げる方向だけ（5 = 天井・1 つ下げるごとに -2dB）。
 *  変える入口は 2 つで、どちらも同じ値（NVS の "cfg"）を読み書きする。
 *   - 機体のメニュー（会話ボタン長押し。main.cpp の「メニュー」の節・見本 docs/_img/menu_mock.png）
 *   - ブラウザの設定ページ（同じ Wi-Fi から http://katanori.local/ 。このファイル）
 *
 *  設定ページに合言葉は付けていない。同じ LAN の他人に変えられても耳や機体を傷めるものしか
 *  置かないため。音量の上限も、天井より上には上げられないので同じ扱い（unmute は置かない）。
 * ============================================================================
 */

#ifndef KATANORI_SETTINGS_H
#define KATANORI_SETTINGS_H

#include <Arduino.h>

namespace katanori {

class Settings {
public:
    static constexpr uint8_t kBrightLevels = 5;   // あかるさ 1〜5
    static constexpr uint8_t kSleepOptions = 5;   // しない／1／3／5／10 分
    static constexpr uint8_t kMaxVolLevels = 5;   // おんりょうMAX 1〜5（5 = ファームの天井）

    /**
     * 呼び名の上限（全角の文字数）。
     *
     * 画面の日本語フォント（b16_t_japanese1）は1行が全角8文字（128px）まで。
     * 機体のメニューに収まる長さに切る。
     */
    static constexpr uint8_t kWakeNameMaxChars = 8;
    /** 呼び名の既定。 */
    static const char* const kDefaultWakeName;

    /** NVS から読む。setup() の早いうちに 1 回。 */
    void begin();

    /** あかるさ 1〜5。 */
    uint8_t brightness() const { return bright_; }
    /** あかるさを SSD1306 のコントラスト値へ。 */
    static uint8_t contrastFor(uint8_t level);
    uint8_t contrast() const { return contrastFor(bright_); }

    /** 眠るまでの選択肢の番号 0〜4。 */
    uint8_t sleepIndex() const { return sleepIdx_; }
    /** 番号 → 分（0 = 眠らない）。 */
    static uint16_t sleepMinutesAt(uint8_t idx);
    /** 眠るまで [ms]。0 = 眠らない。 */
    uint32_t sleepMs() const { return sleepMinutesAt(sleepIdx_) * 60000ul; }

    /** 起動の声（「カタノリ、起動しました」）を鳴らすか。 */
    bool bootVoice() const { return bootVoice_; }

    /** おんりょうMAX 1〜5。 */
    uint8_t maxVolume() const { return maxVol_; }
    /** 天井（ceiling）に対する倍率。5 で 1.0、1 つ下げるごとに -2dB。 */
    static float maxVolumeScaleFor(uint8_t level);
    float maxVolumeScale() const { return maxVolumeScaleFor(maxVol_); }

    /**
     * 呼びかけに使う名前。
     *
     * 🔒 ユーザー 2026-09-21「WEBから名前を登録できるように。カタノリ本体の
     *    設定からは見える＆リセットできるだけでいい。デフォルトはカタノリ」
     *    「呼び名はカタカナのみ（Web の入力欄で制限）で良いです」。
     *
     * カタカナに限るのは2つの理由から。画面のフォントに漢字が無いこと
     * （main.cpp の描画の注）と、文字起こしの表記が揺れるので読みで
     * 突き合わせたいこと（katanori-backend の wake.ts）。
     */
    const String& wakeName() const { return wakeName_; }

    /**
     * 呼び名を保存する。
     *
     * @return カタカナ以外が混ざっているか長すぎれば false（保存しない）
     */
    bool setWakeName(const String& name);

    /** 呼び名を既定（カタノリ）へ戻す。機体のメニューから使う。 */
    void resetWakeName();

    /**
     * 呼びかけで会話を始めるか。
     *
     * 🔴 既定は「切」。2026-09-21 の実機で、咳が「カタノリ」と文字起こしされて
     * 確実に起動する状態だった（whisper は咳を「言葉である」と判定し、立ち上がりの
     * 速さで落とす試みも外れた）。切ってあれば会話ボタンだけになり、今までどおり
     * 確実に動く。呼びかけの調整はその上で続ける。
     */
    bool wakeEnabled() const { return wakeOn_; }
    void setWakeEnabled(bool on);

    /** カタカナだけでできているか。文字数も返す。 */
    static bool isKatakanaOnly(const String& s, uint8_t& chars);

    void setBrightness(uint8_t level);
    void setSleepIndex(uint8_t idx);
    void setBootVoice(bool on);
    void setMaxVolume(uint8_t level);

    /** 値が変わったときに呼ぶ関数（main.cpp が画面の明るさや眠る時間に反映する）。 */
    void setOnChange(void (*fn)()) { onChange_ = fn; }

    /** 設定ページの待受と応答。main loop から毎回呼ぶ。 */
    void webLoop();
    /** 設定ページを畳む。Wi-Fi 設定モードに入る前（同じ 80 番を使う）と、WIFI_OFF の前に呼ぶ。 */
    void webSuspend();

    /** シリアル `cfg` の表示。 */
    void print() const;

private:
    void save(const char* key, uint8_t v);
    void changed();

    uint8_t bright_ = kBrightLevels;  // 既定は今までと同じ明るさ（0xCF）
    uint8_t sleepIdx_ = 2;            // 既定は今までと同じ 3 分
    bool bootVoice_ = true;
    uint8_t maxVol_ = kMaxVolLevels;  // 既定は今までと同じ（天井のまま）
    bool wakeOn_ = false;             // 呼びかけ。既定は切
    String wakeName_;                 // begin() で既定を入れる
    void (*onChange_)() = nullptr;
    bool webUp_ = false;
};

extern Settings settings;

} // namespace katanori

#endif // KATANORI_SETTINGS_H
