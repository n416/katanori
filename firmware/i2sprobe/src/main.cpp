/*
 * I2S探り針 — 本体ファームで `mic` が0フレームになる原因を、最小構成で再現する。
 *
 * 【これまでに分かっていること（2026-08-05）】
 * ・新旧どちらの基板でも、XMOSはI2Sクロックを出している（WS = ちょうど16kHz）
 * ・最小構成なら 16384 fps で読め、マイクの音も乗る
 * ・本体ファーム(firmware/esp32)だけが 0フレームになる
 *
 * 【この版でやること】
 * 本体にあって探り針に無いもの＝**再生タスク**（無音を portMAX_DELAY で
 * 書き続ける・core0・優先度5）を足して、読めなくなるかを見る。
 * 同じドライバを入れたまま「タスク前」「タスク後」で読み比べるので、
 * 差が出ればタスクが原因だと確定できる。
 */
#include <Arduino.h>
#include <driver/i2s.h>

// 切り分け段階2 (2026-08-05): -DPROBE_WIFI=1 で Wi-Fi を足す。
// 本体と同じNVS("katanori"/ssid/pass)から読む。パスワードはソースに置かない。
#ifndef PROBE_WIFI
#define PROBE_WIFI 0
#endif
#if PROBE_WIFI
#include <WiFi.h>
#include <Preferences.h>
#endif

#define PROBE_I2S_PORT I2S_NUM_0

static const int PIN_BCLK = 8;   // D9
static const int PIN_WS   = 7;   // D8
static const int PIN_DOUT = 43;  // D6
static const int PIN_DIN  = 44;  // D7

static bool playbackRunning = false;

// 本体 AudioIo::runPlayback() と同じ形。無音を書き続ける。
static void playbackTask(void*) {
    static int16_t silence[256] = { 0 };
    static int32_t slot[512];
    for (;;) {
        const size_t n = 256;
        for (size_t i = 0; i < n; ++i) {
            const int32_t v = static_cast<int32_t>(silence[i]) << 16;
            slot[i * 2] = v;
            slot[i * 2 + 1] = v;
        }
        size_t written = 0;
        i2s_write(PROBE_I2S_PORT, slot, n * 8, &written, portMAX_DELAY);
    }
}

static bool installI2S(bool withTx, int bits) {
    i2s_driver_uninstall(PROBE_I2S_PORT);

    i2s_config_t cfg = {};
    cfg.mode = static_cast<i2s_mode_t>(
        I2S_MODE_SLAVE | I2S_MODE_RX | (withTx ? I2S_MODE_TX : 0));
    cfg.sample_rate = 16000;
    cfg.bits_per_sample = (bits == 32) ? I2S_BITS_PER_SAMPLE_32BIT
                                       : I2S_BITS_PER_SAMPLE_16BIT;
    cfg.channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT;
    cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
    cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
    cfg.dma_buf_count = 4;
    cfg.dma_buf_len = 256;
    cfg.use_apll = false;
    cfg.tx_desc_auto_clear = true;
    cfg.fixed_mclk = 0;

    if (i2s_driver_install(PROBE_I2S_PORT, &cfg, 0, nullptr) != ESP_OK) {
        Serial.println("  driver_install 失敗");
        return false;
    }
    i2s_pin_config_t pins = {};
    pins.mck_io_num = I2S_PIN_NO_CHANGE;
    pins.bck_io_num = PIN_BCLK;
    pins.ws_io_num = PIN_WS;
    pins.data_out_num = withTx ? PIN_DOUT : I2S_PIN_NO_CHANGE;
    pins.data_in_num = PIN_DIN;
    if (i2s_set_pin(PROBE_I2S_PORT, &pins) != ESP_OK) {
        Serial.println("  set_pin 失敗");
        i2s_driver_uninstall(PROBE_I2S_PORT);
        return false;
    }
    i2s_zero_dma_buffer(PROBE_I2S_PORT);
    return true;
}

// ドライバはそのままに、読むだけ。本体 micTest と同じ 100ms タイムアウト。
static void readOnce(const char* label) {
    static int32_t buf[512];
    size_t totalBytes = 0;
    uint32_t reads = 0, empty = 0;
    int32_t peak = 0;

    const uint32_t t0 = millis();
    while (millis() - t0 < 500) {
        size_t got = 0;
        const esp_err_t err = i2s_read(PROBE_I2S_PORT, buf, sizeof(buf), &got,
                                       pdMS_TO_TICKS(100));
        ++reads;
        if (err != ESP_OK) {
            Serial.printf("  %-28s i2s_read エラー: %s\n", label, esp_err_to_name(err));
            return;
        }
        if (got == 0) {
            ++empty;
            continue;
        }
        totalBytes += got;
        const size_t n = got / sizeof(int32_t);
        for (size_t i = 0; i < n; i++) {
            const int32_t v = buf[i] >> 16;
            if (abs(v) > peak) peak = abs(v);
        }
    }
    const unsigned frames = static_cast<unsigned>(totalBytes / 8);
    Serial.printf("  %-28s %6u frames (%u fps)  peak=%6ld   読み%lu回中 空%lu回\n",
                  label, frames, frames * 2, (long)peak,
                  (unsigned long)reads, (unsigned long)empty);
}

static void countEdges(const char* name, int gpio) {
    pinMode(gpio, INPUT);
    const uint32_t t0 = micros();
    int prev = digitalRead(gpio);
    uint32_t edges = 0;
    while ((micros() - t0) < 50000) {
        const int v = digitalRead(gpio);
        if (v != prev) { edges++; prev = v; }
    }
    Serial.printf("  %-5s(GPIO%-2d): エッジ %6lu 回 / 50ms\n", name, gpio, (unsigned long)edges);
}

void setup() {
    Serial.begin(115200);
    delay(3000);

    Serial.println();
    Serial.println("=============================================");
    Serial.println(" I2S探り針 — 再生タスクが犯人か");
    Serial.println("=============================================");

    Serial.println("--- 0. クロックが来ているか（I2Sドライバを通さない） ---");
    countEdges("BCLK", PIN_BCLK);
    countEdges("WS", PIN_WS);

    Serial.println("--- 1. ドライバ TX+RX 32bit を入れて読む（タスク無し） ---");
    if (!installI2S(true, 32)) return;
    readOnce("タスク無し 1回目");
    readOnce("タスク無し 2回目");

    Serial.println("--- 2. 本体と同じ再生タスクを起動（core0 / 優先度5） ---");
    xTaskCreatePinnedToCore(playbackTask, "probe_play", 4096, nullptr, 5, nullptr, 0);
    playbackRunning = true;
    delay(500);
    Serial.println("  起動しました");

    Serial.println("--- 3. 同じドライバのまま、もう一度読む ---");
    readOnce("タスク有り 1回目");
    readOnce("タスク有り 2回目");
    readOnce("タスク有り 3回目");

    Serial.println();
    Serial.println("★ 3で0フレームになれば、犯人は再生タスク。");
    Serial.println();

#if PROBE_WIFI
    Serial.println("--- 4. Wi-Fiを起動して接続する（本体と同じSTAモード） ---");
    {
        Preferences prefs;
        prefs.begin("katanori", true);
        String ssid = prefs.getString("ssid", "");
        String pass = prefs.getString("pass", "");
        prefs.end();
        if (ssid.length() == 0) {
            Serial.println("  NVSにSSIDがありません。Wi-Fi段階はスキップします");
        } else {
            Serial.printf("  SSID=\"%s\" へ接続します\n", ssid.c_str());
            WiFi.mode(WIFI_STA);
            WiFi.begin(ssid.c_str(), pass.c_str());
            const uint32_t t0 = millis();
            while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) {
                delay(250);
            }
            Serial.printf("  %s (%.1f秒)\n",
                          WiFi.status() == WL_CONNECTED ? "接続しました" : "接続できませんでした（電波は出ている状態で続行）",
                          (millis() - t0) / 1000.0f);
        }
    }

    Serial.println("--- 5. Wi-Fiが動いたまま、もう一度読む ---");
    readOnce("Wi-Fi有り 1回目");
    readOnce("Wi-Fi有り 2回目");
    readOnce("Wi-Fi有り 3回目");
    Serial.println();
    Serial.println("★ 5で0フレームになれば、犯人はWi-Fi。");
    Serial.println();
#endif
}

void loop() {
    readOnce(playbackRunning ? "継続監視(タスク有り)" : "継続監視");
    delay(2000);
}
