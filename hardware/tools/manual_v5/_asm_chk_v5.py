# -*- coding: utf-8 -*-
"""組み立ての動きの掃引（_asm_chk_v5.scad を T を変えて回し、重なりの体積を並べる）。
python hardware/tools/manual_v5/_asm_chk_v5.py [SW ...]   … 省略で全部。結果は hardware/_tmp_v5/asm_chk/<SW>.txt と標準出力
"""
import os, subprocess, sys, concurrent.futures as cf
HERE = os.path.dirname(os.path.abspath(__file__))          # hardware/tools/manual_v5
HW = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(HW, 'tools')); from stl_read import tris
OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.com')
OUT = os.path.join(HW, '_tmp_v5', 'asm_chk'); os.makedirs(OUT, exist_ok=True)
WIRES = '--wires' in sys.argv

def frange(a, b, s):
    v = a; out = []
    while v <= b + 1e-9: out.append(round(v, 3)); v += s
    return out

SWEEPS = {
    'st2':   frange(0, 36, 3),
    'st4l':  frange(0, 24, 1),
    'st4r':  frange(0, 24, 1),
    'st5':   frange(0, 18, 1),
    'st6':   frange(0, 30, 1),
    'st7a':  frange(0, 24, 1),
    'st7b':  frange(0, 2, 0.25),
    'st8':   frange(0, 60, 2),
    'st9':   frange(0, 20, 1),
    'st11':  frange(0, 30, 2),
    'st12t': frange(0, 30, 1),
    'st12f': frange(0, 16, 1),
    'st13r': frange(0, 30, 1),
    'st13y': frange(0, 14, 0.5),
    'st13r2': frange(0, 30, 1),
    'st13u': frange(0, 14, 1),
    'st4lb': frange(0, 24, 1),
    'st4rb': frange(0, 24, 1),
    'st5t': frange(0, 24, 1),
    'st4lt': frange(0, 24, 1),
    'st4lc': frange(0, 24, 1),
    'st4rc': frange(0, 24, 1),
    'probeL': [0],
    'probeR': [0],
}

def vol(p):
    if not os.path.exists(p): return None   # 空（重なり無し）は STL が書かれない
    v = 0.0; t = tris(p)
    for a, b, c in t:
        v += (a[0]*(b[1]*c[2]-b[2]*c[1]) - a[1]*(b[0]*c[2]-b[2]*c[0]) + a[2]*(b[0]*c[1]-b[1]*c[0])) / 6.0
    return abs(v)

def one(sw, t):
    stl = os.path.join(OUT, '%s_%s%s.stl' % (sw, t, '_w' if WIRES else ''))
    if os.path.exists(stl): os.remove(stl)
    args = [OPENSCAD, '--backend=manifold', '-D', 'SW="%s"' % sw, '-D', 'T=%s' % t, '-o', stl, os.path.join(HERE, '_asm_chk_v5.scad')]
    if WIRES: args[2:2] = ['-D', 'WIRES=true']
    r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = (r.stdout or '') + (r.stderr or '')
    if 'top level object is empty' in out:
        return (sw, t, None, '')          # 空 = 重なり無し
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
            lines.append('%-6s T=%-6s %s' % (sw, t, s))
        txt = '\n'.join(lines)
        open(os.path.join(OUT, sw + ('_w' if WIRES else '') + '.txt'), 'w', encoding='utf-8').write(txt + '\n')
        print(txt); print()

if __name__ == '__main__': main()
