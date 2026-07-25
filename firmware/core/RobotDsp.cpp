#include "RobotDsp.h"
#include <cmath>

namespace katanori {

RobotDsp::RobotDsp(int sampleRate)
    : sampleRate_(sampleRate)
    , pitchRatio_(1.10f)
    , combFeedback_(0.75f)
    , windowSizeMs_(44.0f)
    , phase_(0.0f)
    , maxDelaySamples_(0)
    , combDelaySamples_(0)
    , wrIdx_(0)
    , outIdx_(0)
{
    delayBuf_ = new float[DELAY_BUF_SIZE]();
    outBuf_ = new float[OUT_BUF_SIZE]();

    setParameters(pitchRatio_, combFeedback_, windowSizeMs_);
}

RobotDsp::~RobotDsp() {
    delete[] delayBuf_;
    delete[] outBuf_;
}

void RobotDsp::setParameters(float pitchRatio, float combFeedback, float windowSizeMs) {
    pitchRatio_ = pitchRatio;
    combFeedback_ = combFeedback;
    windowSizeMs_ = windowSizeMs;

    combDelaySamples_ = static_cast<int>(sampleRate_ * 0.003f); // 3ms
    if (combDelaySamples_ >= static_cast<int>(OUT_BUF_SIZE)) {
        combDelaySamples_ = OUT_BUF_SIZE - 1;
    }

    maxDelaySamples_ = static_cast<int>(sampleRate_ * (windowSizeMs_ / 1000.0f));
    if (maxDelaySamples_ < 10) {
        maxDelaySamples_ = 10;
    }
    if (maxDelaySamples_ >= static_cast<int>(DELAY_BUF_SIZE)) {
        maxDelaySamples_ = DELAY_BUF_SIZE - 1;
    }
}

void RobotDsp::process(const int16_t* in, int16_t* out, size_t numSamples) {
    if (!in || !out || numSamples == 0) return;

    float phaseInc = 0.0f;
    if (pitchRatio_ != 1.0f) {
        phaseInc = (1.0f - pitchRatio_) / static_cast<float>(maxDelaySamples_);
    }

    for (size_t i = 0; i < numSamples; ++i) {
        // リングバッファへ書き込み
        delayBuf_[wrIdx_] = static_cast<float>(in[i]);

        // LFO更新
        phase_ += phaseInc;
        if (phase_ >= 1.0f) {
            phase_ -= 1.0f;
        } else if (phase_ < 0.0f) {
            phase_ += 1.0f;
        }

        // 2つの位相 (180度反転)
        float phase1 = phase_;
        float phase2 = phase_ + 0.5f;
        if (phase2 >= 1.0f) {
            phase2 -= 1.0f;
        }

        float d1 = phase1 * static_cast<float>(maxDelaySamples_);
        float d2 = phase2 * static_cast<float>(maxDelaySamples_);

        // 三角窓
        float w1 = 1.0f - std::abs(2.0f * phase1 - 1.0f);
        float w2 = 1.0f - std::abs(2.0f * phase2 - 1.0f);

        // ポインタ1読み出し (線形補間)
        float rd1 = static_cast<float>(wrIdx_) - d1;
        if (rd1 < 0.0f) rd1 += static_cast<float>(DELAY_BUF_SIZE);
        int idx1_0 = static_cast<int>(rd1);
        int idx1_1 = (idx1_0 + 1) % DELAY_BUF_SIZE;
        float frac1 = rd1 - static_cast<float>(idx1_0);
        float s1 = delayBuf_[idx1_0] + frac1 * (delayBuf_[idx1_1] - delayBuf_[idx1_0]);

        // ポインタ2読み出し (線形補間)
        float rd2 = static_cast<float>(wrIdx_) - d2;
        if (rd2 < 0.0f) rd2 += static_cast<float>(DELAY_BUF_SIZE);
        int idx2_0 = static_cast<int>(rd2);
        int idx2_1 = (idx2_0 + 1) % DELAY_BUF_SIZE;
        float frac2 = rd2 - static_cast<float>(idx2_0);
        float s2 = delayBuf_[idx2_0] + frac2 * (delayBuf_[idx2_1] - delayBuf_[idx2_0]);

        // クロスフェード
        float val = s1 * w1 + s2 * w2;

        // コムフィルター (ショートディレイでメタリック共鳴を付加)
        int prevOutIdx = (outIdx_ - combDelaySamples_ + OUT_BUF_SIZE) % OUT_BUF_SIZE;
        val += outBuf_[prevOutIdx] * combFeedback_;

        // クリッピングガード
        if (val > 32767.0f) val = 32767.0f;
        else if (val < -32768.0f) val = -32768.0f;

        // フィードバックバッファへ保存
        outBuf_[outIdx_] = val;
        outIdx_ = (outIdx_ + 1) % OUT_BUF_SIZE;

        out[i] = static_cast<int16_t>(val);
        wrIdx_ = (wrIdx_ + 1) % DELAY_BUF_SIZE;
    }
}

} // namespace katanori
