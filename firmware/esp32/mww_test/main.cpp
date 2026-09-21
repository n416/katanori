// 呼び名の聞き分け（microWakeWord）を Arduino で動かす試験。本体のファームとは別に組む。
//   pio run -e mww_test
//
// 1 段目: katanori.tflite を読み、特徴量 → 推論が 1 周まわるか・時間と arena の量を見る。
// 前処理の設定と int8 への変換は ESPHome の micro_wake_word（preprocessor_settings.h と
// micro_wake_word.cpp の generate_features_）に合わせる。学習側の特徴量と同じでないと当たらない。

#include <Arduino.h>
#include <esp_heap_caps.h>

#include "frontend.h"
#include "frontend_util.h"
#include "tensorflow/lite/micro/micro_allocator.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/micro_resource_variable.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include "katanori_model.h"
#include "test_clips.h"

namespace {

constexpr int kSampleRate = 16000;
constexpr int kFeatureSize = 40;          // PREPROCESSOR_FEATURE_SIZE
constexpr int kFeatureDurationMs = 30;    // FEATURE_DURATION_MS
constexpr int kFeatureStepMs = 10;        // katanori.json の feature_step_size
constexpr size_t kTensorArenaSize = 30000;  // katanori.json の tensor_arena_size
constexpr size_t kVariableArenaSize = 1024; // ESPHome の STREAMING_MODEL_VARIABLE_ARENA_SIZE

FrontendConfig gFrontendConfig;
FrontendState gFrontendState;

tflite::MicroMutableOpResolver<20> gResolver;
tflite::MicroInterpreter* gInterp = nullptr;
uint8_t* gTensorArena = nullptr;
uint8_t* gVarArena = nullptr;

bool setupFrontend() {
  gFrontendConfig.window.size_ms = kFeatureDurationMs;
  gFrontendConfig.window.step_size_ms = kFeatureStepMs;
  gFrontendConfig.filterbank.num_channels = kFeatureSize;
  gFrontendConfig.filterbank.lower_band_limit = 125.0f;
  gFrontendConfig.filterbank.upper_band_limit = 7500.0f;
  gFrontendConfig.noise_reduction.smoothing_bits = 10;
  gFrontendConfig.noise_reduction.even_smoothing = 0.025f;
  gFrontendConfig.noise_reduction.odd_smoothing = 0.06f;
  gFrontendConfig.noise_reduction.min_signal_remaining = 0.05f;
  gFrontendConfig.pcan_gain_control.enable_pcan = 1;
  gFrontendConfig.pcan_gain_control.strength = 0.95f;
  gFrontendConfig.pcan_gain_control.offset = 80.0f;
  gFrontendConfig.pcan_gain_control.gain_bits = 21;
  gFrontendConfig.log_scale.enable_log = 1;
  gFrontendConfig.log_scale.scale_shift = 6;
  return FrontendPopulateState(&gFrontendConfig, &gFrontendState, kSampleRate) != 0;
}

// ESPHome の generate_features_ と同じ変換（25.6 × 26.0 = 666 で割って -128）
void toInt8(const FrontendOutput& out, int8_t* dst) {
  constexpr int32_t kScale = 256, kDiv = 666;
  for (size_t i = 0; i < out.size; i++) {
    int32_t v = ((int32_t)out.values[i] * kScale + kDiv / 2) / kDiv + INT8_MIN;
    dst[i] = (int8_t)constrain(v, INT8_MIN, INT8_MAX);
  }
}

bool setupModel() {
  const tflite::Model* model = tflite::GetModel(kKatanoriModel);
  if (model->version() != TFLITE_SCHEMA_VERSION) {
    Serial.printf("[mww] モデルの版が違う: %lu\n", (unsigned long)model->version());
    return false;
  }
  // ESPHome の register_streaming_ops_ と同じ 20 種
  gResolver.AddCallOnce();
  gResolver.AddVarHandle();
  gResolver.AddReshape();
  gResolver.AddReadVariable();
  gResolver.AddStridedSlice();
  gResolver.AddConcatenation();
  gResolver.AddAssignVariable();
  gResolver.AddConv2D();
  gResolver.AddMul();
  gResolver.AddAdd();
  gResolver.AddMean();
  gResolver.AddFullyConnected();
  gResolver.AddLogistic();
  gResolver.AddQuantize();
  gResolver.AddDepthwiseConv2D();
  gResolver.AddAveragePool2D();
  gResolver.AddMaxPool2D();
  gResolver.AddPad();
  gResolver.AddPack();
  gResolver.AddSplitV();

  gTensorArena = (uint8_t*)heap_caps_aligned_alloc(16, kTensorArenaSize, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
  gVarArena = (uint8_t*)heap_caps_aligned_alloc(16, kVariableArenaSize, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
  if (!gTensorArena || !gVarArena) {
    Serial.println("[mww] arena を取れない");
    return false;
  }
  tflite::MicroAllocator* varAlloc = tflite::MicroAllocator::Create(gVarArena, kVariableArenaSize);
  tflite::MicroResourceVariables* vars = tflite::MicroResourceVariables::Create(varAlloc, 20);
  static tflite::MicroInterpreter interp(model, gResolver, gTensorArena, kTensorArenaSize, vars);
  gInterp = &interp;
  if (gInterp->AllocateTensors() != kTfLiteOk) {
    Serial.println("[mww] AllocateTensors に失敗");
    return false;
  }
  TfLiteTensor* in = gInterp->input(0);
  TfLiteTensor* out = gInterp->output(0);
  Serial.printf("[mww] 入力 型%d 形[%d,%d,%d] 出力 型%d 形[%d,%d] arena 使用 %u / %u バイト\n",
                in->type, in->dims->data[0], in->dims->data[1], in->dims->data[2],
                out->type, out->dims->data[0], out->dims->data[1],
                (unsigned)gInterp->arena_used_bytes(), (unsigned)kTensorArenaSize);
  return true;
}

// 1 秒ぶんの音（無音 → 440Hz）を流して、特徴量と推論の時間を測る
void runOnce() {
  static int16_t audio[kSampleRate];
  for (int i = 0; i < kSampleRate; i++) {
    audio[i] = (i < kSampleRate / 2) ? 0 : (int16_t)(3000 * sinf(2 * PI * 440 * i / kSampleRate));
  }
  TfLiteTensor* in = gInterp->input(0);
  const int stride = in->dims->data[1];  // 1 回に食わせる特徴量の列数（katanori は 3）
  int filled = 0, invokes = 0;
  uint32_t tFeat = 0, tInvoke = 0;
  uint8_t maxProb = 0;
  const int16_t* p = audio;
  size_t left = kSampleRate;
  while (left > 0) {
    size_t used = 0;
    uint32_t t0 = micros();
    FrontendOutput fo = FrontendProcessSamples(&gFrontendState, p, left, &used);
    tFeat += micros() - t0;
    p += used;
    left -= used;
    if (fo.size == 0) {
      if (used == 0) break;
      continue;
    }
    toInt8(fo, in->data.int8 + filled * kFeatureSize);
    if (++filled < stride) continue;
    filled = 0;
    t0 = micros();
    if (gInterp->Invoke() != kTfLiteOk) {
      Serial.println("[mww] Invoke に失敗");
      return;
    }
    tInvoke += micros() - t0;
    invokes++;
    uint8_t prob = gInterp->output(0)->data.uint8[0];
    if (prob > maxProb) maxProb = prob;
  }
  Serial.printf("[mww] 1 秒ぶん: 推論 %d 回・特徴量 %lu us・推論 %lu us（1 回 %lu us）・最大の確からしさ %u/255\n",
                invokes, (unsigned long)tFeat, (unsigned long)tInvoke,
                invokes ? (unsigned long)(tInvoke / invokes) : 0UL, maxProb);
}

// 録音を 1 つ流す。PC の predict_clip と同じ条件にするため、録音ごとに前処理とモデルの
// 内部状態を初期化し、無音を足さずに頭から流す（前の録音の状態を引きずると数字がずれた）。
// 判定は ESPHome と同じく直近 5 回の平均（sliding_window_size）がしきい値 0.9 を越えるか
void runClip(const TestClip& c) {
  FrontendReset(&gFrontendState);
  gInterp->Reset();
  TfLiteTensor* in = gInterp->input(0);
  const int stride = in->dims->data[1];
  uint8_t win[5] = {0};
  int wi = 0, filled = 0, n = 0;
  float maxProb = 0, maxAvg = 0;
  {
    const int16_t* p = c.data;
    size_t left = c.len;
    while (left > 0) {
      size_t used = 0;
      FrontendOutput fo = FrontendProcessSamples(&gFrontendState, p, left, &used);
      p += used;
      left -= used;
      if (fo.size == 0) {
        if (used == 0) break;
        continue;
      }
      toInt8(fo, in->data.int8 + filled * kFeatureSize);
      if (++filled < stride) continue;
      filled = 0;
      if (gInterp->Invoke() != kTfLiteOk) return;
      uint8_t prob = gInterp->output(0)->data.uint8[0];
      win[wi] = prob;
      wi = (wi + 1) % 5;
      maxProb = max(maxProb, prob / 255.0f);
      if (++n >= 5) {
        int sum = 0;
        for (uint8_t v : win) sum += v;
        maxAvg = max(maxAvg, sum / 5.0f / 255.0f);
      }
    }
  }
  Serial.printf("[mww] %-20s %.2f秒  最大 %.3f  5回平均の最大 %.3f  %s\n", c.name, c.len / 16000.0f,
                maxProb, maxAvg, maxAvg > 0.9f ? "起きる" : "起きない");
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.println("[mww] 呼び名の聞き分けの試験");
  if (!setupFrontend()) {
    Serial.println("[mww] 前処理の初期化に失敗");
    return;
  }
  if (!setupModel()) return;
  runOnce();
  Serial.printf("[mww] 空きヒープ 内部 %u / PSRAM %u\n",
                (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL),
                (unsigned)heap_caps_get_free_size(MALLOC_CAP_SPIRAM));
}

// 書き込み直後の出力を取りこぼしても読めるよう、5 秒ごとに繰り返す
void loop() {
  delay(5000);
  if (!gInterp) return;
  Serial.printf("[mww] arena 使用 %u / %u バイト\n", (unsigned)gInterp->arena_used_bytes(), (unsigned)kTensorArenaSize);
  runOnce();
  for (const TestClip& c : kClips) runClip(c);
}
