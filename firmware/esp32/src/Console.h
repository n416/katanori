/*
 * ============================================================================
 *  Console - シリアルモニタを Wi-Fi 越しにも出す（2026-09-11 追加）
 *
 *  USB の口は筐体に入れると挿せない。OTA は書き込みの口しか無いので、ログも
 *  コマンド（`knob`・`knobzero`・`bat` …）も USB を挿さない限り届かなかった。
 *
 *  これは USB のシリアルへ書くのと同じ内容を、TCP の 23 番に繋いだ 1 台にも流し、
 *  そこから打った行を USB から打った行と同じように handleSerial() へ渡す。
 *
 *  ■ 使い方
 *    katanori.local の 23 番へ TCP で繋ぐ（telnet・PuTTY の Raw など）。
 *    最初の 1 行に OTA と同じ合言葉（KATANORI_OTA_PASSWORD）を送る。通れば以後は
 *    ログが流れ、打った行がコマンドになる。繋げるのは同時に 1 台だけ。
 *    合言葉を置くのは、ここから `unmute`・`beep2`・`forget` が打てるため
 *    （同じ LAN の他人に耳元のスピーカーを鳴らさせない）。
 *
 *  ■ 仕組み
 *    既存のコードは `Serial.printf` を 400 か所以上で直接呼んでいる。書き換えずに
 *    済ませるため、このヘッダの末尾で `Serial` をこのクラスへ差し替えている。
 *    ⚠ **このヘッダは各 .cpp の #include の最後に置くこと。**後から入るヘッダの中の
 *    `Serial` まで差し替わってしまう。
 *    Wi-Fi へは直接書かず、いったん輪のバッファに積んで loop() で送る。
 *    printf は音声のタスクからも来るのと、送りが詰まって main loop が止まるのを避けるため。
 * ============================================================================
 */

#ifndef KATANORI_CONSOLE_H
#define KATANORI_CONSOLE_H

#include <Arduino.h>

#ifndef KATANORI_CONSOLE_PORT
#define KATANORI_CONSOLE_PORT 23
#endif

namespace katanori {

class Console : public Stream {
public:
    /** USB シリアルを開く（`Serial.begin(115200)` がここへ来る）。 */
    void begin(unsigned long baud);

    /**
     * USB にだけ直接書く（RTC のログにも Wi-Fi の輪にも写さない）。wakestream の行のように
     * 量が多くて残す価値の無い物のため。受け皿に入る分だけ書いて、待たない。
     */
    size_t writeRaw(const uint8_t* buf, size_t n);
    int rawAvailableForWrite();
    /** Wi-Fi の相手に最初に求める合言葉。setup() で OTA と同じものを渡す。 */
    void setPassword(const char* pass) { password_ = pass; }

    /** 待受・受信・送信。main loop の先頭で毎回呼ぶ。 */
    void loop();
    /** 無線を WIFI_OFF まで落とす直前に呼ぶ。相手を切って待受を畳む。 */
    void suspend();
    /** 合言葉を通った相手が繋がっているか（待機スリープはこの間眠らない）。 */
    bool remoteActive() const { return authed_; }

    /** 前回の起動の最後のログ（再起動をまたいで残した約 3KB）を出す。シリアル `lastlog`。 */
    void printPreviousLog();

    /** USB のホストが開いているか（`while (!Serial)` 用）。 */
    explicit operator bool() const;

    size_t write(uint8_t c) override;
    size_t write(const uint8_t* buf, size_t n) override;
    using Print::write;
    int available() override;
    int read() override;
    int peek() override;
    void flush() override;

private:
    void pushOut(const uint8_t* buf, size_t n);
    void sendOut();
    void takeInput();

    const char* password_ = "";
    bool serverUp_ = false;
    volatile bool authed_ = false;
};

extern Console console;

} // namespace katanori

#ifndef KATANORI_CONSOLE_IMPL
#define Serial katanori::console
#endif

#endif // KATANORI_CONSOLE_H
