"""48kHz の取り出しから 2 通りの 16kHz を作り、同じモデルにかけて並べる。
  python compare48.py <48kHz の wav> <model>...
  平均3 : 機体と同じ「3 サンプルの平均」
  正しく: scipy の resample_poly（折り返しを落とす低域通過つき）
"""
import sys
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
import pcinfer

wav, models = sys.argv[1], sys.argv[2:]
x, sr = sf.read(wav, dtype='int16')
assert sr == 48000
x = x.astype(np.int32)
n = len(x) // 3 * 3
avg3 = (x[:n].reshape(-1, 3).sum(axis=1) // 3).astype(np.int16)
good = np.clip(np.round(resample_poly(x.astype(np.float64), 1, 3)), -32768, 32767).astype(np.int16)
for m in models:
    print('==', m.split('/')[-1])
    for name, pcm in (('平均3', avg3), ('正しく', good)):
        p = pcinfer.predict(m, pcm)
        avg = np.convolve(p, np.ones(5) / 5, mode='valid')
        peaks, k = [], 0
        while k < len(avg):
            if avg[k] > 0.3:
                j = k
                while j < len(avg) and avg[j] > 0.3:
                    j += 1
                peaks.append(f'{k * 0.03:5.1f}秒 {avg[k:j].max():.3f}')
                k = j
            else:
                k += 1
        print(f'  {name}: ' + ' / '.join(peaks))
