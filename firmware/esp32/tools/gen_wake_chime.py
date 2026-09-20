# -*- coding: utf-8 -*-
"""呼びかけに気づいた合図の音を作る（木を2回叩いた音）。

    python firmware/esp32/tools/gen_wake_chime.py > firmware/esp32/src/Chimes.h
    python firmware/esp32/tools/gen_wake_chime.py --wav out.wav   （聞いて確かめる）

🔴 正弦波を足して作ってはいけない。電子音になる（2026-09-21 にユーザーへ聞かせて
「電子音ですねこれは」と却下された）。打撃音は「広帯域のインパルスが共振モードで
色付けされたもの」なので、**短いノイズを共振器（2次のバンドパス）へ通す**。

木の板のモードは整数比に乗らない（非調和）。整数比にすると楽器の音になり、
木を叩いた音に聞こえない。外部ライブラリは使わない。
"""
import math
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', newline='\n')

RATE = 16000

# (周波数[Hz], 減衰の時定数[ms], 重み)
# 自由な木片のモード比に近い非調和な並び。高い成分ほど速く消す
MODES = [
    (392.0, 55.0, 1.00),
    (721.0, 30.0, 0.62),
    (1544.0, 18.0, 0.45),
    (2310.0, 10.0, 0.26),
    (3670.0, 6.0, 0.14),
]

NOISE_MS = 4.0       # 叩いた瞬間の励起。これが音色の元になる
RAW_NOISE = 0.10     # フィルタを通さない生のノイズ。爪が当たる感じ
HIT_GAP_MS = 150.0   # 2打の間隔
SECOND_HIT = 0.82    # 2打目の強さ。同じだと機械的になる
PEAK = 10000         # 約 -10dBFS。合図なので控えめに


class Rnd:
    """線形合同法。毎回同じ音にしたいので固定種。"""

    def __init__(self, seed):
        self.s = seed

    def next(self):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return (self.s / 0x3FFFFFFF) - 1.0


def resonate(exc, freq, tau_ms):
    """2次共振器。インパルス応答が「その周波数で鳴って減衰する」形になる。

    r は1サンプルあたりの減衰、w は角周波数。
    y[n] = x[n] + 2r cos(w) y[n-1] - r^2 y[n-2]
    """
    w = 2.0 * math.pi * freq / RATE
    r = math.exp(-1.0 / (RATE * tau_ms / 1000.0))
    a1 = 2.0 * r * math.cos(w)
    a2 = -(r * r)
    y1 = y2 = 0.0
    out = [0.0] * len(exc)
    for i, x in enumerate(exc):
        y = x + a1 * y1 + a2 * y2
        out[i] = y
        y2, y1 = y1, y
    # 共振の鋭さで振幅が変わるので、鳴り方を揃えるために正規化
    peak = max(abs(v) for v in out) or 1.0
    return [v / peak for v in out]


def one_hit(scale, seed):
    n = int(RATE * (max(m[1] for m in MODES) * 5) / 1000)
    rnd = Rnd(seed)

    # 励起。4ms のノイズバースト。頭を少しなだらかにして段差を作らない
    exc = [0.0] * n
    nb = int(RATE * NOISE_MS / 1000)
    for i in range(nb):
        t = i / nb
        exc[i] = rnd.next() * (1.0 - t) * min(1.0, i / 8.0)

    out = [0.0] * n
    for (freq, tau, wgt) in MODES:
        band = resonate(exc, freq, tau)
        for i in range(n):
            out[i] += wgt * band[i]
    # 生のノイズを少しだけ重ねる（当たった瞬間の質感）
    for i in range(nb):
        out[i] += RAW_NOISE * exc[i] * 8.0

    peak = max(abs(v) for v in out) or 1.0
    return [v / peak * scale for v in out]


def main():
    a = one_hit(1.0, 12345)
    b = one_hit(SECOND_HIT, 67890)
    gap = int(RATE * HIT_GAP_MS / 1000)
    total = max(len(a), gap + len(b))
    buf = [0.0] * total
    for i, v in enumerate(a):
        buf[i] += v
    for i, v in enumerate(b):
        buf[gap + i] += v

    peak = max(abs(v) for v in buf) or 1.0
    pcm = [int(max(-32768, min(32767, round(v / peak * PEAK)))) for v in buf]

    if len(sys.argv) >= 3 and sys.argv[1] == "--wav":
        raw = struct.pack("<%dh" % len(pcm), *pcm)
        with open(sys.argv[2], "wb") as f:
            f.write(b"RIFF")
            f.write(struct.pack("<I", 36 + len(raw)))
            f.write(b"WAVEfmt ")
            f.write(struct.pack("<IHHIIHH", 16, 1, 1, RATE, RATE * 2, 2, 16))
            f.write(b"data")
            f.write(struct.pack("<I", len(raw)))
            f.write(raw)
        sys.stderr.write("%s (%dms)\n" % (sys.argv[2], round(len(pcm) / RATE * 1000)))
        return

    w = sys.stdout.write
    w("/*\n")
    w(" * 自動生成ファイル — 手で編集しないこと。\n")
    w(" *\n")
    w(" * 生成: python firmware/esp32/tools/gen_wake_chime.py > firmware/esp32/src/Chimes.h\n")
    w(" * 形式: 16000Hz 16bit モノラル（実機のI2Sと同じ。そのまま play() へ）\n")
    w(" *\n")
    w(" * 呼びかけに気づいたことを知らせる音。顔（目）だけでは、機体を見ていない\n")
    w(" * ときに伝わらない。判定に3〜6秒かかるので、黙っていると届いていないと\n")
    w(" * 思って呼び直され、その全部が控えから送られて会話が壊れる。\n")
    w(" */\n\n")
    w("#ifndef KATANORI_CHIMES_H\n#define KATANORI_CHIMES_H\n\n")
    w("#include <Arduino.h>\n\n")
    w("namespace katanori {\nnamespace chimes {\n\n")
    w("constexpr uint32_t RATE = %d;\n\n" % RATE)
    w("/** 木を2回叩いた音 %dms — 呼びかけを聞き取ったとき */\n" % round(total / RATE * 1000))
    w("static const int16_t WAKE_ACK[] = {\n")
    for i in range(0, len(pcm), 16):
        w("    " + ",".join(str(v) for v in pcm[i:i + 16]) + ",\n")
    w("};\n")
    w("constexpr size_t WAKE_ACK_SAMPLES = sizeof(WAKE_ACK) / sizeof(WAKE_ACK[0]);\n\n")
    w("} // namespace chimes\n} // namespace katanori\n\n")
    w("#endif // KATANORI_CHIMES_H\n")


main()
