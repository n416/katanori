# -*- coding: utf-8 -*-
"""hardware/stl/v4/ の STL を全部 1 面に並べる _v4_plate.scad を書き出す。

   使い方: python hardware/_v4_plate.py
   見る側: OpenSCAD で case_v4.scad を開き `part = "plate"`（または -D 'part="plate"'）。

   並べるのは **焼いた STL そのもの**なので、支柱もラフトも犠牲タブも付いた状態で出る
   （STL は PROPS_OFF=false で焼かれている）。モデルを描き直して並べるのではないから、
   ここに見えている物がそのままスライサへ行く物と 1:1 になる。
   支柱とラフトは部品の**下**に付くので、真上から見ると見えない。回して下から見ること。

   ⚠ 動かすのは X と Y だけ。**Z は 1mm も動かさない。**
      底が Z=0 に無い部品は浮いたまま並ぶ（それが見えることがこの絵の目的の 1 つ）。
   ⚠ 隙間は「見て区別が付く量」であって、プレートへの詰め方ではない。
      Mars 3 のプレートは 143 × 89mm で、100.66mm の板は 2 枚並ばない（PRINT.md）。
      この絵は 1 回の印刷の割り付けではなく、**刷る物の棚卸し**。

   🔒 2026-08-27 ユーザー「全部白くていいです」: 色分けはしない。部品も名札も全部同じ色。
   焼いた時刻は名札に出したままなので、古い STL が混ざっているかは時刻を見れば分かる。

   底が FLOAT_Z より浮いている部品には名札に [FLOAT] を足す（しきい値は _stl_preflight.py と同じ）。
"""
import glob
import io
import os
import struct
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'stl', 'v4')
DST = os.path.join(HERE, '_v4_plate.scad')

GAP = 8.0        # 部品どうしの隙間
ROW_W = 260.0    # 1 行の幅（これを超えたら次の行へ）
NAME_H = 4.5     # 名札 1 行目（部品の名前）の文字の大きさ
SUB_H = 2.6      # 名札 2 行目（寸法と焼いた時刻）の文字の大きさ
CHAR_W = 0.62    # 文字の幅 ÷ 高さ の目安（名札のぶん場所を空けるため）
LABEL_SP = 11.0  # 名札 2 行ぶん、部品の下に空ける高さ
FLOAT_Z = 0.05   # これより浮いていたら [FLOAT]（_stl_preflight.py と同じしきい値）


def bbox(path):
    """STL（バイナリ／アスキー両対応）の min/max を返す。"""
    d = open(path, 'rb').read()
    if d[:5] == b'solid' and b'facet' in d[:400]:
        t = d.decode('utf8', 'ignore').split()
        pts, i = [], 0
        while i < len(t):
            if t[i] == 'vertex':
                pts.append(tuple(float(x) for x in t[i + 1:i + 4])); i += 4
            else:
                i += 1
    else:
        n = struct.unpack('<I', d[80:84])[0]
        pts = []
        for i in range(n):
            f = struct.unpack('<12f', d[84 + i * 50:84 + i * 50 + 48])
            pts += [f[3:6], f[6:9], f[9:12]]
    lo = [min(p[k] for p in pts) for k in (0, 1, 2)]
    hi = [max(p[k] for p in pts) for k in (0, 1, 2)]
    return lo, hi


def collect():
    items = []
    for p in sorted(glob.glob(os.path.join(SRC, '*.stl'))):
        lo, hi = bbox(p)
        items.append({
            'name': os.path.splitext(os.path.basename(p))[0].replace('v4_', ''),
            'file': 'stl/v4/' + os.path.basename(p),
            'lo': lo, 'hi': hi,
            'w': hi[0] - lo[0], 'h': hi[1] - lo[1], 'z': hi[2] - lo[2],
            'mt': os.path.getmtime(p),
        })
    if not items:
        raise SystemExit('stl/v4/ に STL が無い。先に `python hardware/_stl_v4.py`')

    for it in items:
        flags = ''
        if it['lo'][2] > FLOAT_Z:
            flags += ' [FLOAT z=%.2f]' % it['lo'][2]
        it['sub'] = '%.1f x %.1f x %.1f  %s%s' % (
            it['w'], it['h'], it['z'],
            time.strftime('%m-%d %H:%M', time.localtime(it['mt'])), flags)
        # 名札が部品よりはみ出す小さい部品があるので、場所は「部品と名札の広いほう」で取る
        it['cell'] = max(it['w'], len(it['name']) * NAME_H * CHAR_W, len(it['sub']) * SUB_H * CHAR_W)
    return items


def pack(items):
    """奥行き（Y）の深い順に棚詰めする。ROW_W を超えたら次の行へ。"""
    rows, cur, curw = [], [], 0.0
    for it in sorted(items, key=lambda i: -i['h']):
        add = it['cell'] if not cur else GAP + it['cell']
        if cur and curw + add > ROW_W:
            rows.append(cur); cur, curw, add = [], 0.0, it['cell']
        cur.append(it); curw += add
    if cur:
        rows.append(cur)

    y = 0.0
    for row in rows:
        x = 0.0
        for it in row:
            it['at'] = (x, y)                      # 名札の左下（部品はこの上に載る）
            x += it['cell'] + GAP
        y += max(r['h'] for r in row) + LABEL_SP + GAP
    return max(it['at'][0] + it['cell'] for it in items), y - GAP


def main():
    items = collect()
    ext_x, ext_y = pack(items)

    out = [
        '// 🔴 自動生成。手で直さない。並べ直しは `python hardware/_v4_plate.py`',
        '//    中身は stl/v4/*.stl そのもの（支柱・ラフト・犠牲タブ込みで焼いたもの）。',
        '//    支柱とラフトは部品の下に付くので、真上からは見えない。回して下から見ること。',
        '//    X と Y だけ動かしてある。**Z は動かしていない**ので、浮いている部品は浮いたまま出る。',
        '//    🔒 色分けはしない（2026-08-27 ユーザー「全部白くていいです」）。焼いた時刻は名札に出ている。',
        'PLATE_COLOR = "#b6c0cc";',
        'PLATE_NAME_H = %.1f; PLATE_SUB_H = %.1f;' % (NAME_H, SUB_H),
        'module plate_label(x, y, name, sub) color("#8a8a8a") translate([x, y, 0]) {',
        '    linear_extrude(0.2) text(sub, size = PLATE_SUB_H);',
        '    translate([0, PLATE_SUB_H * 1.7, 0]) linear_extrude(0.2) text(name, size = PLATE_NAME_H);',
        '}',
        '',
        '// 並べた全体は %.1f x %.1f mm（%d 部品）' % (ext_x, ext_y, len(items)),
        'module plate_all() {',
    ]
    for it in sorted(items, key=lambda i: i['name']):
        x, y = it['at']
        out.append('    color(PLATE_COLOR) translate([%.3f, %.3f, 0]) import("%s");'
                   % (x - it['lo'][0], y + LABEL_SP - it['lo'][1], it['file']))
        out.append('    plate_label(%.3f, %.3f, "%s", "%s");' % (x, y, it['name'], it['sub']))
    out.append('}')

    io.open(DST, 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')

    print('%d 部品を %.1f x %.1f mm に並べた -> %s' % (len(items), ext_x, ext_y, DST))
    for it in sorted(items, key=lambda i: i['name']):
        mark = '! 底が Z=%.2f に浮いている' % it['lo'][2] if it['lo'][2] > FLOAT_Z else ''
        print('  %-10s %s  %s' % (it['name'], it['sub'], mark))
    print('見る: OpenSCAD で case_v4.scad を開いて part = "plate"')


if __name__ == '__main__':
    main()
