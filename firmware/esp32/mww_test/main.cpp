// 呼び名の聞き分け（microWakeWord）を Arduino で動かす試験。本体のファームとは別に組む。
//   pio run -e mww_test -t upload   … 焼き込んだ録音を流す（PC の predict_clip と突き合わせる）
//   pio run -e mww_live -t upload   … マイクの入れ方を 4 通り並べて同時に聞き分けにかけて比べる
//
// 前処理の設定と int8 への変換は ESPHome の micro_wake_word（preprocessor_settings.h と
// micro_wake_word.cpp の generate_features_）に合わせる。学習側の特徴量と同じでないと当たらない。
// 2026-09-22: 録音 5 つで PC と突き合わせ、4 つが 0.01 以内で一致した。

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
#include "okay_nabu_model.h"

#ifdef MWW_LIVE
#include <driver/i2s.h>
#else
#include "test_clips.h"
#endif

namespace {

constexpr int kSampleRate = 16000;
constexpr int kFeatureSize = 40;             // PREPROCESSOR_FEATURE_SIZE
constexpr int kFeatureDurationMs = 30;       // FEATURE_DURATION_MS
constexpr int kFeatureStepMs = 10;           // katanori.json の feature_step_size
constexpr size_t kTensorArenaSize = 30000;   // katanori.json の tensor_arena_size
constexpr size_t kVariableArenaSize = 1024;  // ESPHome の STREAMING_MODEL_VARIABLE_ARENA_SIZE
constexpr int kWindow = 5;                   // katanori.json の sliding_window_size
constexpr float kCutoff = 0.9f;              // katanori.json の probability_cutoff

tflite::MicroMutableOpResolver<20> gResolver;

void setupResolver() {
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
}

// 前処理 1 つとモデル 1 つの組。ch0 と ch1 を同時に比べるため 2 つ持てるようにする
struct Detector {
  const uint8_t* modelData = kKatanoriModel;
  FrontendConfig cfg{};
  FrontendState fs{};
  tflite::MicroInterpreter* interp = nullptr;
  int filled = 0;
  uint8_t win[kWindow] = {0};
  int wi = 0, n = 0;

  bool begin() {
    cfg.window.size_ms = kFeatureDurationMs;
    cfg.window.step_size_ms = kFeatureStepMs;
    cfg.filterbank.num_channels = kFeatureSize;
    cfg.filterbank.lower_band_limit = 125.0f;
    cfg.filterbank.upper_band_limit = 7500.0f;
    cfg.noise_reduction.smoothing_bits = 10;
    cfg.noise_reduction.even_smoothing = 0.025f;
    cfg.noise_reduction.odd_smoothing = 0.06f;
    cfg.noise_reduction.min_signal_remaining = 0.05f;
    cfg.pcan_gain_control.enable_pcan = 1;
    cfg.pcan_gain_control.strength = 0.95f;
    cfg.pcan_gain_control.offset = 80.0f;
    cfg.pcan_gain_control.gain_bits = 21;
    cfg.log_scale.enable_log = 1;
    cfg.log_scale.scale_shift = 6;
    if (!FrontendPopulateState(&cfg, &fs, kSampleRate)) {
      Serial.println("[mww] 前処理の初期化に失敗");
      return false;
    }
    const tflite::Model* model = tflite::GetModel(modelData);
    if (model->version() != TFLITE_SCHEMA_VERSION) {
      Serial.printf("[mww] モデルの版が違う: %lu\n", (unsigned long)model->version());
      return false;
    }
    auto* arena = (uint8_t*)heap_caps_aligned_alloc(16, kTensorArenaSize, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    auto* varArena = (uint8_t*)heap_caps_aligned_alloc(16, kVariableArenaSize, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    if (!arena || !varArena) {
      Serial.println("[mww] arena を取れない");
      return false;
    }
    auto* varAlloc = tflite::MicroAllocator::Create(varArena, kVariableArenaSize);
    auto* vars = tflite::MicroResourceVariables::Create(varAlloc, 20);
    interp = new tflite::MicroInterpreter(model, gResolver, arena, kTensorArenaSize, vars);
    if (interp->AllocateTensors() != kTfLiteOk) {
      Serial.println("[mww] AllocateTensors に失敗");
      return false;
    }
    return true;
  }

  void reset() {
    FrontendReset(&fs);
    interp->Reset();
    filled = wi = n = 0;
    memset(win, 0, sizeof(win));
  }

  // 音を流す。推論が回るたびに onProb(1 回の確からしさ, 直近 5 回の平均) を呼ぶ
  template <typename F>
  void feed(const int16_t* p, size_t left, F onProb) {
    TfLiteTensor* in = interp->input(0);
    const int stride = in->dims->data[1];  // katanori は 3 列ずつ食う
    while (left > 0) {
      size_t used = 0;
      FrontendOutput fo = FrontendProcessSamples(&fs, p, left, &used);
      p += used;
      left -= used;
      if (fo.size == 0) {
        if (used == 0) break;
        continue;
      }
      // ESPHome の generate_features_ と同じ変換（25.6 × 26.0 = 666 で割って -128）
      int8_t* dst = in->data.int8 + filled * kFeatureSize;
      for (size_t i = 0; i < fo.size; i++) {
        int32_t v = ((int32_t)fo.values[i] * 256 + 333) / 666 + INT8_MIN;
        dst[i] = (int8_t)constrain(v, INT8_MIN, INT8_MAX);
      }
      if (++filled < stride) continue;
      filled = 0;
      if (interp->Invoke() != kTfLiteOk) return;
      const uint8_t prob = interp->output(0)->data.uint8[0];
      win[wi] = prob;
      wi = (wi + 1) % kWindow;
      int sum = 0;
      for (uint8_t v : win) sum += v;
      const float avg = ++n >= kWindow ? sum / (float)kWindow / 255.0f : 0.0f;
      onProb(prob / 255.0f, avg);
    }
  }
};

#ifndef MWW_LIVE
// ---------------------------------------------------------------------------
// 焼き込んだ録音を流す。PC の predict_clip と同じ条件にするため、録音ごとに状態を
// 初期化し、無音を足さずに頭から流す（前の録音の状態を引きずると数字がずれた）
// ---------------------------------------------------------------------------
Detector gDet;

void runClip(const TestClip& c) {
  gDet.reset();
  float maxProb = 0, maxAvg = 0;
  gDet.feed(c.data, c.len, [&](float p, float a) {
    maxProb = max(maxProb, p);
    maxAvg = max(maxAvg, a);
  });
  Serial.printf("[mww] %-20s %.2f秒  最大 %.3f  5回平均の最大 %.3f  %s\n", c.name, c.len / 16000.0f,
                maxProb, maxAvg, maxAvg > kCutoff ? "起きる" : "起きない");
}

#else
// ---------------------------------------------------------------------------
// マイクを聞く。I2S の設定は本体の AudioIo と同じ（48kHz 版の XMOS・スレーブ・
// 32bit スロット）。3 サンプルの平均で 16kHz に落とす。
//
// 入れ方を 4 通り並べて同時に聞き分けにかける（2026-09-22）。1 回目の試しでは
// ch0×16 も ch1×1 も当たりが半分以下で、ch1 は話しても RMS 5〜25 しか無かった。
//   - 倍率は 32bit のまま掛けてから 16bit に落とす（下位のビットを捨てない）
//   - ch1×4 は ESPHome の ReSpeaker Lite 用設定（formatBCE の yaml: channels 1・gain_factor 4）
// ---------------------------------------------------------------------------
constexpr i2s_port_t kPort = I2S_NUM_0;
constexpr int kRatio = 3;  // 48kHz → 16kHz
constexpr size_t kFrames = 512 * kRatio;

struct Input {
  const char* name;
  int ch;     // I2S の何番目のスロットか
  int shift;  // 32bit 値を右へずらす量。16 で素通し、14 で 4 倍、12 で 16 倍
  const uint8_t* model;
  float cutoff;
};
// 2 回目（2026-09-22）: 既製の Okay Nabu を同じ聞き方で載せ、機体の聞き方が正しいかを切り分ける。
// 1 回目の結果（カタノリ・8 回）では ch0x4 が一番ましで、ch1 は音が小さすぎた
constexpr Input kInputs[] = {
    {"nabu_ch0x4", 0, 14, kOkayNabuModel, 0.97f},
    {"nabu_ch1x4", 1, 14, kOkayNabuModel, 0.97f},  // ESPHome の ReSpeaker Lite 用設定と同じ
    {"nabu_ch0x16", 0, 12, kOkayNabuModel, 0.97f},
    {"kata_ch0x4", 0, 14, kKatanoriModel, 0.9f},
};
constexpr int kN = sizeof(kInputs) / sizeof(kInputs[0]);

Detector gDet[kN];
int32_t gRaw[kFrames * 2];
int16_t gMono[kN][kFrames / kRatio];
int64_t gAcc[2] = {0, 0};
int gAccN = 0;

double gSq[kN] = {0};
uint32_t gClip[kN] = {0};
uint32_t gSqN = 0;
uint32_t gLastReport = 0;
// 呼びかけ 1 回ぶんの山（どれかの平均が 0.3 を越えてから、全部 0.1 を割って 0.3 秒たつまで）
bool gInEvent = false;
float gEvMax[kN] = {0};
uint32_t gEvStart = 0, gEvQuietSince = 0;
int gEvCount = 0;

bool setupI2s() {
  i2s_config_t cfg = {};
  cfg.mode = (i2s_mode_t)(I2S_MODE_SLAVE | I2S_MODE_TX | I2S_MODE_RX);
  cfg.sample_rate = 48000;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT;
  cfg.channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT;
  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count = 4 * kRatio;
  cfg.dma_buf_len = 256;
  cfg.tx_desc_auto_clear = true;
  if (i2s_driver_install(kPort, &cfg, 0, nullptr) != ESP_OK) return false;
  i2s_pin_config_t pins = {};
  pins.mck_io_num = I2S_PIN_NO_CHANGE;
  pins.bck_io_num = 8;
  pins.ws_io_num = 7;
  pins.data_out_num = 43;
  pins.data_in_num = 44;
  if (i2s_set_pin(kPort, &pins) != ESP_OK) return false;
  i2s_zero_dma_buffer(kPort);
  return true;
}

void pumpMic() {
  size_t bytes = 0;
  if (i2s_read(kPort, gRaw, sizeof(gRaw), &bytes, pdMS_TO_TICKS(50)) != ESP_OK) return;
  const size_t frames = bytes / (sizeof(int32_t) * 2);
  size_t produced = 0;
  for (size_t i = 0; i < frames; i++) {
    gAcc[0] += gRaw[i * 2];
    gAcc[1] += gRaw[i * 2 + 1];
    if (++gAccN < kRatio) continue;
    for (int k = 0; k < kN; k++) {
      int64_t v = (gAcc[kInputs[k].ch] / kRatio) >> kInputs[k].shift;
      if (v > 32767 || v < -32768) gClip[k]++;
      const int16_t s = (int16_t)constrain(v, (int64_t)-32768, (int64_t)32767);
      gMono[k][produced] = s;
      gSq[k] += (double)s * s;
    }
    gAcc[0] = gAcc[1] = 0;
    gAccN = 0;
    produced++;
  }
  gSqN += produced;
  float cur[kN] = {0};
  for (int k = 0; k < kN; k++) {
    gDet[k].feed(gMono[k], produced, [&](float, float a) {
      cur[k] = max(cur[k], a);
      if (gInEvent) gEvMax[k] = max(gEvMax[k], a);
    });
  }
  const uint32_t now = millis();
  float hi = 0;
  for (int k = 0; k < kN; k++) hi = max(hi, cur[k]);
  if (!gInEvent && hi > 0.3f) {
    gInEvent = true;
    gEvStart = now;
    gEvQuietSince = 0;
    for (int k = 0; k < kN; k++) gEvMax[k] = cur[k];
  } else if (gInEvent) {
    if (hi >= 0.1f) {
      gEvQuietSince = 0;
    } else if (gEvQuietSince == 0) {
      gEvQuietSince = now;
    } else if (now - gEvQuietSince > 300) {
      gInEvent = false;
      gEvCount++;
      Serial.printf("[呼] %2d 回目", gEvCount);
      for (int k = 0; k < kN; k++) {
        Serial.printf("  %s %.3f%s", kInputs[k].name, gEvMax[k], gEvMax[k] > kInputs[k].cutoff ? "★" : "  ");
      }
      Serial.println();
    }
  }
  if (now - gLastReport >= 5000) {
    gLastReport = now;
    Serial.print("[耳] RMS");
    for (int k = 0; k < kN; k++) {
      Serial.printf("  %s %5.0f(振切%lu)", kInputs[k].name, gSqN ? sqrt(gSq[k] / gSqN) : 0.0,
                    (unsigned long)gClip[k]);
      gSq[k] = 0;
      gClip[k] = 0;
    }
    Serial.println();
    gSqN = 0;
  }
}
#endif

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(1500);
  setupResolver();
#ifndef MWW_LIVE
  Serial.println("[mww] 焼き込んだ録音を流す試験");
  if (!gDet.begin()) return;
  Serial.printf("[mww] arena 使用 %u / %u バイト\n", (unsigned)gDet.interp->arena_used_bytes(),
                (unsigned)kTensorArenaSize);
#else
  Serial.println("[mww] マイクの ch0 と ch1 を同時に聞く試験");
  for (int k = 0; k < kN; k++) {
    gDet[k].modelData = kInputs[k].model;
    if (!gDet[k].begin()) return;
  }
  if (!setupI2s()) {
    Serial.println("[mww] I2S の初期化に失敗");
    return;
  }
  Serial.printf("[mww] 空きヒープ 内部 %u\n", (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL));
#endif
}

void loop() {
#ifndef MWW_LIVE
  // 書き込み直後の出力を取りこぼしても読めるよう、5 秒ごとに繰り返す
  delay(5000);
  if (!gDet.interp) return;
  for (const TestClip& c : kClips) runClip(c);
#else
  if (gDet[kN - 1].interp) pumpMic();
#endif
}
