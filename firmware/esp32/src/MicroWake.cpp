#include "MicroWake.h"

#include <esp_heap_caps.h>

#include "frontend.h"
#include "frontend_util.h"
#include "tensorflow/lite/micro/micro_allocator.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/micro_resource_variable.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include "WakeModel.h"
#include "Console.h" // 最後に置く（Serial を Wi-Fi モニタへも流す差し替え。Console.h）

namespace katanori {

MicroWake microWake;

namespace {

// ESPHome の preprocessor_settings.h と同じ値。学習側の特徴量と揃っていないと当たらない
constexpr int kSampleRate = 16000;
constexpr int kFeatureSize = 40;
constexpr int kFeatureDurationMs = 30;
constexpr size_t kVariableArenaSize = 1024;  // ESPHome の STREAMING_MODEL_VARIABLE_ARENA_SIZE

FrontendConfig frontendCfg;
FrontendState frontend;
tflite::MicroMutableOpResolver<20> resolver;
tflite::MicroInterpreter* interp = nullptr;
int filled = 0;
uint8_t win[kWakeWindow] = {0};
int winPos = 0;
int winCount = 0;

void setupFrontendConfig() {
    frontendCfg.window.size_ms = kFeatureDurationMs;
    frontendCfg.window.step_size_ms = kWakeFeatureStepMs;
    frontendCfg.filterbank.num_channels = kFeatureSize;
    frontendCfg.filterbank.lower_band_limit = 125.0f;
    frontendCfg.filterbank.upper_band_limit = 7500.0f;
    frontendCfg.noise_reduction.smoothing_bits = 10;
    frontendCfg.noise_reduction.even_smoothing = 0.025f;
    frontendCfg.noise_reduction.odd_smoothing = 0.06f;
    frontendCfg.noise_reduction.min_signal_remaining = 0.05f;
    frontendCfg.pcan_gain_control.enable_pcan = 1;
    frontendCfg.pcan_gain_control.strength = 0.95f;
    frontendCfg.pcan_gain_control.offset = 80.0f;
    frontendCfg.pcan_gain_control.gain_bits = 21;
    frontendCfg.log_scale.enable_log = 1;
    frontendCfg.log_scale.scale_shift = 6;
}

void setupResolver() {
    // ESPHome の register_streaming_ops_ と同じ 20 種
    resolver.AddCallOnce();
    resolver.AddVarHandle();
    resolver.AddReshape();
    resolver.AddReadVariable();
    resolver.AddStridedSlice();
    resolver.AddConcatenation();
    resolver.AddAssignVariable();
    resolver.AddConv2D();
    resolver.AddMul();
    resolver.AddAdd();
    resolver.AddMean();
    resolver.AddFullyConnected();
    resolver.AddLogistic();
    resolver.AddQuantize();
    resolver.AddDepthwiseConv2D();
    resolver.AddAveragePool2D();
    resolver.AddMaxPool2D();
    resolver.AddPad();
    resolver.AddPack();
    resolver.AddSplitV();
}

} // namespace

bool MicroWake::begin() {
    if (ready_) {
        return true;
    }
    setupFrontendConfig();
    if (!FrontendPopulateState(&frontendCfg, &frontend, kSampleRate)) {
        Serial.println("[MWW] 前処理の初期化に失敗しました");
        return false;
    }
    const tflite::Model* model = tflite::GetModel(kWakeModel);
    if (model->version() != TFLITE_SCHEMA_VERSION) {
        Serial.printf("[MWW] モデルの版が違います: %lu\n", (unsigned long)model->version());
        return false;
    }
    // 推論は内部 RAM で回す（PSRAM に置くと遅い）
    auto* arena = (uint8_t*)heap_caps_aligned_alloc(16, kWakeArenaSize, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    auto* varArena = (uint8_t*)heap_caps_aligned_alloc(16, kVariableArenaSize, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    if (!arena || !varArena) {
        Serial.println("[MWW] 内部 RAM が足りません");
        return false;
    }
    setupResolver();
    auto* varAlloc = tflite::MicroAllocator::Create(varArena, kVariableArenaSize);
    auto* vars = tflite::MicroResourceVariables::Create(varAlloc, 20);
    interp = new tflite::MicroInterpreter(model, resolver, arena, kWakeArenaSize, vars);
    if (interp->AllocateTensors() != kTfLiteOk) {
        Serial.println("[MWW] AllocateTensors に失敗しました");
        return false;
    }
    Serial.printf("[MWW] 呼び名の聞き分けを用意しました（arena %u / %u バイト・しきい値 %.2f）\n",
                  (unsigned)interp->arena_used_bytes(), (unsigned)kWakeArenaSize, kWakeCutoff);
    ready_ = true;
    return true;
}

void MicroWake::reset() {
    if (!ready_) {
        return;
    }
    FrontendReset(&frontend);
    interp->Reset();
    filled = 0;
    winPos = 0;
    winCount = 0;
    memset(win, 0, sizeof(win));
    peak_ = 0.0f;
}

bool MicroWake::feed(const int16_t* pcm, size_t n) {
    if (!ready_) {
        return false;
    }
    TfLiteTensor* in = interp->input(0);
    const int stride = in->dims->data[1];  // 1 回に食わせる特徴量の列数（katanori は 3）
    bool woke = false;
    while (n > 0) {
        size_t used = 0;
        FrontendOutput fo = FrontendProcessSamples(&frontend, pcm, n, &used);
        pcm += used;
        n -= used;
        if (fo.size == 0) {
            if (used == 0) {
                break;
            }
            continue;
        }
        // ESPHome の generate_features_ と同じ変換（25.6 × 26.0 = 666 で割って -128）
        int8_t* dst = in->data.int8 + filled * kFeatureSize;
        for (size_t i = 0; i < fo.size; ++i) {
            const int32_t v = ((int32_t)fo.values[i] * 256 + 333) / 666 + INT8_MIN;
            dst[i] = (int8_t)constrain(v, INT8_MIN, INT8_MAX);
        }
        if (++filled < stride) {
            continue;
        }
        filled = 0;
        const uint32_t t0 = micros();
        if (interp->Invoke() != kTfLiteOk) {
            return false;
        }
        invokeUs_ += micros() - t0;
        ++invokes_;
        win[winPos] = interp->output(0)->data.uint8[0];
        winPos = (winPos + 1) % kWakeWindow;
        if (++winCount < kWakeWindow) {
            continue;
        }
        int sum = 0;
        for (uint8_t v : win) {
            sum += v;
        }
        const float avg = sum / (float)kWakeWindow / 255.0f;
        if (avg > peak_) {
            peak_ = avg;
        }
        if (avg > kWakeCutoff) {
            woke = true;
        }
    }
    return woke;
}

} // namespace katanori
