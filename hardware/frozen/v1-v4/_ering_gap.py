# -*- coding: utf-8 -*-
"""E リングの通り道と、まわりの物（柱・ねじ・ナット）の**最小隙間**を mm で出す。

   🔴 2026-08-27 ユーザー「高さが減らないなら検査がゴミ」。それまでの ering_path_check は
      交わりの体積（0 か 0 でないか）しか出しておらず、隙間が何 mm あるかも、一番近い相手が
      何かも見えなかった。実際 0.75mm で、しかも一番近いのは柱ではなく**島を留めるナット**だった。
      PRINT.md/CLAUDE の「通り道の検査は空/非空でなく最小隙間を数字で出す」を、ここで守る。

   使い方: python hardware/_ering_gap.py [-D 名前=値 ...]
      -D はそのまま OpenSCAD へ渡る（形を変えた前後を比べるとき用）。
   ⚠ 通り道は hull() で作った**実物より太った経路**なので、出る数字は保守側（実物はこれ以上空く）。
"""
import io, os, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
from scipy import ndimage as ndi
O = r'C:\Program Files\OpenSCAD (Nightly)\openscad.exe'
_argv = sys.argv; sys.argv = [sys.argv[0]]          # _stl_preflight は argv[2] を数値で読む
_ns = {}; _src = io.open(os.path.join(HERE, '_stl_preflight.py'), encoding='utf-8').read()
exec(_src[:_src.index("for p in sorted(glob.glob(")], _ns)
sys.argv = _argv
read_stl = _ns['read_stl']
P = 0.25
extra = sys.argv[1:]
def bake(what):
    p = os.path.join(HERE, '_pf', 'gap_%s.stl' % what)
    if os.path.exists(p): os.remove(p)
    subprocess.run([O, '--backend=manifold', '--export-format=binstl', '-o', p,
                    '-D', 'WHAT="%s"' % what] + extra + [os.path.join(HERE, '_ering_gap.scad')], capture_output=True)
    return read_stl(p)
A = bake('sweep'); B = bake(os.environ.get('GAP_VS', 'obst'))
lo = np.minimum(A.reshape(-1,3).min(0), B.reshape(-1,3).min(0)) - 1
hi = np.maximum(A.reshape(-1,3).max(0), B.reshape(-1,3).max(0)) + 1
nx, ny, nz = [int(np.ceil((hi[i]-lo[i])/P)) for i in range(3)]
def vox(tris):
    g = np.zeros((nx, ny, nz), bool)
    col, zs, ze, us, vs, nu, nv = _ns['zcolumns'](tris, P)
    for c, z0, z1 in zip(col, zs, ze):
        i = int((us[c // nv] - lo[0]) / P); j = int((vs[c % nv] - lo[1]) / P)
        if not (0 <= i < nx and 0 <= j < ny): continue
        k0 = max(0, int(np.ceil((z0 - lo[2]) / P))); k1 = min(nz, int((z1 - lo[2]) / P))
        if k1 > k0: g[i, j, k0:k1] = True
    return g
a = vox(A); b = vox(B)
if (a & b).any():
    print('当たっている（%.3f mm3）' % ((a & b).sum() * P**3)); raise SystemExit
d = ndi.distance_transform_edt(~b, sampling=P)
m = d[a].min()
idx = np.argwhere(a)[np.argmin(d[a])]
print('E リングの通り道と、柱・ねじ・ナットの最小隙間 %.2f mm  （一番近い所 x %.1f y %.1f z %.1f）'
      % (m, lo[0]+idx[0]*P, lo[1]+idx[1]*P, lo[2]+idx[2]*P))
