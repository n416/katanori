# -*- coding: utf-8 -*-
"""筐体 v6.1n（MJF ナイロン）の発注用 STL 7 点を hardware/stl/v61n/ へ書き出す（2026-09-15。2026-09-16 に分割を底パーツ＋蓋に変えた）。
   python hardware/tools/stl_v61n.py                 全部（7 点）
   python hardware/tools/stl_v61n.py btn_tub top     名前を指定（stl/v61n/v61n_<名前>.stl）
   python hardware/tools/stl_v61n.py --check         筐体の静止の当たり検査（seam_shell_lid・sk_* ほか）を hardware/_tmp_v61n/ に出して体積を出す
   ⚠ **入れる道の検査はこちらではない** ── `python hardware/tools/sweep_chk.py hub rsp oled bat lidmain lidflap`（2026-09-17 に移した。docs/COLLISION-SURVEY.md）
   python hardware/tools/stl_v61n.py --resin-check   同じくレジンで。ナイロン専用の検査（NYLON_ONLY）は回さない
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
    ('shell',      CASE, 'print_shell'),     # 底パーツ（床＋前＋後ろ＋右の壁＋左の壁の帯。2026-09-16 の分割）
    ('lid',        CASE, 'print_lid'),       # 蓋（天板＋左の板＋鉤＋PCB の受け。2026-09-16 まで 'top' = 天板だけだった）
    ('knob',       KNOB, 'knob'),            # つまみ本体
    ('island',     KNOB, 'wall'),            # つまみの島（座金＋タブ）
    ('spktub',     SPK,  'print_tub'),       # スピーカーのバスタブ
    ('btn_piston', BTN,  'print_piston2'),   # 会話ボタンの押し子
    ('btn_tub',    BTN,  'print_tub'),       # 会話ボタンのバスタブ
]
# 筐体の当たり検査（docs/CASE-V61N.md 5 章の表）。0 か、表の値が正
CHECKS = ['seam_shell_lid', 'plugpath', 'hit_wires', 'sk_rsp', 'sk_oled', 'sk_hub', 'sk_spktub', 'sk_tgl', 'sk_btn', 'hit_btn']
# ⭐ 2026-09-18: nutpath をここから外した。ナット／ねじの口は `python hardware/tools/nutpath_chk.py --mat nylon`（口 29・場面ごと。docs/SWEEP.md 10 章）
# 🔴 2026-09-17: 入れる道の掃引（path_*）をここから外した（🔒 ユーザー「旧の掃引検査は削除」）。
#   姿勢を n 個 union して交わりを作る方式は、細かくすると面数が爆発して PC が固まる。
#   ⇒ `python hardware/tools/sweep_chk.py hub rsp oled bat lidmain lidflap`（距離クエリ・刻みは自動）。
#      動画は `python hardware/tools/sweep_movie.py <key>`。docs/COLLISION-SURVEY.md
# 🔴 ナイロンでしか意味を持たない検査（2026-09-16）。レジンでは回さない。
#   seam_shell_lid … 底パーツ＋蓋の継ぎ目。レジンは板 6 枚なので、この分割自体が無い
NYLON_ONLY = ['seam_shell_lid']
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

def dup_defs():
    """module / function の二重定義を探す（⭐ 2026-09-16 夕）。

    OpenSCAD は**後の定義が勝つ**ので、同じ名前を 2 回書くと前の方が黙って消える。
    今日 2 回踏んだ: rear_post（並走セッションとの編集の衝突）と
    skin（「定義が無い」と見て色無しの 2 つ目を足し、箱が既定の黄色で出た）。
    どちらも検査は通り、絵だけが違っていた。
    """
    import glob, re, collections
    bad = []
    for f in sorted(glob.glob(os.path.join(HW, '*.scad')) + glob.glob(os.path.join(HW, 'parts', '*.scad'))):
        t = open(f, encoding='utf-8', errors='replace').read()
        for kind, pat in (('module', r'^\s*module\s+([A-Za-z_]\w*)\s*\('),
                          ('function', r'^\s*function\s+([A-Za-z_]\w*)\s*\(')):
            for n, c in collections.Counter(re.findall(pat, t, re.M)).items():
                if c > 1:
                    bad.append('%s: %s %s が %d 回' % (os.path.basename(f), kind, n, c))
    return bad


if '--check' in sys.argv or '--resin-check' in sys.argv:
    for b in dup_defs():
        print('🔴 二重定義（後の方が勝つ）', b)
    tmp = os.path.join(HW, '_tmp_v61n'); os.makedirs(tmp, exist_ok=True)
    sys.path.insert(0, HERE); from stl_read import tris
    nylon = '--resin-check' not in sys.argv
    checks = CHECKS if nylon else [c for c in CHECKS if c not in NYLON_ONLY]
    if not nylon:
        print('レジン: ナイロン専用の %d 件は回さない（%s）' % (len(NYLON_ONLY), ' '.join(NYLON_ONLY)))
    print('入れる道は別の道具: python hardware/tools/sweep_chk.py hub rsp oled bat lidmain lidflap')
    for c in checks:
        dst = os.path.join(tmp, c + '.stl')
        size, dt, err = export(dst, CASE, c, nylon=nylon)
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
