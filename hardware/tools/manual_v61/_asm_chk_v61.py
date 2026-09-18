# -*- coding: utf-8 -*-
"""組み立ての動きの掃引 v6.1 / v6.1n（_asm_chk_v61.scad を T を変えて回し、重なりの体積を並べる）。
python hardware/tools/manual_v61/_asm_chk_v61.py [SW ...]   … 省略で全部。結果は hardware/check/asm/<SW>.txt（git に入る・模型の刻印つき）と標準出力。交わりの STL は hardware/_tmp_v61man/asm_chk/
SW の頭が r ならレジン（MAT="resin"）、n ならナイロン（MAT="nylon"）で回す。
"""
import os, subprocess, sys, concurrent.futures as cf
HERE = os.path.dirname(os.path.abspath(__file__))          # hardware/tools/manual_v61
HW = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(HW, 'tools')); from stl_read import tris
from check_stamp import stamp_line, out_dir
OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.com')
OUT = os.path.join(HW, '_tmp_v61man', 'asm_chk'); os.makedirs(OUT, exist_ok=True)   # 交わりの STL（中間物）
RES = out_dir('asm')                                                                   # 判定の txt（git に入る）


def frange(a, b, s):
    v = a; out = []
    while v <= b + 1e-9: out.append(round(v, 3)); v += s
    return out


SWEEPS = {
    'r_hub':    frange(0, 45, 1.5),
    'r_rsp':    frange(0, 50, 1.5),
    'r_oriser': frange(0, 45, 1.5),
    'r_lwall':  frange(0, 24, 0.5),
    'r_rwall':  frange(0, 24, 0.5),
    'r_top':    frange(0, 40, 1),
    'r_front':  frange(0, 20, 0.5),
    'r_hatch':  frange(0, 24, 0.5),
    'r_top_after_front': frange(0, 20, 1),
    'n_hub_case':  frange(0, 45, 1.5),
    'n_hub_dn':    frange(0, 45, 1.5),
    'n_hub_back':  frange(0, 5.5, 0.25),
    'n_hub_right': frange(0, 0.8, 0.1),
    'n_tgl':       frange(0, 16, 0.5),
    'n_rsp':       frange(0, 50, 1.5),
    'n_oled':      frange(0, 50, 1.5),
    'n_bat':       frange(0, 70, 2),
    'n_lid':       frange(0.3, 14, 0.5),
    'n_lid_seat':  [0.3, 0.15, 0.0],
}


def vol(p):
    v = 0.0
    for a, b, c in tris(p):
        v += (a[0]*(b[1]*c[2]-b[2]*c[1]) - a[1]*(b[0]*c[2]-b[2]*c[0]) + a[2]*(b[0]*c[1]-b[1]*c[0])) / 6.0
    return abs(v)


def one(sw, t):
    stl = os.path.join(OUT, '%s_%s.stl' % (sw, t))
    if os.path.exists(stl): os.remove(stl)
    mat = 'resin' if sw.startswith('r') else 'nylon'
    args = [OPENSCAD, '--backend=manifold', '-D', 'MAT="%s"' % mat, '-D', 'SW="%s"' % sw, '-D', 'T=%s' % t,
            '-o', stl, os.path.join(HERE, '_asm_chk_v61.scad')]
    r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = (r.stdout or '') + (r.stderr or '')
    if 'top level object is empty' in out.lower() or ('Current top level object is empty' in out):
        return (sw, t, None, '')
    if r.returncode != 0 or not os.path.exists(stl):
        return (sw, t, 'ERROR', out[-400:])
    return (sw, t, vol(stl), '')


def main():
    sws = [a for a in sys.argv[1:] if not a.startswith('--')] or list(SWEEPS)
    jobs = [(sw, t) for sw in sws for t in SWEEPS[sw]]
    res = {}
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for sw, t, v, err in ex.map(lambda j: one(*j), jobs):
            res.setdefault(sw, []).append((t, v, err))
    for sw in sws:
        lines = []
        for t, v, err in sorted(res[sw]):
            s = 'ERROR ' + err.replace('\n', ' ') if v == 'ERROR' else ('0 (empty)' if v is None else '%.2f mm3' % v)
            lines.append('%-12s T=%-6s %s' % (sw, t, s))
        mx = max([v for t, v, e in res[sw] if isinstance(v, float)] + [0])
        lines.append('%-12s MAX %.2f mm3' % (sw, mx))
        txt = '\n'.join(lines)
        open(os.path.join(RES, sw + '.txt'), 'w', encoding='utf-8').write(stamp_line() + '\n' + txt + '\n')
        print(txt); print()


if __name__ == '__main__': main()
