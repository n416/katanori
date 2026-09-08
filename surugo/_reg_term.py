# -*- coding: utf-8 -*-
"""刷るぞーに 1 回ぶん登録する（AI が画面を触れないので、app.html の「並べる」→「書き出す」を
   そのまま呼ぶだけの口）。人は `python surugo/server.py` の画面を使うこと。
   python surugo/_reg_term.py 見るだけ | python surugo/_reg_term.py 書く

   🔴 **下の PLATE_W / PLATE_H / PLATE_EDGE / SPREAD / ANCHOR_* は app.html の写し**（app.html:316〜328）。
      置き場所を散らす計算（spreadMove）が画面側にしか無いための重複である。
      **片方だけ動かすと、記録の座標と実際に刷る座標がずれる。** 触るときは必ず両方。
   ⚠ 測る・並べる・書き出す・ログに積むの本体は server.py / store.py を呼んでいるので、そちらは重複しない。"""
import json, math, os, sys, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import measure as M, server as SV, store as S
PATHS = ['hardware/stl/v5/v5_spktub.stl', 'hardware/stl/v5/v5_spktest.stl']
PLATE_W, PLATE_H, PLATE_EDGE = 143, 89, 8.0
SPREAD = [[0,0],[-1,-1],[1,1],[1,-1],[-1,1],[-1,0],[1,0],[0,1],[0,-1]]
ANCHOR_STL, ANCHOR_SZ, ANCHOR_OUT = 'surugo/anchor.stl', 6.0, 6.0
st = S.state()
print('開いている回:', [t['id'] for t in st.get('open_terms', [])])
print('フィルム交換からの回数:', st.get('film_terms_since_change'))
parts = [M.measure(os.path.join(ROOT, p)) for p in PATHS]
for p in parts:
    print('  %-16s 接地 %.1f mm2  層 %d  背 %.2f  警告 %s' % (
        p['name'], p['grip'], p['layers'], p['height'], p['warn'] or 'なし'))
r = SV.arrange(parts)
if r.get('stop'): print('■ 止まった:', r['stop']); sys.exit(1)
PL = r['placements']
bb = [min(p['cx']-p['w']/2 for p in PL), min(p['cy']-p['h']/2 for p in PL),
      max(p['cx']+p['w']/2 for p in PL), max(p['cy']+p['h']/2 for p in PL)]
n = st.get('film_terms_since_change') or 0
rx = max(0.0, (PLATE_W-(bb[2]-bb[0]))/2 - PLATE_EDGE); ry = max(0.0, (PLATE_H-(bb[3]-bb[1]))/2 - PLATE_EDGE)
u = SPREAD[n % len(SPREAD)]
q = lambda v: round(v*2)/2
shift = lambda dx, dy: [dict(p, cx=p['cx']+dx, cy=p['cy']+dy) for p in PL]
dx, dy = q(u[0]*rx), q(u[1]*ry)
# 🔒 ヘラが届く所に置く（scraper_reach_mm）。散らしの向きを優先し、駄目なら動かせる範囲で近い所を探す
if SV.scraper_far(shift(dx, dy)):
    grid = lambda r: sorted({q(v/2.0) for v in range(-int(r*2), int(r*2)+1)})
    cand = [(abs(x-dx)+abs(y-dy), x, y) for x in grid(rx) for y in grid(ry)
            if not SV.scraper_far(shift(x, y))]
    if not cand:
        print('■ 止まった: ヘラ（届く深さ %.0fmm）が寝たまま届く配置にならない。'
              '部品を減らすか、並べ方を変えてください' % SV.scraper_reach()); sys.exit(1)
    _, dx, dy = min(cand)
    print('ずらしをヘラの規則で寄せ直した（散らしの向きは %s）' % (u,))
PL = shift(dx, dy)
print('ずらし X %.1f / Y %.1f（%d 回目・動かせる範囲 ±%.1f / ±%.1f）' % (dx, dy, n+1, q(rx), q(ry)))
print('ヘラの奥行き: ' + ' / '.join('%s %.1fmm' % (p['name'], SV.scraper_inset(p)) for p in PL)
      + '（届く %.0fmm）' % SV.scraper_reach())
for w in r.get('warn', []): print('  ⚠', w)
for p in parts:
    for w in p['warn']: print('  ⚠ %s ── %s' % (p['name'], w))
if r.get('time'): print('層数 %s（背の高い %s が決めている）' % (r['time']['layers'], r['time']['by']))
for p in PL: print('  置いた %-16s cx %.2f cy %.2f rot %s' % (p['name'], p['cx'], p['cy'], p.get('rot')))
if len(sys.argv) < 2 or sys.argv[1] != '書く':
    print('--- 見るだけ。書いていない ---'); sys.exit(0)
d = datetime.datetime.now()
TERM = '%04d-%02d-%02d-%02d%02d' % (d.year, d.month, d.day, d.hour, d.minute)
out = 'hardware/stl/term/%s.stl' % TERM
if os.path.exists(os.path.join(ROOT, out)):
    print('■ 同じ名前の STL がもうある。上書きしない:', out); sys.exit(1)
ax, ay = PLATE_W/2+ANCHOR_OUT, PLATE_H/2+ANCHOR_OUT
anch = [{'path': ANCHOR_STL, 'name': 'anchor', 'cx': sx*ax, 'cy': sy*ay,
         'w': ANCHOR_SZ, 'h': ANCHOR_SZ, 'rot': 0, 'grip': 0, 'layers': 0, 'height': 0}
        for sx in (-1, 1) for sy in (-1, 1)]
e = SV.export(PL + anch, out)
print('書き出した: %s（面 %d）' % (e['out'], e['facets']))
ev = S.append({'t': 'term', 'id': TERM, 'out': out, 'move': [dx, dy],
               'parts': [{'name': p['name'], 'path': p['path'], 'grip': p['grip'],
                          'profile_max': p.get('profile_max'), 'layers': p['layers'],
                          'height': p['height'], 'cx': p['cx'], 'cy': p['cy'],
                          'w': p['w'], 'h': p['h'], 'rot': p.get('rot') or 0} for p in PL]}, by='ai')   # w/h/rot は画面の「編集」が図を出すのに使う（2026-09-05）
print('登録した:', json.dumps(ev, ensure_ascii=False)[:200])
