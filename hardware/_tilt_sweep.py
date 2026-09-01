"""STL を傾けて、層ごとの断面積の「立ち上がり」がいちばん緩やかになる向きを探す。

出典（docs/PRINT.md §3.9）: 光造形で部品を落とすのは FEP から剥がすときの力で、
これは**その層の断面積に比例する**。底が平らな部品は断面が一段に跳ねるので吸盤になり、
処方は「傾けて層ごとの断面積が少しずつ変わるようにする」。
⇒ **向きの良し悪しを測る物差しは「1 層あたりの断面積の増分の最大値」**である。

層ごとの断面積そのものは surugo/measure.py が既に出しているので（`profile`）、
ここがやるのは「三角形を回してから同じ計算へ渡す」ことと「角度を振る」ことだけ。

  python hardware/_tilt_sweep.py hardware/stl/v4/v4_post_0.stl
"""
import sys, os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# ⚠ `_stl_preflight` は import しただけで本体が走る（surugo/measure.py と同じ回避）。
#   読み込む間だけ argv を「何にも当たらない glob」に差し替える。
_saved = sys.argv
sys.argv = [sys.argv[0], "__tiltsweep_no_match__*.stl", "0.30"]
import _stl_preflight as PF        # noqa: E402
sys.argv = _saved

DZ = PF.DZ          # 0.05 層の高さ


def profile(tris, pitch):
    """層ごとの断面積 mm² の列。層 0 が接地。surugo/measure.py の _profile と同じ数え方"""
    col, zs, ze, us, vs, nu, nv = PF.zcolumns(tris, pitch)
    z0 = zs.min()
    n = int(np.ceil((ze.max() - z0) / DZ))
    if n <= 0:
        return np.zeros(0)
    s = np.clip(np.ceil((zs - z0) / DZ - 0.5).astype(int), 0, n)
    e = np.clip(np.ceil((ze - z0) / DZ - 0.5).astype(int), 0, n)
    d = np.zeros(n + 2)
    np.add.at(d, s, 1.0)
    np.add.at(d, e, -1.0)
    return np.cumsum(d)[:n] * pitch * pitch


def rotated(tris, tilt_deg, az_deg):
    """方位 az だけ Z 回りに回してから、tilt だけ X 回りに倒す"""
    a = np.radians(az_deg); t = np.radians(tilt_deg)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(t), -np.sin(t)], [0, np.sin(t), np.cos(t)]])
    return tris.reshape(-1, 3) @ (Rx @ Rz).T


def score(tris, tilt, az, pitch):
    v = rotated(tris, tilt, az).reshape(-1, 3, 3)
    p = profile(v, pitch)
    if len(p) < 2:
        return None
    step = np.diff(p)                       # 1 層ごとの断面積の増分 mm²
    i = int(np.argmax(step))
    return {
        "tilt": tilt, "az": az,
        "layers": len(p),
        "height": len(p) * DZ,
        "first": float(p[0]),               # 接地（層 0）
        "max_area": float(p.max()),         # いちばん大きい断面
        "max_step": float(step[i]),         # 🔴 これが物差し。1 層で増える面積の最大
        "at_z": (i + 1) * DZ,               # その跳ねが起きる高さ
    }


def main():
    path = sys.argv[1]
    pitch = float(sys.argv[2]) if len(sys.argv) > 2 else 0.1
    tris = PF.read_stl(path)
    print(f"{os.path.basename(path)}  pitch={pitch}  層 {DZ}mm")
    print(f"{'傾き':>5} {'方位':>5} {'接地':>8} {'最大断面':>9} "
          f"{'最大の跳ね':>11} {'その高さ':>9} {'層数':>6}")
    rows = []
    for tilt in range(0, 91, 5):
        azs = [0] if tilt == 0 else [0, 45, 90, 135, 180, 225, 270, 315]
        for az in azs:
            r = score(tris, tilt, az, pitch)
            if r:
                rows.append(r)
    rows.sort(key=lambda r: r["max_step"])
    for r in rows:
        print(f"{r['tilt']:5.0f} {r['az']:5.0f} {r['first']:8.2f} {r['max_area']:9.2f} "
              f"{r['max_step']:11.2f} {r['at_z']:9.2f} {r['layers']:6d}")


if __name__ == "__main__":
    main()
