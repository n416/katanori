# -*- coding: utf-8 -*-
# 中身どうしの静止の総当たり（🆕 2026-08-27・9 度目の机上の通し）
#
#   python hardware/_asm_pairs.py            # 20 部品の総当たり（まず「1 ↔ 他の全部」で粗く、出たものだけ 1 対 1）
#   python hardware/_asm_pairs.py 7          # 7 番だけ ↔ 他の全部
#
# 🔴 なぜ要るか: ここまでの静止の検査は **皮 ↔ 中身**（case_v4 の chk_all ほか）と、
# **名指しの 1 対 1**（chk_tc など）しか無かった。中身どうしは誰も総当たりで当てていない。
# 「Type-C 基板のデュポン ↔ ハブ基板」の 1.169mm³ は、そのせいで 8 度の机上の通しを素通りした。
import os, subprocess, sys, struct, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.exe')
TMP = os.environ.get('PAIR_TMP', os.path.join(tempfile.gettempdir(), 'katanori_pairs'))
SIM = os.path.join(HERE, '_asm_sim_v4.scad')

NAMES = ['床', 'ハブ基板', 'ハブに挿した口 10 本', 'ReSpeaker＋XIAO の線', '充電基板の受け',
         '左の壁', '右の壁', 'Type-C 基板（デュポン込み）', 'ブリッジ本体', 'ブリッジの前板',
         'ブリッジのビスとナット', '留め帯 3 本', '電池', '電流計', 'PowerBoost',
         'OLED', '天面一式', 'フロント', 'ハッチ＋トグル', '電池の蓋']
# 設計どおり食い込んでいる組（当たって当たり前・除外して読む）
KNOWN = {
    (1, 2):  'ハブの口に挿したハウジング（挿さっている姿そのもの）',
    (3, 16): 'ReSpeaker の押さえ 0.3（chk_press の 4.7mm³ ＝ これが 0 だと不合格）',
}

def vol(p):
    d = open(p, 'rb').read()
    n = struct.unpack('<I', d[80:84])[0]
    s = 0.0
    for i in range(n):
        o = 84 + i * 50
        f = struct.unpack('<12f', d[o:o + 48])
        a, b, c = f[3:6], f[6:9], f[9:12]
        s += (a[0]*(b[1]*c[2]-b[2]*c[1]) - a[1]*(b[0]*c[2]-b[2]*c[0]) + a[2]*(b[0]*c[1]-b[1]*c[0])) / 6.0
    return abs(s)

def bbox(p):
    d = open(p, 'rb').read()
    n = struct.unpack('<I', d[80:84])[0]
    pts = []
    for i in range(n):
        o = 84 + i * 50
        f = struct.unpack('<12f', d[o:o + 48])
        pts += [f[3:6], f[6:9], f[9:12]]
    return [(round(min(q[k] for q in pts), 3), round(max(q[k] for q in pts), 3)) for k in (0, 1, 2)]

def run(a, b=None):
    os.makedirs(TMP, exist_ok=True)
    out = os.path.join(TMP, 'pair_%s_%s.stl' % (a, b))
    if os.path.exists(out): os.remove(out)
    cmd = [OPENSCAD, '--backend=manifold', '--export-format=binstl', '-o', out,
           '-D', 'PAIR_A=%d' % a]
    if b is not None: cmd += ['-D', 'PAIR_B=%d' % b]
    cmd += [SIM]
    subprocess.run(cmd, capture_output=True)
    if not os.path.exists(out) or os.path.getsize(out) < 200: return 0.0, None
    return vol(out), bbox(out)

if __name__ == '__main__':
    only = [int(sys.argv[1])] if len(sys.argv) > 1 else list(range(len(NAMES)))
    hot = []
    for a in only:
        v, _ = run(a)
        print('%2d %-26s ↔ 他の全部  %10.3f mm3' % (a, NAMES[a], v))
        if v > 1e-6: hot.append(a)
    print('\n---- 出たものを 1 対 1 に割る（設計どおりの食い込みは除いて読む）----')
    seen = set()
    for a in hot:
        for b in range(len(NAMES)):
            if b == a or (min(a, b), max(a, b)) in seen: continue
            seen.add((min(a, b), max(a, b)))
            v, bb = run(a, b)
            if v <= 1e-6: continue
            tag = KNOWN.get((min(a, b), max(a, b)), '')
            print('%-26s ↔ %-26s %10.3f mm3  %s%s'
                  % (NAMES[a], NAMES[b], v, bb, '  ← ' + tag if tag else ''))
