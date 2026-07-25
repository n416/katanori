#ifndef KATANORI_ROBOT_DSP_H
#define KATANORI_ROBOT_DSP_H

#include <cstdint>
#include <cstddef>

namespace katanori {

class RobotDsp {
public:
    // デフォルト24000Hz (Gemini Multimodal Live APIの標準レート)
    explicit RobotDsp(int sampleRate = 24000);
    ~RobotDsp();

    // 処理パラメータの更新
    void setParameters(float pitchRatio, float combFeedback, float windowSizeMs);

    // in と out は同じバッファ（In-place処理）でも別バッファでも可
    void process(const int16_t* in, int16_t* out, size_t numSamples);

private:
    int sampleRate_;
    float pitchRatio_;
    float combFeedback_;
    float windowSizeMs_;

    float phase_;
    int maxDelaySamples_;
    int combDelaySamples_;

    // メモリを圧迫しないよう、最低限のリングバッファサイズ
    // 24kHzで 4096 = 約170ms。WindowSizeの最大値(100ms)もカバー可能。
    static constexpr size_t DELAY_BUF_SIZE = 4096;
    float* delayBuf_;
    size_t wrIdx_;

    // コムフィルターのフィードバック用（3ms = 72 @ 24kHz）
    static constexpr size_t OUT_BUF_SIZE = 512;
    float* outBuf_;
    size_t outIdx_;
};

} // namespace katanori

#endif // KATANORI_ROBOT_DSP_H
