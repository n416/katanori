#include "WakeWatch.h"

#include "NetLink.h"

namespace katanori {

WakeWatch wakeWatch;

/** マイクのレート。ReSpeaker Lite から来るのは 16kHz 固定。 */
static constexpr uint32_t kRate = 16000;

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

} // namespace katanori
