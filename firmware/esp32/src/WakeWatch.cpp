#include "WakeWatch.h"

#include <HTTPClient.h>
#include <WiFiClientSecure.h>

#include "NetLink.h"
#include "RootCa.h"

namespace katanori {

WakeWatch wakeWatch;

/** マイクのレート。ReSpeaker Lite から来るのは 16kHz 固定。 */
static constexpr uint32_t kRate = 16000;

/**
 * 送信タスクのスタック。
 *
 * TLS のハンドシェイクで深く潜るため、通常のタスクより厚く取る。
 * 8KB では足りずに落ちる（mbedTLS の作業領域が積まれる）。
 */
static constexpr uint32_t kTaskStack = 16384;

/** 1回に NetLink へ渡すサンプル数。4KB ぶん。 */
static constexpr size_t kDrainChunk = 2048;

bool WakeWatch::begin() {
    if (ring_) {
        return true;
    }
    ringLen_ = kRate * WakeWatch::kRingMs / 1000;
    const size_t bytes = ringLen_ * sizeof(int16_t);

    // PSRAM に置く。内蔵RAMは再生バッファと WebSocket で埋まっている
    ring_ = (int16_t*)ps_malloc(bytes);
    if (!ring_) {
        Serial.printf("[WAKE] PSRAM %uKB が取れません。呼びかけの見張りは動きません\n",
                      (unsigned)(bytes / 1024));
        ringLen_ = 0;
        return false;
    }
    memset(ring_, 0, bytes);
    Serial.printf("[WAKE] 控えの準備ができました（%.1f秒ぶん・PSRAM %uKB）\n",
                  WakeWatch::kRingMs / 1000.0f, (unsigned)(bytes / 1024));
    return true;
}

void WakeWatch::feed(const int16_t* pcm, size_t n) {
    if (!ring_ || n == 0) {
        return;
    }
    uint32_t w = wpos_;
    for (size_t i = 0; i < n; ++i) {
        ring_[w] = pcm[i];
        w = (w + 1) % ringLen_;
    }
    wpos_ = w;
    written_ += n;
}

void WakeWatch::markSegment(uint32_t backMs) {
    if (!ring_) {
        return;
    }
    const uint32_t back = kRate * backMs / 1000;
    segAt_ = written_ > back ? written_ - back : 0;
    hasSeg_ = true;
}

void WakeWatch::markTurn(uint32_t backMs) {
    if (!ring_) {
        return;
    }
    const uint32_t back = kRate * backMs / 1000;
    turnAt_ = written_ > back ? written_ - back : 0;
    hasTurn_ = true;
}

/**
 * 印の位置から取り出せるサンプル数と、リング上の読み出し開始位置。
 * リングを1周されたぶんは失われているので、その場合は最古まで切り詰める。
 */
static void locate(uint32_t written, uint32_t wpos, uint32_t ringLen,
                   uint32_t at, uint32_t& count, uint32_t& rpos) {
    const uint32_t behind = written > at ? written - at : 0;
    count = behind > ringLen ? ringLen : behind;
    rpos = (wpos + ringLen - count) % ringLen;
}

/** 無音かどうかを見る単位。20ms（16kHz で 320 サンプル）。 */
static constexpr uint32_t kFrameSamples = 320;

/**
 * 無音を残す長さ。
 *
 * 全部消すと語と語がぶつかって聞き取りにくくなる。ひと呼吸ぶんだけ残す。
 * 2秒の間があっても 0.2秒に詰まるので、Gemini の発話終了判定には掛からない。
 */
static constexpr uint32_t kKeepSilenceFrames = 10;  // 200ms

/**
 * 声の直前に残す長さ。
 *
 * 🔴 「カ」の k は息を止めてから弾く小さな音で、ゲートを越えない。直前の無音と一緒に
 * 捨てると、大きな母音から先だけが届く。2026-09-22 の実機で、呼び名を 5 回送って
 * 4 回が「たのに」「あたのに」と聞き取られた。声のあるフレームの手前はゲート未満でも残す。
 */
static constexpr uint32_t kPreRollFrames = 15;  // 300ms（160ms でも 3 回に 1 回「たのり」だった）

uint32_t WakeWatch::drainToNetLink(float gateRms) {
    trimmed_ = 0;
    if (!ring_ || !hasTurn_) {
        return 0;
    }
    hasTurn_ = false;

    uint32_t count = 0, rpos = 0;
    locate(written_, wpos_, ringLen_, turnAt_, count, rpos);
    if (count == 0) {
        return 0;
    }

    // 先にフレームごとの声の有無を全部測る。声の手前（kPreRollFrames）を残すには、
    // 後ろのフレームを見てから前のフレームの扱いを決める必要がある
    const uint32_t frames = count / kFrameSamples;
    uint8_t* keep = (uint8_t*)calloc(frames ? frames : 1, 1);  // 0=捨てる 1=声 2=残す無音
    if (!keep) {
        return 0;
    }
    for (uint32_t f = 0; f < frames; ++f) {
        // このフレームの音量。リングは環状なので添字を折り返す
        double acc = 0.0;
        for (uint32_t i = 0; i < kFrameSamples; ++i) {
            const double v = ring_[(rpos + f * kFrameSamples + i) % ringLen_];
            acc += v * v;
        }
        if ((float)sqrt(acc / kFrameSamples) >= gateRms) {
            keep[f] = 1;
            for (uint32_t b = 1; b <= kPreRollFrames && b <= f; ++b) {
                if (keep[f - b] == 0) {
                    keep[f - b] = 2;  // 声の手前（k の破裂など、ゲート未満の子音）
                }
            }
        }
    }
    // 無音はひと呼吸ぶんだけ残す（声の手前として残したものは数えない）
    uint32_t silentRun = 0;
    for (uint32_t f = 0; f < frames; ++f) {
        if (keep[f] != 0) {
            silentRun = 0;
        } else if (++silentRun <= kKeepSilenceFrames) {
            keep[f] = 2;
        }
    }

    int16_t chunk[kDrainChunk];
    size_t fill = 0;
    uint32_t sent = 0;
    bool stopped = false;

    for (uint32_t f = 0; f < frames && !stopped; ++f) {
        const uint32_t off = f * kFrameSamples;
        if (keep[f] == 0) {
            trimmed_ += kFrameSamples;   // ひと呼吸ぶんを超えた無音は落とす
            continue;
        }

        for (uint32_t i = 0; i < kFrameSamples; ++i) {
            chunk[fill++] = ring_[(rpos + off + i) % ringLen_];
            if (fill == kDrainChunk) {
                if (!netLink.sendAudio(chunk, fill)) {
                    stopped = true;
                    break;
                }
                sent += fill;
                fill = 0;
            }
        }
    }
    if (!stopped && fill > 0 && netLink.sendAudio(chunk, fill)) {
        sent += fill;
    }
    free(keep);

    Serial.printf("[WAKE] 繋がるまでに溜めた %.1f秒ぶんを送りました（無音 %.1f秒を詰めた）\n",
                  sent / (float)kRate, trimmed_ / (float)kRate);
    return sent;
}

bool WakeWatch::submitAsync(const char* name) {
    if (!ring_ || !hasSeg_ || busy_) {
        return false;
    }
    hasSeg_ = false;

    uint32_t count = 0, rpos = 0;
    locate(written_, wpos_, ringLen_, segAt_, count, rpos);
    const uint32_t maxSamples = kRate * WakeWatch::kMaxSendMs / 1000;
    if (count > maxSamples) {
        count = maxSamples;  // 頭から kMaxSendMs ぶんだけ送る
    }
    if (count == 0) {
        return false;
    }

    // タスクへ渡すぶんを一続きへ写す。リングは走り続けるので、ここで確定させる
    payloadBytes_ = count * sizeof(int16_t);
    payload_ = (uint8_t*)ps_malloc(payloadBytes_);
    if (!payload_) {
        Serial.println("[WAKE] 送信用のPSRAMが取れませんでした");
        payloadBytes_ = 0;
        return false;
    }
    int16_t* dst = (int16_t*)payload_;
    for (uint32_t i = 0; i < count; ++i) {
        dst[i] = ring_[(rpos + i) % ringLen_];
    }

    // 呼ばれていた場合、この区間の頭から Gemini へ渡す（「カタノリ、〜」の
    // 呼びかけごと会話に含める）。呼びかけでなければ呼び出し側が捨てる
    turnAt_ = segAt_;
    hasTurn_ = true;

    name_ = name && *name ? name : "";
    busy_ = true;
    done_ = false;
    woke_ = false;
    text_ = "";

    // 送信は別タスク。ここで待つと main loop が止まり、返事を待つあいだの
    // マイクが読まれない（＝会話の頭が欠ける）
    if (xTaskCreatePinnedToCore(taskEntry, "wakepost", kTaskStack, this, 1,
                                nullptr, 0) != pdPASS) {
        Serial.println("[WAKE] 送信タスクを作れませんでした");
        free(payload_);
        payload_ = nullptr;
        payloadBytes_ = 0;
        busy_ = false;
        return false;
    }
    return true;
}

void WakeWatch::taskEntry(void* arg) {
    static_cast<WakeWatch*>(arg)->runSubmit();
    vTaskDelete(nullptr);
}

void WakeWatch::runSubmit() {
    const uint32_t t0 = millis();

    String url = String("https://") + KATANORI_WS_HOST + "/wake?rate=" + String(kRate);
    if (name_.length() > 0) {
        url += "&name=";
        // 呼び名はカタカナなので、そのままではURLに載らない。パーセント符号化する
        for (size_t i = 0; i < name_.length(); ++i) {
            const uint8_t c = (uint8_t)name_[i];
            if (isalnum(c)) {
                url += (char)c;
            } else {
                char hex[4];
                snprintf(hex, sizeof(hex), "%%%02X", c);
                url += hex;
            }
        }
    }

    WiFiClientSecure client;
    client.setCACert(KATANORI_ROOT_CA_PEM);
    HTTPClient http;
    http.setTimeout(10000);
    if (http.begin(client, url)) {
        http.addHeader("Content-Type", "application/octet-stream");
        const int code = http.POST(payload_, payloadBytes_);
        if (code == 200) {
            const String body = http.getString();
            // 小さなJSONなのでパーサは積まない。必要なのは2つだけ
            woke_ = body.indexOf("\"wake\":true") >= 0;
            const int ts = body.indexOf("\"text\":\"");
            if (ts >= 0) {
                const int te = body.indexOf('"', ts + 8);
                if (te > ts) {
                    text_ = body.substring(ts + 8, te);
                }
            }
            // 「言葉ではない確率」。雑音を呼び名と読み違えていないか見るため
            const int ns = body.indexOf("\"no_speech\":");
            if (ns >= 0) {
                int e = ns + 12;
                while (e < (int)body.length() && body[e] != ',' && body[e] != '}') {
                    ++e;
                }
                noSpeech_ = body.substring(ns + 12, e);
            }
            if (text_.length() == 0) {
                // 空で返ったときだけ中身を出す。音声が届いていないのか、
                // 届いたが言葉として拾えなかったのかを分ける
                Serial.printf("[WAKE] 空でした: %s\n", body.c_str());
            }
        } else {
            Serial.printf("[WAKE] 送信に失敗しました (HTTP %d)\n", code);
        }
        http.end();
    } else {
        Serial.println("[WAKE] 接続を開始できませんでした");
    }

    free(payload_);
    payload_ = nullptr;
    payloadBytes_ = 0;
    lastMs_ = millis() - t0;
    done_ = true;
    busy_ = false;
}

bool WakeWatch::takeResult(bool& woke, String& text) {
    if (!done_) {
        return false;
    }
    done_ = false;
    woke = woke_;
    text = text_;
    return true;
}

} // namespace katanori
