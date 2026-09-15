# -*- coding: utf-8 -*-
"""筐体 v6.1n（MJF ナイロン）の発注用 STL 7 点を hardware/stl/v61n/ へ書き出す（2026-09-15）。
   python hardware/tools/stl_v61n.py                 全部（7 点）
   python hardware/tools/stl_v61n.py btn_tub top     名前を指定（stl/v61n/v61n_<名前>.stl）
   python hardware/tools/stl_v61n.py --check         筐体の当たり検査（seam_shell_top ほか）を hardware/_tmp_v61n/ に出して体積を出す
   ⚠ 出力先は書き出す前に必ず消す（OpenSCAD は空だと STL を書かないので、古いファイルを読む事故が起きる）。
   支柱・ラフト・FIT_PRINT は渡さない（MJF。MAT="nylon" で PROPS_OFF・RIBS_OFF が true）。
   材料は -D で渡す（case: MAT="nylon"・部品ファイル: $mat="nylon"）。--resin-check はレジン（MAT="resin" を渡す）で検査だけ回す。
   書き出したら `python hardware/tools/_stl_preflight.py "hardware/stl/v61n/*.stl"` を通す（道に v61n があるので nylon の判定になる）。
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))          # hardware/tools
HW = os.path.dirname(HERE)                                   # hardware
OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.exe')
OUT = os.path.join(HW, 'stl', 'v61n')

CASE = os.path.join(HW, 'case_v6_1.scad')            # 2026-09-15: 写し（case_v6_1n）は畳まれ、MAT で切り替える
KNOB = os.path.join(HW, 'parts', 'knob_v61.scad')
BTN  = os.path.join(HW, 'parts', 'btn_v61.scad')
SPK  = os.path.join(HW, 'parts', 'spk_v61.scad')
# 材料は -D で渡す（2026-09-16）: case には MAT="nylon"、部品ファイルには $mat="nylon"（parts/mat.scad の説明）。2026-09-15 までは mat.scad の 1 行を書き換えて戻していた
def mat_defs(src, nylon=True):
    m = 'nylon' if nylon else 'resin'   # 🔴 resin も明示する（ファイルの既定 MAT は GUI で書き換わることがある・2026-09-16）
    return ['-D', 'MAT="%s"' % m] if src == CASE else ['-D', '$mat="%s"' % m]
# ファイル名 → (元の .scad, part の値)。名前は v61n_<キー>.stl になる（コミット 26b3e3a と同じ 7 点）
PARTS = [
    ('shell',      CASE, 'print_shell'),     # 床＋4 壁の一体シェル
    ('top',        CASE, 'print_top'),       # 天板（外面を下）
    ('knob',       KNOB, 'knob'),            # つまみ本体
    ('island',     KNOB, 'wall'),            # つまみの島（座金＋タブ）
    ('spktub',     SPK,  'print_tub'),       # スピーカーのバスタブ
    ('btn_piston', BTN,  'print_piston2'),   # 会話ボタンの押し子
    ('btn_tub',    BTN,  'print_tub'),       # 会話ボタンのバスタブ
]
# 筐体の当たり検査（docs/CASE-V61N.md 5 章の表）。0 か、表の値が正
CHECKS = ['seam_shell_top', 'plugpath', 'hit_wires', 'nutpath', 'sk_rsp', 'sk_hub', 'sk_spktub', 'sk_tgl', 'sk_btn', 'hit_btn']
NAMES = [k for k, _, _ in PARTS]

def export(dst, src, pname, nylon=True):
    if os.path.exists(dst): os.remove(dst)
    t = time.time()
    r = subprocess.run([OPENSCAD, '--backend=manifold', '--export-format=binstl', '-o', dst,
                        '-D', 'part="%s"' % pname] + mat_defs(src, nylon) + [src], capture_output=True)
    err = r.stderr.decode('utf-8', 'replace')
    if not os.path.exists(dst):
        return None, time.time() - t, err
    return os.path.getsize(dst), time.time() - t, err

if '--check' in sys.argv or '--resin-check' in sys.argv:
    tmp = os.path.join(HW, '_tmp_v61n'); os.makedirs(tmp, exist_ok=True)
    sys.path.insert(0, HERE); from stl_read import tris
    for c in CHECKS:
        dst = os.path.join(tmp, c + '.stl')
        size, dt, err = export(dst, CASE, c, nylon='--resin-check' not in sys.argv)
        if size is None:
            print('%-16s EMPTY (0)   %5.1fs  %s' % (c, dt, err.strip().splitlines()[-1][:80] if 'ERROR' in err or 'assert' in err.lower() else '')); continue
        v = 0.0
        for a, b, cc in tris(dst):
            v += (a[0]*(b[1]*cc[2]-b[2]*cc[1]) - a[1]*(b[0]*cc[2]-b[2]*cc[0]) + a[2]*(b[0]*cc[1]-b[1]*cc[0])) / 6.0
        print('%-16s %8.2f mm3  %5.1fs' % (c, abs(v), dt))
    raise SystemExit

want = [a for a in sys.argv[1:] if not a.startswith('-')] or NAMES
os.makedirs(OUT, exist_ok=True)
for k in want:
  if k not in NAMES: raise SystemExit('知らない部品: %s（%s）' % (k, ' '.join(NAMES)))
  src, pname = next((f, p) for n, f, p in PARTS if n == k)
  dst = os.path.join(OUT, 'v61n_%s.stl' % k)
  size, dt, err = export(dst, src, pname)
  if size is None:
      print('%-10s NG 書けなかった\n%s' % (k, err[-800:])); continue
  print('%-10s %8d bytes  %5.1fs  warn %d' % (k, size, dt, err.count('WARNING')))
