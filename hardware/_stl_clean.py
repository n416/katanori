# -*- coding: utf-8 -*-
"""STL から潰れた三角（面積ゼロ）を取り除く。
   使い方: python hardware/_stl_clean.py hardware/stl/v4/*.stl

   なぜ要るか:
     🔴 2026-09-04 ユーザーが OpenSCAD の画面で気付いた。CSG の切り口に**面積ゼロの三角**が残る。
        天板 599 枚 / ブリッジ 317 枚 / 前脚 16 枚 / バスタブ 8 枚 / 留め帯 8 枚（v4・$fn 48）。
        スライサーによっては穴として扱われる。形の情報は持っていないので、消しても形は変わらない。

   安全のため、書き戻す前に 3 つ確かめる:
     ① 消したあとも**閉じている**（どの辺もちょうど 2 枚の三角に使われている）
     ② 体積が変わらない（面積ゼロなので理屈の上でも変わらない）
     ③ 外形が変わらない
   1 つでも外れたらそのファイルは書き換えない。
"""
import struct, sys, glob, os
import numpy as np

EPS_AREA = 1e-12
SNAP     = 1e-4      # 頂点をこの刻みに丸めてから比べる（STL は float32 なので 80mm 付近の刻みは約 5e-6mm。それより粗く取る）


def read_stl(path):
    b = open(path, 'rb').read()
    if b[:5] == b'solid' and b'facet' in b[:2000]:
        v = [[float(x) for x in L.split()[1:4]]
             for L in b.decode('utf-8', 'replace').splitlines() if L.strip().startswith('vertex')]
        return np.array(v).reshape(-1, 3, 3), True
    n = struct.unpack('<I', b[80:84])[0]
    a = np.frombuffer(b[84:84 + 50 * n], dtype=np.uint8).reshape(n, 50)
    return a[:, 12:48].copy().view(np.float32).reshape(n, 3, 3).astype(np.float64), False


def write_binary(T, path):
    out = bytearray(b'\0' * 80)
    out += struct.pack('<I', len(T))
    for t in T:
        n = np.cross(t[1] - t[0], t[2] - t[0])
        L = np.linalg.norm(n)
        n = n / L if L > 1e-15 else np.zeros(3)
        out += struct.pack('<12fH', *n, *t[0], *t[1], *t[2], 0)
    open(path, 'wb').write(bytes(out))


def volume(T):
    A, B, C = T[:, 0], T[:, 1], T[:, 2]
    return float(abs(np.einsum('ij,ij->i', A, np.cross(B, C)).sum() / 6.0))


def closed(T):
    """どの辺もちょうど 2 枚に使われているか。閉じていれば True。"""
    key = np.round(T.reshape(-1, 3) / SNAP).astype(np.int64)
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    f = inv.reshape(-1, 3)
    e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    e = np.sort(e, axis=1)
    _, cnt = np.unique(e, axis=0, return_counts=True)
    return bool((cnt == 2).all()), int((cnt != 2).sum())


def clean(path):
    T, was_ascii = read_stl(path)
    area = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    bad = area < EPS_AREA
    if not bad.any():
        print('%-24s 面積ゼロ 0 枚。触らない' % os.path.basename(path))
        return
    K = T[~bad]
    ok0, n0 = closed(T)
    ok1, n1 = closed(K)
    v0, v1 = volume(T), volume(K)
    b0 = np.r_[T.reshape(-1, 3).min(0), T.reshape(-1, 3).max(0)]
    b1 = np.r_[K.reshape(-1, 3).min(0), K.reshape(-1, 3).max(0)]
    db = float(np.abs(b0 - b1).max())
    good = ok1 and abs(v1 - v0) < 1e-6 and db < 1e-9
    print('%-24s %5d 枚消す（%d → %d）/ 閉じ %s → %s / 体積 %+.3e / 外形差 %.1e  %s' % (
        os.path.basename(path), bad.sum(), len(T), len(K),
        'OK' if ok0 else 'NG(%d)' % n0, 'OK' if ok1 else 'NG(%d)' % n1,
        v1 - v0, db, '⇒ 書き戻す' if good else '⇒ 🔴 条件を満たさないので書き換えない'))
    if good:
        write_binary(K, path)


if __name__ == '__main__':
    args = sys.argv[1:] or ['hardware/stl/v4/*.stl']
    files = []
    for a in args:
        files += sorted(glob.glob(a))
    if not files:
        raise SystemExit('STL が見つからない: %s' % ' '.join(args))
    for f in files:
        clean(f)
