/*
 * ============================================================================
 *  カタノリロボ 実機ファームウェア (XIAO ESP32S3 + SSD1306 OLED)
 *
 *  Stage 1: 「顔が出る」まで
 *    - I2Cスキャンで OLED の実在を確認 (配線チェック)
 *    - firmware/core の RobotCore を実機で回して OLED に顔を描画
 *    - シリアル / BOOTボタンから状態遷移イベントを注入して目視確認
 *
 *  音声(I2S)・Wi-Fi・WebSocket は Stage 2 以降で追加する。
 *  このファイルが唯一の「実機依存コード」であり、firmware/core は
 *  シミュレーターとまったく同じソースを共有している。
 * ============================================================================
 */

#include <Arduino.h>
#include <Wire.h>
#include <Preferences.h>
#include <U8g2lib.h>
#include <WiFi.h>
#include <ArduinoOTA.h>

#include "IHal.h"
#include "RobotCore.h"
#include "NetLink.h"
#include "AudioIo.h"
#include "Provisioning.h"
#include "VoiceClips.h"

#include <qrcode.h>

// ---------------------------------------------------------------------------
// ボード設定
// ---------------------------------------------------------------------------

// XIAO ESP32S3 の I2C: D4 = GPIO5 (SDA) / D5 = GPIO6 (SCL)
// ReSpeaker Lite に直挿しした場合は Grove I2C コネクタがこの2本に出ている。
#ifndef KATANORI_I2C_SDA
#define KATANORI_I2C_SDA 5
#endif
#ifndef KATANORI_I2C_SCL
#define KATANORI_I2C_SCL 6
#endif

// SSD1306 のI2Cアドレス (7bit)。基板によっては 0x3D の個体もある。
#ifndef KATANORI_OLED_ADDR
#define KATANORI_OLED_ADDR 0x3C
#endif

// XIAO ESP32S3 の BOOT ボタン (押下でLOW)
#ifndef KATANORI_BOOT_BUTTON
#define KATANORI_BOOT_BUTTON 0
#endif

// ReSpeaker Lite 裏の Usr ボタン。基板の Usr-D2 穴にジャンパーピンを通して
// 導通させている（はんだ付けは一切していない。ピンはぶら下がっているだけ）。
// D2 = GPIO3。XMOS側は未使用なので、押下でGNDに落ちる普通のボタンとして読める。
// (GPIO3はストラッピングピンだが INPUT_PULLUP で読むだけなら影響しない)
#ifndef KATANORI_USR_BUTTON
#define KATANORI_USR_BUTTON 3
#endif

// OTA (Wi-Fi経由のファーム更新)。筐体に封入した後もファームを直せるようにする。
// パスワードは「LAN内の他人が勝手に書き込めない」ための合言葉で、秘匿情報ではない
// (Wi-Fi資格情報と違いNVSではなくビルドフラグで差し替える)。
#ifndef KATANORI_OTA_HOSTNAME
#define KATANORI_OTA_HOSTNAME "katanori"
#endif
#ifndef KATANORI_OTA_PASSWORD
#define KATANORI_OTA_PASSWORD "katanori"
#endif

// XIAO ESP32S3 のユーザーLED (GPIO21)。アクティブLOW = LOWで点灯。
// 未設定のままだと点きっぱなしで眩しいので起動時に明示的に消す。
// 仕様書では「通信中のステータス表示」に使う予定なので Stage 2 で点灯制御を入れる。
#ifndef KATANORI_USER_LED
#define KATANORI_USER_LED 21
#endif

// 音量つまみ: AS5600 磁気角度センサ (I2C 0x36。docs/KNOB-ENCODER.md)。
// RAW ANGLE(12bit) を読み、ゼロ点（NVS保存。'knobzero' で設定）からの相対角度を
// 0-100% へ写す。起動時に 0x36 が応答しなければ下の可変抵抗(ADC)経路へ
// フォールバックする（机の上で配線を差し替えて切り替えられるように残してある）。
#ifndef KATANORI_KNOB_SPAN_DEG
#define KATANORI_KNOB_SPAN_DEG 270  // ゼロ点からこの角度で100%。本番は機構の壁に合わせる
#endif
#ifndef KATANORI_KNOB_OFF_DEG
#define KATANORI_KNOB_OFF_DEG 5    // この角度未満はOFF。リードが閉じる数度手前に置く(docs/POWER.md)
#endif
#ifndef KATANORI_KNOB_FULL_DEG
#define KATANORI_KNOB_FULL_DEG 10  // 上端からこの角度以内は100%。回し切りを点で当てずに済む
#endif
#ifndef KATANORI_KNOB_DIR_INVERT
#define KATANORI_KNOB_DIR_INVERT 0  // 回して%が逆に動く組み付けはこれを1に (DIR=GNDで時計回り増が既定)
#endif

// 音量つまみ（旧・フォールバック: スイッチ付き可変抵抗 RV121SF-20-02J-B10K）
// 中点 -> D0 = GPIO1 (ADC1_CH0)。外側2本は 3V3 と GND（OFF位置でワイパーが
// 導通している側の端子がGND。半田付け前にテスターで確認済みであること）。
#ifndef KATANORI_VOL_ADC
#define KATANORI_VOL_ADC 1
#endif

// つまみ連動スイッチ。⚠ 旧設計では D1 = GPIO2 を使っていたが、**D1(GPIO2)は
// 基板内でXMOSのリセット線（アクティブHIGH）に繋がっている**（2026-08-05確定。
// ESPHome公式構成の reset_pin: GPIO2 と、この1行の有無で mic 0フレームが
// 再現/解消することの両方で確認）。INPUT_PULLUP にした瞬間、XMOSはリセットに
// 押さえ込まれてI2Sが止まる。**GPIO2には二度と pinMode しないこと。**
// 旧ボードで「つまみを回すとコーデックが死ぬ」ように見えたのもこれ
// （スイッチがGNDに落としている間だけXMOSが動けていた）。
// -1 = スイッチ無し（常にON扱い。OFF判定はAS5600の角度閾値が担う）
#ifndef KATANORI_KNOB_SW
#define KATANORI_KNOB_SW -1
#endif
#ifndef KATANORI_KNOB_SW_INVERT
#define KATANORI_KNOB_SW_INVERT 0
#endif

// つまみ最大位置のゲイン。アンプは5Wまで出せるがスピーカーは2W・耳も近いので
// 上限を切る（既定の再生音量0.35が「実用の中心」になる程度の頭打ち）。
#ifndef KATANORI_KNOB_MAX_GAIN
#define KATANORI_KNOB_MAX_GAIN 0.70f
#endif

// ADCフォールバック時のつまみ位置の換算は線形式ではなく実測テーブル kKnobCurve
// （音量つまみの節）。外側2本の向きの吸収もテーブルが担う（旧 KATANORI_VOL_INVERT は廃止）。

// 描画レート。128x64 の全面転送は 400kHz I2C で約23ms かかるため、
// 20FPS(50ms)がこの構成の実用上限。上げたい場合は I2C を 1MHz にする。
static constexpr uint32_t FRAME_INTERVAL_MS = 50;
// 音声受信中はこちらへ落とす（描画がCPUを占有して受信を落とすのを防ぐ）
static constexpr uint32_t FRAME_INTERVAL_SLOW_MS = 120;

// DisplayBuffer は MSB(0x80)=左ピクセル。U8g2 の drawBitmap() は U8glib互換の
// MSB-first なのでそのまま渡せる。万一 8ピクセル単位で左右反転して見えたら
// この定義を 1 にして XBM(LSB-first)へ変換する経路へ切り替える。
#ifndef KATANORI_DISPLAY_BIT_REVERSE
#define KATANORI_DISPLAY_BIT_REVERSE 0
#endif

// 診断用: I2Cバスに一切触らないビルド（-DKATANORI_I2C_SILENCE=1）。
//
// このI2CバスはXMOSとESP32の2マスター構成（コーデックを設定するのはXMOS。
// そこへESP32もミュート書き込み・スキャン・OLED転送を撃ち込む）。起動直後の
// 同時アクセスがXMOSを飛ばし、I2Sクロック停止（mic 0フレーム）を起こしている
// 疑いがある（2026-08-05・⚠推定）。このフラグはその切り分け専用で、
// コーデック・OLED・AS5600への全I2Cを黙らせる。顔は表示されない。
// ⚠ コーデックのミュートもしないので、スピーカー線を外して使うこと。
#ifndef KATANORI_I2C_SILENCE
#define KATANORI_I2C_SILENCE 0
#endif

// 診断用: audioIo.begin() 直後で setup を打ち切り、micだけ回す（-DKATANORI_MIN_BOOT=1）
#ifndef KATANORI_MIN_BOOT
#define KATANORI_MIN_BOOT 0
#endif

// ---------------------------------------------------------------------------
// グローバル
// ---------------------------------------------------------------------------

static U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, /* reset= */ U8X8_PIN_NONE);

#if KATANORI_DISPLAY_BIT_REVERSE
static uint8_t reverseByte(uint8_t b) {
    b = static_cast<uint8_t>((b & 0xF0) >> 4 | (b & 0x0F) << 4);
    b = static_cast<uint8_t>((b & 0xCC) >> 2 | (b & 0x33) << 2);
    b = static_cast<uint8_t>((b & 0xAA) >> 1 | (b & 0x55) << 1);
    return b;
}
#endif

// ---------------------------------------------------------------------------
// 接続状況の表示（繋がっていない間は、顔をやめてこれを出す）
//
// 顔だけを出していると「動いている = 正常」に見える。Wi-Fiに繋がっていなくても
// 顔は同じように動くので、繋がっていないことに気づけない。
// 実際、引っ越しで保存済みSSIDが消えた機体が、顔を出したまま1分近く黙って
// 再試行を続けた（2026-07-29）。繋がっていない間は、必ずここに理由を出す。
//
// 【顔の下に10pxの帯で重ねる方式は失敗した】128pxに9文字入れるには1文字10pxしか
// 使えず、実機では「つ」が潰れて読めなかった。文字を大きくすると顔と同居できない。
// 伝えるほうが顔より大事なので、繋がっていない間は画面ごと文字に明け渡す。
// 繋がれば顔に戻る。
//
// 文字は日本語。読むのは設置した本人ではなく使う人で、"no WiFi" では伝わらない。
// 16pxの日本語フォント(b16_t_japanese1)を2行。1行は全角8文字（128px）が上限で、
// 超えるとシリアルに警告が出る。**漢字は使わない**（japanese1 に無い字は
// 幅0で消える）。かな＋ASCIIに留めること。
// ---------------------------------------------------------------------------

/** 2行ぶん。1行目が空なら顔を出す（= 繋がっていて伝えることが無い）。UTF-8。 */
static char netMsg1[40] = {0};
static char netMsg2[40] = {0};

static void setNetMessage(const char* line1, const char* line2 = "") {
    if (line1 == nullptr) line1 = "";
    if (line2 == nullptr) line2 = "";
    if (strncmp(netMsg1, line1, sizeof(netMsg1)) == 0 &&
        strncmp(netMsg2, line2, sizeof(netMsg2)) == 0) {
        return;
    }
    strncpy(netMsg1, line1, sizeof(netMsg1) - 1);
    netMsg1[sizeof(netMsg1) - 1] = '\0';
    strncpy(netMsg2, line2, sizeof(netMsg2) - 1);
    netMsg2[sizeof(netMsg2) - 1] = '\0';
}

/** 自己診断パターンの表示終了時刻。この間は顔で上書きしない。 */
static uint32_t selfTestUntilMs = 0;

/** 音量オーバーレイ（つまみを回した直後だけ顔に重ねる）の表示終了時刻と値。 */
static uint32_t volOverlayUntilMs = 0;
static int volOverlayPct = 0;
/**
 * 次の1回だけ音量表示を出さない。
 *
 * ONへ戻すとしきい値を跨いだぶんで必ず%が変わるため、そのままだと
 * ブラウン管が開いた直後に音量画面が割り込み、顔より先に数字が出る。
 *
 * **時間で抑えてはいけない**（一度そうして直した）。抑えている間に回しても
 * 数字が動かず、「OFF直後にひねっても%が変わらない」という別の不満になる。
 * 跨いだ1回ぶんだけ捨てれば、手を止めれば顔・回し続ければ%と両立する。
 */
static bool volOverlaySuppressOnce = false;
/**
 * この時刻まで画面を黒のままにする（顔も接続表示も描かない）。
 *
 * ブラウン管が開いた直後に顔を描くと、まだ回している人には
 * 「顔が一瞬出てから数字に差し替わる」ちらつきになる。開いた後を少し黒で
 * 持たせれば、その間に回していれば数字へ・止まっていれば顔へ、直接分岐できる。
 */
static uint32_t uiBlankUntilMs = 0;

/**
 * 音量の画面（数字を大きく＋下にインジケーター）を1枚描く。
 *
 * **顔は出さない。** 顔に小さく重ねる案は読みにくかった（ユーザー判断
 * 2026-08-03）。治具には壁が無く「今どこまで回ったか・100%はどこか・
 * 折返し帯に入ったか」が手の感触では分からないため、回している間はこれだけを見せる。
 * OFFへ倒した瞬間にも直接呼ぶ（ブラウン管アニメの前に「OFF」を見せるため）。
 */
static void drawVolumeScreen(int pct) {
    if (KATANORI_I2C_SILENCE) {
        return;
    }
    char buf[8];
    if (pct <= 0) {
        snprintf(buf, sizeof(buf), "OFF");
    } else {
        snprintf(buf, sizeof(buf), "%d%%", pct);
    }

    u8g2.clearBuffer();
    u8g2.setDrawColor(1);
    u8g2.setFont(u8g2_font_fub25_tr);
    int w = u8g2.getStrWidth(buf);
    int x = (128 - w) / 2;
    if (x < 0) {
        x = 0;
    }
    u8g2.drawStr(x, 36, buf);

    // 下のインジケーター。枠を常に出して「あとどれだけ回せるか」を見せる
    const int bx = 4, bw = 120, by = 48, bh = 12;
    u8g2.drawFrame(bx, by, bw, bh);
    int fill = pct * (bw - 4) / 100;
    if (fill > 0) {
        u8g2.drawBox(bx + 2, by + 2, fill, bh - 4);
    }
    u8g2.sendBuffer();
}
/** オーバーレイの表示時間。回している最中は指を止めるたびに延長される。 */
static constexpr uint32_t kVolOverlayMs = 1500;

/**
 * 接続状況の表示を確かめている最中か（シリアル `bn`）。
 *
 * この表示はWi-Fiに繋がっていないときだけ出るので、繋がる機体では見られない。
 * 文字の大きさ・読みやすさは実物を見ないと判断できない（10pxの帯にしたときは
 * 実機で「つ」が潰れて読めなかった）ため、繋がったままでも出せる口を用意する。
 * この間は自動接続が表示を消すのを止める。
 */
static bool bannerDemo = false;

class Esp32Hal : public katanori::IHal {
public:
    uint32_t millis() override {
        return ::millis();
    }

    float getMicLevel() override {
        return katanori::audioIo.micLevel();
    }

    /** 音量表示の期間中なら1枚描いて true。描画の実体は drawVolumeScreen()。 */
    static bool drawVolumeScreenIfActive() {
        if (static_cast<int32_t>(::millis() - volOverlayUntilMs) >= 0) {
            return false;
        }
        drawVolumeScreen(volOverlayPct);
        return true;
    }

    /** 1行を中央に置く。幅が足りなければシリアルに出す（黙って切れないように）。 */
    static void drawCenteredLine(const char* text, int baselineY) {
        if (text[0] == '\0') {
            return;
        }
        const int w = u8g2.getUTF8Width(text);
        static int lastWarnedW = -1;
        if (w > 128 && w != lastWarnedW) {
            lastWarnedW = w;
            Serial.printf("[UI] !! \"%s\" は%dpx。128pxに収まりません（右が切れます）\n",
                          text, w);
        }
        int x = (128 - w) / 2;
        if (x < 0) {
            x = 0;
        }
        u8g2.drawUTF8(x, baselineY, text);
    }

    void flushDisplay(const uint8_t* fb) override {
        if (KATANORI_I2C_SILENCE) {
            return;
        }
        u8g2.clearBuffer();

        // つまみを回している間は音量だけ。顔も接続表示も出さない（最優先）
        if (drawVolumeScreenIfActive()) {
            return; // 描画と転送は drawVolumeScreen() の中で済んでいる
        }

        // 復帰アニメ直後の黒。ここで顔を描くと、まだ回している人には
        // 顔が一瞬出てから数字へ差し替わるちらつきになる
        if (static_cast<int32_t>(::millis() - uiBlankUntilMs) < 0) {
            u8g2.sendBuffer(); // clearBuffer 済み = 黒
            return;
        }

        // 繋がっていないときは顔を出さない。顔と併記できる大きさでは読めなかった。
        if (netMsg1[0] != '\0') {
            u8g2.setDrawColor(1);
            u8g2.setFont(u8g2_font_b16_t_japanese1);
            drawCenteredLine(netMsg1, 28);
            drawCenteredLine(netMsg2, 56);
            u8g2.sendBuffer();
            return;
        }

#if KATANORI_DISPLAY_BIT_REVERSE
        static uint8_t xbm[katanori::DisplayBuffer::BUFFER_SIZE];
        for (size_t i = 0; i < katanori::DisplayBuffer::BUFFER_SIZE; ++i) {
            xbm[i] = reverseByte(fb[i]);
        }
        u8g2.drawXBM(0, 0, katanori::DisplayBuffer::W, katanori::DisplayBuffer::H, xbm);
#else
        u8g2.drawBitmap(0, 0,
                        katanori::DisplayBuffer::W / 8,
                        katanori::DisplayBuffer::H,
                        fb);
#endif
        u8g2.sendBuffer();
    }

    void log(const char* msg) override {
        Serial.println(msg);
    }
};

static Esp32Hal hal;
static katanori::RobotCore robot(hal);

// ---------------------------------------------------------------------------
// 対話フロー
//
// wrapper.py が確立した手順をそのまま実機へ移したもの:
//   ウェイクワード -> 録音してDOへ送る -> audioStreamEnd で発話終了を確定
//   -> 応答音声を再生 -> turnComplete + 再生完了で IDLE へ戻る
// ---------------------------------------------------------------------------

// 応答音声の受信中か（顔をSPEAKにするため）
static bool speaking = false;
// Geminiがターンを終えたか。再生キューが空になるまで IDLE には戻らない。
static bool turnComplete = false;
// audioStreamEnd を送った時刻（応答遅延の実測用）
static uint32_t streamEndMs = 0;

// ---------------------------------------------------------------------------
// 自動接続
//
// 渡した相手はUSBもシリアルコンソールも持たない。電源を入れたら、こちらから
// 何も操作せずに会話できる状態まで行き着かなければならない。
//
// Wi-Fi は起動後すぐ自動で繋ぐ。WebSocketは「話しかけられたときに張る」まま
// にする（DOは接続と同時にGeminiへ繋ぐので、常時接続はセッションの浪費になる。
// 詳細は NetLink.h の設計方針）。
// ---------------------------------------------------------------------------

/** 次にWi-Fi接続を試す時刻。0なら即試す。 */
static uint32_t nextWifiTryMs = 0;
/** 連続失敗回数。成功したら0に戻す。 */
static uint8_t wifiFailures = 0;
/**
 * 起動してから一度でもWi-Fiに繋がったか。
 *
 * 一度も繋がらないなら設定が悪い（SSID変更・パスワード間違い）と判断して
 * 設定モードへ落ちる。一度繋がった後の切断はルーターの再起動や電波状況が
 * 原因なので、設定モードへ落とさず再試行を続ける（勝手に設定モードへ入って
 * 会話が終わるほうが利用者には理不尽）。
 */
static bool wifiEverConnected = false;
/** 一度も繋がらないまま何回失敗したら設定モードへ落ちるか。 */
static constexpr uint8_t WIFI_FAILURES_TO_PROVISIONING = 3;

/**
 * 直近の失敗が「そのSSIDが電波に出ていない」だったか。
 *
 * 画面に出す文言を変えるためと、再試行の間隔を詰めるために持つ。
 * 「パスワードが違う」と「引っ越してSSIDが消えた」は、利用者から見れば
 * まったく別の出来事なので、同じ文言で済ませてはいけない。
 */
static bool ssidMissing = false;
/**
 * SSIDが見当たらないときの再試行の間隔。
 *
 * この失敗は約2.5秒で返ってくる（理由コード201が来た時点で打ち切るため）ので、
 * 間隔も詰めてよい。3回失敗して設定モードへ移るまで、電源投入から約15秒。
 * 以前は12秒×3回＋広がる待ち時間で約56秒かかっていた。
 */
static constexpr uint32_t NO_AP_RETRY_MS = 4000;

// --- 焼き込み音声（VoiceClips.h） ---
//
// サーバーに繋がる前・繋がらないときに状況を伝えるための音。シリアルを持たない
// 相手にとっては、これが唯一の「今どうなっているか」の手がかりになる。

/** 起動アナウンスを鳴らしたか。電源を入れてから1回だけ。 */
static bool bootAnnounced = false;

// ---------------------------------------------------------------------------
// 音量つまみ（AS5600 磁気角度センサ。docs/KNOB-ENCODER.md）
//
// 磁石の絶対角度をI2Cで読んで再生ゲインへ反映する。回るのは磁石だけで、
// 電気的な接点も配線も動かない（可変抵抗で起きた摩耗・熱劣化・回転中の
// コーデック死をまとめて消すための移行）。
//
// ゼロ点＝OFF位置の RAW ANGLE は NVS に持つ（'knobzero' で保存）。AS5600 の
// OTP(ZPOS/MPOS) は焼き直しが効かないので一生使わない。OFF判定は角度の閾値で、
// 左に回し切ると将来はリードスイッチが昇圧ICのENを落として電源ごと切る
// （docs/POWER.md。ファームはENに触らない）。電源基板が無い今は
// 「会話を終え、出力ゲートを閉じ、Wi-Fiと画面を畳む」ところまでを担当する
// （疑似電源OFF。pumpPowerDown()）。
//
// 起動時に 0x36 が応答しなければ旧経路（可変抵抗のADC＋連動スイッチ）へ
// フォールバックする。判定し直しは 'knobsrc'。
// ---------------------------------------------------------------------------

// 会話制御・AS5600の読み出しは下の方で定義されるため前方宣言
static bool conversationActive();
static void endConversation();
static bool as5600Read(uint8_t reg, uint8_t* out, uint8_t len);
static uint16_t as5600Word(const uint8_t* p);

/** つまみがOFF位置か。デバウンス済み。 */
static bool knobOff = false;
/** ならした後のつまみ位置(0-100)。-1 = まだ一度も読めていない。 */
static int knobPercent = -1;

/** AS5600で角度を読めているか。false のあいだはADC経路で動く。 */
static bool knobAs5600Ok = false;
/** ゼロ点（OFF位置のRAW ANGLE値）。NVSの "knob/zero"。 */
static uint16_t knobZeroRaw = 0;
/** ゼロ点を一度でも保存したか。未設定のままでは角度が当てにならない。 */
static bool knobZeroSet = false;
/** 連続して読めなかった回数。続いたらADCへフォールバックする。 */
static uint8_t knobReadFailures = 0;

// 角度(度)をRAW ANGLEの刻み(4096/周)へ。閾値の比較はすべてこの単位で行う
static constexpr uint16_t kKnobSpanRaw =
    (uint16_t)((uint32_t)KATANORI_KNOB_SPAN_DEG * 4096 / 360);
static constexpr uint16_t kKnobOffRaw =
    (uint16_t)((uint32_t)KATANORI_KNOB_OFF_DEG * 4096 / 360);
static constexpr uint16_t kKnobFullRaw =
    (uint16_t)((uint32_t)KATANORI_KNOB_FULL_DEG * 4096 / 360);
/** 100%に吸着し始める相対角度。ここから上端までは全部100%。 */
static constexpr uint16_t kKnobFullFromRaw =
    (kKnobSpanRaw > kKnobFullRaw + kKnobOffRaw) ? (uint16_t)(kKnobSpanRaw - kKnobFullRaw)
                                                : kKnobSpanRaw;
/** OFF解除はOFF閾値より3度上（境目でのバタつき防止のヒステリシス）。 */
static constexpr uint16_t kKnobHystRaw = (uint16_t)(3ul * 4096 / 360);

/** スイッチの生読み（ADCフォールバック用）。ON位置=接点が閉じてGNDに落ちる=LOW。 */
static bool knobSwitchRawOn() {
#if KATANORI_KNOB_SW < 0
    return true;  // スイッチ無し構成: 常にON。OFFはAS5600の角度閾値で判定する
#elif KATANORI_KNOB_SW_INVERT
    return digitalRead(KATANORI_KNOB_SW) == HIGH;
#else
    return digitalRead(KATANORI_KNOB_SW) == LOW;
#endif
}

/**
 * つまみ位置(0-100)を再生ゲインへ写す。
 *
 * Bカーブ×振幅リニアだと聴感では上半分がほとんど変化しないため、
 * デシベル直線（1%あたり0.3dB、全域で-30dB..0dB）の指数カーブにする。
 * 0%は完全な無音。100%で上限ゲイン。
 */
static void applyKnobVolume(int pct) {
    float g = 0.0f;
    if (pct > 0) {
        float db = (pct - 100) * 0.30f;
        g = KATANORI_KNOB_MAX_GAIN * powf(10.0f, db / 20.0f);
    }
    katanori::audioIo.setGain(g);
}

/**
 * RAW ANGLE -> ゼロ点からの相対角度（RAW刻み・0..kKnobSpanRaw）。
 *
 * 本番の機構は壁があるので 0..SPAN の外へは行けないが、治具には壁が無い。
 * 範囲外へ回された値は近いほうの端（ゼロ点の少し手前→0 / 上端超え→SPAN）へ
 * 倒し、ありえない%が出ないようにする。
 */
static uint16_t knobRelAngle(uint16_t raw) {
#if KATANORI_KNOB_DIR_INVERT
    uint16_t rel = (uint16_t)((knobZeroRaw - raw) & 0x0FFF);
#else
    uint16_t rel = (uint16_t)((raw - knobZeroRaw) & 0x0FFF);
#endif
    if (rel > kKnobSpanRaw) {
        rel = (uint16_t)(rel - kKnobSpanRaw) < (uint16_t)((4096 - kKnobSpanRaw) / 2)
                  ? kKnobSpanRaw
                  : 0;
    }
    return rel;
}

/**
 * 相対角度 -> つまみ位置(%)。OFF閾値以下は0、上端で100。
 *
 * **0% は「OFF判定と同じ意味」でなければならない。** 素直に按分すると整数の
 * 切り捨てで OFF閾値の少し上（5.0〜7.6度）まで0%になり、「画面と音量は0%なのに
 * 疑似電源OFFに入らない」帯ができる（2026-08-03に実機で再現）。
 * OFF閾値を超えたら最低でも1%を返して、0%を OFF専用の値にしておく。
 */
static int knobAngleToPercent(uint16_t rel) {
    if (rel <= kKnobOffRaw) {
        return 0;
    }
    // 上端も帯にする。OFF側が5度の帯を持つのに100%だけ点で当てるのは非対称で、
    // 壁の無い治具では回し切っても100%に届かない（ユーザー指摘 2026-08-03）
    if (rel >= kKnobFullFromRaw) {
        return 100;
    }
    int pct = 1 + (int)((uint32_t)(rel - kKnobOffRaw) * 99u / (kKnobFullFromRaw - kKnobOffRaw));
    return pct > 100 ? 100 : pct;
}

// ADC実測値 -> つまみ位置(%)。2026-07-29 にこの個体で実測した換算テーブル。
// B10K（直線）のはずが実際は「3時で22%・4時→5時の区間に全変化の6割」という
// 極端なカーブで、線形換算では音量調整として使いものにならない。実測点を
// 区間線形補間して「見た目の回転角 ≒ %」へ戻す。
// ADCが減少方向なのは左端（OFF側）が3V3に付いている個体だから。向きの吸収も
// この表が担う。つまみを交換・再半田したら必ず取り直すこと（各位置で `knob` を
// 読んで下の点を差し替える）。
static const struct { int adc; int pct; } kKnobCurve[] = {
    { 4095,   0 },  // 最小（カチッの直後）
    { 3464,  50 },  // 12時
    { 3116,  78 },  // 3時
    { 2619,  88 },  // 4時
    {   24,  97 },  // 5時
    {    0, 100 },  // 右端
};

static int knobAdcToPercent(int adc) {
    if (adc >= kKnobCurve[0].adc) {
        return kKnobCurve[0].pct;
    }
    for (size_t i = 1; i < sizeof(kKnobCurve) / sizeof(kKnobCurve[0]); ++i) {
        if (adc >= kKnobCurve[i].adc) {
            long span = kKnobCurve[i - 1].adc - kKnobCurve[i].adc;
            long dpct = kKnobCurve[i].pct - kKnobCurve[i - 1].pct;
            return kKnobCurve[i - 1].pct
                 + static_cast<int>((kKnobCurve[i - 1].adc - adc) * dpct / span);
        }
    }
    return 100;
}

/**
 * つまみを読むか。シリアル `knobdis` で止められる。
 *
 * 配線を外して切り分けるときに使う。外したままだとピンが浮いて「OFF位置」と
 * 誤認し、ソフト側の理由で無音になるため、電気的な原因と区別がつかなくなる。
 * 止めているあいだはゲインもOFF判定も固定される。
 */
// I2C_SILENCEビルドでは最初から止める。つまみ未接続のADC浮きが「OFF位置」に
// 化けて疑似電源OFFへ落ち、micテストを邪魔するのを防ぐ。
static bool knobEnabled = KATANORI_I2C_SILENCE == 0;

/**
 * OFF状態の確定。切り替わったときの後始末は経路（AS5600/ADC）によらず同じ。
 */
/**
 * ブラウン管が消えるときの演出。中央の横線につぶれ、点になって消える。
 *
 * つまみをOFFへ回した瞬間に出す。画面が黙って消えると「壊れた」と見えるが、
 * この2/3秒があるだけで「自分が消した」になる（ユーザー要望 2026-08-03）。
 * 描画を止めて一気に描く（OLEDの全面転送が約29msなので、これで約0.4秒）。
 */
static void powerSleepOled(); // 定義は疑似電源OFFの節（powerOledDown の直後）

static void playCrtOffAnimation() {
    const int cx = 64;
    const int cy = 32;

    // 1) 上下の縁が中央へ寄り、映像が横線へつぶれる
    //    白ベタで塗らないこと。OLEDでは白=全画素点灯で、ブラウン管とは逆の
    //    印象になる（実物で光っているのは縁の走査線で、中は黒）
    for (int h = 64; h >= 2; h -= 10) {
        u8g2.clearBuffer();
        u8g2.setDrawColor(1);
        u8g2.drawBox(0, cy - h / 2, 128, 2);
        u8g2.drawBox(0, cy + h / 2 - 2, 128, 2);
        u8g2.sendBuffer();
    }
    // 2) 横線が中央の点へ縮む
    for (int w = 128; w >= 4; w -= 20) {
        u8g2.clearBuffer();
        u8g2.drawBox(cx - w / 2, cy - 1, w, 2);
        u8g2.sendBuffer();
    }
    // 3) 残光。3px -> 1px と細めてから消す（いきなり消すと角が立つ）
    //    ※ 最後に画面そのものを落とす。演出の後に顔が戻らないようにするため
    u8g2.clearBuffer();
    u8g2.drawBox(cx - 1, cy - 1, 3, 3);
    u8g2.sendBuffer();
    delay(80);
    u8g2.clearBuffer();
    u8g2.drawPixel(cx, cy);
    u8g2.sendBuffer();
    delay(60);
    u8g2.clearBuffer();
    u8g2.sendBuffer();

    /*
     * 画面を落とすところまでが演出。
     *
     * 疑似電源OFFが画面を消すのは「OFF判定から2秒後」だが、演出は約1.2秒で
     * 終わる。その差の約0.8秒で通常の描画が動き、**消えた直後に顔が戻る**
     * （2026-08-03に実機で発生）。演出まで出したならもう確定でよい。
     */
    powerSleepOled();
}

static void powerWakeOled(); // 定義は疑似電源OFFの節（powerOledDown の直後）

/** 上の逆再生。点が灯り、横に伸び、画面が開く。つまみをONへ回した瞬間に出す。 */
static void playCrtOnAnimation() {
    // 疑似電源OFF中は表示が止まっている。戻すのは pumpPowerDown だが
    // それはこの後の処理なので、ここで自分で起こさないとアニメが見えない
    powerWakeOled();

    const int cx = 64;
    const int cy = 32;

    // 1) 点が灯る
    u8g2.clearBuffer();
    u8g2.setDrawColor(1);
    u8g2.drawBox(cx - 1, cy - 1, 3, 3);
    u8g2.sendBuffer();
    delay(80);

    // 2) 横線が伸びる
    for (int w = 4; w <= 128; w += 20) {
        u8g2.clearBuffer();
        u8g2.drawBox(cx - w / 2, cy - 1, w, 2);
        u8g2.sendBuffer();
    }
    // 3) 縁が上下へ開く。中は黒のままなので、開き切ると自然に真っ黒で終わる
    //    （白ベタで開くと、真っ白から顔が出ることになって違和感が出る）
    for (int h = 2; h <= 64; h += 10) {
        u8g2.clearBuffer();
        u8g2.drawBox(0, cy - h / 2, 128, 2);
        u8g2.drawBox(0, cy + h / 2 - 2, 128, 2);
        u8g2.sendBuffer();
    }
    // 4) 消え際を柔らかく。縁を1pxに細めてから消す（2pxのまま消すと角が立つ）
    u8g2.clearBuffer();
    u8g2.drawBox(0, 0, 128, 1);
    u8g2.drawBox(0, 63, 128, 1);
    u8g2.sendBuffer();

    // 5) 黒のまま少し置いてから顔へ渡す。開き切った次のフレームで顔が出ると
    //    「開く」と「映る」が重なって忙しく見える
    u8g2.clearBuffer();
    u8g2.sendBuffer();
    delay(120);

    // 6) しきい値を跨いだぶんの%変化は1回だけ捨てる。捨てないと顔ではなく
    //    数字が先に出てしまう（回し続けたときは2回目以降が出るので邪魔しない）
    volOverlayUntilMs = millis();
    volOverlaySuppressOnce = true;

    // 7) その後しばらく黒で持たせる。この間に回していれば数字へ、
    //    止まっていれば顔へ直接入る（顔をちらっと見せない）
    uiBlankUntilMs = millis() + 250;
}

static void knobSetOffState(bool off) {
    // 起動直後の初回同期では鳴らさない（自己診断パターンを潰さないため）
    static bool inited = false;
    bool animate = inited;
    inited = true;

    knobOff = off;
    if (off) {
        Serial.println("[KNOB] OFF位置 -> 会話を終了し、出力を閉じたままにします");
        if (conversationActive()) {
            endConversation();
        }
        // Wi-Fi設定モード中はQRを消してはいけない（読み取り中の可能性がある）
        if (animate && !katanori::provisioning.active()) {
            // 先に「OFF」を見せる。いきなり消えると、自分がOFFにしたのか
            // 勝手に落ちたのかが分からない（ユーザー要望 2026-08-03）
            drawVolumeScreen(0);
            delay(700);
            playCrtOffAnimation();
            // 消えた後に音量表示が蒸し返さないよう、余韻を残さず切る
            volOverlayUntilMs = millis();
        }
        // 画面と通信は pumpPowerDown() が遅らせて落とす（すぐ戻されたら
        // 何も起きなかったことにするため）
    } else {
        Serial.println("[KNOB] ON位置");
        if (animate && !katanori::provisioning.active()) {
            playCrtOnAnimation();
        }
    }
}

/**
 * 位置(%)の確定。ノイズでコーデック音量を叩き続けないためのデッドバンド(2%≒0.6dB)。
 * ただし両端(0/100)へは即吸着させる（「回し切ったのに無音にならない」を防ぐ）。
 */
static void knobSetPercent(int pct) {
    bool endstop = (pct == 0 || pct == 100) && pct != knobPercent;
    if (knobPercent < 0 || endstop || abs(pct - knobPercent) >= 2) {
        knobPercent = pct;
        applyKnobVolume(pct);
        // 回した本人に見えるように画面へ出す。ただし復帰アニメ直後の1回だけは
        // 捨てる（顔が戻るのを先に見せる。回し続ければ次からは普通に出る）
        if (volOverlaySuppressOnce) {
            volOverlaySuppressOnce = false;
        } else {
            volOverlayPct = pct;
            volOverlayUntilMs = millis() + kVolOverlayMs;
        }
    }
}

/** AS5600経路。RAW ANGLE -> 相対角度 -> % と、角度閾値でのOFF判定。 */
static void pumpKnobAs5600(uint32_t now) {
    uint8_t buf[2];
    if (!as5600Read(0x0C, buf, 2)) {
        // 1回の失敗では騒がない（バスはOLEDの全面転送と共用で混んでいる）。
        // 続くようなら配線が抜けたと判断してADC経路へ落とす。
        if (++knobReadFailures >= 5) {
            knobAs5600Ok = false;
            knobReadFailures = 0;
            Serial.println("[KNOB] !! AS5600が応答しません。可変抵抗(ADC)の読みへ切り替えます");
            Serial.println("[KNOB]    配線を確認して 'knobsrc' で再判定（'mag' で詳細が見えます）");
        }
        return;
    }
    knobReadFailures = 0;

    uint16_t rel = knobRelAngle(as5600Word(buf));

    // --- OFF判定（角度の閾値。3度のヒステリシス + 30msデバウンス） ---
    static bool rawLast = false;
    static uint32_t rawChangedMs = 0;
    static bool inited = false;
    // 入るときは「OFF閾値以下」。knobAngleToPercent の0%と同じ条件にしておく
    // （< と <= がずれていると、境目の1カウントで0%とOFFが食い違う）
    bool rawOff = knobOff ? (rel < kKnobOffRaw + kKnobHystRaw)
                          : (rel <= kKnobOffRaw);
    if (rawOff != rawLast) {
        rawLast = rawOff;
        rawChangedMs = now;
    } else if ((now - rawChangedMs) >= 30) {
        if (!inited || rawOff != knobOff) {
            inited = true;
            knobSetOffState(rawOff);
        }
    }

    // 12bitの角度はADCと違ってほぼ揺れないので、IIRは掛けずそのまま%へ。
    // OFF中は必ず0%（ヒステリシスの戻り帯5〜8度で「2%なのに疑似電源OFF」に
    // なるのを防ぐ。表示と実際の状態を常に一致させる）
    knobSetPercent(knobOff ? 0 : knobAngleToPercent(rel));
}

/** 旧経路（可変抵抗のADC＋連動スイッチ）。AS5600が応答しないときのフォールバック。 */
static void pumpKnobAdc(uint32_t now) {
    // --- 連動スイッチ（30msデバウンス） ---
    static bool rawLast = false;
    static uint32_t rawChangedMs = 0;
    static bool inited = false;
    bool raw = knobSwitchRawOn();
    if (raw != rawLast) {
        rawLast = raw;
        rawChangedMs = now;
    } else if ((now - rawChangedMs) >= 30) {
        bool off = !raw;
        if (!inited || off != knobOff) {
            inited = true;
            knobSetOffState(off);
        }
    }

    // --- 音量（1/8 IIRでならす） ---
    int adc = analogRead(KATANORI_VOL_ADC); // 12bit: 0..4095
    static int avg = -1;
    avg = (avg < 0) ? adc : avg + (adc - avg) / 8;

    knobSetPercent(knobAdcToPercent(avg));
}

/** つまみの監視。main loop から毎回呼ぶ（実際は20ms間隔で動く）。 */
static void pumpVolumeKnob() {
    if (!knobEnabled) {
        return;
    }
    static uint32_t lastPollMs = 0;
    uint32_t now = millis();
    if ((now - lastPollMs) < 20) {
        return;
    }
    lastPollMs = now;

    if (knobAs5600Ok) {
        pumpKnobAs5600(now);
    } else {
        pumpKnobAdc(now);
    }
}

/**
 * ゼロ点（OFF位置）の保存。つまみを左の壁（OFF位置）に当てて 'knobzero' を打つ。
 *
 * OTPには焼かない。NVSなら何度でもやり直せるし、機構を刷り直したら
 * ゼロ点も変わるのが当たり前なので、書き換えられる場所に持つのが正しい。
 */
static void knobSaveZero() {
    if (!knobAs5600Ok) {
        Serial.println("[KNOB] AS5600が使えません（ADC経路で動作中。'knobsrc' で再判定）");
        return;
    }
    uint8_t buf[2];
    if (!as5600Read(0x0C, buf, 2)) {
        Serial.println("[KNOB] RAW ANGLE が読めませんでした。'mag' で状態を見てください");
        return;
    }
    knobZeroRaw = as5600Word(buf);
    knobZeroSet = true;
    Preferences prefs;
    prefs.begin("knob", false);
    prefs.putUShort("zero", knobZeroRaw);
    prefs.end();
    Serial.printf("[KNOB] ゼロ点を保存しました RAW=%u (%.1f度)\n",
                  knobZeroRaw, knobZeroRaw * 360.0f / 4096.0f);
    Serial.printf("[KNOB] ここから右へ%d度でOFF解除、%d度で100%%になります\n",
                  KATANORI_KNOB_OFF_DEG, KATANORI_KNOB_SPAN_DEG);
}

/** つまみの読み元の判定。起動時と 'knobsrc' で呼ぶ。 */
static void knobProbeSource(bool verbose) {
    if (KATANORI_I2C_SILENCE) {
        knobAs5600Ok = false;
        if (verbose) {
            Serial.println("[KNOB] I2C_SILENCE: AS5600を探しません（ADC経路）");
        }
        return;
    }
    uint8_t status = 0;
    knobAs5600Ok = as5600Read(0x0B, &status, 1);
    knobReadFailures = 0;
    if (knobAs5600Ok) {
        Serial.printf("[KNOB] AS5600で角度を読みます（ゼロ点 RAW=%u%s）\n",
                      knobZeroRaw, knobZeroSet ? "" : " ※未設定");
        if (!knobZeroSet) {
            Serial.println("[KNOB] ★ つまみをOFF位置にして 'knobzero' でゼロ点を保存してください");
        }
    } else if (verbose) {
        Serial.println("[KNOB] AS5600(0x36)が応答しないため可変抵抗(ADC)の読みで動きます");
    }
}

/** つまみの初期化。NVSからゼロ点を読み、読み元を判定する。setup() から1回。 */
static void knobInit() {
    Preferences prefs;
    prefs.begin("knob", false);
    knobZeroSet = prefs.isKey("zero");
    knobZeroRaw = prefs.getUShort("zero", 0);
    prefs.end();
    knobProbeSource(true);

    // AS5600が居らず連動スイッチも無い＝つまみのハードが丸ごと未接続。
    // そのままADCフォールバックに落とすと、浮いたD0の読みが音量に化けて
    // 予測不能な大音量になり得る（2026-08-05: 30%でも驚かせた）。読みを止めて
    // 既定ゲインで動く。AS5600を繋げば次回起動から自動で有効になる。
    if (!knobAs5600Ok && KATANORI_KNOB_SW < 0) {
        knobEnabled = false;
        Serial.println("[KNOB] つまみ未接続（AS5600なし・スイッチなし）: 読み取りを止め、既定音量で動きます");
    }
}

// ---------------------------------------------------------------------------
// 疑似電源OFF（つまみOFF位置）
//
// 電源基板が載るまで、本当に電源を切ることはできない（USBでもXMOSごと生きている）。
// できるのは「切ったように見せて、ESP32側の消費だけ減らす」ところまで。
// 昇圧ICのEN制御が載ったら、通信を落とした直後（下の netDown のところ）に
// EN=LOW を足す。ミュート→切断→電源断の順序がそこで揃う。
//
// 一気に落とさず、段階を踏む。つまみは回し切る途中で一瞬OFFを通ることがあるし、
// 「切ったつもりが違った」とすぐ戻すこともある。落とすのが早いほど、戻したときに
// Wi-Fiの再接続で十数秒待たされる。落とし切る前に戻れば、何も起きなかったことになる。
// ---------------------------------------------------------------------------

/** OFF位置になってから画面を消すまで。 */
static constexpr uint32_t KNOB_OFF_OLED_MS = 2000;
/** OFF位置になってから通信を止めるまで。 */
static constexpr uint32_t KNOB_OFF_NET_MS = 5000;

/** 画面を消したか。ONへ戻したとき「消したものだけ」を戻すために持つ。 */
static bool powerOledDown = false;
/** 通信を止めたか。 */
static bool powerNetDown = false;

/** 消えている画面を先に起こす。ON復帰アニメを見せるために使う。 */
static void powerWakeOled() {
    if (powerOledDown) {
        powerOledDown = false;
        u8g2.setPowerSave(0);
    }
}

/**
 * 画面を落とす。OFF演出の最後に呼ぶ。
 *
 * pumpPowerDown() の2秒待ちを待たずに落とすのは、演出が終わってから
 * 待ち時間が明けるまでの隙間で顔が描き直されてしまうため。
 * 段階の管理は powerOledDown が持つので、ここで立てておけば
 * pumpPowerDown() は二重に落とさず、ONへ戻せば正しく戻る。
 */
static void powerSleepOled() {
    if (!powerOledDown) {
        powerOledDown = true;
        u8g2.setPowerSave(1);
    }
}

/**
 * 疑似電源OFFを働かせるか。シリアル `pwr` でトグルする。
 *
 * 無効にすると、つまみOFF位置の挙動はこの機能を足す前と同じ（会話終了と消音だけ）に
 * なる。「つまみを回したら音が出なくなった」の原因がこの機能かどうかを、焼き直さずに
 * 切り分けるために置いてある。
 */
static bool powerDownEnabled = true;

/**
 * 疑似電源OFFで無線を `WIFI_OFF` まで落とすか。シリアル `wifikill` でトグルする。
 *
 * 既定は false（切断まで）。消費電流は WIFI_OFF のほうが小さいので、本当は
 * true にしたい。実測してから決めること。
 *
 * 【この判断を2度間違えている記録】
 * 「WIFI_OFF にするとI2Sが巻き添えで止まる」(2026-07-29) →
 * 「I2Sではなくコーデックの設定が飛ぶ」(2026-07-30) → **どちらも誤り**。
 * 根拠にした試験はどちらも「つまみを回す」操作を含んでいて、そちらが犯人だった。
 * `wifistop` で WIFI_OFF を15秒保持しても、コーデックは生きたままになる。
 * コーデックが死ぬのはつまみを回している最中で、スイッチが開くより前
 * （docs/KNOB-TROUBLE.md）。**一度に1つしか変えないこと。**
 */
static bool powerWifiOff = false;

/** 疑似電源OFFの進行。main loop から毎回呼ぶ。 */
static void pumpPowerDown() {
    static bool counting = false;
    static uint32_t offSinceMs = 0;

    if (!knobOff || !powerDownEnabled) {
        counting = false;
        // 落としたものだけを戻す。まだ落ちていない段階には触らない。
        if (powerOledDown) {
            powerOledDown = false;
            u8g2.setPowerSave(0);
            Serial.println("[PWR] 画面を戻しました");
        }
        if (powerNetDown) {
            powerNetDown = false;
            // 再試行の待ち時間を捨てて即つなぎにいく。つまみを戻した人を
            // 最大30秒待たせるのは、故障と区別がつかない。
            nextWifiTryMs = 0;
            wifiFailures = 0;
            ssidMissing = false;
            Serial.println("[PWR] 通信を戻します（自動接続が動きます）");
        }
        return;
    }

    uint32_t now = millis();
    if (!counting) {
        counting = true;
        offSinceMs = now;
        return;
    }
    uint32_t held = now - offSinceMs;

    if (!powerOledDown && held >= KNOB_OFF_OLED_MS) {
        powerOledDown = true;
        u8g2.setPowerSave(1); // 表示だけ止まる。バッファは残るので戻せば同じ絵が出る
        Serial.printf("[PWR] 画面を消しました（OFFから%u秒）\n",
                      (unsigned)(KNOB_OFF_OLED_MS / 1000));
    }

    if (!powerNetDown && held >= KNOB_OFF_NET_MS) {
        powerNetDown = true;
        katanori::netLink.wsDisconnect();
        // WIFI_OFF まで落とすかどうかは powerWifiOff で切り替わる（既定 false）。
        // 「WIFI_OFF がコーデックを殺す」と一度は結論づけたが、それは誤りだった
        // （詳細は powerWifiOff のコメント）。既定を変えるなら消費電流を実測してから。
        if (powerWifiOff) {
            katanori::netLink.wifiStop();
        } else {
            katanori::netLink.wifiDisconnect();
        }
        // LEDは「通信中」の表示なので、切り終わってから消す
        digitalWrite(KATANORI_USER_LED, HIGH); // アクティブLOW
        Serial.printf("[PWR] 通信を止めました（OFFから%u秒）\n",
                      (unsigned)(KNOB_OFF_NET_MS / 1000));
        // ここに EN=LOW（電源基板が載ったら）
    }
}

// ---------------------------------------------------------------------------
// コーデックの見張り
//
// 3.3Vが一瞬落ちるとコーデック(AIC3204)がリセットされ、設定が初期値へ戻って
// 音が出なくなる。設定を書いているのはXMOSで、それをやるのは基板の電源投入時
// だけなので、ESP32を再起動しても直らない（USBを抜き差しするまで戻らない）。
//
// I2Cは応答し、I2Sのクロックも来ていて、再生サンプル数も増える。つまり
// 見ていないと気づけない。ここで気づけるようにしておく。
// 実機で発生した経緯は firmware/esp32/README.md を参照。
// ---------------------------------------------------------------------------

static void pumpCodecWatch() {
    if (KATANORI_I2C_SILENCE) {
        return;
    }
    static uint32_t lastPollMs = 0;
    static bool lastAlive = true;

    uint32_t now = millis();
    if ((now - lastPollMs) < 200) {
        return;
    }
    lastPollMs = now;

    bool alive = katanori::audioIo.codecOutputAlive();
    if (alive == lastAlive) {
        return;
    }
    lastAlive = alive;
    if (!alive) {
        Serial.println("[CODEC] !! リセットを検出しました（DACの電源が落ちています）");
        Serial.println("[CODEC]    3.3Vが瞬断しています。ESP32を再起動しても直りません");
        Serial.println("[CODEC]    USBを抜き差しするとXMOSが設定し直して復旧します");
    } else {
        Serial.println("[CODEC] 出力が復帰しました");
    }
}

// ---------------------------------------------------------------------------
// 出力ゲート
//
// コーデックの開け閉めは、必ずここ1か所だけで行う。
//
// 開けっ放しのまま電源を切られる/リセットされると、その状態がコーデックに
// 残り、次の起動でROMブートログ(115200bps)がGPIO43=I2S DOUTからそのまま
// 増幅されて轟音になる。実際にこれで耳を痛めている。
//
// 以前は再生経路ごとに setOutputMute() を呼んでいた（応答再生・割り込み・
// ターン終了）。経路が増えるたびに閉じ忘れの穴ができる作りで、起動アナウンスを
// 足した時点で「電源を入れるだけで自動的に開く」経路が生まれてしまった。
//
// 方針: 鳴らすものがキューにあるあいだだけ開ける。それ以外は必ず閉じる。
// ---------------------------------------------------------------------------

/**
 * キューが空になってから閉じるまでの猶予。
 *
 * isPlaying() が見ているのはソフト側のキューだけで、I2Sドライバ内にはまだ
 * 送信待ちが残っている。空になった瞬間に閉じると語尾が切れる。
 */
static constexpr uint32_t OUTPUT_TAIL_MS = 250;

/**
 * 手動 `unmute` のあいだだけゲートを止める。
 *
 * ゲートは「鳴っていなければ閉じる」ので、そのままでは手動で開けても
 * すぐ閉じられてスピーカー単独の切り分けができない。`mute` で戻る。
 */
static bool outputGateOverride = false;

/** 出力ゲート。main loop から毎回呼ぶ。 */
static void pumpOutputGate() {
    if (KATANORI_I2C_SILENCE) {
        return;
    }
    static uint32_t emptySinceMs = 0;

    // つまみがOFF位置のあいだは何があっても閉じておく。
    // 手動 `unmute`（診断用）より物理操作を優先する。
    if (knobOff) {
        emptySinceMs = 0;
        if (!katanori::audioIo.outputMuted()) {
            katanori::audioIo.setOutputMute(true);
        }
        return;
    }

    if (outputGateOverride) {
        return;
    }

    if (katanori::audioIo.isPlaying()) {
        emptySinceMs = 0;
        if (katanori::audioIo.outputMuted()) {
            katanori::audioIo.setOutputMute(false);
        }
        return;
    }

    if (katanori::audioIo.outputMuted()) {
        return;
    }
    if (emptySinceMs == 0) {
        emptySinceMs = millis();
        return;
    }
    if (millis() - emptySinceMs >= OUTPUT_TAIL_MS) {
        emptySinceMs = 0;
        katanori::audioIo.setOutputMute(true);
    }
}

/**
 * こちらから再起動する前にコーデックを閉じる。
 *
 * 開いたままESP32だけがリセットされると、次の起動でROMブートログが増幅される。
 * クラッシュ・電池切れ・ブラウンアウトによるリセットはここを通らないので塞げないが、
 * 意図して落とすときは必ず閉じてから落とす（OTAの onStart も同じことをしている）。
 */
static void muteBeforeRestart() {
    if (!katanori::audioIo.setOutputMute(true)) {
        Serial.println("[CODEC] !! ミュートに失敗しました。スピーカーを耳から離してください");
    }
}

/** ボタンが押されたが、まだサーバーに繋がっていない状態か。 */
static bool pendingTurn = false;
/** その待ち始めた時刻。 */
static uint32_t pendingTurnMs = 0;
/** 接続を待つ上限。TLSハンドシェイクを含めても実測2秒程度で繋がる。 */
static constexpr uint32_t PENDING_TURN_TIMEOUT_MS = 15000;

// VAD計測モード（定義は下）。会話とマイクを共有するので、送信側から参照する。
static bool vadMeasuringActive();
static void vadFeed(const int16_t* pcm, size_t n);

/**
 * 状態機械を目的の状態まで歩かせる。
 *
 * StateMachine は IDLE -> LISTEN -> THINK -> SPEAK の一本道で、途中の
 * イベントを飛ばせない。一方 Gemini は自前のVADで勝手にターンを進めるため、
 * こちらの状態と食い違う（例: LISTENが10秒でタイムアウトしてIDLEに戻った後に
 * 応答音声が届く）。顔を実際の会話に追従させるため、必要なイベントを
 * 順に注入して追いつかせる。
 */
static void driveTo(katanori::RobotState target) {
    for (int guard = 0; guard < 4 && robot.state() != target; ++guard) {
        switch (robot.state()) {
        case katanori::RobotState::IDLE:
            robot.injectEvent(katanori::RobotEvent::WAKE_WORD);
            break;
        case katanori::RobotState::LISTEN:
            robot.injectEvent(katanori::RobotEvent::SPEECH_END);
            break;
        case katanori::RobotState::THINK:
            robot.injectEvent(katanori::RobotEvent::RESPONSE_READY);
            break;
        case katanori::RobotState::SPEAK:
            robot.injectEvent(katanori::RobotEvent::SPEECH_DONE);
            break;
        }
    }
}

/** DOから届いた生PCM。そのまま再生キューへ積むだけ。 */
static void onAudio(const int16_t* pcm, size_t samples) {
    if (!speaking) {
        speaking = true;
        turnComplete = false;
        // 出力を開けるのは pumpOutputGate() の仕事。ここでは触らない。
        if (streamEndMs != 0) {
            Serial.printf("[TURN] 発話終了 -> 応答開始 %.2f秒\n",
                          (millis() - streamEndMs) / 1000.0f);
            streamEndMs = 0;
        }
        driveTo(katanori::RobotState::SPEAK);
    }
    katanori::audioIo.play(pcm, samples);
}

/** DOから届いた制御JSON。パーサは積まず、必要な語だけ拾う。 */
static void onControl(const char* json) {
    // 割り込み: マイクがスピーカー音を拾うと Gemini がこれを返す。
    // 未再生ぶんを捨てないと、古い応答が延々と流れ続ける。
    if (strstr(json, "\"interrupted\"") != nullptr) {
        Serial.println("[TURN] 割り込み検知 — 再生を中断します");
        // キューを空にすれば pumpOutputGate() が閉じる
        katanori::audioIo.stopPlayback();
        speaking = false;
        turnComplete = false;
        robot.injectEvent(katanori::RobotEvent::SPEECH_DONE);
        return;
    }
    if (strstr(json, "\"turnComplete\"") != nullptr) {
        turnComplete = true;
    }

    // GeminiのVADをそのまま顔に反映する。ボタンを押さなくても
    // 喋り始め・喋り終わりで表情が変わる。
    if (strstr(json, "\"speechState\":\"SPEECH\"") != nullptr) {
        if (!speaking) {
            driveTo(katanori::RobotState::LISTEN);
        }
    } else if (strstr(json, "\"speechState\":\"NON_SPEECH\"") != nullptr) {
        if (!speaking && robot.state() == katanori::RobotState::LISTEN) {
            robot.injectEvent(katanori::RobotEvent::SPEECH_END); // -> THINK
        }
    }
}

/** ウェイクワード相当。接続してから録音を始める。 */
static void startTurn() {
    if (vadMeasuringActive()) {
        Serial.println("[TURN] VAD計測中です。'vad' で終了してから話しかけてください");
        return;
    }
    if (!katanori::netLink.wifiConnected()) {
        // 自動接続が動いている。ここで諦めさせず、繋がったらもう一度押せばよい。
        Serial.println("[TURN] Wi-Fi未接続です（自動で接続を試みています）");
        return;
    }

    // まだサーバーに繋がっていなければ、ここから張って繋がり次第録音を始める。
    // 待つのは setupComplete まで。WebSocketが繋がっただけで音声を送ると
    // Gemini側のsetupが終わっておらず、最初のひと言が捨てられる。
    if (!katanori::netLink.wsReady()) {
        if (!pendingTurn) {
            pendingTurn = true;
            pendingTurnMs = millis();
            Serial.println("[TURN] サーバーへ接続します。繋がり次第録音を始めます");
        }
        if (!katanori::netLink.wsConnected()) {
            katanori::netLink.wsConnect();
        }
        return;
    }

    pendingTurn = false;
    streamEndMs = 0;
    katanori::audioIo.startRecording();
    robot.injectEvent(katanori::RobotEvent::WAKE_WORD);
    Serial.println("[TURN] 会話開始（発話の区切りは自動判定。もう一度ボタンで会話終了）");
}

/** 発話終了。audioStreamEnd を送ると Gemini が応答生成を始める。 */
static void endTurn() {
    if (!katanori::audioIo.isRecording()) {
        return;
    }
    katanori::audioIo.stopRecording();
    robot.injectEvent(katanori::RobotEvent::SPEECH_END);

    // clientContent+turnComplete はVADが発話中と認識していると無視されて
    // ハングする。audioStreamEnd を使うこと（wrapper.py で確定済みの知見）
    if (katanori::netLink.sendControl("{\"realtimeInput\":{\"audioStreamEnd\":true}}")) {
        streamEndMs = millis();
        Serial.println("[TURN] audioStreamEnd 送信（応答待ち）");
    }
}

/**
 * 会話しているか。ボタンの「開始/終了」の分岐に使う。
 *
 * 録音中だけでなく、応答の受信中・再生中・接続待ちも「会話中」。
 * どの瞬間に押されても「終了」に倒れるようにする。
 */
static bool conversationActive() {
    return pendingTurn || speaking ||
           katanori::audioIo.isRecording() ||
           katanori::audioIo.isPlaying();
}

/**
 * 会話全体を終了する。録音・再生を止め、サーバーとの接続も畳む。
 *
 * DOは接続と同時にGeminiセッションを張る（＝繋ぎっぱなしは課金される）ので、
 * 会話をやめたら接続ごと切るのが正しい。次の会話は startTurn() が張り直す。
 */
static void endConversation() {
    pendingTurn = false;
    katanori::audioIo.stopRecording();
    katanori::audioIo.stopPlayback();   // 喋りかけでも即座に黙る
    speaking = false;
    turnComplete = false;
    streamEndMs = 0;
    katanori::netLink.wsDisconnect();
    driveTo(katanori::RobotState::IDLE);
    Serial.println("[TURN] 会話を終了しました");
}

/**
 * ファームに焼いた音声を鳴らす。
 *
 * 出力の開け閉めは pumpOutputGate() に任せる（ここでミュートを触らない）。
 */
static void announce(const int16_t* pcm, size_t samples, const char* what) {
    if (speaking) {
        // Geminiの応答再生中。割り込んで喋ると会話を壊すので見送る。
        return;
    }
    Serial.printf("[VOICE] %s\n", what);

    // 先にキューへ積む。出力を開けるのはこの後 pumpOutputGate() が行う。
    // 「開けてから積む」順にすると、音が出ていない状態で開いた時間ができる。
    katanori::audioIo.play(pcm, samples);
    pumpOutputGate();
}

/** Wi-Fiが繋がった。初回なら起動アナウンスを鳴らす。 */
static void noteWifiUp() {
    wifiFailures = 0;
    wifiEverConnected = true;
    if (!bootAnnounced) {
        bootAnnounced = true;
        // ここが「使える状態になった」の合図。シリアルを持たない相手には
        // これが唯一の手がかりになる。
        announce(katanori::clips::BOOT_READY,
                 katanori::clips::BOOT_READY_SAMPLES,
                 "カタノリ、起動しました！");
    }
}

/** Wi-Fi設定モードへ入る。入ったことを声でも伝える。 */
static bool enterProvisioning() {
    if (!katanori::provisioning.begin()) {
        return false;
    }
    // 設定モードの画面が読めない/見えない相手にも状況を伝える
    announce(katanori::clips::PROV_NEEDED,
             katanori::clips::PROV_NEEDED_SAMPLES,
             "ワイファイの設定をしてください");
    return true;
}

/**
 * 画面に今すぐ反映する。この後で main loop が数秒止まる処理の前に呼ぶ。
 *
 * 帯を書き換えただけでは、次の描画まで画面は前のままになる。接続やスキャンで
 * 数秒止まる直前に呼んでおかないと、状況が出るのが常に一手遅れる。
 */
static void showNow() {
    if (static_cast<int32_t>(millis() - selfTestUntilMs) < 0) {
        return; // 自己診断パターンの表示中は上書きしない
    }
    robot.tick();
}

/**
 * 表示を順に出す（シリアル `bn`）。
 *
 * 実際に使う文言をそのまま出す。テスト用の別文字列にすると、本番の文言が
 * 読めるか・幅に収まっているかを確かめたことにならない。
 */
struct NetMessage { const char* l1; const char* l2; };
static const NetMessage NET_MESSAGES[] = {
    { "WiFiに",   "つないでいます" },
    { "WiFiが",   "みつかりません" },
    { "WiFiに",   "つながりません" },
    { "WiFiを",   "せっていして"   },
};
static constexpr uint32_t BANNER_DEMO_EACH_MS = 3000;
static uint8_t bannerDemoIndex = 0;
static uint32_t bannerDemoNextMs = 0;

static void bannerDemoStart() {
    bannerDemo = true;
    bannerDemoIndex = 0;
    bannerDemoNextMs = millis(); // 次の loop で1つ目を出す
    Serial.printf("[UI] 接続状況の表示を%u種類、%u秒ずつ画面に出します\n",
                  (unsigned)(sizeof(NET_MESSAGES) / sizeof(NET_MESSAGES[0])),
                  (unsigned)(BANNER_DEMO_EACH_MS / 1000));
}

/** 表示デモの進行。main loop から毎回呼ぶ。 */
static void pumpBannerDemo() {
    if (!bannerDemo || (int32_t)(millis() - bannerDemoNextMs) < 0) {
        return;
    }
    constexpr uint8_t count = sizeof(NET_MESSAGES) / sizeof(NET_MESSAGES[0]);
    if (bannerDemoIndex >= count) {
        bannerDemo = false;
        setNetMessage("");
        Serial.println("[UI] 表示を終わります（顔に戻ります）");
        return;
    }
    const NetMessage& m = NET_MESSAGES[bannerDemoIndex++];
    Serial.printf("[UI] %s%s\n", m.l1, m.l2);
    setNetMessage(m.l1, m.l2);
    bannerDemoNextMs = millis() + BANNER_DEMO_EACH_MS;
}

/**
 * Wi-Fiの接続待ちのあいだに呼ばれる。顔を動かし続けるためのもの。
 *
 * これが無いと wifiConnect() の十数秒のあいだ main loop ごと止まり、
 * 顔が固まる。利用者からは故障と区別がつかない。
 */
static void wifiWaitTick() {
    static uint32_t lastMs = 0;
    uint32_t now = millis();
    if ((now - lastMs) < FRAME_INTERVAL_MS) {
        return;
    }
    lastMs = now;
    showNow();
}

/**
 * Wi-Fiへ自動で繋ぐ。main loop から毎回呼ぶ。
 *
 * 電源の入れ方によっては、ロボットのほうがルーターより先に起きる。一度失敗した
 * ら諦めるのではなく、間隔を広げながら試し続ける。
 *
 * ただし「待てば繋がる」ものと「待っても繋がらない」ものは分ける。
 * 保存済みSSIDが電波に出ていない（引っ越し・ルーター交換）、パスワードが違う、
 * この2つは何度試しても結果が変わらないので、待たせずに設定モードへ渡す。
 */
static void pumpAutoConnect() {
    if (katanori::provisioning.active() || !katanori::netLink.hasCredentials()) {
        return;
    }
    if (katanori::netLink.wifiConnected()) {
        if (!bannerDemo) {
            setNetMessage("");
        }
        noteWifiUp();
        return;
    }
    if (nextWifiTryMs != 0 && (int32_t)(millis() - nextWifiTryMs) < 0) {
        // 待っている間も黙らない。顔だけが動いていると「正常」に見えてしまう。
        setNetMessage(ssidMissing ? "WiFiが" : "WiFiに",
                      ssidMissing ? "みつかりません" : "つながりません");
        return;
    }

    // --- 1. 繋ぐ ---
    Serial.printf("[NET] 自動接続を試みます（%u回目）\n", (unsigned)wifiFailures + 1);
    setNetMessage(ssidMissing ? "WiFiを" : "WiFiに",
                  ssidMissing ? "さがしています" : "つないでいます");
    showNow();
    // 既定の20秒はここでは長い。待っている間は wifiWaitTick が顔を回す。
    // 結論が出た時点で打ち切られるので、駄目なときは実測2.5秒で戻ってくる。
    if (katanori::netLink.wifiConnect(12000, wifiWaitTick)) {
        setNetMessage("");
        noteWifiUp();
        return;
    }

    ++wifiFailures;

    // --- 2. なぜ繋がらなかったのかで分ける ---
    const bool authBad = katanori::netLink.lastFailureWasAuth();
    const bool noAp = katanori::netLink.lastFailureWasNoAp();
    ssidMissing = noAp;
    setNetMessage(noAp ? "WiFiが" : "WiFiに",
                  noAp ? "みつかりません" : "つながりません");

    // 一度も繋がっていない機体だけを設定モードへ落とす。一度繋がった後の切断は
    // ルーターの再起動や電波状況なので、勝手に設定モードへ入れない
    // （会話の途中で設定画面になるほうが利用者には理不尽）。
    if (!wifiEverConnected &&
        (authBad || wifiFailures >= WIFI_FAILURES_TO_PROVISIONING)) {
        // 保存された設定では繋がらない。利用者が自分で直せるよう設定モードへ。
        Serial.println(authBad ? "[NET] パスワードが違うようです。Wi-Fi設定モードへ移ります"
                       : noAp  ? "[NET] 設定されたWi-Fiが見当たりません。"
                                 "場所か機器が変わったとみて設定モードへ移ります"
                               : "[NET] 保存された設定では繋がりませんでした。"
                                 "Wi-Fi設定モードへ移ります");
        wifiFailures = 0;
        ssidMissing = false;
        nextWifiTryMs = 0;
        setNetMessage("");
        if (!enterProvisioning()) {
            setNetMessage("WiFiを", "せっていして");
        }
        return;
    }

    // 5秒, 10秒, 15秒... と広げる。上限30秒。
    // ただしSSIDが見当たらないだけなら、失敗そのものが速い（約2.5秒）ので
    // 間隔も詰める。ルーターの起動待ちなら、そのぶん早く繋がる。
    uint32_t waitMs = noAp ? NO_AP_RETRY_MS : 5000u * wifiFailures;
    if (waitMs > 30000u) {
        waitMs = 30000u;
    }
    nextWifiTryMs = millis() + waitMs;
    Serial.printf("[NET] %u秒後にもう一度試します\n", (unsigned)(waitMs / 1000));
}

/** ボタンを押したがサーバー未接続だった場合の続き。繋がり次第録音を始める。 */
static void pumpPendingTurn() {
    if (!pendingTurn) {
        return;
    }
    if (katanori::netLink.wsReady()) {
        pendingTurn = false;
        startTurn();
        return;
    }
    if (millis() - pendingTurnMs > PENDING_TURN_TIMEOUT_MS) {
        pendingTurn = false;
        Serial.println("[TURN] サーバーへ接続できませんでした。もう一度押してください");
    }
}

/** マイクを読んでDOへ送る。main loop から毎回呼ぶ。 */
static void pumpMic() {
    static int16_t buf[512];

    if (!katanori::audioIo.isRecording()) {
        return;
    }
    size_t n = katanori::audioIo.readMic(buf, sizeof(buf) / sizeof(buf[0]));
    if (n == 0) {
        return;
    }

    // 計測モード中は数えるだけ。送らない。
    if (vadMeasuringActive()) {
        vadFeed(buf, n);
        return;
    }

    // エコーガード: 再生中はマイクを送らない。
    // 送ると自分の声で Gemini が割り込み判定して会話が破綻する。
    // (ReSpeaker Lite のハードウェアAECが効けば不要になるはずの暫定措置)
    if (katanori::audioIo.isPlaying()) {
        return;
    }
    katanori::netLink.sendAudio(buf, n);
}

// ---------------------------------------------------------------------------
// VAD計測モード
//
// ウェイクワードを「クラウドで文字にして照合する」方式にするなら、費用は
// 「1日に何分ぶん送るか」だけで決まる。単価は音声1分あたり $0.00051
// (Cloudflare Workers AI whisper-large-v3-turbo, 2026-07時点) なので、
// 発話が1日1時間なら月140円ほど。費用は問題にならない。
//
// 分からないのは「実際の部屋で何分になるか」。テレビや家族の会話でVADが開けば
// そのぶん増える。ここは推測しても意味がないので実測する。
//
// このモードは音声をどこにも送らない。ローカルで有声区間を数えるだけ。
// ここで作るVADは、方式を採用した場合そのまま送信の判断に使える。
// ---------------------------------------------------------------------------

/** 計測中か。 */
static bool vadMeasuring = false;

static bool vadMeasuringActive() {
    return vadMeasuring;
}

/** 騒音床の測定に使う時間。この間は判定しない。 */
static constexpr uint32_t VAD_CALIBRATE_MS = 2000;
/** 騒音床の何倍を超えたら有声とみなすか。 */
static constexpr float VAD_MARGIN = 3.0f;
/** 静かすぎる部屋で騒音床が0近くになったときの下限。 */
static constexpr float VAD_MIN_THRESHOLD = 60.0f;
/**
 * 装着者ゲートの既定値（騒音床の何倍）。
 *
 * 実測(2026-07-26, 肩乗り・横に家族):
 *   家族の相槌   RMS 1856〜4287 (床の4〜9倍)
 *   装着者の発話 RMS 7242・22033 (床の15〜47倍)
 * 倍以上の差がある。口がマイクに近いぶんだけ大きく入るため。
 * この差で「装着者が喋ったか」を切り分ける。長さでは切り分けられない
 * （装着者の5秒の発話と家族の短い相槌が、長さでは逆に出る）。
 */
static constexpr float VAD_GATE_MARGIN = 13.0f;

/** これだけ続けて超えたら発話開始とみなす（単発の物音を弾く）。 */
static constexpr uint32_t VAD_ATTACK_MS = 96;
/** これだけ続けて下回ったら発話終了とみなす（語間の息継ぎで切らない）。 */
static constexpr uint32_t VAD_RELEASE_MS = 500;

/**
 * 1区間の上限。これを超えたら打ち切る。
 *
 * 騒音床を1回しか測らない作りだと、部屋が少し騒がしくなった時点で「声が
 * 続いている」と判断したまま永久に閉じなくなる（実測で2分間無反応になった）。
 * 呼びかけでも会話でも10秒は超えないので、超えたら打ち切って床を測り直す。
 */
static constexpr uint32_t VAD_MAX_SEGMENT_MS = 10000;

/**
 * 騒音床の追従の速さ（静かなフレーム1つあたり）。
 *
 * 部屋の静けさは時間で変わる。ReSpeaker側の自動音量調整でも絶対値が動く
 * （実測で床が38〜469まで12倍動いた）。1回測って固定にはできない。
 */
static constexpr float VAD_FLOOR_ADAPT = 0.02f;
/** 報告の間隔。 */
static constexpr uint32_t VAD_REPORT_MS = 60000;

/** 音声1分あたりの単価(USD)。上記コメントの出典と揃えること。 */
static constexpr float STT_USD_PER_MIN = 0.00051f;
/** 月額の目安を円で出すための為替。厳密さは不要（桁を知りたいだけ）。 */
static constexpr float USD_JPY = 150.0f;

static uint32_t vadStartMs = 0;
static uint32_t vadLastReportMs = 0;
static float vadNoiseFloor = 0.0f;
static uint32_t vadCalibratedMs = 0;
static uint32_t vadCalibrateFrames = 0;
static bool vadInSpeech = false;
static uint32_t vadAboveMs = 0;
static uint32_t vadBelowMs = 0;
/*
 * 区間ごとのピーク音量。
 *
 * 肩乗りなので、装着者の声は口の近くから入り、周囲の音より大きく入る。
 * 「呼びかけかどうか」を音量と長さで切り分けられるかを見るために、
 * 区間ごとの実測値を出す。しきい値はこの数字を見てから決める。
 */
static float vadSegPeakRms = 0.0f;

/**
 * 装着者ゲート。この音量を超えた区間だけ「装着者が喋った」とみなす。
 *
 * 0 なら騒音床 × VAD_GATE_MARGIN を使う。`vadth <値>` で直接指定、
 * `vadme` で自分の声を測って自動設定する。
 */
static float vadGateRms = 0.0f;

/** ゲートを通った区間の数と時間（これが実際にクラウドへ送る量になる）。 */
static uint32_t vadGatedSegments = 0;
static uint32_t vadGatedMs = 0;

/*
 * 正解ラベル。
 *
 * しきい値を決めるには「どの区間が装着者の声だったか」が要る。ログの数字だけ
 * では判断できず、勘で動かすことになる（実測で 1260〜1674 の帯がどちらとも
 * つかず行き詰まった）。
 *
 * 計測中はボタンを「今喋っているのは自分」の目印として使う。押しながら喋れば
 * その区間は自分、押さなければ周囲として集計し、境界を機体に計算させる。
 */
static bool vadLabelSelf = false;
/**
 * シリアルから切り替えたラベル。
 *
 * XIAOのBOOTボタンは基板上の小さなスイッチで、押しながら喋るのは現実的でない。
 * モニタを開いているなら `me` と打って切り替えるほうが楽なので両方使えるようにする。
 */
static bool vadLabelSelfLatched = false;
/** 今の区間中に一度でも「自分」とされたか。 */
static bool vadSegLabeled = false;
static uint32_t vadSelfCount = 0;
static uint32_t vadOtherCount = 0;
/** 自分の声の最小と、周囲の最大。この2つの間が、しきい値の置ける範囲。 */
static float vadSelfMinRms = 0.0f;
static float vadOtherMaxRms = 0.0f;

/** 区間中の最小音量。打ち切ったときに騒音床を測り直すのに使う。 */
static float vadSegMinRms = 0.0f;

/*
 * 低域比（近接効果）。
 *
 * 口がマイクに近いほど低い周波数が持ち上がる。これは距離で決まる物理現象なので、
 * 遠くの人が大声を出しても真似できない。音量だけでは「近くの小声」と「遠くの
 * 大声」が同じに見えるが、低域比なら分けられる可能性がある。
 *
 * マイク2本の方向検知が使えれば一番良かったが、この機体では取り出せない
 * （DOAは4マイクの上位機の機能で、I2Sから来るのは処理済みの音声）。
 * 1本のマイクで距離の手がかりを得る代わりの手段。
 *
 * XMOS側のノイズ抑制が低域を削っている可能性があるので、効くかどうかは実測で判断する。
 */
static constexpr float VAD_LPF_ALPHA = 0.111f; // 一次ローパス ≒ 300Hz @16kHz
static float vadLpfState = 0.0f;
static double vadSegLowEnergy = 0.0;
static double vadSegTotalEnergy = 0.0;
/** 直近の区間の低域比（0〜1）。1に近いほど低音寄り＝近い。 */
static float vadSegLowRatio = 0.0f;
/** ラベルごとの低域比の合計と数（平均を出すため）。 */
static double vadSelfLowSum = 0.0;
static double vadOtherLowSum = 0.0;
/** 最後に音量を表示した時刻。無反応のとき原因を見えるようにするため。 */
static uint32_t vadLastLevelMs = 0;
/** 音量の表示間隔。 */
static constexpr uint32_t VAD_LEVEL_MS = 5000;

/** 自分の声を測っている最中か（`vadme`）。 */
static bool vadEnrolling = false;
static uint32_t vadEnrollStartMs = 0;
static float vadEnrollPeak = 0.0f;
/** 測った自分の声のピークに対して、この割合をゲートにする。 */
static constexpr float VAD_ENROLL_FACTOR = 0.35f;
/** 自分の声を測る時間。 */
static constexpr uint32_t VAD_ENROLL_MS = 4000;

/** 現在有効なゲート音量。 */
static float vadGate() {
    if (vadGateRms > 0.0f) {
        return vadGateRms;
    }
    const float g = vadNoiseFloor * VAD_GATE_MARGIN;
    return g > VAD_MIN_THRESHOLD ? g : VAD_MIN_THRESHOLD;
}
// 直近の報告区間ぶん
static uint32_t vadSegments = 0;
static uint32_t vadVoicedMs = 0;
// 計測開始からの累計
static uint32_t vadSegmentsTotal = 0;
static uint32_t vadVoicedMsTotal = 0;
static uint32_t vadLongestMs = 0;
static uint32_t vadCurrentMs = 0;

static void vadReport(bool final) {
    const uint32_t elapsed = millis() - vadStartMs;
    if (elapsed == 0) {
        return;
    }
    // 費用はゲートを通った分だけで決まる（送るのはそれだけなので）
    const float ratio = (float)vadGatedMs / (float)elapsed;
    // この割合で1日中身に着けていたら、という換算
    const float minPerMonth = ratio * 60.0f * 24.0f * 30.0f;
    const float yen = minPerMonth * STT_USD_PER_MIN * USD_JPY;

    Serial.printf(
        "[VAD] %s %.1f分 | 検出 %u回/%.1f秒 → ゲート通過 %u回/%.1f秒 (%.1f%%) | "
        "騒音床RMS=%.0f ゲート=%.0f | 送るぶんの月額目安 約%.0f円\n",
        final ? "計測終了" : "報告",
        elapsed / 60000.0f,
        (unsigned)vadSegmentsTotal, vadVoicedMsTotal / 1000.0f,
        (unsigned)vadGatedSegments, vadGatedMs / 1000.0f, ratio * 100.0f,
        vadNoiseFloor, vadGate(),
        yen);

    // 正解を付けた区間があれば、しきい値の置ける範囲を出す
    if (vadSelfCount == 0 && vadOtherCount == 0) {
        return;
    }

    Serial.printf("[VAD] 正解ラベル 自分%u回(最小RMS=%.0f) / 周囲%u回(最大RMS=%.0f)  → ",
                  (unsigned)vadSelfCount, vadSelfMinRms,
                  (unsigned)vadOtherCount, vadOtherMaxRms);
    if (vadSelfCount == 0) {
        Serial.println("自分の声が未記録。'me' で【自分】にしてから喋ってください");
        return;
    }
    if (vadOtherCount == 0) {
        Serial.printf("周囲が未記録。暫定ゲート %.0f\n", vadSelfMinRms * 0.7f);
        return;
    }

    if (vadSelfMinRms > vadOtherMaxRms) {
        // 綺麗に分かれている。真ん中に置けば両方満たせる
        Serial.printf("音量で分離できています。推奨ゲート %.0f\n",
                      (vadSelfMinRms + vadOtherMaxRms) / 2.0f);
    } else {
        // 重なっている。音量だけではどちらかを取りこぼす
        Serial.printf("重なっています(%.0f〜%.0f)。音量だけでは分けられません\n",
                      vadSelfMinRms, vadOtherMaxRms);
    }

    // 低域比（近さの手がかり）が音量の代わりになるかを見る
    const float selfLow = (float)(vadSelfLowSum / vadSelfCount);
    const float otherLow = (float)(vadOtherLowSum / vadOtherCount);
    Serial.printf("[VAD] 低域比の平均 自分=%.2f / 周囲=%.2f  → %s\n",
                  selfLow, otherLow,
                  selfLow > otherLow * 1.15f
                      ? "近接効果が出ています。距離の手がかりとして使えます"
                      : "差がありません。低域比は使えません");

    vadSegments = 0;
    vadVoicedMs = 0;
}

/**
 * 区間を1つ閉じて集計・表示する。
 *
 * @param forced 上限に達して打ち切った場合。声ではなく騒音の可能性が高い。
 */
static void vadCloseSegment(bool forced) {
    vadInSpeech = false;

    // 語尾判定に使った無音は長さから戻す（実際に声が出ていた分だけ見る）
    const uint32_t voicedMs =
        vadCurrentMs > VAD_RELEASE_MS ? vadCurrentMs - VAD_RELEASE_MS : vadCurrentMs;
    vadVoicedMs += vadCurrentMs;
    vadVoicedMsTotal += vadCurrentMs;
    if (vadCurrentMs > vadLongestMs) {
        vadLongestMs = vadCurrentMs;
    }

    /*
     * 判定は音量だけで行う。長さでは切り分けられない（実測で、装着者の5秒の
     * 発話と家族の0.2秒の相槌が、長さでは逆の判定になった）。
     *
     * 見るのは絶対値ではなく騒音床との倍率。ReSpeaker側の自動音量調整で
     * 絶対値は動くが、倍率は安定している（実測で床が38〜469まで動いても
     * 自分15〜58倍 / 周囲4〜10倍 の帯は変わらなかった）。
     */
    const float ratio = vadNoiseFloor > 1.0f ? vadSegPeakRms / vadNoiseFloor : 0.0f;
    vadSegLowRatio = vadSegTotalEnergy > 0.0
                         ? (float)sqrt(vadSegLowEnergy / vadSegTotalEnergy)
                         : 0.0f;
    const bool passed = !forced && vadSegPeakRms >= vadGate();
    if (passed) {
        ++vadGatedSegments;
        vadGatedMs += vadCurrentMs;
    }
    // 正解が付いていれば、しきい値決めの材料として集計する（打ち切りは除く）
    if (!forced) {
        if (vadSegLabeled) {
            ++vadSelfCount;
            vadSelfLowSum += vadSegLowRatio;
            if (vadSelfMinRms == 0.0f || vadSegPeakRms < vadSelfMinRms) {
                vadSelfMinRms = vadSegPeakRms;
            }
        } else {
            ++vadOtherCount;
            vadOtherLowSum += vadSegLowRatio;
            if (vadSegPeakRms > vadOtherMaxRms) {
                vadOtherMaxRms = vadSegPeakRms;
            }
        }
    }

    Serial.printf("[VAD] 区間 %.2f秒  音量RMS=%.0f (床の%.1f倍)  低域比=%.2f  [%s]  → %s\n",
                  voicedMs / 1000.0f, vadSegPeakRms, ratio, vadSegLowRatio,
                  forced ? "打ち切り" : (vadSegLabeled ? "自分" : "周囲"),
                  forced ? "対象外" : (passed ? "送る" : "送らない"));

    vadCurrentMs = 0;
    vadBelowMs = 0;
    vadAboveMs = 0;
    vadSegPeakRms = 0.0f;
    vadSegMinRms = 0.0f;
    vadSegLabeled = false;
}

/** マイクの1フレームを食わせる。送信はしない。 */
static void vadFeed(const int16_t* pcm, size_t n) {
    if (n == 0) {
        return;
    }
    double acc = 0;
    double lowAcc = 0;
    for (size_t i = 0; i < n; ++i) {
        const float x = (float)pcm[i];
        acc += (double)x * (double)x;
        // 一次ローパスを通した成分＝低域のエネルギー
        vadLpfState += VAD_LPF_ALPHA * (x - vadLpfState);
        lowAcc += (double)vadLpfState * (double)vadLpfState;
    }
    const float rms = sqrt(acc / (double)n);
    const uint32_t frameMs = (uint32_t)((n * 1000) / KATANORI_AUDIO_RATE);

    // 自分の声を測っている最中（`vadme`）。ピークだけ拾ってゲートを決める。
    if (vadEnrolling) {
        if (rms > vadEnrollPeak) {
            vadEnrollPeak = rms;
        }
        if (millis() - vadEnrollStartMs >= VAD_ENROLL_MS) {
            vadEnrolling = false;
            vadGateRms = vadEnrollPeak * VAD_ENROLL_FACTOR;
            Serial.printf("[VAD] 自分の声のピーク RMS=%.0f → ゲートを %.0f にしました"
                          "（%.0f%%）\n",
                          vadEnrollPeak, vadGateRms, VAD_ENROLL_FACTOR * 100.0f);
            Serial.println("[VAD] このまま計測を続けます。家族に喋ってもらって"
                           "「送らない」と出るか確かめてください");
        }
        return;
    }

    // 最初の2秒は「この部屋の静けさ」を測るのに使う。固定しきい値では
    // 部屋ごとの騒音差を吸収できない。
    if (vadCalibratedMs < VAD_CALIBRATE_MS) {
        vadCalibratedMs += frameMs;
        vadNoiseFloor = (vadNoiseFloor * vadCalibrateFrames + rms) / (vadCalibrateFrames + 1);
        ++vadCalibrateFrames;
        if (vadCalibratedMs >= VAD_CALIBRATE_MS) {
            Serial.printf("[VAD] 騒音床 RMS=%.0f → しきい値 %.0f で計測を始めます\n",
                          vadNoiseFloor,
                          vadNoiseFloor * VAD_MARGIN > VAD_MIN_THRESHOLD
                              ? vadNoiseFloor * VAD_MARGIN : VAD_MIN_THRESHOLD);
            vadStartMs = millis();
            vadLastReportMs = vadStartMs;
        }
        return;
    }

    const float threshold = vadNoiseFloor * VAD_MARGIN > VAD_MIN_THRESHOLD
                                ? vadNoiseFloor * VAD_MARGIN : VAD_MIN_THRESHOLD;

    if (rms >= threshold) {
        vadBelowMs = 0;
        vadAboveMs += frameMs;
        if (!vadInSpeech && vadAboveMs >= VAD_ATTACK_MS) {
            vadInSpeech = true;
            vadCurrentMs = vadAboveMs; // 立ち上がりぶんも有声に数える
            vadSegPeakRms = rms;
            vadSegMinRms = rms;
            vadSegLowEnergy = lowAcc;
            vadSegTotalEnergy = acc;
            vadSegLabeled = vadLabelSelf || vadLabelSelfLatched;
            ++vadSegments;
            ++vadSegmentsTotal;
        } else if (vadInSpeech) {
            vadCurrentMs += frameMs;
            if (rms > vadSegPeakRms) {
                vadSegPeakRms = rms;
            }
            if (rms < vadSegMinRms) {
                vadSegMinRms = rms;
            }
            vadSegLowEnergy += lowAcc;
            vadSegTotalEnergy += acc;
            // 押し始めが少し遅れても拾えるように、区間中に一度でも押されたら自分
            if (vadLabelSelf || vadLabelSelfLatched) {
                vadSegLabeled = true;
            }
        }

        // 閉じないまま延々と続くのは、部屋が騒がしくなって床が古くなった証拠。
        // 打ち切って、この区間で一番静かだったところを新しい床として測り直す。
        if (vadInSpeech && vadCurrentMs >= VAD_MAX_SEGMENT_MS) {
            vadCloseSegment(true);
            const float before = vadNoiseFloor;
            vadNoiseFloor = vadSegMinRms > 1.0f ? vadSegMinRms : vadNoiseFloor;
            Serial.printf("[VAD] 音が途切れないため打ち切りました。騒音床を %.0f → %.0f に測り直します\n",
                          before, vadNoiseFloor);
        }
    } else {
        vadAboveMs = 0;
        if (vadInSpeech) {
            vadBelowMs += frameMs;
            vadCurrentMs += frameMs; // 息継ぎぶんも送ることになるので数に入れる
            if (rms < vadSegMinRms) {
                vadSegMinRms = rms;
            }
            if (vadBelowMs >= VAD_RELEASE_MS) {
                vadCloseSegment(false);
            }
        } else {
            // 静かなあいだは床を少しずつ追従させる。1回測って固定にすると、
            // 部屋が騒がしくなった時点で永久に「発話中」になる。
            vadNoiseFloor = vadNoiseFloor * (1.0f - VAD_FLOOR_ADAPT) + rms * VAD_FLOOR_ADAPT;
        }
    }

    // 無反応のときに何が起きているか分かるよう、5秒ごとに今の音量を出す
    if (millis() - vadLastLevelMs >= VAD_LEVEL_MS) {
        vadLastLevelMs = millis();
        Serial.printf("[VAD] 音量RMS=%.0f  床=%.0f  検出=%.0f  ゲート=%.0f  %s\n",
                      rms, vadNoiseFloor, threshold, vadGate(),
                      vadInSpeech ? "発話中" : "静か");
    }

    if (vadCalibratedMs >= VAD_CALIBRATE_MS && millis() - vadLastReportMs >= VAD_REPORT_MS) {
        vadLastReportMs = millis();
        vadReport(false);
    }
}

/** 計測モードの開始・停止。 */
static void vadToggle() {
    if (vadMeasuring) {
        vadMeasuring = false;
        katanori::audioIo.stopRecording();
        vadReport(true);
        Serial.println("[VAD] 計測を終了しました");
        return;
    }

    if (katanori::audioIo.isRecording()) {
        Serial.println("[VAD] 会話中は計測できません");
        return;
    }

    vadMeasuring = true;
    vadNoiseFloor = 0.0f;
    vadCalibratedMs = 0;
    vadCalibrateFrames = 0;
    vadInSpeech = false;
    vadAboveMs = vadBelowMs = vadCurrentMs = 0;
    vadSegments = vadVoicedMs = 0;
    vadSegmentsTotal = vadVoicedMsTotal = vadLongestMs = 0;
    vadGatedSegments = vadGatedMs = 0;
    vadSegPeakRms = 0.0f;
    vadEnrolling = false;
    vadLabelSelf = vadLabelSelfLatched = vadSegLabeled = false;
    vadSelfCount = vadOtherCount = 0;
    vadSelfMinRms = vadOtherMaxRms = vadSegMinRms = 0.0f;
    vadLpfState = 0.0f;
    vadSegLowEnergy = vadSegTotalEnergy = 0.0;
    vadSegLowRatio = 0.0f;
    vadSelfLowSum = vadOtherLowSum = 0.0;
    vadLastLevelMs = millis();
    vadStartMs = vadLastReportMs = millis();
    katanori::audioIo.startRecording();

    Serial.println("[VAD] 計測を始めます。音声はどこにも送りません");
    Serial.println("[VAD] 最初の2秒は静かにしてください（騒音床の測定）");
    Serial.printf("[VAD] %u秒ごとに報告します。'vad' でもう一度打つと終了\n",
                  (unsigned)(VAD_REPORT_MS / 1000));
    Serial.println("[VAD] ★ 'me' と打つと【自分】、もう一度打つと【周囲】に切り替わります");
    Serial.println("[VAD]   （BOOTボタンを押しながら喋る方法でも同じです）");
    Serial.println("[VAD]   どれが自分の声だったかを記録して、しきい値を計算します");
    Serial.println("[VAD] ゲートの決め方: 'vadme' で自分の声から自動設定 / "
                   "'vadth <RMS>' で直接指定");
}

/** ゲート音量を直接指定する。0なら騒音床からの自動計算に戻す。 */
static void vadSetThreshold(float rms) {
    vadGateRms = rms < 0.0f ? 0.0f : rms;
    if (vadGateRms == 0.0f) {
        Serial.printf("[VAD] ゲートを自動（騒音床の%.0f倍 = %.0f）に戻しました\n",
                      VAD_GATE_MARGIN, vadGate());
    } else {
        Serial.printf("[VAD] ゲートを %.0f にしました\n", vadGateRms);
    }
}

/**
 * 自分の声を測ってゲートを決める。
 *
 * 固定値では体格・装着位置・声の大きさの差を吸収できない。装着した本人が
 * 普通の声で数秒喋れば、そのピークからゲートを決められる。呼び名を覚えさせる
 * のではなく「自分の声の大きさ」を覚えさせる、という考え方。
 */
static void vadEnroll() {
    if (!vadMeasuring) {
        Serial.println("[VAD] 先に 'vad' で計測を始めてください");
        return;
    }
    vadEnrolling = true;
    vadEnrollStartMs = millis();
    vadEnrollPeak = 0.0f;
    Serial.printf("[VAD] %u秒間、普通の声で喋ってください（例:「ねーねー、聞こえる？」）\n",
                  (unsigned)(VAD_ENROLL_MS / 1000));
}

/** ターンの終了判定。Geminiが喋り終え、再生キューも空になったら IDLE へ。 */
static void pumpTurnState() {
    if (speaking && turnComplete && !katanori::audioIo.isPlaying()) {
        speaking = false;
        turnComplete = false;
        // 出力を閉じるのは pumpOutputGate()（キューが空になった時点で閉じる）
        driveTo(katanori::RobotState::IDLE);
        Serial.println("[TURN] 応答の再生が完了しました（続けて話せます。ボタンで会話終了）");
    }
}

// ---------------------------------------------------------------------------
// ヘルパー
// ---------------------------------------------------------------------------

static const char* stateName(katanori::RobotState s) {
    switch (s) {
    case katanori::RobotState::IDLE:   return "IDLE";
    case katanori::RobotState::LISTEN: return "LISTEN";
    case katanori::RobotState::THINK:  return "THINK";
    case katanori::RobotState::SPEAK:  return "SPEAK";
    }
    return "?";
}

/**
 * I2Cデバイスの素性を調べる。読み出しのみで書き込みはしない。
 *
 * 0x18 は音声コーデック(TLV320AIC3104等)の定番アドレスだが、
 * 加速度センサー LIS3DH / LIS2DH12 の標準アドレスでもある。
 * WHO_AM_I を読めば区別できる。加速度センサーなら本体の向きで
 * 操作する、といった使い方の余地が生まれる。
 */
static void identifyI2c(uint8_t addr) {
    Serial.printf("[ID] 0x%02X のレジスタを読みます（書き込みはしません）\n", addr);

    // よくある「型番レジスタ」を順に読む
    struct Probe { uint8_t reg; const char* name; };
    static const Probe probes[] = {
        { 0x0F, "WHO_AM_I (LIS3DH=0x33 / LIS2DH12=0x33 / LSM6DS3=0x69)" },
        { 0x00, "reg0x00" },
        { 0x01, "reg0x01" },
        { 0x75, "WHO_AM_I (MPU6050=0x68)" },
    };

    bool any = false;
    for (const auto& p : probes) {
        Wire.beginTransmission(addr);
        Wire.write(p.reg);
        if (Wire.endTransmission(false) != 0) {
            continue;
        }
        if (Wire.requestFrom(addr, (uint8_t)1) != 1) {
            continue;
        }
        uint8_t v = Wire.read();
        any = true;
        Serial.printf("[ID]   0x%02X = 0x%02X   %s\n", p.reg, v, p.name);

        if (p.reg == 0x0F && v == 0x33) {
            Serial.println("[ID]   ★ LIS3DH系の加速度センサーです");
        }
    }

    if (!any) {
        Serial.println("[ID]   レジスタ読み出しに応答しません（単純なI2Cスレーブではない）");
    }
}

// ---------------------------------------------------------------------------
// AS5600（磁気角度センサ）の診断。つまみの非接触化で使う（docs/KNOB-ENCODER.md）。
//
// **読み出ししかしない。** AS5600 は ZPOS/MPOS を OTP に焼けるが回数制限があり、
// 焼き直しが効かない。ゼロ点はソフト側のオフセットで持つ方針なので、ここから
// 書き込むことは今後も無い。
//
// 組み付けの良否は「なんとなく動かない」では切り分けられないので、磁石の検出状態を
// 数字で出す。特にこの機体では、電源断用のリードスイッチの磁石が近くに来る
// （docs/POWER.md）ため、**2つ目の磁石が角度を狂わせていないか**をここで見る。
// ---------------------------------------------------------------------------
static const uint8_t kAs5600Addr = 0x36;

/** AS5600 のレジスタを len バイト読む。失敗したら false。 */
static bool as5600Read(uint8_t reg, uint8_t* out, uint8_t len) {
    Wire.beginTransmission(kAs5600Addr);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) {
        return false;
    }
    if (Wire.requestFrom(kAs5600Addr, len) != len) {
        return false;
    }
    for (uint8_t i = 0; i < len; ++i) {
        out[i] = Wire.read();
    }
    return true;
}

/** 上位バイト+下位バイトの12bit値を組む（AS5600の角度・磁力はこの形）。 */
static uint16_t as5600Word(const uint8_t* p) {
    return static_cast<uint16_t>(((p[0] & 0x0F) << 8) | p[1]);
}

/** `mag` コマンド。磁石の状態と角度を1回だけ表示する。 */
static void dumpAs5600() {
    Serial.printf("[MAG] AS5600 (0x%02X) を読みます（書き込みはしません）\n", kAs5600Addr);

    uint8_t status = 0;
    if (!as5600Read(0x0B, &status, 1)) {
        Serial.println("[MAG] !! 応答しません。");
        Serial.println("[MAG]    's' でバスを見て、0x36 が出るか確認してください。");
        Serial.println("[MAG]    出ないなら VCC/GND/SDA/SCL の配線です（3V3線に抵抗を挟まないこと）。");
        return;
    }

    // STATUS(0x0B): bit5=MD(検出) bit4=ML(弱すぎ) bit3=MH(強すぎ)
    bool md = status & 0x20;
    bool ml = status & 0x10;
    bool mh = status & 0x08;
    Serial.printf("[MAG]   STATUS(0x0B) = 0x%02X   MD=%s ML=%s MH=%s\n",
                  status, md ? "検出" : "無し", ml ? "弱すぎ" : "-", mh ? "強すぎ" : "-");
    if (!md) {
        Serial.println("[MAG]   → ★磁石が見えていません。近づけるか、径方向着磁のものか確認を");
    } else if (ml) {
        Serial.println("[MAG]   → ★磁力が足りません。チップ面へ近づける（0.5〜3mmが目安）");
    } else if (mh) {
        Serial.println("[MAG]   → ★磁力が強すぎます。離す");
    } else {
        Serial.println("[MAG]   → 磁石OK");
    }

    // AGC(0x1A): 3V3動作では 0..128。中央付近が理想で、端に寄るほど余裕が無い。
    uint8_t agc = 0;
    if (as5600Read(0x1A, &agc, 1)) {
        Serial.printf("[MAG]   AGC(0x1A)    = %u / 128   （3V3動作。64前後が理想）\n", agc);
        if (agc < 16) {
            Serial.println("[MAG]   → 磁石が近すぎ／強すぎ。少し離す");
        } else if (agc > 112) {
            Serial.println("[MAG]   → 磁石が遠すぎ／弱すぎ。少し近づける");
        } else {
            Serial.println("[MAG]   → 良好");
        }
    }

    uint8_t buf[2] = {0, 0};
    if (as5600Read(0x1B, buf, 2)) {
        Serial.printf("[MAG]   MAGNITUDE    = %u\n", as5600Word(buf));
    }

    // RAW ANGLE(0x0C): 生の角度。ANGLE(0x0E) は ZPOS/MPOS とフィルタを通った後。
    // ゼロ点はソフトで持つ方針なので、実際に使うのは RAW ANGLE のほう。
    if (as5600Read(0x0C, buf, 2)) {
        uint16_t raw = as5600Word(buf);
        Serial.printf("[MAG]   RAW ANGLE    = %4u  (%.1f度)\n", raw, raw * 360.0f / 4096.0f);
    }
    if (as5600Read(0x0E, buf, 2)) {
        uint16_t ang = as5600Word(buf);
        Serial.printf("[MAG]   ANGLE        = %4u  (%.1f度)\n", ang, ang * 360.0f / 4096.0f);
    }
}

/** チップ・メモリ情報。ブート時に取りこぼしても 'i' で再表示できる。 */
static void printBootInfo() {
    Serial.printf("[INFO] chip=%s rev=%d cores=%d cpu=%dMHz\n",
                  ESP.getChipModel(), ESP.getChipRevision(),
                  ESP.getChipCores(), getCpuFrequencyMhz());
    Serial.printf("[INFO] flash=%uKB heap=%uKB psram=%uKB\n",
                  ESP.getFlashChipSize() / 1024,
                  ESP.getHeapSize() / 1024,
                  ESP.getPsramSize() / 1024);
    Serial.printf("[INFO] I2C SDA=GPIO%d SCL=GPIO%d  OLED addr=0x%02X\n",
                  KATANORI_I2C_SDA, KATANORI_I2C_SCL, KATANORI_OLED_ADDR);

    if (ESP.getPsramSize() == 0) {
        // Stage 3 の音声バッファ + TLS で必ず効いてくるのでここで警告しておく
        Serial.println("[INFO] !! PSRAM が見えていません。platformio.ini の");
        Serial.println("[INFO]    board_build.arduino.memory_type = qio_opi を確認してください。");
    }
}

/**
 * I2Cバスを総なめして応答するアドレスを列挙する。
 * 「配線が正しいか」を最初に切り分けるための最重要ログ。
 * ここで 0x3C が出なければソフトの問題ではなく配線か電源の問題。
 */
static bool scanI2c() {
    bool foundOled = false;
    int count = 0;

    Serial.println("[I2C] scanning bus...");
    for (uint8_t addr = 1; addr < 127; ++addr) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0) {
            Serial.printf("[I2C]   device found at 0x%02X\n", addr);
            ++count;
            if (addr == KATANORI_OLED_ADDR) {
                foundOled = true;
            }
        }
    }

    if (count == 0) {
        Serial.println("[I2C] !! no devices found.");
        Serial.println("[I2C]    SDA/SCL/VCC/GND の配線と、OLEDへの給電を確認してください。");
    } else if (!foundOled) {
        Serial.printf("[I2C] !! 0x%02X (OLED) が見つかりません。上の一覧のアドレスを\n",
                      KATANORI_OLED_ADDR);
        Serial.println("[I2C]    KATANORI_OLED_ADDR に指定し直してください (0x3D の個体があります)。");
    }
    return foundOled;
}

/** D番号 -> GPIO番号 (XIAO ESP32S3)。範囲外は -1。 */
static int gpioForD(int d) {
    static const int kMap[] = { 1, 2, 3, 4, 5, 6, 43, 44, 7, 8, 9 }; // D0..D10
    if (d < 0 || d > 10) {
        return -1;
    }
    return kMap[d];
}

/**
 * 簡易電圧計。テスターが無い環境で「そこに電気が来ているか」を判定するために
 * ESP32 の ADC を使う。測りたい点から指定ピンへジャンパーを1本渡して実行する。
 *
 * 【重要】入力は 3.3V まで。5V の点を繋ぐとピンが壊れる。
 */
static void measureVoltage(int d) {
    int gpio = gpioForD(d);
    if (gpio < 0) {
        Serial.println("[MEAS] D0〜D10 で指定してください (例: v0)");
        return;
    }
    if (gpio == 43 || gpio == 44) {
        Serial.printf("[MEAS] D%d(GPIO%d) はADC非対応です。D0〜D5 か D8〜D10 を使ってください。\n",
                      d, gpio);
        return;
    }

    uint32_t mv = analogReadMilliVolts(gpio);
    Serial.printf("[MEAS] D%d(GPIO%d) = %u mV", d, gpio, mv);
    if (mv < 200) {
        Serial.println("  -> 電圧が来ていません（未接続 / 給電なし）");
    } else if (mv > 2800) {
        Serial.println("  -> 3.3V級。給電OK");
    } else {
        Serial.println("  -> 中途半端な電圧。接触不良かプルアップ経由の可能性");
    }

    // I2Cピンを測った場合はバスを張り直す
    if (gpio == KATANORI_I2C_SDA || gpio == KATANORI_I2C_SCL) {
        Wire.end();
        Wire.begin(KATANORI_I2C_SDA, KATANORI_I2C_SCL, 400000);
        Serial.println("[MEAS] I2Cバスを再初期化しました");
    }
}

/**
 * 簡易導通チェッカー。内部プルアップを有効にして読むだけ。
 * GND に落ちていれば LOW、浮いていれば HIGH。
 * 「GNDがちゃんと繋がっているか」はADCでは測れないのでこちらで見る。
 */
static void testGround(int d) {
    int gpio = gpioForD(d);
    if (gpio < 0) {
        Serial.println("[MEAS] D0〜D10 で指定してください (例: g1)");
        return;
    }

    pinMode(gpio, INPUT_PULLUP);
    delay(5);
    bool low = (digitalRead(gpio) == LOW);
    Serial.printf("[MEAS] D%d(GPIO%d) GND導通: %s\n", d, gpio,
                  low ? "あり (LOW)  -> GNDに繋がっています"
                      : "なし (HIGH) -> 浮いています");

    if (gpio == KATANORI_I2C_SDA || gpio == KATANORI_I2C_SCL) {
        Wire.end();
        Wire.begin(KATANORI_I2C_SDA, KATANORI_I2C_SCL, 400000);
        Serial.println("[MEAS] I2Cバスを再初期化しました");
    }
}

/**
 * XIAO ESP32S3 の外部ピン D0..D10 の全組み合わせを I2C として叩き、
 * SSD1306 (0x3C / 0x3D) がぶら下がっているピンペアを探す。
 *
 * 「どのピンに繋いだか分からない / 繋いだつもりのピンと違う」を潰すための最終手段。
 * VCC と GND さえ正しければ、SDA/SCL がどこであっても必ず見つかる。
 * 逆にここで何も出なければ、原因は信号線ではなく給電かモジュール故障に絞られる。
 */
static void sweepI2cPins() {
    struct PinDef { const char* name; int gpio; };
    static const PinDef pins[] = {
        {"D0",  1}, {"D1",  2}, {"D2",  3}, {"D3",  4}, {"D4",  5}, {"D5",  6},
        {"D6", 43}, {"D7", 44}, {"D8",  7}, {"D9",  8}, {"D10", 9},
    };
    const size_t n = sizeof(pins) / sizeof(pins[0]);

    Serial.println("[SWEEP] D0..D10 の全組み合わせで 0x3C / 0x3D を探索します...");
    int hits = 0;

    for (size_t s = 0; s < n; ++s) {
        for (size_t c = 0; c < n; ++c) {
            if (s == c) {
                continue;
            }
            Wire.end();
            if (!Wire.begin(pins[s].gpio, pins[c].gpio, 100000)) {
                continue;
            }
            for (uint8_t addr = 0x3C; addr <= 0x3D; ++addr) {
                Wire.beginTransmission(addr);
                if (Wire.endTransmission() == 0) {
                    Serial.printf("[SWEEP] >>> HIT  SDA=%s(GPIO%d)  SCL=%s(GPIO%d)  addr=0x%02X\n",
                                  pins[s].name, pins[s].gpio,
                                  pins[c].name, pins[c].gpio, addr);
                    ++hits;
                }
            }
        }
    }

    // 元のバス設定へ戻す
    Wire.end();
    Wire.begin(KATANORI_I2C_SDA, KATANORI_I2C_SCL, 400000);

    if (hits == 0) {
        Serial.println("[SWEEP] 見つかりませんでした。信号線ではなく給電側の問題です。");
        Serial.println("[SWEEP]   - OLED の VCC-GND 間の電圧を測ってください (3.3V か 5V が出ているか)");
        Serial.println("[SWEEP]   - ブレッドボードの電源レールに給電されているか");
        Serial.println("[SWEEP]   - モジュール自体の故障");
    } else {
        Serial.printf("[SWEEP] %d件ヒットしました。platformio.ini の build_flags に\n", hits);
        Serial.println("[SWEEP]   -DKATANORI_I2C_SDA=<GPIO番号> -DKATANORI_I2C_SCL=<GPIO番号>");
        Serial.println("[SWEEP] を追加して書き込み直してください。");
    }
}

/**
 * OLEDの自己診断。DisplayBuffer を一切通さず U8g2 の描画関数だけで
 * 枠・塗り・文字を出す。
 *   ここで何か見える  -> 配線とOLED初期化はOK。問題は DisplayBuffer の転送側
 *   ここでも真っ暗    -> 配線 / I2Cアドレス / 給電の問題
 * この二分岐が Stage 1 のデバッグで一番効く。
 * (selfTestUntilMs はファイル先頭で宣言している。描画側からも見るため)
 */
static void runSelfTest() {
    if (KATANORI_I2C_SILENCE) {
        return;
    }
    Serial.println("[TEST] 自己診断パターンを5秒表示します (U8g2直描画)");
    u8g2.clearBuffer();
    u8g2.drawFrame(0, 0, 128, 64);
    u8g2.drawBox(6, 6, 18, 18);
    u8g2.drawLine(0, 63, 127, 0);
    u8g2.setFont(u8g2_font_6x10_tf);
    u8g2.drawStr(34, 26, "KATANORI");
    u8g2.drawStr(34, 40, "SELFTEST");
    u8g2.sendBuffer();
    selfTestUntilMs = millis() + 5000;
}

/**
 * 設定モードで QR画面 / 文字画面 のどちらを出しているか。
 *
 * 時間で自動切り替えしてはいけない。QRの読み取りには数秒かかることがあり、
 * その最中に画面が変わると失敗する。BOOTボタンの短押しで切り替える
 * （設定モード中は短押しに他の役目が無い）。
 */
static bool provShowQr = true;

/**
 * 設定モードの画面。QRと文字を横に並べる。
 *
 *   QR : Version2(25モジュール) を1モジュール2pxで 50x50px、上下7pxの余白。
 *        128x64 の左側に置くと右に78px余るので、切り替えなしで文字を併置できる。
 *   右 : AP名・URL・ステータス。ステータスだけが状況に応じて変わる。
 */
static void renderProvisioning() {
    if (KATANORI_I2C_SILENCE) {
        return;
    }
    static char lastPayload[64] = {0};
    static QRCode qr;
    // qrcode_getBufferSize() は関数なので配列長に使えない。
    // Version3 は 29x29 = 841ビット = 106バイト。余裕を見て固定確保する。
    static uint8_t qrData[160];

    const char* payload = katanori::provisioning.wifiQrPayload();
    if (strcmp(lastPayload, payload) != 0) {
        strncpy(lastPayload, payload, sizeof(lastPayload) - 1);
        // バージョンは自動で上がらないので、収まる最小を明示的に選ぶ
        if (qrcode_initText(&qr, qrData, 2, ECC_LOW, payload) != 0) {
            qrcode_initText(&qr, qrData, 3, ECC_LOW, payload);
        }
    }

    const auto phase = katanori::provisioning.phase();
    const bool showQr = provShowQr;

    u8g2.clearBuffer();

    if (showQr) {
        // --- QR画面: 白地に黒モジュール（SSD1306は点灯=白なので地を点灯させる） ---
        const int scale = 2;
        const int qrPx = qr.size * scale;
        const int quiet = (64 - qrPx) / 2;   // 上下の余白がクワイエットゾーンを兼ねる
        const int block = qrPx + quiet * 2;

        u8g2.setDrawColor(1);
        u8g2.drawBox(0, 0, block, 64);
        u8g2.setDrawColor(0);
        for (uint8_t y = 0; y < qr.size; ++y) {
            for (uint8_t x = 0; x < qr.size; ++x) {
                if (qrcode_getModule(&qr, x, y)) {
                    u8g2.drawBox(quiet + x * scale, quiet + y * scale, scale, scale);
                }
            }
        }

        // 右の60pxに収まる短い語だけを大きめの字で置く
        u8g2.setDrawColor(1);
        const int tx = block + 4;
        u8g2.setFont(u8g2_font_7x13B_tr);
        u8g2.drawStr(tx, 20, "WiFi");
        u8g2.drawStr(tx, 34, "SETUP");
        u8g2.setFont(u8g2_font_6x12_tr);
        switch (phase) {
        case katanori::Provisioning::Phase::WAITING:   u8g2.drawStr(tx, 54, "scan me"); break;
        case katanori::Provisioning::Phase::CONNECTED: u8g2.drawStr(tx, 54, "connected"); break;
        case katanori::Provisioning::Phase::SAVED:     u8g2.drawStr(tx, 54, "saved!"); break;
        }
    } else {
        // --- 文字画面: 全幅を使って読める大きさで出す ---
        // 9x15 なら 128px に14文字。"katanori-setup" がちょうど収まる。
        u8g2.setDrawColor(1);
        u8g2.setFont(u8g2_font_9x15B_tr);
        u8g2.drawStr(0, 14, katanori::provisioning.apSsid());
        u8g2.drawStr(0, 34, katanori::provisioning.apIp().toString().c_str());

        u8g2.setFont(u8g2_font_7x13B_tr);
        switch (phase) {
        case katanori::Provisioning::Phase::WAITING:
            u8g2.drawStr(0, 52, "waiting...");
            break;
        case katanori::Provisioning::Phase::CONNECTED:
            u8g2.drawStr(0, 52, "connected");
            break;
        case katanori::Provisioning::Phase::SAVED:
            u8g2.drawStr(0, 52, "saved! reboot");
            break;
        }
        u8g2.setFont(u8g2_font_6x12_tr);
        u8g2.drawStr(0, 64, "[btn] show QR");
    }

    u8g2.sendBuffer();
}

// ---------------------------------------------------------------------------
// OTA (Wi-Fi経由のファーム更新)
//
// 「筐体に封入したらUSBを挿せない」への備え (docs/TODO.md の優先2位)。
// Wi-Fiが繋がった時点で待受を自動開始し、PC側は
//   pio run -e xiao_esp32s3_ota -t upload
// で書き込む。転送はMD5検証つきで反対側のOTAスロットへ書かれ、検証に通って
// 初めて起動先が切り替わる (途中で切れても現行ファームのまま起動する)。
// ---------------------------------------------------------------------------

static bool otaEnabled = true;  // `otadis` で切れる (更新中の誤爆を避けたい計測時用)
static bool otaBegun = false;   // begin() は Wi-Fi 接続後に一度だけ

/** OTA進捗画面。転送中は ArduinoOTA.handle() の中に居続けるので顔とは競合しない。 */
static void renderOtaProgress(unsigned int pct) {
    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_7x13B_tr);
    u8g2.drawStr(33, 22, "UPDATING");
    u8g2.drawFrame(14, 32, 100, 12);
    if (pct > 100) pct = 100;
    u8g2.drawBox(14, 32, pct, 12);
    char buf[8];
    snprintf(buf, sizeof(buf), "%u%%", pct);
    u8g2.setFont(u8g2_font_6x12_tr);
    u8g2.drawStr(58, 58, buf);
    u8g2.sendBuffer();
}

static void pumpOta() {
    if (!otaEnabled) {
        return;
    }
    if (!otaBegun) {
        if (!katanori::netLink.wifiConnected()) {
            return; // Wi-Fiが繋がるまで待つ (切断→再接続しても待受は生きている)
        }
        ArduinoOTA.setHostname(KATANORI_OTA_HOSTNAME);
        ArduinoOTA.setPassword(KATANORI_OTA_PASSWORD);
        ArduinoOTA.onStart([]() {
            // 転送中はこの loop() に戻ってこない。音と通信は先に畳んでおく
            Serial.println("[OTA] 更新開始。音声と通信を止めます");
            katanori::netLink.wsDisconnect();
            katanori::audioIo.stopRecording();
            katanori::audioIo.setOutputMute(true);
            renderOtaProgress(0);
        });
        ArduinoOTA.onProgress([](unsigned int done, unsigned int total) {
            // OLED全面転送は約29ms。毎回描くと転送を遅くするので5%刻みに間引く
            static unsigned int lastPct = 200;
            unsigned int pct = total ? done * 100u / total : 0;
            if (pct != lastPct && pct % 5 == 0) {
                lastPct = pct;
                renderOtaProgress(pct);
                Serial.printf("[OTA] %u%%\n", pct);
            }
        });
        ArduinoOTA.onEnd([]() {
            Serial.println("[OTA] 書き込み完了。検証OKなら再起動します");
        });
        ArduinoOTA.onError([](ota_error_t error) {
            // 失敗しても現行ファームは無傷 (起動先の切替は検証通過後のため)
            const char* msg = "不明";
            switch (error) {
                case OTA_AUTH_ERROR:    msg = "認証失敗 (--auth の値が違う)"; break;
                case OTA_BEGIN_ERROR:   msg = "開始失敗 (OTAスロット確保できず)"; break;
                case OTA_CONNECT_ERROR: msg = "接続失敗"; break;
                case OTA_RECEIVE_ERROR: msg = "受信失敗 (Wi-Fiが不安定)"; break;
                case OTA_END_ERROR:     msg = "検証失敗 (イメージ破損)"; break;
            }
            Serial.printf("[OTA] !! 失敗: %s。現行ファームのまま動き続けます\n", msg);
            runSelfTest(); // 顔の描画に戻ったことを目視できるように
        });
        ArduinoOTA.begin();
        otaBegun = true;
        Serial.printf("[OTA] 待受開始: %s.local (%s) port 3232\n",
                      KATANORI_OTA_HOSTNAME, WiFi.localIP().toString().c_str());
    }
    ArduinoOTA.handle();
}

static void printHelp() {
    Serial.println("---------------------------------------------");
    Serial.println(" 会話");
    Serial.println("   1 : 話し始める（録音開始してDOへ送る）");
    Serial.println("   2 : 話し終わる（audioStreamEnd を送って応答を待つ）");
    Serial.println("   au  : 音声の状態を表示");
    Serial.println("   mic : マイク単独テスト(5秒) ch0/ch1のレベルを測る");
    Serial.println("   vol <0-100> : 再生音量（つまみを動かすと上書きされる）");
    Serial.println("   knob        : 音量つまみの生値と状態を表示（AS5600は磁石の数字も出る）");
    Serial.println("   knobzero    : 今の位置をゼロ点(OFF位置)としてNVSへ保存");
    Serial.println("   knobsrc     : つまみの読み元を再判定（AS5600が応答すればAS5600、駄目ならADC）");
    Serial.println("   pwr         : 疑似電源OFF(つまみOFF位置の消灯・切断)の有効/無効");
    Serial.println("   wifikill    : 疑似電源OFFで無線をWIFI_OFFまで落とすか切替（再検証用）");
    Serial.println("   cpu <MHz>   : CPU周波数を変える(80/160/240)。コーデック死亡の切り分け用");
    Serial.println("   wifistop    : WIFI_OFFまで落とす ※コーデックが死ぬ。復旧はUSB抜き差し");
    Serial.println("   reboot      : ESP32だけ再起動（RSTボタンの代わり。USBは切れない）");
    Serial.println("   creg        : コーデックの主要レジスタをダンプ（正常時と見比べる）");
    Serial.println("   knobdis     : つまみの読み取りを止める/再開（配線を外して切り分ける用）");
    Serial.println("   mute/unmute : コーデック出力（普段は自動。unmuteは自動制御を止めるので戻すこと）");
    Serial.println("   vad         : VAD計測モードの開始/終了（音声は送らず有声区間だけ数える）");
    Serial.println("   me          : 計測中のラベルを 自分/周囲 で切り替える");
    Serial.println("   vadme       : 自分の声を4秒測って装着者ゲートを自動設定");
    Serial.println("   vadth <RMS> : 装着者ゲートを直接指定（0で自動に戻す）");
    Serial.println("   beep : スピーカー単独テスト(440Hzを1秒, 振幅600)");
    Serial.println("   beep2: 同上だが振幅4000 ※イヤホンを耳に着けないこと");
    Serial.println("   scan2: I2S設定の総当たり（無音状態で実行）");
    Serial.println("   i2s <m|s> <i2s|msb> <16|32> : I2S設定を実行時に切替");
    Serial.println(" 顔の状態を直接いじる（音声なしの確認用）");
    Serial.println("   3 : RESPONSE_READY (THINK  -> SPEAK)");
    Serial.println("   4 : SPEECH_DONE    (SPEAK  -> IDLE)");
    Serial.println("   s : I2Cバスを再スキャン");
    Serial.println("   mag : AS5600(0x36)の磁石の状態と角度を表示（読み出しのみ）");
    Serial.println("   a : D0..D10 の全ピン組み合わせでOLEDを探索");
    Serial.println("   vN: D<N>ピンの電圧を測る    (例: v0)  ※入力は3.3Vまで");
    Serial.println("   gN: D<N>ピンのGND導通を見る (例: g1)");
    Serial.println("   l : ユーザーLEDの点灯/消灯を切り替え");
    Serial.println("   r : OLEDを再初期化（配線を直した後に使う）");
    Serial.println("   R : ソフトウェア再起動");
    Serial.println("   t : OLED自己診断パターンを表示");
    Serial.println("   bn: 接続状況の表示を順に出す（顔の代わりに出る2行）。大きさの確認用");
    Serial.println("   i : ブート情報を再表示");
    Serial.println("   ? : このヘルプ");
    Serial.println(" BOOT/Usrボタン: 短押しで会話の開始/終了、3秒長押しでWi-Fi設定モード");
    Serial.println("--- ネットワーク ---------------------------");
    Serial.println("   ssid <名前>       : Wi-Fi の SSID を保存");
    Serial.println("   pass <パスワード> : Wi-Fi のパスワードを保存");
    Serial.println("   prov / provoff    : Wi-Fi設定モードの開始/終了（BOOT3秒長押しでも可）");
    Serial.println("   forget            : 保存したWi-Fi設定を消去");
    Serial.println("   scan              : 周囲のAPを一覧表示");
    Serial.println("   wifi              : Wi-Fiへ接続");
    Serial.println("   wifioff           : Wi-Fiを切断");
    Serial.println("   c                 : Durable Object へ WebSocket 接続");
    Serial.println("   d                 : WebSocket を切断");
    Serial.println("   n                 : ネットワーク状態を表示");
    Serial.println("   ota               : OTA(Wi-Fi書き込み)の状態を表示");
    Serial.println("   otadis            : OTA待受の無効/有効を切替");
    Serial.println("---------------------------------------------");
}

/**
 * シリアルからのイベント注入。
 * wrapper.py が使っている "CMD:SPEAK_START" / "CMD:SPEAK_END" も受理しておく。
 * Stage 3 で PC 側ラッパーを実機に向けて動作確認する際にそのまま使えるため。
 */
static void exitProvisioning(); // 定義は下（handleButton の直前）

static void handleSerial() {
    // SSIDとパスワードを受け取るため余裕を持たせる
    static char line[160];
    static size_t len = 0;

    while (Serial.available() > 0) {
        char c = static_cast<char>(Serial.read());

        if (c == '\r') {
            continue;
        }
        if (c != '\n') {
            if (len < sizeof(line) - 1) {
                line[len++] = c;
            }
            continue;
        }

        line[len] = '\0';
        len = 0;

        if (strcmp(line, "1") == 0) {
            startTurn();
        } else if (strcmp(line, "2") == 0) {
            endTurn();
        } else if (strcmp(line, "3") == 0) {
            robot.injectEvent(katanori::RobotEvent::RESPONSE_READY);
        } else if (strcmp(line, "4") == 0) {
            robot.injectEvent(katanori::RobotEvent::SPEECH_DONE);
        } else if (strcmp(line, "CMD:SPEAK_START") == 0) {
            robot.injectEvent(katanori::RobotEvent::RESPONSE_READY);
        } else if (strcmp(line, "CMD:SPEAK_END") == 0) {
            robot.injectEvent(katanori::RobotEvent::SPEECH_DONE);

        // --- ネットワーク (単文字コマンドより先に判定すること) ---
        } else if (strncmp(line, "ssid ", 5) == 0) {
            katanori::netLink.setSsid(line + 5);
        } else if (strncmp(line, "pass ", 5) == 0) {
            katanori::netLink.setPassword(line + 5);
        } else if (strcmp(line, "forget") == 0) {
            katanori::netLink.clearCredentials();
        } else if (strcmp(line, "scan") == 0) {
            katanori::netLink.scan();
        } else if (strcmp(line, "wifi") == 0) {
            katanori::netLink.wifiConnect();
        } else if (strcmp(line, "wifioff") == 0) {
            katanori::netLink.wifiDisconnect();
        } else if (strcmp(line, "c") == 0) {
            katanori::netLink.wsConnect();
        } else if (strcmp(line, "d") == 0) {
            katanori::netLink.wsDisconnect();
        } else if (strcmp(line, "n") == 0) {
            katanori::netLink.printStatus();
        } else if (strcmp(line, "ota") == 0) {
            Serial.printf("[OTA] %s / 待受%s",
                          otaEnabled ? "有効" : "無効(otadisで切替)",
                          otaBegun ? "中" : "前(Wi-Fi接続後に自動開始)");
            if (otaBegun) {
                Serial.printf(" %s.local (%s) port 3232",
                              KATANORI_OTA_HOSTNAME,
                              WiFi.localIP().toString().c_str());
            }
            Serial.println();
            Serial.println("[OTA] 書き込みは: pio run -e xiao_esp32s3_ota -t upload");
        } else if (strcmp(line, "otadis") == 0) {
            otaEnabled = !otaEnabled;
            Serial.printf("[OTA] %s\n", otaEnabled ? "有効化しました"
                                                   : "無効化しました（再起動でも有効に戻ります）");
        } else if (strcmp(line, "au") == 0) {
            katanori::audioIo.printStatus();
        } else if (strcmp(line, "mic") == 0) {
            katanori::audioIo.micTest(5000);
        } else if (strcmp(line, "beep") == 0) {
            katanori::audioIo.toneTest(1000, 440, 600);
        } else if (strcmp(line, "beep2") == 0) {
            katanori::audioIo.toneTest(1000, 440, 4000);
        } else if (strncmp(line, "vol ", 4) == 0) {
            katanori::audioIo.setGain(atoi(line + 4) / 100.0f);
        } else if (strcmp(line, "knob") == 0) {
            if (knobAs5600Ok) {
                uint8_t buf[2];
                uint16_t raw = 0;
                if (as5600Read(0x0C, buf, 2)) {
                    raw = as5600Word(buf);
                }
                uint16_t rel = knobRelAngle(raw);
                Serial.printf("[KNOB] AS5600 RAW=%u (%.1f度) ゼロ点=%u%s 相対=%.1f度 "
                              "位置=%d%% ゲイン=%.2f -> つまみ%s\n",
                              raw, raw * 360.0f / 4096.0f,
                              knobZeroRaw, knobZeroSet ? "" : "(未設定!)",
                              rel * 360.0f / 4096.0f,
                              knobPercent, katanori::audioIo.gain(),
                              knobOff ? "OFF" : "ON");
                // 組み付けの良否は磁石の数字で見る。出さないと
                // 「なんとなく動かない」で詰まる（docs/KNOB-ENCODER.md）
                uint8_t status = 0;
                uint8_t agc = 0;
                uint16_t magnitude = 0;
                as5600Read(0x0B, &status, 1);
                as5600Read(0x1A, &agc, 1);
                if (as5600Read(0x1B, buf, 2)) {
                    magnitude = as5600Word(buf);
                }
                Serial.printf("[KNOB] 磁石 MD=%s ML=%s MH=%s AGC=%u/128 MAGNITUDE=%u\n",
                              (status & 0x20) ? "検出" : "★無し",
                              (status & 0x10) ? "★弱すぎ" : "-",
                              (status & 0x08) ? "★強すぎ" : "-",
                              agc, magnitude);
            } else {
                Serial.printf("[KNOB] (ADCフォールバック) ADC=%d 位置=%d%% ゲイン=%.2f "
                              "SW=%s -> つまみ%s\n",
                              analogRead(KATANORI_VOL_ADC), knobPercent,
                              katanori::audioIo.gain(),
                              KATANORI_KNOB_SW < 0 ? "無し(常時ON)"
                                  : (knobSwitchRawOn() ? "閉" : "開"),
                              knobOff ? "OFF" : "ON");
            }
            Serial.printf("[PWR]  疑似電源OFF=%s 画面=%s 通信=%s\n",
                          powerDownEnabled ? "有効" : "無効",
                          powerOledDown ? "消灯" : "点灯",
                          powerNetDown ? "停止" : "動作");
        } else if (strcmp(line, "knobzero") == 0) {
            knobSaveZero();
        } else if (strcmp(line, "knobsrc") == 0) {
            knobProbeSource(true);
        } else if (strcmp(line, "knobdis") == 0) {
            knobEnabled = !knobEnabled;
            if (!knobEnabled) {
                knobOff = false; // 浮いたピンでOFFと誤認させない
                Serial.printf("[KNOB] 読み取りを止めました（ゲイン%.2f固定・OFF判定なし）\n",
                              katanori::audioIo.gain());
                Serial.println("[KNOB] 配線を外して切り分けるときはこの状態で行うこと");
            } else {
                Serial.println("[KNOB] 読み取りを再開しました");
            }
        } else if (strncmp(line, "low ", 4) == 0) {
            // 指定したDピンを一瞬GNDへ落とす。「このピンをGNDに繋ぐと何が起きるか」を
            // つまみに触らずに再現するための診断。終わったらINPUT_PULLUPへ戻す。
            int d = atoi(line + 4);
            int gpio = gpioForD(d);
            if (gpio < 0) {
                Serial.println("[LOW] D0〜D10 で指定してください (例: low 1)");
            } else {
                Serial.printf("[LOW] D%d = GPIO%d を300ms LOWにします\n", d, gpio);
                pinMode(gpio, OUTPUT);
                digitalWrite(gpio, LOW);
                delay(300);
                pinMode(gpio, INPUT_PULLUP);
                Serial.println("[LOW] 戻しました");
            }
        } else if (strcmp(line, "creg") == 0) {
            katanori::audioIo.dumpCodec();
        } else if (strcmp(line, "pwr") == 0) {
            powerDownEnabled = !powerDownEnabled;
            Serial.printf("[PWR] 疑似電源OFFを%sにしました%s\n",
                          powerDownEnabled ? "有効" : "無効",
                          powerDownEnabled ? "" : "（つまみOFFは会話終了と消音だけになります）");
        } else if (strncmp(line, "cpu ", 4) == 0) {
            /*
             * CPU周波数を変える。コーデックが死ぬ原因の切り分け用。
             *
             * 「WIFI_OFF でAPBクロックの電源管理ロックが外れるから」が本当なら、
             * WiFiを触らずに周波数を落とすだけでも同じことが起きるはず。起きなければ
             * その説は捨てられる（ESP32はI2Sスレーブで、コーデックのクロックを
             * 供給していないので、そもそも筋は良くない）。
             */
            int mhz = atoi(line + 4);
            if (mhz != 80 && mhz != 160 && mhz != 240) {
                Serial.println("[CPU] 80 / 160 / 240 のどれかにしてください");
                Serial.println("[CPU]   それ未満はネイティブUSBのシリアルが切れて戻せなくなります");
            } else {
                Serial.printf("[CPU] %dMHz -> %dMHz\n", getCpuFrequencyMhz(), mhz);
                Serial.flush();
                setCpuFrequencyMhz(mhz);
                Serial.printf("[CPU] 現在 %dMHz（コーデックの生死は creg で見ること）\n",
                              getCpuFrequencyMhz());
            }
        } else if (strcmp(line, "wifistop") == 0) {
            // つまみを回さずに WIFI_OFF を再現する。死ぬまでの時間を測るため。
            // 【注意】これを撃つとコーデックが死に、USBを抜き差しするまで音が戻らない。
            Serial.println("[NET] WIFI_OFF まで落とします（コーデックが死ぬなら復旧はUSB抜き差し）");
            Serial.flush();
            katanori::netLink.wifiStop();
            // 自動接続を止めておく。止めないと0.2秒後に繋ぎ直してしまい、
            // 「OFFのまま置く」という条件そのものが作れない（実測でそうなった）。
            nextWifiTryMs = millis() + 15000;
            Serial.println("[NET] 15秒は繋ぎ直しません（この間に creg で見ること）");
        } else if (strcmp(line, "wifikill") == 0) {
            powerWifiOff = !powerWifiOff;
            Serial.printf("[PWR] 疑似電源OFFの無線は%s\n",
                          powerWifiOff ? "WIFI_OFF まで落とします（再検証用）"
                                       : "切断までに留めます（従来の挙動）");
        } else if (strcmp(line, "reboot") == 0) {
            // RSTボタンが押せない位置にあるため、シリアルから同じことをする。
            // USBの給電は切れないので「ESP32だけ再起動」の切り分けに使える。
            muteBeforeRestart();
            Serial.println("[SYS] 再起動します（USBは抜きません）");
            Serial.flush();
            delay(50);
            ESP.restart();
        } else if (strcmp(line, "mute") == 0) {
            outputGateOverride = false;
            katanori::audioIo.setOutputMute(true);
        } else if (strcmp(line, "unmute") == 0) {
            // 開けっ放しは危険なので、手動で開けたことを明示しておく
            outputGateOverride = true;
            katanori::audioIo.setOutputMute(false);
            Serial.println("[CODEC] !! 手動で開けました。自動の開け閉めは止まります");
            Serial.println("[CODEC]    この状態でリセットすると起動時に轟音が出ます。'mute' で戻してください");
        } else if (strcmp(line, "bn") == 0) {
            bannerDemoStart();
        } else if (strcmp(line, "vad") == 0) {
            vadToggle();
        } else if (strcmp(line, "me") == 0) {
            vadLabelSelfLatched = !vadLabelSelfLatched;
            Serial.printf("[VAD] これ以降の声は【%s】として記録します\n",
                          vadLabelSelfLatched ? "自分" : "周囲");
        } else if (strcmp(line, "vadme") == 0) {
            vadEnroll();
        } else if (strncmp(line, "vadth ", 6) == 0) {
            vadSetThreshold(atof(line + 6));
        } else if (strcmp(line, "scan2") == 0) {
            katanori::audioIo.scanConfigs();
        } else if (strncmp(line, "i2s ", 4) == 0) {
            // 例: "i2s s msb 32"  (master/slave, i2s/msb, 16/32)
            bool slave = (line[4] == 's');
            bool msb = (strstr(line, "msb") != nullptr);
            int bits = (strstr(line, "32") != nullptr) ? 32 : 16;
            if (katanori::audioIo.applyConfig(slave, msb, bits)) {
                Serial.printf("[I2S] %s / %s / %dbit に切り替えました\n",
                              slave ? "SLAVE" : "MASTER", msb ? "MSB" : "標準I2S", bits);
            }

        } else if (strcmp(line, "s") == 0) {
            scanI2c();
        } else if (strcmp(line, "a") == 0) {
            sweepI2cPins();
        } else if (strcmp(line, "id") == 0) {
            identifyI2c(0x18);
        } else if (strcmp(line, "mag") == 0) {
            dumpAs5600();
        } else if (strcmp(line, "prov") == 0) {
            katanori::netLink.wsDisconnect();
            katanori::audioIo.stopRecording();
            katanori::provisioning.begin();
        } else if (strcmp(line, "provoff") == 0) {
            exitProvisioning();
        } else if (strcmp(line, "r") == 0) {
            // 起動時にOLEDが繋がっていなかった場合、初期化コマンド列がパネルに
            // 届いていない。配線を直した後にリセットボタンを押さずやり直すための口。
            Serial.println("[OLED] 再初期化します");
            if (u8g2.begin()) {
                Serial.println("[OLED] SSD1306 init ok");
            } else {
                Serial.println("[OLED] !! init failed");
            }
            u8g2.setBusClock(400000);
            runSelfTest();
        } else if (strcmp(line, "R") == 0) {
            muteBeforeRestart();
            Serial.println("[SYS] 再起動します");
            Serial.flush();
            delay(50);
            ESP.restart();
        } else if (strcmp(line, "l") == 0) {
            static bool ledOn = false;
            ledOn = !ledOn;
            digitalWrite(KATANORI_USER_LED, ledOn ? LOW : HIGH);
            Serial.printf("[LED] ユーザーLED(GPIO%d) = %s\n",
                          KATANORI_USER_LED, ledOn ? "点灯" : "消灯");
        } else if (line[0] == 'v' && isdigit((unsigned char)line[1])) {
            measureVoltage(atoi(line + 1));
        } else if (line[0] == 'g' && isdigit((unsigned char)line[1])) {
            testGround(atoi(line + 1));
        } else if (strcmp(line, "t") == 0) {
            runSelfTest();
        } else if (strcmp(line, "i") == 0) {
            printBootInfo();
        } else if (line[0] == '?') {
            printHelp();
        } else if (line[0] != '\0') {
            Serial.printf("[CMD] unknown: \"%s\"  ('?' でヘルプ)\n", line);
        }
    }
}

/** 設定モードを抜けて通常動作へ戻る。保存済みの設定があれば繋ぎ直す。 */
static void exitProvisioning() {
    if (!katanori::provisioning.active()) {
        return;
    }
    katanori::provisioning.stop();
    // 自動接続のカウンタを畳む。設定し直した直後に「3回失敗したから設定モード」へ
    // すぐ戻ってしまうのを防ぐ。
    wifiFailures = 0;
    ssidMissing = false;
    nextWifiTryMs = 0;
    setNetMessage("");
    if (katanori::netLink.hasCredentials()) {
        katanori::netLink.wifiConnect();
    }
}

/**
 * BOOT / Usr ボタン（役割は同じ）。
 *   短押し   : 会話の開始 / 会話全体の終了 を交互に
 *              （発話ごとの区切りはGeminiの無音検知に任せる。ボタンでは切らない）
 *   3秒長押し: Wi-Fi設定モードへ入る
 */
/** BOOTボタンとUsrボタンのどちらかが押されていれば true。役割は同じ。 */
static bool anyButtonPressed() {
    return digitalRead(KATANORI_BOOT_BUTTON) == LOW ||
           digitalRead(KATANORI_USR_BUTTON) == LOW;
}

static void handleButton() {
    if (vadMeasuringActive()) {
        /*
         * 計測中はボタンの役目を「今喋っているのは自分」の目印に差し替える。
         *
         * 会話開始も設定モードもここでは動かさない。長押しで設定モードへ
         * 落ちてしまうと、長い発話にラベルを付けられなくなる。
         */
        vadLabelSelf = anyButtonPressed();
        return;
    }

    static bool lastPressed = false;
    static uint32_t pressedAtMs = 0;
    static uint32_t lastChangeMs = 0;
    static bool longFired = false;

    bool pressed = anyButtonPressed();
    uint32_t now = millis();

    if (pressed != lastPressed && (now - lastChangeMs) > 30) {
        lastChangeMs = now;
        lastPressed = pressed;

        if (pressed) {
            pressedAtMs = now;
            longFired = false;
        } else if (!longFired) {
            // 離した時点で短押し確定
            if (katanori::provisioning.active()) {
                provShowQr = !provShowQr;
                Serial.printf("[BTN] 表示切替 -> %s\n", provShowQr ? "QR" : "文字");
            } else if (conversationActive()) {
                Serial.println("[BTN] ボタン -> 会話終了");
                endConversation();
            } else if (knobOff) {
                // OFF位置は「電源を切ったつもり」の状態。勝手に喋り出さない
                Serial.println("[BTN] つまみがOFF位置です。右へ回してから押してください");
            } else {
                Serial.println("[BTN] ボタン -> 会話開始");
                startTurn();
            }
        }
    }

    if (pressed && !longFired && (now - pressedAtMs) >= 3000) {
        longFired = true;
        if (katanori::provisioning.active()) {
            // 設定モードから抜ける。保存せずに戻りたいときの逃げ道。
            Serial.println("[BTN] BOOT長押し -> 設定モードを抜けます");
            exitProvisioning();
        } else {
            Serial.println("[BTN] BOOT長押し -> Wi-Fi設定モードへ");
            katanori::netLink.wsDisconnect();
            katanori::audioIo.stopRecording();
            enterProvisioning();
        }
    }
}

// ---------------------------------------------------------------------------
// setup / loop
// ---------------------------------------------------------------------------

void setup() {
    Serial.begin(115200);

    // 【最優先】I2Sを真っ先に初期化する。
    //
    // ESP32-S3 では GPIO43 が UART0 の TX であり、この構成では同じピンが
    // I2S DOUT（ReSpeaker のオーディオ入力）でもある。リセット直後、
    // ROMブートローダが 115200bps でブートメッセージを吐くと、そのビット列が
    // そのままオーディオとして増幅されて轟音になる。
    // ROM側は止められないが、アプリ側が I2S を握るまでの空白は最短にできる。
    // （この初期化中のログは、下のシリアル待ちより前なので取りこぼされる。
    //   結果は後で printStatus() で確認できる）
    // コーデックのミュートに I2C を使うので、Wire を先に立ち上げておく（即座に終わる）
    Wire.setPins(KATANORI_I2C_SDA, KATANORI_I2C_SCL);
    Wire.begin();
    Wire.setClock(400000);

    bool audioOk = katanori::audioIo.begin();

    // 出力は既定でミュート。この状態が次のリセットまで保持されるので、
    // 起動時にROMブートログが轟音になるのを防げる。喋る直前だけ解除する。
    // I2C_SILENCE中はこの書き込みもしない（XMOSのコーデック初期化と重なる、
    // まさに疑っているタイミングのため）。スピーカー線は外しておくこと。
    if (!KATANORI_I2C_SILENCE) {
        katanori::audioIo.setOutputMute(true);
    }

    // ネイティブUSB CDC はホストが開くまで出力が捨てられる。
    // ブートログを取りこぼさないよう最大3秒待つ (未接続でも先へ進む)。
    uint32_t t0 = millis();
    while (!Serial && (millis() - t0) < 3000) {
        delay(10);
    }

#if KATANORI_MIN_BOOT == 1
    // 診断: audioIo.begin() の直後で setup を打ち切る。これで mic が読めれば
    // 犯人はこの下の初期化のどれか。読めなければ begin() 内部かビルド構成。
    // → 結果(2026-08-05): ★読めた(16384fps)。犯人はこの下にいる
    Serial.printf("[MINBOOT] audioOk=%d ここでsetupを打ち切ります\n", audioOk ? 1 : 0);
    return;
#endif

    Serial.println();
    Serial.println("=============================================");
    Serial.println(" katanori firmware - Stage 1 (face only)");
    Serial.println("=============================================");
    printBootInfo();

    pinMode(KATANORI_BOOT_BUTTON, INPUT_PULLUP);
    pinMode(KATANORI_USR_BUTTON, INPUT_PULLUP);

#if KATANORI_MIN_BOOT == 4
    // 診断: prints + BOOT/USRボタンのpinModeまで通して打ち切る
    Serial.println("[MINBOOT4] BOOT/USR pinMode 後に打ち切ります");
    return;
#endif

    // 音量つまみ。ADCフォールバック用のピンも従来どおり構えておく。
    // ⚠ KATANORI_KNOB_SW は既定 -1（スイッチ無し）。GPIO2はXMOSのリセット線
    //   なので、正の値を入れる場合でも 2 は絶対に指定しないこと（上の定義の注記）。
#if KATANORI_KNOB_SW >= 0
    pinMode(KATANORI_KNOB_SW, INPUT_PULLUP);
#endif

#if KATANORI_MIN_BOOT == 6
    // 診断: pinMode(KNOB_SW=GPIO2/D1) だけ通して打ち切る
    Serial.println("[MINBOOT6] pinMode(KNOB_SW) 後に打ち切ります");
    return;
#endif

    analogReadResolution(12);

#if KATANORI_MIN_BOOT == 5
    // 診断: pinMode(KNOB_SW) + analogReadResolution まで通して打ち切る
    Serial.println("[MINBOOT5] analogReadResolution 後に打ち切ります");
    return;
#endif

    knobInit(); // AS5600が応答すれば角度読み、しなければADC（Wireは初期化済み）

    // ユーザーLEDを消灯 (アクティブLOWなのでHIGHで消える)
    pinMode(KATANORI_USER_LED, OUTPUT);
    digitalWrite(KATANORI_USER_LED, HIGH);

    // Wire は setup() 冒頭で初期化済み（コーデックのミュートに必要なため）
    Serial.printf("[I2C] SDA=GPIO%d SCL=GPIO%d @400kHz\n",
                  KATANORI_I2C_SDA, KATANORI_I2C_SCL);

    bool oledOk = false;
    if (KATANORI_I2C_SILENCE) {
        Serial.println("[I2C] SILENCEビルド: スキャン・OLED・コーデックに一切触りません");
    } else {
        oledOk = scanI2c();

        u8g2.setI2CAddress(KATANORI_OLED_ADDR << 1);
        u8g2.setBusClock(400000);
        if (u8g2.begin()) {
            Serial.println("[OLED] SSD1306 init ok");
        } else {
            Serial.println("[OLED] !! init failed");
        }
        if (!oledOk) {
            Serial.println("[OLED] (I2Cスキャンで見つからなかったため描画されない可能性があります)");
        }
    }

#if KATANORI_MIN_BOOT == 3
    // 診断: pinMode/knobInit までは通し、netLink.begin() の手前で打ち切る
    Serial.println("[MINBOOT3] netLink.begin() の手前で打ち切ります");
    return;
#endif

    katanori::netLink.begin();
    katanori::netLink.setAudioSink(onAudio);
    katanori::netLink.setControlSink(onControl);

#if KATANORI_MIN_BOOT == 2
    // 診断: netLink.begin() まで通してから打ち切る
    Serial.println("[MINBOOT2] netLink.begin() 後に打ち切ります");
    return;
#endif

    if (audioOk) {
        katanori::audioIo.printStatus();
    } else {
        Serial.println("[I2S] !! 音声の初期化に失敗しました。顔の表示だけ動きます");
    }

    printHelp();

    // Wi-Fi未設定なら、いきなり設定モードで立ち上がる（仕様書3章）
    if (!katanori::netLink.hasCredentials()) {
        Serial.println("[BOOT] Wi-Fi未設定のため設定モードで起動します");
        if (enterProvisioning()) {
            renderProvisioning();
            return;
        }
    }

    // 起動直後は自己診断パターンを出す。ネイティブUSB CDC ではブートログが
    // モニタ接続前に流れてしまうため、「電源を入れたら画面に何か出る」ことを
    // ログに頼らず目視できるようにしておく。
    runSelfTest();

    Serial.println("[BOOT] ready. 自己診断の後、顔が表示されれば Stage 1 完了です。");
}

void loop() {
#if KATANORI_MIN_BOOT
    // 診断: 5秒ごとに1秒だけマイクを読む。それ以外は何もしない。
    static uint32_t lastMicMs = 0;
    if (millis() - lastMicMs >= 5000) {
        lastMicMs = millis();
        katanori::audioIo.micTest(1000);
    }
    delay(10);
    return;
#endif
    handleSerial();
    handleButton();

    // つまみは設定モード中も読む（OFF位置の検知が pumpOutputGate の前提になる）
    pumpVolumeKnob();

    // 設定モード中も閉じ忘れが起きてはいけないので、下の early return より前に置く
    pumpOutputGate();

    // 音が出ない原因のうち、これだけは黙って起きるので常に見張る
    pumpCodecWatch();

    // OTA待受。疑似電源OFFや設定モードの early return より前に置く
    // (Wi-Fiが生きている限り、どの状態からでも更新を受けられるように)
    pumpOta();

    // Wi-Fi設定モード中は顔も音声も止めて、設定画面だけを回す
    if (katanori::provisioning.active()) {
        katanori::provisioning.loop();

        // 変化したときだけ描き直す。QRを読ませている最中に無用な
        // 全面転送(約29ms)を挟むと読み取りの邪魔になる。
        static int lastSig = -1;
        int sig = (provShowQr ? 1 : 0) * 16 + static_cast<int>(katanori::provisioning.phase());
        if (sig != lastSig) {
            lastSig = sig;
            renderProvisioning();
        }
        delay(1);
        return;
    }

    // つまみOFF位置は疑似電源OFF。段階的に落とし、戻せば落とした分だけ復帰する。
    // 設定モードは上で return しているので、ここには来ない（設定中は画面もAPも要る）。
    pumpPowerDown();
    if (knobOff && powerDownEnabled) {
        // 通信を落とすまでの数秒はWebSocketを生かしておく。この間に戻されれば
        // 繋ぎ直しが要らない。顔とマイクは止める（OFFに見えなければ意味がない）。
        if (!powerNetDown) {
            katanori::netLink.loop();
        }
        delay(10);
        return;
    }

    // 電源を入れるだけで会話できる状態まで自力で行き着かせる
    pumpAutoConnect();
    pumpBannerDemo(); // `bn` のときだけ動く（表示を消す pumpAutoConnect より後）

    katanori::netLink.loop();
    pumpPendingTurn(); // setupComplete は netLink.loop() の中で届く
    pumpMic();
    pumpTurnState();

    // 仕様書どおり、内蔵LEDを通信中のステータス表示に使う
    static bool lastWsState = false;
    bool wsNow = katanori::netLink.wsConnected();
    if (wsNow != lastWsState) {
        lastWsState = wsNow;
        digitalWrite(KATANORI_USER_LED, wsNow ? LOW : HIGH); // アクティブLOW
    }

    static uint32_t lastFrameMs = 0;
    static uint32_t lastStatMs = 0;
    static uint32_t frameCount = 0;
    static katanori::RobotState lastState = katanori::RobotState::IDLE;

    uint32_t now = millis();

    // 自己診断パターン表示中は顔の描画で上書きしない
    if (static_cast<int32_t>(now - selfTestUntilMs) < 0) {
        delay(1);
        return;
    }

    // 応答音声の受信中は描画を間引く。OLEDの全面転送は約29msブロックするので、
    // 20FPSのままだと時間の半分以上を描画に取られて受信が追いつかない。
    uint32_t interval = katanori::audioIo.isPlaying() ? FRAME_INTERVAL_SLOW_MS
                                                      : FRAME_INTERVAL_MS;
    if ((now - lastFrameMs) >= interval) {
        lastFrameMs = now;
        robot.tick();
        ++frameCount;

        katanori::RobotState s = robot.state();
        if (s != lastState) {
            Serial.printf("[STATE] %s -> %s\n", stateName(lastState), stateName(s));
            lastState = s;
        }
    }

    // 5秒ごとの生存確認。描画が固まっていないか / メモリが減り続けていないかを見る
    if ((now - lastStatMs) >= 5000) {
        Serial.printf("[STAT] state=%s fps=%.1f heap=%uB\n",
                      stateName(robot.state()),
                      frameCount * 1000.0f / (now - lastStatMs),
                      ESP.getFreeHeap());
        lastStatMs = now;
        frameCount = 0;
    }

    delay(1);
}
