# -*- coding: utf-8 -*-
# 組み立てマニュアル（hardware/assembly_v3.html）を case_v3.scad から作り直す道具。
#
#   python hardware/_asm_manual.py            挿絵を出し直して HTML を書く
#   python hardware/_asm_manual.py --no-render 挿絵はそのままで HTML だけ書き直す
#
# 手順は 1 か所（下の STEPS）にしか無い。数字の出どころは docs/CASE-V3.md。
# 挿絵は openscad の --render を PNG にして、背景の一色を縁から塗りつぶして透過にし、
# 全部を同じ枠で切って倍率を揃えている（段を並べたときに大きさが飛ばないように）。
import base64, math, os, subprocess, sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
IMGDIR = os.path.join(HERE, '_manual_img')
OUT = os.path.join(HERE, 'assembly_v3.html')
OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.exe')

# 同じカメラで撮る 8 枚（倍率を揃える）と、全体図 2 枚（それぞれ viewall）
CAM = ['--projection=p', '--camera=43,36,25,60,0,30,360', '--imgsize=1100,850']
SEQ = ['st_hub', 'st_manaita0', 'st_manaita', 'st_top', 'st_sideb', 'st_9', 'st_12', 'st_all']
WIDE = [('explode', 'case_v3.scad', 'part'), ('wires', 'case_v3.scad', 'part')]


def render():
    os.makedirs(IMGDIR, exist_ok=True)
    for st in SEQ:
        subprocess.run([OPENSCAD, '--backend=manifold', '--render'] + CAM +
                       ['-o', os.path.join(IMGDIR, st + '.png'), '-D', 'ST="%s"' % st,
                        os.path.join(HERE, '_asm_sim.scad')],
                       check=True, capture_output=True)
    for name, scad, var in WIDE:
        subprocess.run([OPENSCAD, '--backend=manifold', '--render', '--projection=p',
                        '--autocenter', '--viewall', '--camera=0,0,0,60,0,30,0',
                        '--imgsize=1100,900', '-o', os.path.join(IMGDIR, name + '.png'),
                        '-D', '%s="%s"' % (var, name), os.path.join(HERE, scad)],
                       check=True, capture_output=True)


def _alpha(path):
    """背景（角の色と同じで、縁から繋がっている画素）だけを透明にする。
       模型の中にも同じ色があるので、色の一致ではなく縁からの塗りつぶしで判定する。"""
    import numpy as np
    from PIL import Image
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(np.int16)
    near = (np.abs(a - a[0, 0]).sum(2) < 24)
    h, w = near.shape
    seen = np.zeros((h, w), bool)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if near[y, x] and not seen[y, x]:
                seen[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if near[y, x] and not seen[y, x]:
                seen[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and near[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                q.append((ny, nx))
    rgba = np.dstack([np.asarray(im), np.where(seen, 0, 255).astype(np.uint8)])
    return rgba, ~seen


def clean():
    import numpy as np
    from PIL import Image
    data, boxes = {}, []
    for n in SEQ:
        rgba, solid = _alpha(os.path.join(IMGDIR, n + '.png'))
        data[n] = rgba
        ys, xs = np.nonzero(solid)
        boxes.append((ys.min(), ys.max(), xs.min(), xs.max()))
    y0 = max(0, min(b[0] for b in boxes) - 10); y1 = max(b[1] for b in boxes) + 11
    x0 = max(0, min(b[2] for b in boxes) - 10); x1 = max(b[3] for b in boxes) + 11
    for n in SEQ:                                     # 8 枚を同じ枠で切る = 倍率が揃う
        im = Image.fromarray(data[n][y0:y1, x0:x1], 'RGBA')
        if im.width > 900:
            im = im.resize((900, round(im.height * 900 / im.width)), Image.LANCZOS)
        im.save(os.path.join(IMGDIR, 'c_' + n + '.png'), optimize=True)
    for n, _, _ in WIDE:                              # 全体図はそれぞれ自前の枠で切る
        rgba, solid = _alpha(os.path.join(IMGDIR, n + '.png'))
        ys, xs = np.nonzero(solid)
        im = Image.fromarray(rgba[max(0, ys.min() - 8):ys.max() + 9,
                                  max(0, xs.min() - 8):xs.max() + 9], 'RGBA')
        if im.width > 980:
            im = im.resize((980, round(im.height * 980 / im.width)), Image.LANCZOS)
        im.save(os.path.join(IMGDIR, 'c_' + n + '.png'), optimize=True)


def img(name):
    with open(os.path.join(IMGDIR, name), 'rb') as f:
        return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()


# ---- 中身 -----------------------------------------------------------------
# 番号は docs/CASE-V3.md の ①〜⑬ と同じ。⑩ は 🔒「⑨ より先」なので置く順だけ入れ替える
STEPS = [
 dict(n='1', t='まな板をつくる', img='hub', blank=False, acts=[
   '床を<b>裏返して</b>机に置き、四隅の穴に <span class="d">M3×8</span> を裏から通す。頭は裏のザグリに沈む。',
   'ハブ基板を柱（<span class="d">φ7 × 2.5</span>）に載せ、上から <span class="d">M3</span> ナット 4 個で締める。',
 ], note='床の裏はスタンドに載る面。ビスの頭が出ていると座らない。'),

 dict(n='2', t='ReSpeaker を立てる', img='mana0', blank=False, acts=[
   '床の溝に差すだけ。<b>ビスは無い。</b>手順 12 で天面のリブが頭を <span class="d">0.3mm</span> 押さえる。',
   'USB-C の口が右の壁の側（<span class="d">X 86</span>）を向くこと。',
 ]),

 dict(n='3', t='ReSpeaker と OLED をハブへつなぐ', img='mana', blank=False, acts=[
   '<span class="w">XIAO</span>（I2C・電源）と <span class="w">PHIN</span>（J2 → リレー）と <span class="w">OLED</span> の 3 本。ハブの口は全部上向きで、いまは上が開いている。',
   'OLED はこの時点で宙ぶらりん。手順 4 で天面に留める。',
 ]),

 dict(n='4', t='天面に OLED・つまみ・ボタンを付ける', img='top', blank=False, acts=[
   'OLED は<b>ガラスを上に</b>して置き、天面の L を裏から当てて、ガラス側から <span class="d">M2×6</span> ×2 で締める。',
   'ナットは先に L の後ろのポケットへ落とす。空きは左 <span class="d">8.1</span>・右 <span class="d">1.3mm</span> なので<b>ピンセット</b>。',
   'つまみの島（<span class="d">M2×6</span> ×2）・会話ボタンの受けとキャップ・スピーカー（両面テープ）・リードスイッチ。',
 ]),

 dict(n='5', t='天面側をハブへつなぐ', img=None, blank=False, acts=[
   '<span class="w">AS5600</span> 5 本・<span class="w">BTN2</span> 2 本・<span class="w">REED</span> 2 本・<span class="w">PHOUT</span> 2 本。',
   'この後、天面は線でまな板につながったまま <b>箱の左に裏返して</b>置く。手順 12 まで動かさない。',
 ], note='置き場で要る線の長さが変わる。左が最短で、手前だと BTN2 が +21mm、右だと +50mm 要る。'),

 dict(n='6', t='側面構造体を手元で組む', img='side', blank=False, acts=[
   '左の壁の棚 2 か所と右の柱の棚 1 か所に <span class="d">M2</span> ナットを落とす（<b>ピンセット</b>）。',
   'ブリッジを載せ、上から <span class="d">M2×15</span> ×3 で締める。穴は屋根の <span class="d">φ4.0</span>（左 2 本）と立ち上がり（右 1 本）から。',
   'PowerBoost を右の壁のダボ 4 本に差す。',
   '電池をトンネルへ入れ、蓋・ロック・磁石を付ける。',
 ], warn='ブリッジの 3 本は<b>電池より先に</b>締める。電池が入っていると工具の軸が <span class="d">1.6mm</span> で塞がる（空なら <span class="d">7.6mm</span>）。',
    open_='INA226 はまだ置けない。径と穴の位置が未実測で、受けの形が決まっていない。'),

 dict(n='7', t='充電ケーブルを PowerBoost へ', img=None, blank=True, acts=[
   'PowerBoost の micro-B に中で挿し、箱の外は Type-C。',
 ], warn='Type-C の受けの座のビスは <b>左の壁 1 枚のうちに</b>留める。壁を 2 枚組んだ後は、軸が箱を横切るので上からも下からも工具が入らない。',
    open_='変換ケーブルが着荷待ち（8/27〜9/6）。受け本体は別刷りで未作成。'),

 dict(n='8', t='電池まわりを配線する', img=None, blank=False, acts=[
   '電池の JST → INA226 の INPUT → OUT → PowerBoost の JST。',
   'これで電池が生きる。トグルを入れるまで基板側は無電源。',
 ]),

 dict(n='10', t='残りの電力配線をハブへ挿す', img=None, blank=False, first=True, acts=[
   '側面構造体を <span class="d">20〜60mm</span> 持ち上げた状態で、<span class="w">PWR</span> 3 本・<span class="w">INA</span> 4 本・<span class="w">TOGGLE</span> 2 本を挿す。',
   'これでハブの口 10 本が全部埋まる。',
 ], note='載せた後では、ブリッジの後ろの 19mm の隙間からしか口に届かない。だから先に挿す。持ち上げる高さは PWR の線の長さにそのまま効く（60mm 上げると +42mm 要る）。'),

 dict(n='9', t='側面構造体をまな板へ降ろして留める', img='s9', blank=False, acts=[
   'まっすぐ <b>Z で</b>降ろす。傾けない。',
   '床の裏から <span class="d">M2×15</span> ×3。ナットは壁の下の柱へ<b>先に上から</b>落としておく。',
 ], warn='後ろ右のナットは、まっすぐ落とすと右の壁の棚の角に <span class="d">0.4mm</span> かする。Y に 0.4 ずらせば通る。'),

 dict(n='11', t='トグルをハッチに付ける', img=None, blank=False, acts=[
   'ハッチの穴にネジ部を通し、<b>外から六角ナット</b>で締める。',
   '胴はトンネルの屋根の <span class="d">0.3mm</span> 上に浮くだけで、レールは無い。',
 ]),

 dict(n='12', t='天面を降ろし、最後にフロントを差し込む', img='s12', blank=False, acts=[
   '天面の後ろの柱 2 本と、耳の下の柱 2 本に <span class="d">M2</span> ナットを落とす。壁にぴったりなので<b>ピンセット</b>。',
   '天面＋OLED を <b>Z で</b>降ろす。',
   'フロントを<b>前から +Y に</b>差し込む。',
   '四隅を <span class="d">M2×6</span> ×4 で締める。前の 2 本は 天面 → 耳 → 柱 の 3 枚を通る。',
 ], warn='この 4 個のナットは天面を載せる前にしか入らない。入れ忘れたら天面を外してやり直し。'),

 dict(n='13', t='ハッチを閉じて、尻尾を挿す', img='all', blank=False, acts=[
   '下の爪を床の後ろのバーへ <span class="d">−Y</span> にまっすぐ滑り込ませる。傾けなくてよい。',
   '上はトグルのネジ部に六角ナット。ハッチ自体のビスは無い。',
   'トグルのレバーに尻尾のボアを差す。アンテナ線は尻尾の中の溝へ。',
 ]),
]

WIRES = [
 ('XIAO', '4 / 3', '46 / 47', '—', '71 / 72'),
 ('PHIN', '2', '96', '—', '121'),
 ('OLED', '4', '48', '<b>105</b>', '<b>130</b>'),
 ('AS5600', '4', '98', '92', '123'),
 ('BTN2', '2', '50', '<b>81</b>', '<b>106</b>'),
 ('REED', '2', '149', '143', '174'),
 ('PHOUT', '2', '112', '124', '149'),
 ('TOGGLE', '2', '110', '74', '135'),
 ('PWR', '3', '37', '<b>79</b>', '<b>104</b>'),
 ('INA', '4', '66', '77', '101'),
 ('BAT / BAT2', '2 / 2', '18 / 34', '—', '43 / 59'),
 ('CHG', '4', '121', '—', '146'),
]

SCREWS = [
 ('M3 × 8', '4', 'ハブ → 床', '1'),
 ('M2 × 6', '4', '天面の四隅 → 壁の柱・耳の柱', '12'),
 ('M2 × 6', '2', 'OLED → 天面の L', '4'),
 ('M2 × 6', '2', 'つまみの島', '4'),
 ('M2 × 15', '3', 'ブリッジ → 壁の棚', '6'),
 ('M2 × 15', '3', '床 → 壁の下の柱', '9'),
 ('M2 × 6', '1', '電池の蓋のロック', '6'),
 ('M2 × 6', '1', 'Type-C の受けの座', '7'),
 ('M2 × ?', '2', 'INA226 → ブリッジ', '未定'),
]

TWEEZ = [
 ('天面の耳の柱', '×2', 'φ5 は通るが φ7 では 2.7mm で止まる。壁にぴったり'),
 ('ブリッジの左の棚', '×2', 'φ5 で 13.1mm / 全通、φ7 で 5.6 / 0.1mm'),
 ('OLED の L の後ろ（右）', '×1', '後ろの空きが 1.3mm。ナット厚 1.6 なので入るが指は無理'),
]

BLANKS = [
 ('INA226', '径と穴の位置が未実測。手順 6 の取り付けと 8 の配線が埋まらない', '着荷待ち'),
 ('Type-C の変換ケーブルと受け', '部品が未着。受け本体は別刷りで未作成', '8/27〜9/6'),
 ('つまみ（knob_v5）', 'M2 に変えた後の STL が未出力。島のナット位置は推定', '要出力'),
 ('締め順と手応え', 'まだ 1 度も組んでいない。机上の手順', '初回で直る'),
]

CSS = """
:root {
  --paper:#e8ebef; --card:#ffffff; --sunk:#f3f5f7; --ink:#14171c; --ink2:#525b66;
  --rule:#ccd3db; --rule2:#dfe4ea; --accent:#8f5405; --mark:#c98a1e;
  --stop:#a62f28; --open:#20607f; --sheet:#f7f8fa; --sheetdim:1;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --paper:#0f1216; --card:#181c22; --sunk:#13171c; --ink:#e3e8ee; --ink2:#98a2ae;
    --rule:#2a323c; --rule2:#222932; --accent:#f0aa33; --mark:#f0aa33;
    --stop:#e0776f; --open:#69b6d8; --sheet:#e6e9ed; --sheetdim:.86;
  }
}
:root[data-theme="dark"] {
  --paper:#0f1216; --card:#181c22; --sunk:#13171c; --ink:#e3e8ee; --ink2:#98a2ae;
  --rule:#2a323c; --rule2:#222932; --accent:#f0aa33; --mark:#f0aa33;
  --stop:#e0776f; --open:#69b6d8; --sheet:#e6e9ed; --sheetdim:.86;
}
* { box-sizing: border-box; }
body {
  margin:0; background:var(--paper); color:var(--ink);
  font-family:"BIZ UDPGothic","Hiragino Sans","Yu Gothic UI","Noto Sans JP",system-ui,sans-serif;
  font-size:16px; line-height:1.85; -webkit-font-smoothing:antialiased;
}
.wrap { max-width:960px; margin:0 auto; padding:0 20px 96px; }
.d, .n, .w {
  font-family:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  font-variant-numeric:tabular-nums;
}
.d { font-size:.92em; font-weight:700; color:var(--accent); }
.w { font-size:.86em; font-weight:700; letter-spacing:.04em; }

header.mast { padding:56px 0 28px; border-bottom:2px solid var(--ink); }
.eyebrow {
  font-family:Archivo,system-ui,sans-serif; font-weight:600; font-size:12px;
  letter-spacing:.22em; text-transform:uppercase; color:var(--accent); margin:0 0 10px;
}
h1 {
  font-family:Archivo,"BIZ UDPGothic",system-ui,sans-serif; font-weight:700;
  font-size:clamp(34px,6vw,54px); line-height:1.08; letter-spacing:-.015em;
  margin:0; text-wrap:balance;
}
h1 em { font-style:normal; color:var(--ink2); font-weight:500; }
.sub { margin:14px 0 0; color:var(--ink2); max-width:62ch; }
.meta { display:flex; flex-wrap:wrap; gap:8px 22px; margin:20px 0 0; font-size:13px; color:var(--ink2); }
.meta b { color:var(--ink); font-weight:700; }

.jump {
  position:sticky; top:0; z-index:9; background:var(--paper);
  border-bottom:1px solid var(--rule); padding:9px 0; margin-bottom:34px;
  display:flex; flex-wrap:wrap; gap:6px; align-items:baseline;
}
.jump span {
  font-family:Archivo,sans-serif; font-size:11px; letter-spacing:.16em;
  text-transform:uppercase; color:var(--ink2); margin-right:6px;
}
.jump a {
  font-family:"JetBrains Mono",monospace; font-size:13px; font-weight:700;
  color:var(--ink2); text-decoration:none; padding:2px 8px;
  border:1px solid var(--rule); border-radius:2px;
}
.jump a:hover, .jump a:focus-visible {
  color:var(--card); background:var(--ink); border-color:var(--ink); outline:none;
}

.callout {
  border:1px solid var(--rule); background:var(--card);
  border-left:4px solid var(--stop); padding:16px 20px; margin:0 0 34px;
}
.callout h2 {
  font-family:Archivo,sans-serif; font-size:13px; letter-spacing:.14em;
  text-transform:uppercase; margin:0 0 8px; color:var(--stop);
}
.callout ul { margin:0; padding-left:1.15em; }

h2.sec {
  font-family:Archivo,"BIZ UDPGothic",sans-serif; font-weight:700; font-size:13px;
  letter-spacing:.2em; text-transform:uppercase; color:var(--ink2);
  margin:56px 0 18px; padding-bottom:8px; border-bottom:1px solid var(--rule);
}

.step { display:grid; grid-template-columns:76px 1fr; gap:0 22px; padding:26px 0; border-top:1px solid var(--rule2); }
.step:first-of-type { border-top:none; }
.num { position:relative; }
.num span {
  position:sticky; top:56px; display:block; font-family:Archivo,sans-serif;
  font-weight:700; font-size:38px; line-height:1; color:var(--mark);
  font-variant-numeric:tabular-nums;
}
.body h3 { font-size:20px; line-height:1.5; margin:0 0 14px; font-weight:700; text-wrap:balance; }
.pill.first { color:var(--accent); border-color:var(--accent); }
.pill {
  display:inline-block; vertical-align:middle; font-family:Archivo,sans-serif;
  font-size:11px; font-weight:600; letter-spacing:.12em; text-transform:uppercase;
  color:var(--open); border:1px solid var(--open); border-radius:2px;
  padding:1px 7px; margin-left:8px; white-space:nowrap;
}
.sheet { margin:0 0 16px; background:var(--sheet); border:1px solid var(--rule); padding:6px; filter:brightness(var(--sheetdim)); }
.sheet img { display:block; width:100%; height:auto; }
ol.acts { margin:0; padding-left:1.35em; }
ol.acts li { margin:0 0 6px; }
ol.acts li::marker { color:var(--ink2); font-family:"JetBrains Mono",monospace; font-size:.85em; }
.cal { margin:14px 0 0; padding:11px 14px; background:var(--sunk); border-left:3px solid var(--rule); font-size:14.5px; line-height:1.75; }
.cal .tag {
  font-family:Archivo,sans-serif; font-size:11px; font-weight:700;
  letter-spacing:.12em; text-transform:uppercase; margin-right:10px; vertical-align:1px;
}
.cal.warn { border-left-color:var(--stop); }
.cal.warn .tag { color:var(--stop); }
.cal.open { border-left-color:var(--open); }
.cal.open .tag { color:var(--open); }
.cal.note .tag { color:var(--ink2); }

.tw { overflow-x:auto; border:1px solid var(--rule); background:var(--card); }
table { border-collapse:collapse; width:100%; font-size:14.5px; }
th, td { text-align:left; padding:9px 14px; border-bottom:1px solid var(--rule2); vertical-align:top; }
thead th {
  font-family:Archivo,sans-serif; font-size:11px; letter-spacing:.12em;
  text-transform:uppercase; color:var(--ink2); background:var(--sunk);
  border-bottom:1px solid var(--rule); white-space:nowrap;
}
tbody tr:last-child td { border-bottom:none; }
td.n { font-family:"JetBrains Mono",monospace; font-variant-numeric:tabular-nums; white-space:nowrap; }
td.hi { font-weight:700; color:var(--accent); }
figure.wide { margin:0 0 8px; background:var(--sheet); border:1px solid var(--rule); padding:8px; filter:brightness(var(--sheetdim)); }
figure.wide img { display:block; width:100%; height:auto; }
figcaption { font-size:13px; color:var(--ink2); margin-top:8px; }
.two { display:grid; grid-template-columns:1fr 1fr; gap:22px; align-items:start; }
footer { margin-top:64px; padding-top:20px; border-top:1px solid var(--rule); font-size:13px; color:var(--ink2); }
a { color:var(--accent); }
@media (max-width:720px) {
  .step { grid-template-columns:1fr; gap:0; }
  .num span { position:static; font-size:26px; margin-bottom:4px; }
  .two { grid-template-columns:1fr; }
  .jump { overflow-x:auto; flex-wrap:nowrap; }
}
@media (prefers-reduced-motion:reduce) { * { animation:none !important; transition:none !important; } }
"""

BODY = """
<div class="wrap">
<header class="mast">
  <p class="eyebrow">katanori &middot; enclosure v3</p>
  <h1>カタノリ v3<br><em>組み立て</em></h1>
  <p class="sub">印刷部品 8 点・ビス 20 本・線 13 本を、この順番で組む。順番は入れ替えられない。ナットを入れられる段と、工具が入る向きが決まっているため。</p>
  <div class="meta">
    <span><b>外寸</b> 90 &times; 76 &times; 52.95 mm</span>
    <span><b>内寸</b> 86 &times; 72 &times; 48.45 mm</span>
    <span><b>2026-08-23</b> 版</span>
    <span>番号は <b>docs/CASE-V3.md</b> の ①〜⑬ と同じ</span>
    <span>まだ 1 度も組んでいない机上の手順</span>
  </div>
</header>

<nav class="jump"><span>手順</span>__NAV__</nav>

<div class="callout">
  <h2>始める前に</h2>
  <ul>
    <li><b>ナットのポケットは全部上向き。</b>落としてから締めるまで、箱を傾けない。</li>
    <li><b>ハブの口 10 本は手順 9 の前に全部挿す。</b>側面構造体を載せた後は、ブリッジの後ろの <span class="d">19mm</span> の隙間からしか届かない。</li>
    <li><b>ドライバは先端 φ3.2 以下。</b>座ぐりが <span class="d">φ3.4</span> なので、それより太いと頭に届かない。ほかに<b>ピンセット</b>と、トグル用の<b>六角のスパナ</b>。</li>
  </ul>
</div>

<h2 class="sec">全体</h2>
<div class="two">
  <div>
    <figure class="wide"><img src="__EXP__" alt="分解図"></figure>
    <figcaption>組む向きにばらした図。まな板 → 側面構造体 → 天面 → フロント → ハッチ の順に重なる。</figcaption>
  </div>
  <div>
    <figure class="wide"><img src="__WIRES__" alt="線の図"></figure>
    <figcaption>線 13 本の通り道。手前の板を外して中を見たところ。通路は 3 つ（ReSpeaker の裏・ブリッジの下・ブリッジの後ろ）。</figcaption>
  </div>
</div>

<h2 class="sec">手順</h2>
__STEPS__

<h2 class="sec">線の長さ</h2>
<div class="tw"><table>
<thead><tr><th>線</th><th>本数</th><th>組んだ実長</th><th>置いた姿勢で要る</th><th>作る長さ &ge;</th></tr></thead>
<tbody>__WIREROWS__</tbody>
</table></div>
<p class="cal note"><span class="tag">読み</span>「置いた姿勢で要る」は、天面を箱の左に裏返して置き、手順 12 で 60mm 持ち上げる前提。<b>OLED・BTN2・PWR の 3 本は実長では足りない。</b>「作る長さ」は端末処理と取り回しの余長 25mm 込み。単位はすべて mm。</p>

<h2 class="sec">ビスとナット</h2>
<div class="tw"><table>
<thead><tr><th>ビス</th><th>本数</th><th>どこ</th><th>手順</th></tr></thead>
<tbody>__SCREWROWS__</tbody>
</table></div>
<p class="cal note"><span class="tag">読み</span>樹脂にネジは切らない。全部<b>貫通＋ナット</b>。ナットは M3 &times;4・M2 &times;15（＋INA226 の 2）。長さは <span class="d">M2×6</span> と <span class="d">M2×15</span> の 2 種類だけ。</p>

<h2 class="sec">ピンセットが要る 5 か所</h2>
<div class="tw"><table>
<thead><tr><th>ナット</th><th>数</th><th>入る余地</th></tr></thead>
<tbody>__TWROWS__</tbody>
</table></div>

<h2 class="sec">まだ埋まっていない</h2>
<div class="tw"><table>
<thead><tr><th>もの</th><th>何が足りないか</th><th>いつ</th></tr></thead>
<tbody>__BLANKROWS__</tbody>
</table></div>

<footer>
  作り直すには <b>python hardware/_asm_manual.py</b>。数字の出どころは <b>docs/CASE-V3.md</b>。
  工具の道とナットの道は <b>hardware/_asm_probe.py</b> が STL へ軸に平行な円筒を撃って測った値、線の長さは <b>wire_len</b> の実長。
</footer>
</div>
"""


def build():
    IM = {k: img('c_' + v + '.png') for k, v in {
        'all': 'st_all', 'hub': 'st_hub', 'mana0': 'st_manaita0', 'mana': 'st_manaita',
        'top': 'st_top', 'side': 'st_sideb', 's9': 'st_9', 's12': 'st_12',
        'exp': 'explode', 'wires': 'wires'}.items()}

    def step_html(s):
        fig = ('<figure class="sheet"><img src="{}" alt="手順 {} の状態"></figure>'
               .format(IM[s['img']], s['n'])) if s['img'] else ''
        bits = []
        if s.get('warn'):
            bits.append('<p class="cal warn"><span class="tag">注意</span>{}</p>'.format(s['warn']))
        if s.get('open_'):
            bits.append('<p class="cal open"><span class="tag">未定</span>{}</p>'.format(s['open_']))
        if s.get('note'):
            bits.append('<p class="cal note"><span class="tag">なぜ</span>{}</p>'.format(s['note']))
        pill = ' <span class="pill">この段は未定</span>' if s['blank'] else ''
        if s.get('first'):
            pill += ' <span class="pill first">手順 9 より先</span>'
        return ('<section class="step" id="s{n}">\n'
                '  <div class="num"><span>{n}</span></div>\n'
                '  <div class="body">\n'
                '    <h3>{t}{pill}</h3>\n'
                '    {fig}\n'
                '    <ol class="acts">{acts}</ol>\n'
                '    {bits}\n'
                '  </div>\n'
                '</section>').format(
                    n=s['n'], t=s['t'], pill=pill, fig=fig,
                    acts='\n'.join('<li>{}</li>'.format(x) for x in s['acts']),
                    bits=''.join(bits))

    body = (BODY
            .replace('__NAV__', ' '.join('<a href="#s{0}">{0}</a>'.format(s['n']) for s in STEPS))
            .replace('__EXP__', IM['exp'])
            .replace('__WIRES__', IM['wires'])
            .replace('__STEPS__', '\n'.join(step_html(s) for s in STEPS))
            .replace('__WIREROWS__', '\n'.join(
                '<tr><td class="w">{}</td><td class="n">{}</td><td class="n">{}</td>'
                '<td class="n">{}</td><td class="n hi">{}</td></tr>'.format(*r) for r in WIRES))
            .replace('__SCREWROWS__', '\n'.join(
                '<tr><td class="d">{}</td><td class="n">{}</td><td>{}</td>'
                '<td class="n">{}</td></tr>'.format(*r) for r in SCREWS))
            .replace('__TWROWS__', '\n'.join(
                '<tr><td>{}</td><td class="n">{}</td><td>{}</td></tr>'.format(*r) for r in TWEEZ))
            .replace('__BLANKROWS__', '\n'.join(
                '<tr><td><b>{}</b></td><td>{}</td><td class="n">{}</td></tr>'.format(*r) for r in BLANKS)))

    html = ('<title>カタノリ v3 組み立て</title>\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
            'family=Archivo:wght@500;600;700&family=BIZ+UDPGothic:wght@400;700'
            '&family=JetBrains+Mono:wght@400;700&display=swap">\n'
            '<style>' + CSS + '</style>\n' + body)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print(OUT, os.path.getsize(OUT), 'bytes')


if __name__ == '__main__':
    if '--no-render' not in sys.argv:
        render()
        clean()
    build()
