"""microWakeWord の predict_clip と同じ計算で WAV を推論する。
  python pcinfer.py <model.tflite> <wav>... [--timeline]
"""
import sys
import numpy as np
import soundfile as sf
import tensorflow as tf
from pymicro_features import MicroFrontend


def features(pcm: np.ndarray) -> np.ndarray:
    b = pcm.astype(np.int16).tobytes()
    fe = MicroFrontend()
    out, i = [], 0
    while i + 160 * 2 < len(b):
        r = fe.process_samples(b[i:i + 320])
        i += r.samples_read * 2
        if r.features:
            out.append(r.features)
    return np.array(out, dtype=np.float32)


def predict(model_path: str, pcm: np.ndarray) -> np.ndarray:
    it = tf.lite.Interpreter(model_path=model_path)
    it.allocate_tensors()
    ind, outd = it.get_input_details()[0], it.get_output_details()[0]
    stride = ind["shape"][1]
    sc, zp = ind["quantization"]
    osc, ozp = outd["quantization"]
    spec = features(pcm)  # pymicro_features は既に 1/25.6 倍した値を返す
    probs = []
    for last in range(stride, len(spec) + 1, stride):
        chunk = spec[last - stride:last]
        q = np.clip(np.round(chunk / sc + zp), -128, 127).astype(np.int8)
        it.set_tensor(ind["index"], q.reshape(ind["shape"]))
        it.invoke()
        o = it.get_tensor(outd["index"])[0][0]
        probs.append((float(o) - ozp) * osc)
    return np.array(probs)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    timeline = "--timeline" in sys.argv
    model = args[0]
    for w in args[1:]:
        pcm, sr = sf.read(w, dtype="int16")
        assert sr == 16000, sr
        p = predict(model, pcm)
        avg = np.convolve(p, np.ones(5) / 5, mode="valid") if len(p) >= 5 else np.zeros(1)
        print(f"{w.split('/')[-1].split(chr(92))[-1]:28s} 長さ {len(pcm)/16000:5.2f}秒  最大 {p.max():.3f}  5回平均の最大 {avg.max():.3f}")
        if timeline:
            # 0.3 を越えた山を時刻つきで出す（1 回の推論 = 30ms）
            above = avg > 0.3
            k = 0
            while k < len(avg):
                if above[k]:
                    j = k
                    while j < len(avg) and above[j]:
                        j += 1
                    print(f"    {k * 0.03:6.2f}〜{j * 0.03:6.2f}秒  山 {avg[k:j].max():.3f}")
                    k = j
                else:
                    k += 1


if __name__ == "__main__":
    main()
