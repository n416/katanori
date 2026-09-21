#include "AudioIo.h"

#include <driver/i2s.h>
#include <freertos/FreeRTOS.h>
#include <freertos/stream_buffer.h>
#include <esp_heap_caps.h>
#include <Wire.h>
#include "Console.h" // 最後に置く（Serial を Wi-Fi モニタへも流す差し替え。Console.h）

namespace katanori {

namespace {

constexpr i2s_port_t I2S_PORT = I2S_NUM_0;

/*
 * XMOS のレートと機体の中のレートの比（AudioIo.h）。
 *
 * 16kHz 版のファームなら 1 で、下の変換は全部素通しになる（コンパイル時に消える）。
 * 48kHz 版なら 3。
 */
constexpr int RATE_RATIO = KATANORI_XMOS_RATE / KATANORI_AUDIO_RATE;
static_assert(RATE_RATIO >= 1, "XMOS のレートが機体のレートより低い");
static_assert(KATANORI_XMOS_RATE == KATANORI_AUDIO_RATE * RATE_RATIO,
              "XMOS のレートは機体のレートの整数倍でなければならない");

// I2S から一度に読む量。ステレオ16bit なので 1フレーム = 4バイト。
// 512フレーム = 32ms 相当。OLEDの全面転送(約29ms)の間に溜まる量を吸収できる。
// ⚠ 48kHz のときは3フレームで1サンプルになるので、同じ時間ぶんを読むには
//    比のぶん増やす必要がある（減らすと1回の呼び出しで 10ms 分しか取れない）。
constexpr size_t READ_FRAMES = 512 * RATE_RATIO;

// 再生バッファ。PSRAM があれば潤沢に取る。
// 16kHz/16bit モノラルなので 1秒 = 32000バイト。
constexpr size_t PLAY_BUF_PSRAM = 512 * 1024; // 16秒
constexpr size_t PLAY_BUF_DRAM  = 48 * 1024;  // 1.5秒

StreamBufferHandle_t playBuf = nullptr;
StaticStreamBuffer_t playBufStruct;
uint8_t* playBufStorage = nullptr;
size_t playBufSize = 0;

// ステレオ読み出し用の一時領域。32bitスロットも受けられるよう2倍で確保する。
int32_t* stereoScratch = nullptr;
constexpr size_t SCRATCH_BYTES = READ_FRAMES * sizeof(int32_t) * 2;

bool driverInstalled = false;

/*
 * マイクの受け皿。読み取り用のタスク（captureTask）が I2S から読み続けてここへためる。
 *
 * 🔴 main loop が I2S を直接読んでいたころは、Gemini への接続（TLS の握手で 1〜2 秒
 * loop が止まる）の間にマイクが読まれず、I2S の DMA（64ms 分）が溢れて音が消えていた。
 * 「カタノリ、今日の天気は？」の続きがまるごと落ちた（2026-09-22 実機）。
 * 5 秒あれば、接続がもたついても取りこぼさない。
 */
constexpr uint32_t CAP_SAMPLES = KATANORI_AUDIO_RATE * 5;
int16_t* capMain = nullptr;   // 会話・VAD 用（KATANORI_MIC_CHANNEL・KATANORI_MIC_GAIN）
int16_t* capWake = nullptr;   // 呼び名の聞き分け用（ch1 を 16 倍）
volatile uint32_t capW = 0;   // 書いた総数（タスクだけが進める）
volatile uint32_t capR = 0;   // 読んだ総数（readMic だけが進める）
volatile uint32_t capDropped = 0;
volatile int capHoldCount = 0;  // 診断のコマンドが I2S を直に触る間は止める
volatile bool capHeld = false;

} // namespace

AudioIo audioIo;

bool AudioIo::applyConfig(bool slave, bool msbFormat, int bits) {
    // 実行中に張り替えるときは、読み取り用のタスクを止めてから（入れ子になってよい）
    if (started_) {
        holdCapture(true);
    }
    struct Release {
        AudioIo* a;
        bool on;
        ~Release() { if (on) a->holdCapture(false); }
    } release{this, started_};
    if (started_ || driverInstalled) {
        i2s_driver_uninstall(I2S_PORT);
        driverInstalled = false;
    }

    i2s_config_t cfg = {};
    cfg.mode = static_cast<i2s_mode_t>(
        (slave ? I2S_MODE_SLAVE : I2S_MODE_MASTER) | I2S_MODE_TX | I2S_MODE_RX);
    cfg.sample_rate = KATANORI_XMOS_RATE;  // 機体の中のレートではなく XMOS の実レート
    cfg.bits_per_sample = (bits == 32) ? I2S_BITS_PER_SAMPLE_32BIT
                                       : I2S_BITS_PER_SAMPLE_16BIT;
    cfg.channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT; // ステレオ
    cfg.communication_format = msbFormat ? I2S_COMM_FORMAT_STAND_MSB
                                         : I2S_COMM_FORMAT_STAND_I2S;
    cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
    /*
     * 4 x 256フレーム = 16kHz で 64ms。OLEDの全面転送(約29ms)の間の取りこぼしを
     * 防ぐには十分で、かつ「無音を流し続ける」方式で応答音声に乗る遅延を抑えられる。
     *
     * 🔴 48kHz では同じ数だと 21ms にしかならず、描画の 29ms の間に必ず溢れる。
     * 溢れた不連続が「静かなのに RMS 数千」として出てきて、VAD が誤って起動した
     * （2026-09-21 実機。QUIET が中央 49 から数千へ跳ねた）。比のぶん増やして
     * 時間を揃える。増える内蔵RAMは 32bitステレオで 16KB ほど。
     */
    cfg.dma_buf_count = 4 * RATE_RATIO;
    cfg.dma_buf_len = 256;
    cfg.use_apll = false;
    cfg.tx_desc_auto_clear = true; // 送るものが無いときは無音を流す
    cfg.fixed_mclk = 0;

    esp_err_t err = i2s_driver_install(I2S_PORT, &cfg, 0, nullptr);
    if (err != ESP_OK) {
        Serial.printf("[I2S] driver_install 失敗: %s\n", esp_err_to_name(err));
        return false;
    }

    i2s_pin_config_t pins = {};
    pins.mck_io_num = (KATANORI_I2S_MCLK < 0) ? I2S_PIN_NO_CHANGE : KATANORI_I2S_MCLK;
    pins.bck_io_num = KATANORI_I2S_BCLK;
    pins.ws_io_num = KATANORI_I2S_WS;
    pins.data_out_num = KATANORI_I2S_DOUT;
    pins.data_in_num = KATANORI_I2S_DIN;

    err = i2s_set_pin(I2S_PORT, &pins);
    if (err != ESP_OK) {
        Serial.printf("[I2S] set_pin 失敗: %s\n", esp_err_to_name(err));
        i2s_driver_uninstall(I2S_PORT);
        return false;
    }
    i2s_zero_dma_buffer(I2S_PORT);

    driverInstalled = true;
    curSlave_ = slave;
    curMsb_ = msbFormat;
    curBits_ = bits;
    return true;
}

bool AudioIo::begin() {
    if (started_) {
        return true;
    }

    if (!applyConfig(KATANORI_I2S_SLAVE, KATANORI_I2S_MSB_FORMAT, KATANORI_I2S_BITS)) {
        return false;
    }

    // 読み出し用スクラッチ
    stereoScratch = static_cast<int32_t*>(malloc(SCRATCH_BYTES));
    if (stereoScratch == nullptr) {
        Serial.println("[I2S] スクラッチ確保に失敗");
        i2s_driver_uninstall(I2S_PORT);
        return false;
    }

    // 再生バッファ: PSRAM を優先し、無ければ内蔵RAMで小さく取る
    playBufSize = PLAY_BUF_PSRAM;
    playBufStorage = static_cast<uint8_t*>(
        heap_caps_malloc(playBufSize + 1, MALLOC_CAP_SPIRAM));
    if (playBufStorage == nullptr) {
        playBufSize = PLAY_BUF_DRAM;
        playBufStorage = static_cast<uint8_t*>(malloc(playBufSize + 1));
        Serial.println("[I2S] PSRAMが使えないため再生バッファを縮小しました");
    }
    if (playBufStorage == nullptr) {
        Serial.println("[I2S] 再生バッファ確保に失敗");
        i2s_driver_uninstall(I2S_PORT);
        return false;
    }

    playBuf = xStreamBufferCreateStatic(playBufSize, 1, playBufStorage, &playBufStruct);
    if (playBuf == nullptr) {
        Serial.println("[I2S] StreamBuffer作成に失敗");
        i2s_driver_uninstall(I2S_PORT);
        return false;
    }

    // 再生タスク。描画を止めないよう main loop とは別に回す。
    BaseType_t ok = xTaskCreatePinnedToCore(
        playbackTask, "katanori_play", 4096, this, 5, nullptr, 0);
    if (ok != pdPASS) {
        Serial.println("[I2S] 再生タスクの起動に失敗");
        return false;
    }

    // マイクの受け皿と読み取り用のタスク（capMain の説明）
    capMain = static_cast<int16_t*>(heap_caps_malloc(CAP_SAMPLES * sizeof(int16_t), MALLOC_CAP_SPIRAM));
    capWake = static_cast<int16_t*>(heap_caps_malloc(CAP_SAMPLES * sizeof(int16_t), MALLOC_CAP_SPIRAM));
    if (capMain == nullptr || capWake == nullptr) {
        Serial.println("[I2S] マイクの受け皿（PSRAM）が取れません");
        return false;
    }
    started_ = true;
    // main loop と同じ core 1 で、loop より高い優先度。loop が TLS の握手で止まっていても
    // 割り込んで読む。I2S の読み出しで待つ間は CPU を譲る
    ok = xTaskCreatePinnedToCore(captureTask, "katanori_mic", 4096, this, 5, nullptr, 1);
    if (ok != pdPASS) {
        Serial.println("[I2S] マイクのタスクの起動に失敗");
        started_ = false;
        return false;
    }

    Serial.printf("[I2S] 初期化しました  %dHz 16bit stereo  %s / %s\n",
                  KATANORI_AUDIO_RATE,
                  KATANORI_I2S_SLAVE ? "SLAVE" : "MASTER",
                  KATANORI_I2S_MSB_FORMAT ? "MSB(左詰め)" : "標準I2S");
    Serial.printf("[I2S]   bclk=%d ws=%d dout=%d din=%d mclk=%d\n",
                  KATANORI_I2S_BCLK, KATANORI_I2S_WS,
                  KATANORI_I2S_DOUT, KATANORI_I2S_DIN, KATANORI_I2S_MCLK);
    Serial.printf("[I2S] 再生バッファ %uKB (%.1f秒ぶん)  マイクch=%d\n",
                  (unsigned)(playBufSize / 1024),
                  playBufSize / 2.0f / KATANORI_AUDIO_RATE,
                  KATANORI_MIC_CHANNEL);
    return true;
}

void AudioIo::startRecording() {
    if (!started_) {
        return;
    }
    // 前のターンの残りを持ち込まない（受け皿を空にする）
    capR = capW;
    sentSamples_ = 0;
    recording_ = true;
}

void AudioIo::stopRecording() {
    recording_ = false;
    micLevel_ = 0.0f;
}

size_t AudioIo::frameBytes() const {
    // ステレオなので 16bitスロットなら4バイト、32bitスロットなら8バイト
    return (curBits_ == 32) ? 8 : 4;
}

/** 固定ゲインを掛けて 16bit に収める（AudioIo.h の KATANORI_MIC_GAIN）。 */
int16_t AudioIo::applyMicGain(int16_t v) {
    if (KATANORI_MIC_GAIN == 1) {
        return v;
    }
    int32_t g = static_cast<int32_t>(v) * KATANORI_MIC_GAIN;
    if (g > 32767) {
        g = 32767;
        ++micClipped_;
    } else if (g < -32768) {
        g = -32768;
        ++micClipped_;
    }
    return static_cast<int16_t>(g);
}

/**
 * マイクから読む。readMic が受け皿から取り出すのに対し、こちらは I2S を直に読む。
 * 読み取り用のタスク（captureTask）だけが呼ぶ。
 */
size_t AudioIo::captureFromI2s(int16_t* out, size_t maxSamples, int16_t* wakeOut, TickType_t wait) {
    if (!started_) {
        return 0;
    }

    const size_t fb = frameBytes();
    // 48kHz のときは 3 フレームで 1 サンプルになるので、欲しいサンプル数の
    // 比のぶんだけフレームを読む
    size_t frames = maxSamples * RATE_RATIO;
    if (frames > READ_FRAMES) {
        frames = READ_FRAMES;
    }
    size_t want = frames * fb;
    if (want > SCRATCH_BYTES) {
        want = (SCRATCH_BYTES / fb) * fb;
    }

    size_t bytesRead = 0;
    // タイムアウト0 = 溜まっているぶんだけ。描画を止めない。
    if (i2s_read(I2S_PORT, stereoScratch, want, &bytesRead, wait) != ESP_OK) {
        return 0;
    }

    size_t got = bytesRead / fb;
    if (got == 0) {
        return 0;
    }

    /*
     * ステレオ -> モノラル。ch0 = 音声認識向けの処理済み信号。
     *
     * 48kHz のファームでは、ここで 3 サンプルの平均を 1 つにして 16kHz へ落とす
     * （AudioIo.h の KATANORI_XMOS_RATE）。呼び出し側は常に 16kHz を受け取る。
     *
     * ⚠ 平均は簡易な低域通過で、8kHz あたりの落ちは -6dB ほどしかない。折り返しが
     * 音声認識に響くようなら FIR に替える。まず平均で測る（ReSpeaker の
     * ノイズ抑制を通った後なので高域はもともと少ない）。
     * ⚠ 端数は次の呼び出しへ持ち越す。ここで捨てると 3 回に 1 回ずつ音が飛ぶ。
     */
    int32_t peak = 0;
    size_t produced = 0;
    // 聞き分け用（ch1 を 16 倍）。32bit スロットなら 32bit の段で倍にする（AudioIo.h の wakeOut）
    auto wakeRaw = [&](size_t i) -> int64_t {
        if (curBits_ == 32) {
            return stereoScratch[i * 2 + 1];
        }
        return static_cast<int64_t>(reinterpret_cast<const int16_t*>(stereoScratch)[i * 2 + 1]) << 16;
    };
    auto wakeOf = [](int64_t v32) -> int16_t {
        const int64_t v = v32 >> 12;  // 16bit へは >>16。4 つ少なく落として 16 倍
        return static_cast<int16_t>(v > 32767 ? 32767 : (v < -32768 ? -32768 : v));
    };
    for (size_t i = 0; i < got; ++i) {
        int16_t s;
        if (curBits_ == 32) {
            // XMOS は32bitスロットで送ってくる。実データは上位16bit。
            s = static_cast<int16_t>(stereoScratch[i * 2 + KATANORI_MIC_CHANNEL] >> 16);
        } else {
            const int16_t* src = reinterpret_cast<const int16_t*>(stereoScratch);
            s = src[i * 2 + KATANORI_MIC_CHANNEL];
        }

        if (RATE_RATIO == 1) {
            s = applyMicGain(s);
            if (wakeOut) {
                wakeOut[produced] = wakeOf(wakeRaw(i));
            }
            out[produced++] = s;
        } else {
            decimAcc_ += s;
            decimAccWake_ += wakeRaw(i);
            if (++decimCount_ >= RATE_RATIO) {
                const int16_t avg = applyMicGain(
                    static_cast<int16_t>(decimAcc_ / RATE_RATIO));
                if (wakeOut) {
                    wakeOut[produced] = wakeOf(decimAccWake_ / RATE_RATIO);
                }
                out[produced++] = avg;
                decimAcc_ = 0;
                decimAccWake_ = 0;
                decimCount_ = 0;
                s = avg;  // ピークは出したサンプルで見る
            } else {
                continue;  // まだ 1 サンプル分そろっていない
            }
        }
        const int32_t a = s < 0 ? -static_cast<int32_t>(s) : s;
        if (a > peak) {
            peak = a;
        }
    }

    if (produced == 0) {
        return 0;  // 端数だけだった。次の呼び出しでそろう
    }
    if (recording_) {
        micLevel_ = peak / 32768.0f;
    }
    return produced;
}

void AudioIo::captureTask(void* arg) {
    static_cast<AudioIo*>(arg)->runCapture();
}

void AudioIo::runCapture() {
    static int16_t mainBuf[512];
    static int16_t wakeBuf[512];
    for (;;) {
        if (capHoldCount > 0) {
            capHeld = true;
            vTaskDelay(pdMS_TO_TICKS(5));
            continue;
        }
        capHeld = false;
        const size_t n = captureFromI2s(mainBuf, 512, wakeBuf, pdMS_TO_TICKS(40));
        if (n == 0) {
            vTaskDelay(1);  // I2S が止まっているときに core 1 を占有しない
            continue;
        }
        if (!recording_) {
            continue;  // 録音していないときは読み捨てる（DMA を溢れさせない）
        }
        for (size_t i = 0; i < n; ++i) {
            if (capW - capR >= CAP_SAMPLES) {
                ++capDropped;  // 受け皿が一杯。読む側が 5 秒止まっている
                continue;
            }
            const uint32_t at = capW % CAP_SAMPLES;
            capMain[at] = mainBuf[i];
            capWake[at] = wakeBuf[i];
            capW = capW + 1;
        }
    }
}

size_t AudioIo::readMic(int16_t* out, size_t maxSamples, int16_t* wakeOut) {
    if (!started_ || !recording_) {
        return 0;
    }
    const uint32_t avail = capW - capR;
    const size_t n = avail < maxSamples ? avail : maxSamples;
    for (size_t i = 0; i < n; ++i) {
        const uint32_t at = (capR + i) % CAP_SAMPLES;
        out[i] = capMain[at];
        if (wakeOut) {
            wakeOut[i] = capWake[at];
        }
    }
    capR = capR + n;
    sentSamples_ += n;
    return n;
}

uint32_t AudioIo::micDropped() const {
    return capDropped;
}

void AudioIo::holdCapture(bool hold) {
    if (hold) {
        ++capHoldCount;
        // タスクが I2S から手を離すまで待つ（1 回の読み出しは最長 40ms）
        const uint32_t t0 = millis();
        while (started_ && !capHeld && millis() - t0 < 200) {
            delay(1);
        }
    } else if (capHoldCount > 0) {
        --capHoldCount;
    }
}

/**
 * モノラル16bitを現在のスロット幅でI2Sへ書き出す（左右へ複製）。
 * 32bitスロットのときは上位16bitへ載せる。
 */
void AudioIo::writeMono(const int16_t* mono, size_t samples, TickType_t wait) {
    static int32_t slot[512]; // L,R 交互。タスク専用なので静的で構わない
    const size_t slotFrames = (curBits_ == 32) ? (sizeof(slot) / sizeof(int32_t) / 2)
                                               : (sizeof(slot) / sizeof(int32_t));
    /*
     * 48kHz のファームでは、16kHz の 1 サンプルを 3 フレームへ伸ばす
     * （AudioIo.h の KATANORI_XMOS_RATE）。呼び出し側は常に 16kHz で渡してよい。
     *
     * ⚠ 同じ値を3つ並べる（ゼロ次ホールド）と階段状の段差が高域の雑音になる。
     * 前のサンプルとの間を線形に埋める。掛け算と割り算が1サンプルあたり数回で済む。
     * ⚠ 前回の最後の値を跨いで覚えておくこと。呼び出しの切れ目で段差を作らない。
     */
    const size_t maxIn = slotFrames / RATE_RATIO;  // 1周で処理できる入力サンプル数

    size_t done = 0;
    while (done < samples) {
        size_t n = samples - done;
        if (n > maxIn) {
            n = maxIn;
        }

        size_t frames = 0;
        for (size_t i = 0; i < n; ++i) {
            const int32_t cur = mono[done + i];
            for (int k = 0; k < RATE_RATIO; ++k) {
                int32_t v;
                if (RATE_RATIO == 1) {
                    v = cur;
                } else {
                    // prev から cur へ (k+1)/RATE_RATIO だけ進んだところ
                    v = upsamplePrev_ + (cur - upsamplePrev_) * (k + 1) / RATE_RATIO;
                }
                if (curBits_ == 32) {
                    const int32_t w = v << 16;
                    slot[frames * 2] = w;      // L
                    slot[frames * 2 + 1] = w;  // R
                } else {
                    const uint16_t u = static_cast<uint16_t>(static_cast<int16_t>(v));
                    slot[frames] = static_cast<int32_t>(u | (static_cast<uint32_t>(u) << 16));
                }
                ++frames;
            }
            upsamplePrev_ = cur;
        }

        const size_t bytes = frames * ((curBits_ == 32) ? 8 : 4);
        size_t written = 0;
        if (i2s_write(I2S_PORT, slot, bytes, &written, wait) != ESP_OK || written == 0) {
            return;
        }
        const size_t framesWritten = written / ((curBits_ == 32) ? 8 : 4);
        if (framesWritten < frames) {
            // 書き切れなかった。次の呼び出しで続きから積み直す
            done += framesWritten / RATE_RATIO;
            return;
        }
        done += n;
    }
}

void AudioIo::play(const int16_t* pcm, size_t samples) {
    if (!started_ || playBuf == nullptr || samples == 0) {
        return;
    }
    size_t bytes = samples * sizeof(int16_t);
    size_t sent = xStreamBufferSend(playBuf, pcm, bytes, 0); // 待たない
    if (sent < bytes) {
        droppedSamples_ += (bytes - sent) / sizeof(int16_t);
    }
}

namespace {

// ReSpeaker Lite の音声コーデック。Seeed公式の音量制御サンプルと同じアドレス。
constexpr uint8_t AIC3204_ADDR = 0x18;

bool codecWrite(uint8_t reg, uint8_t value) {
    Wire.beginTransmission(AIC3204_ADDR);
    Wire.write(reg);
    Wire.write(value);
    return Wire.endTransmission() == 0;
}

bool codecRead(uint8_t reg, uint8_t& out) {
    Wire.beginTransmission(AIC3204_ADDR);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) {
        return false;
    }
    if (Wire.requestFrom(AIC3204_ADDR, (uint8_t)1) != 1) {
        return false;
    }
    out = Wire.read();
    return true;
}

} // namespace

bool AudioIo::setOutputMute(bool mute) {
    // ページ0を選択（DACのミュートと音量はページ0にある）
    if (!codecWrite(0x00, 0x00)) {
        Serial.println("[CODEC] 応答がありません (0x18)");
        return false;
    }

    /*
     * reg 0x41/0x42 = DAC左/右のデジタル音量。0.5dBステップ。
     *   0x81 = -63.5dB (最小) / 0xFF = -0.5dB / 0x00 = 0dB
     *
     * 🔴 一気に書き換えるとポップノイズが出る。
     * -63.5dB から 0dB へ 1回で飛ばすと段差が音になり、マイクがそれを拾って
     * Gemini が「人が喋った」と見なし、始めたばかりの応答を割り込みで捨てる
     * （実機で何度も再現。文字起こしは "Porra." "能 做 。" など、短い雑音を
     * 無理に言葉にしたもの）。コーデックのソフトステップはミュートビットには
     * 効くが、この音量レジスタの書き換えには効かない。
     *
     * ⚠ マイクを止めて避けてはいけない。ロボットが喋り始めた直後に人が
     * 割り込む場面で、その分だけ頭が切れる（ユーザー 2026-09-21
     * 「カタノリXXXXしてって言うときに 0.5秒も切れるんだったら使い物にならん」）。
     * 出さないようにするのが正しい。
     */
    static const uint8_t kFade[] = {0x81, 0x91, 0xA1, 0xB1, 0xC1,
                                    0xD1, 0xE1, 0xF1, 0x00};
    static constexpr size_t kFadeCount = sizeof(kFade) / sizeof(kFade[0]);
    static constexpr uint32_t kFadeStepMs = 3;   // 全体で 24ms。1フレームに満たない

    // reg 0x40 = DACチャンネル設定2。D3=左ミュート, D2=右ミュート。
    // 他のビット(ソフトステップ等)を壊さないよう読んでから書き戻す。
    // 解除のときは、音量を最小にしたままミュートビットを外してから上げる
    // （逆にすると 0dB のままミュートが外れて、そこで段差が出る）
    uint8_t v = 0;
    if (!mute && codecRead(0x40, v)) {
        codecWrite(0x41, kFade[0]);
        codecWrite(0x42, kFade[0]);
        codecWrite(0x40, (uint8_t)(v & ~0x0C));
    }

    for (size_t i = 0; i < kFadeCount; ++i) {
        const uint8_t step = mute ? kFade[kFadeCount - 1 - i] : kFade[i];
        codecWrite(0x41, step);
        codecWrite(0x42, step);
        delay(kFadeStepMs);
    }

    // ミュートするときは、最小まで落としたあとにビットを立てる
    if (mute && codecRead(0x40, v)) {
        codecWrite(0x40, (uint8_t)(v | 0x0C));
    }

    muted_ = mute;
    if (!mute) {
        unmutedAt_ = millis();  // ここからしばらくはポップが乗る（AudioIo.h）
    }
    Serial.printf("[CODEC] 出力を%sしました\n", mute ? "ミュート" : "ミュート解除");
    return true;
}

bool AudioIo::codecOutputAlive() const {
    if (!codecWrite(0x00, 0x00)) {
        return true;
    }
    uint8_t v = 0;
    if (!codecRead(0x3F, v)) {
        return true;
    }
    // P0 0x3F: D7=左DAC電源, D6=右DAC電源。リセット直後は 0x14 で両方0。
    return (v & 0xC0) != 0;
}

void AudioIo::dumpCodec() const {
    // 見るべきレジスタだけに絞る。TLV320AIC3204 のデータシートの並び。
    struct Reg { uint8_t page; uint8_t reg; const char* what; };
    static const Reg kRegs[] = {
        { 0, 0x1B, "I2Sインタフェース設定" },
        { 0, 0x3F, "DAC電源 (D7=左 D6=右。0なら落ちている)" },
        { 0, 0x40, "DACミュート (D3=左 D2=右)" },
        { 0, 0x41, "DAC左デジタル音量" },
        { 0, 0x42, "DAC右デジタル音量" },
        { 1, 0x01, "電源設定 (LDO/AVDD)" },
        { 1, 0x09, "出力ドライバ電源 (0なら出力が死んでいる)" },
        { 1, 0x0C, "HPL経路" },
        { 1, 0x0D, "HPR経路" },
        { 1, 0x0E, "LOL経路" },
        { 1, 0x0F, "LOR経路" },
        { 1, 0x10, "HPLゲイン" },
        { 1, 0x11, "HPRゲイン" },
        { 1, 0x12, "LOLゲイン" },
        { 1, 0x13, "LORゲイン" },
    };

    Serial.println("--- コーデック(0x18)レジスタ ---");
    uint8_t curPage = 0xFF;
    for (const Reg& r : kRegs) {
        if (r.page != curPage) {
            if (!codecWrite(0x00, r.page)) {
                Serial.println("  !! 応答がありません (0x18)");
                return;
            }
            curPage = r.page;
        }
        uint8_t v = 0;
        if (codecRead(r.reg, v)) {
            Serial.printf("  P%u 0x%02X = 0x%02X  %s\n", r.page, r.reg, v, r.what);
        } else {
            Serial.printf("  P%u 0x%02X = ??    %s\n", r.page, r.reg, r.what);
        }
    }
    codecWrite(0x00, 0x00); // ページ0へ戻しておく（他の処理の前提）
    Serial.println("--------------------------------");
}

void AudioIo::setGain(float g) {
    if (g < 0.0f) g = 0.0f;
    if (g > 1.0f) g = 1.0f;
    gain_ = g;
    Serial.printf("[AUDIO] 再生音量 %.0f%%\n", g * 100.0f);
}

void AudioIo::stopPlayback() {
    if (playBuf != nullptr) {
        xStreamBufferReset(playBuf);
    }
    i2s_zero_dma_buffer(I2S_PORT);
}

bool AudioIo::isPlaying() const {
    return playBuf != nullptr && !xStreamBufferIsEmpty(playBuf);
}

void AudioIo::playbackTask(void* arg) {
    static_cast<AudioIo*>(arg)->runPlayback();
}

void AudioIo::runPlayback() {
    static int16_t mono[256];
    static const int16_t silence[256] = { 0 };

    for (;;) {
        size_t bytes = xStreamBufferReceive(playBuf, mono, sizeof(mono), pdMS_TO_TICKS(10));
        size_t samples = bytes / sizeof(int16_t);

        if (samples > 0) {
            // 音量を掛ける。ReSpeaker Lite の出力はアンプ経由なので、
            // フルスケールをそのまま出すと近くで聞くには大きすぎる。
            float g = gain_;
            if (g < 0.999f) {
                for (size_t i = 0; i < samples; ++i) {
                    mono[i] = static_cast<int16_t>(mono[i] * g);
                }
            }
            writeMono(mono, samples, portMAX_DELAY);
            playedSamples_ += samples;
        } else {
            // 送るものが無いときは「無音を流し続ける」。
            // TXを止めるとDMAが枯渇し、条件によっては直前の内容を繰り返して
            // 大音量のノイズになる。無音を流し続ければ確実に静かになる。
            writeMono(silence, sizeof(silence) / sizeof(silence[0]), portMAX_DELAY);
        }
    }
}

void AudioIo::scanConfigs() {
    if (!started_) {
        Serial.println("[SCAN] I2Sが初期化されていません");
        return;
    }

    bool wasRecording = recording_;
    recording_ = false;
    holdCapture(true);  // I2S を直に読むので、読み取り用のタスクを止める

    const bool saveSlave = curSlave_;
    const bool saveMsb = curMsb_;
    const int saveBits = curBits_;

    Serial.println("[SCAN] 静かな状態で実行してください。全組み合わせを試します。");
    Serial.println("[SCAN] 無音なのでRMSが最も低い設定が正解の候補です。");
    Serial.println("[SCAN]  mode   format  bits |  frames |    rms  |  peak | 先頭データ");
    Serial.println("[SCAN] ------------------------------------------------------------");

    struct Result { bool slave; bool msb; int bits; float rms; int32_t peak; uint32_t frames; };
    Result best = { false, false, 16, 1e9f, 0, 0 };
    bool haveBest = false;

    for (int s = 0; s < 2; ++s) {
        for (int m = 0; m < 2; ++m) {
            for (int b = 0; b < 2; ++b) {
                const bool slave = (s == 1);
                const bool msb = (m == 1);
                const int bits = (b == 0) ? 16 : 32;

                if (!applyConfig(slave, msb, bits)) {
                    Serial.printf("[SCAN]  %-6s %-7s %2d  | 設定できません\n",
                                  slave ? "SLAVE" : "MASTER", msb ? "MSB" : "I2S", bits);
                    continue;
                }
                delay(120); // クロックが安定するまで待つ

                // 古いデータを捨てる
                size_t n = 0;
                while (i2s_read(I2S_PORT, stereoScratch, SCRATCH_BYTES, &n, 0) == ESP_OK && n > 0) {
                }

                uint64_t sum = 0;
                int32_t peak = 0;
                uint32_t frames = 0;
                uint16_t head[6] = {0};
                bool gotHead = false;

                uint32_t start = millis();
                while (millis() - start < 600) {
                    size_t bytes = 0;
                    if (i2s_read(I2S_PORT, stereoScratch, SCRATCH_BYTES, &bytes,
                                 pdMS_TO_TICKS(100)) != ESP_OK || bytes == 0) {
                        continue;
                    }

                    // 32bitスロットのときは上位16bitを取り出して比較可能にする
                    if (bits == 16) {
                        const int16_t* src = reinterpret_cast<const int16_t*>(stereoScratch);
                        size_t got = bytes / 4; // 1フレーム = L,R の16bit×2
                        if (!gotHead && got >= 3) {
                            gotHead = true;
                            for (int i = 0; i < 6; ++i) head[i] = (uint16_t)src[i];
                        }
                        for (size_t i = 0; i < got; ++i) {
                            int32_t v = src[i * 2];
                            sum += (uint64_t)v * v;
                            int32_t a = v < 0 ? -v : v;
                            if (a > peak) peak = a;
                        }
                        frames += got;
                    } else {
                        const int32_t* src = stereoScratch;
                        size_t got = bytes / 8; // 1フレーム = L,R の32bit×2
                        if (!gotHead && got >= 3) {
                            gotHead = true;
                            for (int i = 0; i < 6; ++i) head[i] = (uint16_t)(src[i] >> 16);
                        }
                        for (size_t i = 0; i < got; ++i) {
                            int32_t v = src[i * 2] >> 16; // 上位16bitを使う
                            sum += (uint64_t)v * v;
                            int32_t a = v < 0 ? -v : v;
                            if (a > peak) peak = a;
                        }
                        frames += got;
                    }
                }

                float rms = frames > 0 ? sqrtf((float)(sum / frames)) : -1.0f;
                Serial.printf("[SCAN]  %-6s %-7s %2d  | %7u | %7.1f | %5d | %04X %04X %04X %04X\n",
                              slave ? "SLAVE" : "MASTER", msb ? "MSB" : "I2S", bits,
                              frames, rms, peak, head[0], head[1], head[2], head[3]);

                // 実測フレームレートが 16kHz から外れているものは除外する。
                // スロット幅が合っていないと、静かに見えてもレートが倍になる
                // （32bitスロットを16bitで2回に割って読んでいる状態）。
                float fps = frames / 0.6f;
                // ⚠ ここで数えているのは i2s_read から来た生のフレームなので、
                //    比べる相手は KATANORI_XMOS_RATE（48kHz 版なら 48000）である
                bool rateOk = fps > KATANORI_XMOS_RATE * 0.85f &&
                              fps < KATANORI_XMOS_RATE * 1.15f;
                if (!rateOk && frames > 0) {
                    Serial.printf("[SCAN]    ^ 実測 %.0f fps は %dHz と合いません（除外）\n",
                                  fps, KATANORI_XMOS_RATE);
                }
                if (rateOk && rms >= 0.0f && rms < best.rms) {
                    best = { slave, msb, bits, rms, peak, frames };
                    haveBest = true;
                }
            }
        }
    }

    Serial.println("[SCAN] ------------------------------------------------------------");
    if (haveBest) {
        Serial.printf("[SCAN] 最も静かだったのは %s / %s / %dbit (rms=%.1f)\n",
                      best.slave ? "SLAVE" : "MASTER", best.msb ? "MSB" : "I2S",
                      best.bits, best.rms);
        Serial.println("[SCAN] この設定にして 'mic' で喋ってみてください。");
        Serial.printf("[SCAN] 採用するなら platformio.ini に:  -DKATANORI_I2S_SLAVE=%d -DKATANORI_I2S_MSB_FORMAT=%d -DKATANORI_I2S_BITS=%d\n",
                      best.slave ? 1 : 0, best.msb ? 1 : 0, best.bits);
        applyConfig(best.slave, best.msb, best.bits);
    } else {
        Serial.println("[SCAN] どの設定でもデータが取れませんでした。");
        applyConfig(saveSlave, saveMsb, saveBits);
    }

    holdCapture(false);
    recording_ = wasRecording;
}

void AudioIo::micTest(uint32_t durationMs) {
    if (!started_) {
        Serial.println("[TEST] I2Sが初期化されていません");
        return;
    }

    bool wasRecording = recording_;
    recording_ = false; // 送信側と競合させない
    holdCapture(true);  // I2S を直に読むので、読み取り用のタスクを止める

    Serial.printf("[TEST] マイクを%.1f秒読みます。何か喋ってください...\n",
                  durationMs / 1000.0f);

    const size_t fb = frameBytes();

    // 溜まっている古いデータを捨てる
    size_t n = 0;
    while (i2s_read(I2S_PORT, stereoScratch, (SCRATCH_BYTES / fb) * fb, &n, 0) == ESP_OK && n > 0) {
    }

    uint64_t sum0 = 0, sum1 = 0;
    int32_t peak0 = 0, peak1 = 0;
    uint32_t frames = 0;
    uint32_t reads = 0, emptyReads = 0;
    bool dumped = false;

    // 500msごとのRMS。本物の音声なら喋った瞬間だけ跳ね上がる。
    // 値が終始一定なら、それは音声ではなくランダムビットである証拠。
    uint64_t winSum = 0;
    uint32_t winFrames = 0;
    uint32_t winStart = millis();

    uint32_t start = millis();
    while (millis() - start < durationMs) {
        size_t bytes = 0;
        // 100msまで待つ。クロックが回っていなければここで空のまま返る。
        esp_err_t err = i2s_read(I2S_PORT, stereoScratch,
                                 (READ_FRAMES * fb > SCRATCH_BYTES)
                                     ? (SCRATCH_BYTES / fb) * fb
                                     : READ_FRAMES * fb,
                                 &bytes, pdMS_TO_TICKS(100));
        ++reads;
        if (err != ESP_OK) {
            Serial.printf("[TEST] i2s_read エラー: %s\n", esp_err_to_name(err));
            break;
        }
        if (bytes == 0) {
            ++emptyReads;
            continue;
        }

        size_t got = bytes / fb;

        // 生データを一度だけ覗く。ビットずれや固定パターンはここに現れる。
        if (!dumped) {
            dumped = true;
            Serial.print("[TEST] 生データ先頭8フレーム(L,R): ");
            for (size_t i = 0; i < 8 && i < got; ++i) {
                if (curBits_ == 32) {
                    Serial.printf("%08X,%08X ",
                                  (unsigned)stereoScratch[i * 2],
                                  (unsigned)stereoScratch[i * 2 + 1]);
                } else {
                    const int16_t* s16 = reinterpret_cast<const int16_t*>(stereoScratch);
                    Serial.printf("%04X,%04X ",
                                  (uint16_t)s16[i * 2], (uint16_t)s16[i * 2 + 1]);
                }
            }
            Serial.println();
        }

        for (size_t i = 0; i < got; ++i) {
            int32_t a, b;
            if (curBits_ == 32) {
                // 実データは32bitスロットの上位16bit
                a = static_cast<int16_t>(stereoScratch[i * 2] >> 16);
                b = static_cast<int16_t>(stereoScratch[i * 2 + 1] >> 16);
            } else {
                const int16_t* s16 = reinterpret_cast<const int16_t*>(stereoScratch);
                a = s16[i * 2];
                b = s16[i * 2 + 1];
            }
            sum0 += static_cast<uint64_t>(a) * a;
            sum1 += static_cast<uint64_t>(b) * b;
            winSum += static_cast<uint64_t>(a) * a;
            int32_t aa = a < 0 ? -a : a;
            int32_t ab = b < 0 ? -b : b;
            if (aa > peak0) peak0 = aa;
            if (ab > peak1) peak1 = ab;
        }
        frames += got;
        winFrames += got;

        if (millis() - winStart >= 500 && winFrames > 0) {
            Serial.printf("[TEST]   +%.1fs  ch0 rms=%7.1f\n",
                          (millis() - start) / 1000.0f,
                          sqrtf((float)(winSum / winFrames)));
            winSum = 0;
            winFrames = 0;
            winStart = millis();
        }
    }

    holdCapture(false);
    recording_ = wasRecording;

    Serial.printf("[TEST] 読めたフレーム: %u (%.2f秒ぶん) / 読み出し%u回中 空%u回\n",
                  frames, frames / (float)KATANORI_AUDIO_RATE, reads, emptyReads);

    if (frames == 0) {
        Serial.println("[TEST] !! 1フレームも読めません。I2Sのクロックが回っていません。");
        Serial.println("[TEST]    -DKATANORI_I2S_SLAVE=1 を試すか、ピン設定を確認してください。");
        return;
    }

    float rms0 = sqrtf((float)(sum0 / frames));
    float rms1 = sqrtf((float)(sum1 / frames));
    Serial.printf("[TEST]   ch0: peak=%5d rms=%7.1f\n", peak0, rms0);
    Serial.printf("[TEST]   ch1: peak=%5d rms=%7.1f\n", peak1, rms1);

    if (peak0 == 0 && peak1 == 0) {
        Serial.println("[TEST] !! データは流れていますが全て0です。");
        Serial.println("[TEST]    ReSpeaker側が音声を出していません（USB版ファームの可能性）。");
    } else if (peak0 == 0 || peak1 == 0) {
        Serial.printf("[TEST] 片チャンネルのみ有効です。KATANORI_MIC_CHANNEL=%d を確認してください。\n",
                      peak0 == 0 ? 1 : 0);
    } else if (rms0 > 12000.0f) {
        // 一様乱数のRMSは 32768/sqrt(3) = 18918。これに近い値は音声ではない。
        Serial.println("[TEST] !! RMSが高すぎます。これは音声ではなくランダムビットです。");
        Serial.println("[TEST]    I2Sのフォーマット不一致か、DINが誰にも駆動されていません:");
        Serial.println("[TEST]      -DKATANORI_I2S_SLAVE=1       (ReSpeaker側がクロックを出す場合)");
        Serial.println("[TEST]      -DKATANORI_I2S_MSB_FORMAT=1  (左詰めフォーマットの場合)");
        Serial.println("[TEST]    上の500msごとのRMSが終始一定なら音声ではない証拠です。");
    } else {
        Serial.println("[TEST] 両チャンネルとも信号があります。マイク入力は正常です。");
    }
}

void AudioIo::toneTest(uint32_t durationMs, int freqHz, int amplitude) {
    if (!started_) {
        Serial.println("[TEST] I2Sが初期化されていません");
        return;
    }
    if (amplitude < 0) amplitude = 0;
    if (amplitude > 32000) amplitude = 32000;

    Serial.printf("[TEST] %dHz の正弦波を%.1f秒鳴らします (振幅 %d / 32767)\n",
                  freqHz, durationMs / 1000.0f, amplitude);
    Serial.println("[TEST] ※イヤホンを耳に着けたまま試さないでください");

    // 以前はここから writeMono() で I2S へ直接書いていたが、再生タスクが
    // 「キューが空なら無音を流し続ける」方式になってからは、無音ストリームと
    // DMAを取り合って負け、ほぼ無音になる（実機で確認 2026-07-29）。
    // 起動アナウンスと同じ再生キューへ積む方式に変更。音量つまみ(gain_)と
    // 出力ゲートも通るので、「実際の会話と同じ経路」の試験になった。
    // 注意: つまみがOFF位置だとゲートが閉じたままなので鳴らない（仕様）。
    if (muted_) {
        Serial.println("[TEST] ミュート中のため解除します（再生後は出力ゲートが自動で閉じます）");
        setOutputMute(false);
    }

    constexpr size_t CHUNK = 256;
    static int16_t mono[CHUNK];
    uint32_t phase = 0;
    uint32_t total = 0;
    const uint32_t need = KATANORI_AUDIO_RATE * durationMs / 1000;
    // 立ち上がり・立ち下がりでプチッというクリックが出ないよう20msかけて増減させる
    const uint32_t fade = KATANORI_AUDIO_RATE * 20 / 1000;

    while (total < need) {
        for (size_t i = 0; i < CHUNK; ++i) {
            uint32_t pos = phase + i;
            float env = 1.0f;
            if (pos < fade) {
                env = (float)pos / fade;
            } else if (pos + fade > need) {
                env = need > pos ? (float)(need - pos) / fade : 0.0f;
            }
            float t = (float)pos / KATANORI_AUDIO_RATE;
            mono[i] = (int16_t)(amplitude * env * sinf(2.0f * (float)M_PI * freqHz * t));
        }
        phase += CHUNK;
        total += CHUNK;

        // play() は満杯だと黙って捨てるので、ここでは送り切るまで待つ
        const uint8_t* p = reinterpret_cast<const uint8_t*>(mono);
        size_t remain = sizeof(mono);
        while (remain > 0) {
            size_t sent = xStreamBufferSend(playBuf, p, remain, pdMS_TO_TICKS(100));
            p += sent;
            remain -= sent;
        }
    }
    Serial.println("[TEST] キューへ積みました。再生されて音が出ましたか？");
}

void AudioIo::printStatus() const {
    Serial.println("--- 音声状態 ---");
    Serial.printf("  I2S       : %s\n", started_ ? "初期化済み" : "未初期化");
    Serial.printf("  録音      : %s  (マイクレベル %.2f)\n",
                  recording_ ? "中" : "停止", micLevel_);
    Serial.printf("  再生      : %s\n", isPlaying() ? "中" : "停止");
    if (playBuf != nullptr) {
        size_t avail = xStreamBufferBytesAvailable(playBuf);
        Serial.printf("  再生キュー: %uB (%.2f秒ぶん) / %uKB\n",
                      (unsigned)avail, avail / 2.0f / KATANORI_AUDIO_RATE,
                      (unsigned)(playBufSize / 1024));
    }
    Serial.printf("  送信      : %u サンプル (%.1f秒)\n",
                  sentSamples_, sentSamples_ / (float)KATANORI_AUDIO_RATE);
    Serial.printf("  再生済み  : %u サンプル (%.1f秒)\n",
                  playedSamples_, playedSamples_ / (float)KATANORI_AUDIO_RATE);
    if (droppedSamples_ > 0) {
        Serial.printf("  !! 溢れ   : %u サンプル破棄\n", droppedSamples_);
    }
    Serial.println("----------------");
}

} // namespace katanori
