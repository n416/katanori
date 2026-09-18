# -*- coding: utf-8 -*-
# 組み立てマニュアル v6.1（レジン・板 6 枚）と v6.1n（ナイロン・底パーツ＋蓋）を case_v6_1.scad から作る道具（2026-09-16）。
#
#   python hardware/tools/manual_v61/_asm_manual_v61.py              挿絵を出し直して HTML を 2 枚書く
#   python hardware/tools/manual_v61/_asm_manual_v61.py --no-render  挿絵はそのままで HTML だけ書き直す
#   python hardware/tools/manual_v61/_asm_manual_v61.py nylon        片方だけ（resin / nylon）
#
# 手順の文は下の STEPS_R / STEPS_N にしか無い。段の絵は _asm_sim_v61.scad、呼び名の絵は _asm_gloss_v61.scad。
# 動きの当たりは _asm_chk_v61.py の結果（hardware/_tmp_v61man/asm_chk/<SW>.txt の MAX 行）をそのまま表に写す。先に回しておくこと。
# 線の長さは case の WIRE_LEN=true の echo から取る。書き方と見た目は v5（hardware/tools/manual_v5/_asm_manual_v5.py）に合わせた。
# 🔴 case_v6_1.scad は読むだけ。ここで形の数字を持たない（文の中の数字は case と docs から写した物で、出どころを文に書く）
import base64, math, os, re, subprocess, sys, concurrent.futures as cf

HERE = os.path.dirname(os.path.abspath(__file__))          # hardware/tools/manual_v61
HW = os.path.dirname(os.path.dirname(HERE))                  # hardware
ROOT = os.path.dirname(HW)
sys.path.insert(0, os.path.join(HW, 'parts'))                # hub_ports（_asm_manual_v4 が読む）
sys.path.insert(0, os.path.join(HW, 'frozen', 'v1-v4'))      # _asm_manual_v4（CSS・RAILJS）
import _asm_manual_v4 as V4

CASE = os.path.join(HW, 'case_v6_1.scad')
SIM = os.path.join(HERE, '_asm_sim_v61.scad')
GLOSS_SCAD = os.path.join(HERE, '_asm_gloss_v61.scad')
TMP = os.path.join(HW, '_tmp_v61man')
CHK = os.path.join(TMP, 'asm_chk')
OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.com')

CAM_D = '43,26,22,30,0,315,300'         # 🔒 ユーザー 2026-09-16 夜「D」: 左前の真上寄り
CAM_UNDER = '43,26,40,145,0,315,260'    # 天板・蓋を裏から
CAM_SUB = '0,0,0,62,0,160,0'            # 机の上の小組（後ろ寄りから・autocenter）
CAM_EXP = '0,0,0,62,0,315,0'            # explode（左前から・autocenter）

MAT = {
    'resin': dict(dir='_manual_img_v61', out='assembly_v61.html', title='カタノリ v6.1 組み立て（レジン）', eyebrow='katanori &middot; enclosure v6.1 &middot; resin'),
    'nylon': dict(dir='_manual_img_v61n', out='assembly_v61n.html', title='カタノリ v6.1n 組み立て（ナイロン）', eyebrow='katanori &middot; enclosure v6.1n &middot; nylon MJF'),
}

# 絵: (名前, scad, 変数, 値, カメラ, autocenter)
IMGS = {
    'resin': [('r%d' % n, SIM, 'ST', 'r%d' % n, CAM_D, False) for n in (1, 2, 3, 4, 5, 7, 8, 9)] + [
        ('rtop', SIM, 'ST', 'rtop', CAM_UNDER, False),
        ('rspsub', SIM, 'ST', 'rspsub', CAM_SUB, True),
        ('frontsub', SIM, 'ST', 'frontsub', '0,0,0,70,0,200,0', True),
        ('wires', SIM, 'ST', 'wires', CAM_D, False),
        ('explode', CASE, 'part', 'explode', CAM_EXP, True),
        ('g_hposts', GLOSS_SCAD, 'G', 'hposts', '0,0,0,50,0,315,0', True),
        ('g_rposts', GLOSS_SCAD, 'G', 'rposts', '0,0,0,50,0,315,0', True),
        ('g_ears', GLOSS_SCAD, 'G', 'ears', '0,0,0,60,0,315,0', True),
        ('g_seat', GLOSS_SCAD, 'G', 'seat', '0,0,0,45,0,315,0', True),
        ('g_press', GLOSS_SCAD, 'G', 'press', '0,0,0,140,0,315,0', True),
        ('g_riser', GLOSS_SCAD, 'G', 'riser', '0,0,0,55,0,160,0', True),
    ],
    'nylon': [('n%d' % n, SIM, 'ST', 'n%d' % n, CAM_D, False) for n in (2, 3, 4, 5, 6, 7, 8)] + [
        ('ntop', SIM, 'ST', 'ntop', CAM_UNDER, False),
        ('rspsub', SIM, 'ST', 'rspsub', CAM_SUB, True),
        ('oledsub', SIM, 'ST', 'oledsub', CAM_SUB, True),
        ('nbat_in', SIM, 'ST', 'nbat_in', CAM_D, False),
        ('nlid_in', SIM, 'ST', 'nlid_in', '43,26,30,55,0,315,330', False),
        ('wires', SIM, 'ST', 'wires', CAM_D, False),
        ('explode', CASE, 'part', 'explode', CAM_EXP, True),
        ('g_shell', GLOSS_SCAD, 'G', 'shell', '0,0,0,50,0,315,0', True),
        ('g_lid', GLOSS_SCAD, 'G', 'lid', '0,0,0,120,0,315,0', True),
        ('g_boss', GLOSS_SCAD, 'G', 'boss', '0,0,0,45,0,300,0', True),
        ('g_rail', GLOSS_SCAD, 'G', 'rail', '0,0,0,50,0,300,0', True),
        ('g_nposts', GLOSS_SCAD, 'G', 'nposts', '0,0,0,50,0,315,0', True),
        ('g_seat', GLOSS_SCAD, 'G', 'seat', '0,0,0,45,0,315,0', True),
        ('g_press', GLOSS_SCAD, 'G', 'press', '0,0,0,140,0,315,0', True),
        ('g_riser', GLOSS_SCAD, 'G', 'riser', '0,0,0,55,0,160,0', True),
    ],
}


def render(mat):
    d = os.path.join(ROOT, 'docs', 'manual', MAT[mat]['dir'])
    os.makedirs(d, exist_ok=True)

    def job(it):
        name, scad, var, val, cam, auto = it
        out = os.path.join(d, name + '.png')
        args = [OPENSCAD, '--backend=manifold', '--render=full', '--projection=p', '--camera=' + cam,
                '--imgsize=1100,850', '-D', 'MAT="%s"' % mat, '-D', '%s="%s"' % (var, val), '-o', out, scad]
        if auto:
            args[4:4] = ['--autocenter', '--viewall']
        r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace')
        return name, r.returncode, (r.stderr or '')[-300:]
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for name, rc, err in ex.map(job, IMGS[mat]):
            print('  ', mat, name, 'OK' if rc == 0 else 'NG ' + err)


def img(mat, name):
    p = os.path.join(ROOT, 'docs', 'manual', MAT[mat]['dir'], name + '.png')
    if not os.path.exists(p):
        return ''
    return 'data:image/png;base64,' + base64.b64encode(open(p, 'rb').read()).decode('ascii')


# ---------------------------------------------------------------- 線（case の 5 本の道の実長）
def wire_lengths(mat):
    os.makedirs(TMP, exist_ok=True)
    r = subprocess.run([OPENSCAD, '--backend=manifold', '-D', 'MAT="%s"' % mat, '-D', 'part="wiresonly"', '-D', 'WIRE_LEN=true',
                        '-o', os.path.join(TMP, 'wl_%s.stl' % mat), CASE], capture_output=True, text=True, encoding='utf-8', errors='replace')
    segs = {}
    for m in re.finditer(r'wlen = \["(\w+)", (\d+), ([0-9.]+)\]', r.stderr + r.stdout):
        segs.setdefault(m.group(1), []).append(float(m.group(3)))
    if not segs:   # 空は「線が無い」ではなく評価の失敗（v5 の 2026-09-07 と同じ罠）
        sys.exit('wire_lengths: wlen の echo が 0 本。\n' + (r.stderr + r.stdout)[-1500:])
    return segs


WIRE_MARGIN = 65   # v5 と同じ決まり: 端末処理 25 ＋ 天板（蓋）を箱の脇に置いて挿すための余り 40（_asm_manual_v5.py）
# 束: (名, echo の名, 本数, 板の口, 口のピン, 逆の端, 色)
#   ピンの並びは hardware/pcb/gen_sch.py（J4・J5 は hub_ports の PHIN・PHOUT、J6・J7 は同ファイルの part()）
#   色は v5 の 🔒 2026-09-06（GND＝黒か白・D2＝紫・EN＝橙）を同じネットに当てた。スピーカー ± は v5 と同じ「仮」
BUNDLES = [
 ('スピーカー OUT', 'spkout', 2, 'J5（横出し・プラグは左 −X から挿す）', '1 SPK−・2 SPK+',
  'スピーカーのリードに<b>直はんだ</b>', '1 白（仮）・2 青（仮）'),
 ('スピーカー IN', 'spkin', 2, 'J4（横出し・プラグは後ろ +Y から挿す）', '1 SPK+・2 SPK−',
  'ReSpeaker の J2（PH2.0 の 2 極プラグ）', '1 青（仮）・2 白（仮）'),
 ('会話ボタン', 'btn2', 2, 'J6（横出し・プラグは前 −Y から挿す）', '1 GND・2 D2',
  'マイクロスイッチの <b>C</b>（GND）と <b>NO</b>（D2）に<b>直はんだ</b>。NC は空き', '1 黒（白でも可）・2 紫'),
 ('リード', 'reed', 2, 'J7 の <b>1・2 番</b>（縦・上から挿す 4 極の殻）', '1 EN・2 GND',
  'つまみの台座のリードスイッチの足に<b>直はんだ</b>（無極性）', '1 橙・2 黒'),
 ('トグル', 'tgl', 2, 'J7 の <b>3・4 番</b>（リードと同じ殻）', '3 EN・4 GND',
  'トグルの端子の<b>中（COM）と上</b>に<b>直はんだ</b>（🔒 ユーザー 2026-09-14「上と真ん中」）', '3 橙・4 黒'),
]


def cut_rows(mat):
    segs = wire_lengths(mat)
    rows = []
    for disp, key, n, port, pins, far, col in BUNDLES:
        ln = max(segs[key])
        cut = int(math.ceil((ln + WIRE_MARGIN) / 5.0) * 5)
        rows.append((disp, n, port, pins, far, col, ln, cut))
    bat = max(segs['bat'])
    return rows, bat


def cuttable(mat):
    rows, bat = cut_rows(mat)
    body = ''.join('<tr><td class="w">{}</td><td class="n">{}</td><td>{}</td><td class="n">{}</td><td>{}</td><td>{}</td>'
                   '<td class="n">{:.0f}</td><td class="n hi"><b>{} mm</b></td></tr>'.format(*r) for r in rows)
    return ('<div class="tw"><table><thead><tr><th>線</th><th>本数</th><th>板の口</th><th>口のピン</th><th>逆の端</th><th>色</th>'
            '<th>模型の実長</th><th>切る長さ</th></tr></thead><tbody>' + body + '</tbody></table></div>'
            '<p>切る長さは、模型の線の道（case_v6_1.scad の <span class="d">wires</span>）の長い方の 1 本に <b>65</b>（v5 と同じ決まり: 端末処理 25 ＋ 天板を箱の脇に置いて挿す余り 40）を足して 5mm 単位に上げた。<b>同じ線の 2 本は同じ長さ</b>に切る。'
            '<b>リードとトグルは 1 つの 4 極の殻（J7 のプラグ）に入る</b>（1・2 番がリード、3・4 番がトグル・gen_sch.py）。</p>'
            '<p><b>電池は切らない。</b>電池のリードの JST-PH のプラグをそのまま板の裏の J10 に挿す（模型の道の実長 %.0f mm。手持ちの電池のリードがこれより短いと届かない）。</p>'
            '<p>色は v5 の決まり（🔒 2026-09-06: GND ＝ 黒か白・会話ボタンの信号 D2 ＝ 紫・EN ＝ 橙）を、v6.1 の同じネットに当てた。スピーカーの ± は v5 と同じく決めていない「仮」。</p>' % bat)


# ---------------------------------------------------------------- 当たりの表（_asm_chk_v61.py の結果）
def chk_max(sw):
    p = os.path.join(CHK, sw + '.txt')
    if not os.path.exists(p):
        return None
    m = re.search(r'MAX ([0-9.]+) mm3', open(p, encoding='utf-8').read())
    return float(m.group(1)) if m else None


def chk_table(rows):
    out = []
    for step, sw, what, note in rows:
        v = chk_max(sw)
        s = '（未実行）' if v is None else ('<b>0</b>' if v < 0.005 else '<b>%.2f</b> mm³' % v)
        out.append('<tr><td class="n">%s</td><td class="d">%s</td><td>%s</td><td class="n hi">%s</td><td>%s</td></tr>' % (step, sw, what, s, note))
    return ('<div class="tw"><table><thead><tr><th>手順</th><th>検査</th><th>動き</th><th>重なりの最大</th><th>読み</th></tr></thead><tbody>'
            + ''.join(out) + '</tbody></table></div>')


# ---------------------------------------------------------------- 共通の文（天板の小組・線）
def acts_topsub(mat):
    ny = mat == 'nylon'
    return [
     '<b>天板を裏返して机に置く。</b>' + ('蓋は天板と左の板が 1 部品なので、左の板が上へ立つ向きで置く。' if ny else ''),
     '<b>リードスイッチ</b>: 足を両端とも下へ曲げてから、つまみの台座の裏の穴へ<b>平らな細い棒</b>で天井に突き当たるまで押し込む（knob_v61.scad の組む順 ⓪）。'
     + ('⚠ ナイロンは穴の天井が 0.5 厚い（<span class="d">REED_TOP</span> −1.0・CASE-V61N.md 5.1）。磁石に反応する距離は実機で見る。' if ny else ''),
     '<b>つまみ</b>: 島をへこみに置き（タブの向きを合わせるだけ）、<span class="d">M2×6</span> 2 本を上から締める。ナットは台座の裏の六角ポケット（天板が裏返しなので口が上を向いて落ちない）。'
     'つまみを軸ごと上から挿し、<b>天板の裏から軸の溝に E リング（呼び 6）を ' + ('2 枚' if ny else '1 枚') + '、左右（±X）から横に差す</b>'
     + ('（🔒 ユーザー 2026-09-15「溝も広げて 2 個入れればいい」）' if ny else '') + '。',
     '<b>磁石</b>: つまみの軸の先に φ4 × 2 を入れる' + ('（ナイロンは穴 φ4.50 に入れて<b>瞬間接着剤</b>で留める・CASE-V61N.md 2 章）' if ny else '（レジンは φ4.10 に圧入）') + '。'
     '磁石は PCB の AS5600 の真上 1.1 に来る（case_v6_1.scad の knob61）。'
     '🔴 <b>v6.1 のつまみの軸は、天板の裏から PCB の上まで伸びた長い軸</b>（🔒 ユーザー 2026-09-14「ノブはながーーい棒を備える事になりますがそれで良い」）。'
     + ('⚠ <b>ところが発注用の hardware/stl/v61n/v61n_knob.stl は v5 と同じ短い軸のまま</b>（高さ 21.4）。長い軸は case の knob61_shaft に絵として描かれているだけで、刷る形になっていない（2026-09-16 夜に気づいた・未対応）。' if ny else
        '⚠ レジンの v6.1 のつまみの STL は書き出していない。長い軸は case の knob61_shaft に絵として描かれているだけで、parts/knob_v61.scad の刷る形は短い軸のまま（2026-09-16 夜・未対応）。'),
     '<b>会話ボタン</b>: バスタブにマイクロスイッチを <span class="d">M2</span> 2 本で留め、押し子を上から通し、天板の裏の腕（ブロック 2 つ・ナット入り）へ耳の下から <span class="d">M2</span> 2 本。',
     '<b>スピーカー</b>: 天板の裏の小判の座へ<b>真下から真っすぐ</b>落とす（グリル側が天板側）。手（倒した板 2 枚）の溝へ <span class="d">M2</span> のナットを 1 個ずつ落とし、リードを後ろの縁から逃がしてバスタブを被せ、<b>壁の外から横に</b> <span class="d">M2×4</span> を 2 本。'
     '（v5 の実物で通っている手順・spk_v61.scad の 2026-09-09 の ✅）',
     '<b>直はんだ 3 か所</b>（手順 0 で作った線の、殻の無い側）: 会話ボタン → スイッチの <b>C（黒）と NO（紫）</b>（端子はレバーの根元から C・NO・NC）、スピーカー OUT → スピーカーのリード、リード → リードスイッチの足。',
     '<b>OLED の L には何も付けない。</b>' + ('ナイロンの L にダボは無い（CASE-V61N.md 8.2）。' if ny else '足の前面のダボ（φ2.8）が折れていないかだけ見る。'),
    ]


# ---------------------------------------------------------------- 手順（ナイロン）
STEPS_N = [
 dict(n='0', t='線を 5 本作る（机の上で）', acts=[
   '<b>v6.1 は 1 枚の PCB に口が集まった</b>ので、v5 の 12 束は無い。線は 5 本（うち 2 本は同じ殻）で、<b>板の側は全部 JST-PH 2.0 の殻</b>。',
   '__CUTTABLE__',
   '<b>板の側だけ先に圧着して殻に入れる。</b>逆の端はスピーカー IN（PH のプラグ）以外は裸のまま（手順 1・4 ではんだ）。',
   '⚠ 殻の 1 番の向きは、板のシルクと <span class="d">hardware/pcb/v61_map.svg</span> で確かめる。表のピンの並びは gen_sch.py の割り当てを写した物。',
 ], note='口の場所と向きは PCB-V61.md 2 章・case_v6_1.scad の PCB_PARTS。'),

 dict(n='1', t='蓋の小組を机の上で作る', img='ntop', cap='蓋を裏から見た図。つまみ・会話ボタン・スピーカーと、羊羹とマッチ棒・OLED の L。',
      acts=lambda: acts_topsub('nylon')),

 dict(n='2', t='底パーツにナットを入れる（空のうちに）', img='n2', acts=[
   '<b>PCB の柱 3 本</b>（電池のケーシングの天板の上に立つ φ7）に <span class="d">M2</span> ナットを横から差す: <b>左前</b>は口が<b>右（+X）</b>、<b>右前・右後ろ</b>は口が<b>斜め 45° 内側</b>（🔒 ユーザー 2026-09-16 夕。真横に開けると溝も口も柱の左へ伸びすぎる）。',
   '<b>左後ろの柱（床から立つ大きい柱）にナットは入れない。</b>ここだけは床の裏からのねじで、相手のナットは<b>蓋の座</b>に入る（手順 8）。',
   '<b>上の柱 4 本</b>: 後ろの 2 本は溝の口が<b>前（−Y）</b>、前の 2 本は<b>箱の内側（X）</b>。左前の柱は前の壁へ 0.8 食い込んでいて、溝は Y −0.15〜4.45（前の肉 1.65・後ろの肉 0.85）。',
   '<b>右前の上の柱のナットは、必ず OLED より先。</b>溝の口の前 1.25 に OLED の板の右端が来る。',
   '左前の柱の奥行きが短いのは、ReSpeaker のボタン K1 が真上から降りる道を空けるため（CASE-V61N.md 8.2）。',
 ], warn='ナイロンの溝は呼び ＋0.5（MJF の穴の公差 ±0.3）でナットは緩い。<b>ねじを締めるまで底パーツを傾けない・伏せない。</b>',
    note='v6.1n の柱はどれも横差しの溝で、口の前に物が来ると入らない（2026-09-08「入れられないナット入れ」）。空の底パーツがいちばん手が入る。'),

 dict(n='3', t='PCB を上から入れて右へ押す', img='n3', acts=[
   '<b>板の裏の口（J10・電池）には、まだ何も挿さない</b>（電池は手順 7）。',
   '__PCBMOVE__',
   '板の上から <span class="d">M2×6</span> を <b>3 本</b>（<b>左前・右前・右後ろ</b>）。<b>左後ろはここでは締めない</b>── 最後に床の裏から 1 本で、床・柱・板・蓋 をまとめて締める（手順 8。🔒 ユーザー「PCB の留めは上から 3 本、下から 1 本」）。',
 ], note='PCB の欠きは無くなった（2026-09-16 夕）。上から降りてくる物（旧の蓋の足）をやめ、左後ろを**床から立つ柱**にしたため。板に開いているのは留めの穴 4 つと、後ろのレールの逃げ 0.3 だけ。'),

 dict(n='4', t='トグルを背面に付ける', img='n4', acts=[
   '<b>先にトグルの端子の中（COM）と上に、手順 0 のトグルの 2 本をはんだ付けする。</b>',
   '箱の中からトグルのブッシングを背面の穴（座 φ14 の中）へ通し、<b>外から</b>ナットで締める。胴は縦・端子は下向きの列。',
   '<b>レバーから先に、傾けて通す。</b>レバーは必ずどちらかへ 12° 倒れていて、まっすぐ押すと穴の縁に掛かる（下の検査 n_tgl）。',
 ], warn='<b>PCB の後。</b>真上から降ろす PCB の道にトグルの胴がある（🔒 ユーザー 2026-09-16 夕「そりゃそうでしょ」）。'),

 dict(n='5', t='ReSpeaker をライザーごと真上から', img='n5', img2='rspsub',
      cap2='机の上の小組: ReSpeaker（XIAO 付き）の XIAO のピンに、ライザーの前向きのメス 2 個を挿した物。', acts=[
   '<b>机の上で</b>、XIAO のライザーの前向きのメスを XIAO のピンへ挿す。<b>USB-C を左にして数えて</b>、下の列は 3〜6 本目（D2・D3・SDA・SCL）、上の列は 1〜3 本目（5V・GND・3V3）。'
   '🔴 7 本のピンに 4 連・3 連のメスは 2 通り以上の位置で入る。1 本ずれると上の列は 5V が GND に乗る。挿したらライザーの左端が XIAO の USB-C 側の端と揃っているか見る。',
   '<b>机の上で</b>、手順 0 のスピーカー IN の片端を ReSpeaker のスピーカーソケット J2 へ挿す。',
   '<b>ReSpeaker とライザーを一緒に持ち、真上から降ろす。</b>ライザーの裏の L 字のメスが PCB の J1（1x07 のオス）に入り、ReSpeaker の板は床の座（台と前の唇）に落ちる。右端は床の<b>止め</b>（右の壁の内側の柱）が受ける。',
   'スピーカー IN の逆の端を PCB の J4 へ、後ろから挿す。',
 ], warn='<b>XIAO の USB-C の殻は左の窓から 1.22 外へ出る。</b>いまは左の板（蓋）が無いので当たらない。ジャックの筒と右の壁の空きは 0.20（⚠ MJF の ±0.3 より小さい。触れば筒は口へ滑り落ちる・CASE-V61N.md 8.4）。',
    note='羊羹とマッチ棒（蓋の裏）が手順 8 で ReSpeaker の頭を 0.3 押さえる。ReSpeaker にねじは無い。'),

 dict(n='6', t='OLED をライザーごと真上から', img='n6', img2='oledsub',
      cap2='机の上の小組: OLED の裏の 4 ピンに、OLED のライザーの前向きのメスを挿した物。', acts=[
   '<b>机の上で</b>、OLED のライザーの前向きのメスを OLED の裏の 4 ピンへ挿す。',
   '<b>OLED とライザーを一緒に持ち、真上から降ろす。</b>ライザーの前向きのメスが ReSpeaker の頭の上を跨ぎ、裏の L 字のメスが PCB の J2（1x04 のオス）に入る。OLED の板の左右の縁は床の<b>ガイド 2 本</b>（内側の上の角が落としてある）に落ち、下辺はリブの前に立つ。',
   'ガラスの面は前の壁の内面の 0.2 後ろ（外面からの奥まり 1.8）。OLED にダボもねじも無い（CASE-V61N.md 8.2）。',
 ], warn='<b>ReSpeaker の後。</b>OLED のライザーのメスが ReSpeaker の頭を跨ぐので、逆の順では入らない。OLED の裏のフィルムが ReSpeaker のマイク面の部品 D1 を 0.4 擦る（⚠ フィルムの高さは写真から置いた値。フィルムは押せば凹む・2026-08-24 ユーザー）。'),

 dict(n='7', t='電池を左の窓から入れて J10 に挿す', img='nbat_in', img2='n7',
      cap='電池を左の窓から入れる途中。', cap2='電池が座った所。', acts=[
   '<b>タブ（線の出る短い辺）を<u>右</u>にして</b>（🔒 ユーザー 2026-09-16 夕「バッテリを Z 軸 180 度回転」。J10 が右へ移ったので線が短い）、左の窓から床の上を右へ滑らせて PCB の下へ入れる。',
   '<b>床と天井の膨らみ（ガイド）を乗り越える。</b>半円断面で角が無いので、電池を押しつければ入る（🔒 ユーザー「電池は膨らみますし、隙間は多少あっても良い」）。余る分はスポンジで詰める。',
   '🔴🔴 <b>挿す前に、電池のプラグの 2 本をテスタの電圧レンジで当たる。</b>3.7〜4.2V が出る側が ＋。<b>J10 の 2 番が ＋・1 番が GND</b>（POWER.md 222 行）。プラグの色では判断しない（2026-09-11 に赤が黒に当たる個体があった）。',
   'J10 は板の裏の<b>右</b>で、<b>縦（トップ型・B2B-PH-K）の下向き</b>。線は電池から真上へ上げて、ケーシングの天板の窓を抜けてそのまま挿さる。',
   '挿したら、通電の前に板の上の VBAT と GND のあいだをテスタで当たり、ショートしていないことを見る。',
 ], warn='ここを逆にすると INA226 から煙が出る。2026-09-11 に実機で起きている（PCB-V61.md 8 章・POWER.md）。'),

 dict(n='8', t='蓋の線を挿して、真上から降ろす', img='nlid_in', img2='n8',
      cap='蓋を降ろす途中（8 上）。左の板は外へ 1.5 たわんで XIAO の USB-C の殻をかわす。', cap2='閉じた所。', acts=[
   '<b>先に蓋の<u>座</u>（左の板の後ろに付く塊）の溝へ <span class="d">M2</span> ナットを後ろから差す。</b>降ろすとハッチの内面が口の 0.8 先を塞ぐので、降ろしている途中も落ちない（🔒 ユーザー「入り口を背面側に付けておけばテープすら不要」）。<b>ナットは座の底（1.6）の上に載る</b>── 下からのねじなのでこの向きでないと蓋を引けない。',
   '<b>蓋を箱の上に持ち、蓋の線を PCB に挿す</b>: スピーカー OUT → <b>J5</b>（板の左の縁・左から）、会話ボタン → <b>J6</b>（前から）、リードとトグルの 4 極 → <b>J7</b>（縦・上から）。',
   '<b>蓋を真上から降ろす。</b>左の板は途中で外へ約 1.5 たわみ、口が XIAO の USB-C の殻に来た所で戻って嵌まる（🔒 ユーザー 2026-09-16・約 8N・ひずみ 0.6%）。板の前後の縁は底パーツの<b>レール</b>に沿って降り、<b>座は PCB の表（Z 13.6）に載る</b>（座は板の面を横切らないので、PCB に欠きは無い）。つまみの軸は ReSpeaker の後ろを通って AS5600 の上へ降りる。',
   '羊羹とマッチ棒が ReSpeaker の頭に当たって蓋が 0.3 浮く。<b>天板のねじ 4 本で引き下ろす</b>: 4 本とも <span class="d">M2×6</span>（ナットは手順 2）。',
   '<b>最後に箱を横に倒し、床の裏の左後ろから <span class="d">M2×18</span> を 1 本。</b>この 1 本が <b>床 → 左後ろの柱 → PCB → 蓋の座のナット</b> をまとめて締める。底パーツと板と蓋が同じねじで留まる（🔒 ユーザー「PCB の留めは上から 3 本、下から 1 本」「板の上の座を持つのはフラップなんだよ」）。',
 ], warn='蓋を<b>回して閉じない</b>。左下の稜を軸にしても右上の稜を軸にしても、左の板が殻と帯に当たる（CASE-V61N.md 8.2 の掃引）。横へずらして押す動きも捨てた（🔒 2026-09-16）。',
    note='たわんで戻る板の縁はレールが受け、下の角はねじが引き戻す（引継ぎ MECH-V61N-HANDOFF.md 3 章）。'),
]

# ---------------------------------------------------------------- 手順（レジン）
STEPS_R = [
 dict(n='0', t='線を 5 本作る（机の上で）', acts=STEPS_N[0]['acts'], note=STEPS_N[0]['note']),

 dict(n='1', t='床にナットを入れ、電池を置く', img='r1', acts=[
   '<b>PCB の柱 4 本</b>（床から立つ φ7）に <span class="d">M2</span> ナットを横から差す。溝の口は<b>箱の内側</b>（左の 2 本は右 +X、右の 2 本は左 −X）。',
   '<b>電池をタブ（線の出る短い辺）を左にして床に置く</b>（X は OLED の中心に揃う・case の BAT_C）。電池にねじも受けも無く、PCB（Z 8.0）が上 2.0 で蓋をする。',
 ], warn='左前・右前の柱の溝は電池の X に向いて開く。<b>ナットは電池より先。</b>',
    note='🔒 ユーザー 2026-09-14「リポ電池を PCB 基板の下へ」「電池を Z 軸 90 度回転」。'),

 dict(n='2', t='PCB を柱に載せ、電池を J10 に挿す', img='r2', acts=[
   '<b>真上から</b>柱 4 本の上へ降ろす。板の後ろの左右の欠きは、後で壁の下の柱が横から入る所。',
   '板の上から <span class="d">M2×6</span> を <b>4 本</b>。',
   '🔴🔴 <b>電池のプラグの 2 本をテスタの電圧レンジで当たり、3.7〜4.2V が出る側が ＋。＋ が手前（OLED 側）のピン</b>に入る向きで、板の裏の <b>J10</b> に<b>左（壁がまだ無い側）から</b>挿す。色では判断しない。挿したら通電の前に VBAT と GND のあいだを当たる（PCB-V61.md 8 章）。',
 ], warn='J10 を逆に挿すと INA226 から煙が出る（2026-09-11 実機）。<b>左の壁より先</b>——壁が立つと板の裏の左の口に手が入らない。'),

 dict(n='3', t='ReSpeaker をライザーごと真上から', img='r3', img2='rspsub',
      cap2='机の上の小組: ReSpeaker（XIAO 付き）の XIAO のピンに、ライザーの前向きのメス 2 個を挿した物。', acts=[
   STEPS_N[5]['acts'][0], STEPS_N[5]['acts'][1],
   '<b>ReSpeaker とライザーを一緒に持ち、真上から降ろす。</b>ライザーの裏の L 字のメスが PCB の J1 に入り、ReSpeaker の板は床の座（台と前の唇）に落ちる。',
   'スピーカー IN の逆の端を PCB の J4 へ、後ろから挿す。',
 ], warn='<b>壁より先。</b>XIAO の USB-C の殻は左の壁の口へ、ジャックの筒は右の壁の口へ入るので、壁が立った後では上から入らない。'),

 dict(n='4', t='OLED のライザーだけを J2 に立てる', img='r4', acts=[
   '<b>OLED は付けない。</b>OLED のライザーだけを、前向きのメスが ReSpeaker の頭を跨ぐ向きで真上から PCB の J2（1x04 のオス）に挿す。',
   'OLED は手順 8 でフロントと一緒に前から差し、そのときピンがこのメスに入る。',
 ], note='レジンの OLED はフロントの窓に 1.0 入り、天板の L のダボが上の 2 穴に前から入る（v5 と同じ）。だから OLED は最後に前から来る。ライザーは先に立てておく。'),

 dict(n='5', t='左右の壁を横から当て、ナットを差す', img='r5', acts=[
   '<b>壁は横から当てる</b>——左の壁を左から、右の壁を右から、<b>まっすぐ X に</b>寄せる。左の壁は XIAO の USB-C の殻が口に入り、下の柱が PCB の左後ろの欠きへ入る。右の壁は充電の USB-C とジャックの筒が口に入る。',
   '<b>壁が立ってから、柱の横穴へ <span class="d">M2</span> ナットを 8 個</b>: 下の柱の前 2 本は口が<b>前（−Y）</b>、下の柱の後ろ 2 本は口が<b>後ろ（+Y）</b>、上の柱の後ろ 2 本は口が<b>前（−Y）</b>、上の柱の前 2 本は口が<b>箱の内側（X）</b>。',
   '下の柱の前後の口は、それぞれフロントとハッチの内面が塞ぐ。',
 ], warn='壁を留めるねじは、フロント・天板・ハッチが揃うまで入らない（下の柱のねじは耳を通すものがある）。<b>締めるまで箱を伏せない。</b>',
    note='下の柱の溝を横差しにしたのは、上向きのポケットだと床の裏からねじ込む力でナットが押し出されて空回りしたため（2026-09-07 実機）。'),

 dict(n='6', t='天板の小組を机の上で作る', img='rtop', cap='天板を裏から見た図。つまみ・会話ボタン・スピーカーと、羊羹とマッチ棒・OLED の L（赤）。',
      acts=lambda: acts_topsub('resin')),

 dict(n='7', t='天板の線を挿し、天板を載せる', img='r7', acts=[
   '<b>天板を箱の上に持ち、線を PCB に挿す</b>: スピーカー OUT → <b>J5</b>（左から）、会話ボタン → <b>J6</b>（前から）、リードとトグルの 4 極 → <b>J7</b>（縦・上から）。トグルの 2 本は後ろへ垂らしておく（手順 9）。',
   '<b>天板を真上から降ろす。</b>羊羹とマッチ棒が ReSpeaker の頭を 0.3 押す。',
   '<b>ねじはまだ締めない。</b>前の 2 本はフロントの耳、後ろの 2 本はハッチの耳を挟んでから（手順 8・9）。',
 ], warn='<b>天板はフロントより先。</b>L のダボは前から OLED の穴へ入る。天板を後にするとダボが穴の上の帯に引っかかる（v5 と同じ理由）。'),

 dict(n='8', t='OLED をフロントに嵌めて、前から差す', img='r8', img2='frontsub',
      cap2='フロントの裏に OLED を嵌めた小組。', acts=[
   '<b>フロントを裏返し、OLED の黒枠を内側から窓へ押し込む。</b>窓は黒枠より縦に 0.15・横に 1.0 大きい（v5 の 🔒 2026-09-07 実機と同じ窓）。',
   '<b>フロントを前からまっすぐ差す。</b>OLED の裏の 4 ピンが手順 4 のライザーのメスへ、天板の L のダボが OLED の上の穴へ入る。上の耳は前の上の柱の上（天板の下）、下の耳は前の下の柱の下の隙間へ。',
   '上は天板の前の 2 本 <span class="d">M2×8</span>（天板 → 耳 → 柱のナット）。下の 2 本は手順 9 の最後にまとめて。',
 ]),

 dict(n='9', t='ハッチにトグルを付け、後ろから押し込んで閉じる', img='r9', acts=[
   '<b>トグルの端子の中（COM）と上に、垂らしておいたトグルの 2 本をはんだ付けし</b>、ハッチの穴へ内側から（レバーから先に、傾けて）通して外からナットで締める。',
   '<b>ハッチの足（下の縁の真ん中）の横穴へ <span class="d">M2</span> ナットを前から差す。</b>',
   '<b>ハッチを垂直のまま、真後ろから押し込む。</b>上の耳 2 つが後ろの上の柱の上（天板の下）へ、足が床の上を滑る。',
   '天板の後ろの 2 本 <span class="d">M2×8</span>。',
   '<b>最後に箱を倒して床の裏から</b>: 下の柱 4 本へ <span class="d">M2×15</span>（前の 2 本はフロントの下の耳を通る）、ハッチの足へ <span class="d">M2×6</span> を 1 本。',
   '最後の 0.35 でハッチの格子の端が左右の壁の格子の端に乗る（v5 と同じ）。押し込むか、格子の端をやすりで一往復。',
 ], warn='ハッチを<b>倒して掛けない</b>（v5 で 1° 倒すと耳が柱の頭に当たった）。'),
]


# ---------------------------------------------------------------- 呼び名・ねじ・部品
GLOSS = {
 'nylon': [
  ('底パーツ', '床＋前・後ろ・右の壁＋左の壁の前後の縦の帯と床の左の稜＋上の柱 4 本。左は大きな窓（電池の抜け道）。', 'g_shell'),
  ('蓋', '天板＋左の板＋左の板の後ろの下の足。つまみ・会話ボタン・スピーカーの台座を持つ。左の板は L 字のたわみ部品。', 'g_lid'),
  ('左後ろの柱と座', '底パーツの<b>床から立つ柱</b>（PCB はこの頭に載る）と、蓋の左の板が持つ<b>座</b>（PCB の表に載り、中に M2 ナット）。床の裏からの M2×18 1 本がこの 4 つをまとめて締める。', 'g_boss'),
  ('レール', '左の窓の前後の縁の裏の受け。左の板の縁がこれに沿って降りて密着する。', 'g_rail'),
  ('柱', 'PCB の柱（右 2 本は床から・左後ろは隅の台）と、天板を留める上の柱 4 本。ナットは全部横差し。', 'g_nposts'),
  ('座・ガイド・止め', 'ReSpeaker の板の台と前の唇、OLED の下辺のリブ、OLED の左右の縁を挟むガイド 2 本、ReSpeaker の右端の止め。', 'g_seat'),
  ('羊羹とマッチ棒・L', '天板の裏から下りて ReSpeaker の頭を 0.3 押す 2 本と、OLED の裏に当たる L の足 2 本。', 'g_press'),
  ('ライザー', 'XIAO のピンを受けて PCB の J1 に立つ板と、OLED のピンを受けて J2 に立つ板。裏の L 字のメスが下向きに PCB のオスへ挿さる。', 'g_riser'),
 ],
 'resin': [
  ('PCB の柱', '床から立つ φ7 の 4 本。ナットは箱の内側へ開く横差しの溝。', 'g_hposts'),
  ('柱', '左右の壁の内面の下の柱（床の裏から M2×15）と上の柱（天板から M2×8）。ナットは横差し。', 'g_rposts'),
  ('耳と足', 'フロントの上 2・下 2 の耳、ハッチの上 2 の耳と下の足 1。ねじが耳を通って柱へ、足へは床から。', 'g_ears'),
  ('座', 'ReSpeaker の板の台と前の唇、OLED の下辺のリブ。', 'g_seat'),
  ('羊羹とマッチ棒・L', '天板の裏から下りて ReSpeaker の頭を 0.3 押す 2 本と、OLED の裏に当たる L の足（前面にダボ φ2.8）。', 'g_press'),
  ('ライザー', 'XIAO のピンを受けて PCB の J1 に立つ板と、OLED のピンを受けて J2 に立つ板。', 'g_riser'),
 ],
}

SCREWS = {
 'nylon': [
  ('M2 × 6', '3', 'PCB → 柱（上から。ナットは柱の横差しの溝）', '3'),
  ('M2 × 6', '4', '天板 → 上の柱（4 本ともナットは横差し）', '8'),
  ('M2 × 15', '1', '床の裏 → 隅の台 → 蓋の足のナット', '8'),
  ('M2 × 6', '2', 'つまみの島 → 天板（ナットは台座の裏の六角）', '1'),
  ('M2', '2', '会話ボタンのスイッチ → バスタブ', '1'),
  ('M2', '2', '会話ボタンのバスタブ → 天板の腕', '1'),
  ('M2 × 4', '2', 'スピーカーのバスタブ → 天板の手（壁の外から横に）', '1'),
  ('トグルのナット', '1', 'トグル（背面の外から）', '4'),
  ('E リング 呼び 6', '2', 'つまみの軸の溝（ナイロンは 2 枚）', '1'),
 ],
 'resin': [
  ('M2 × 6', '4', 'PCB → 柱（上から）', '2'),
  ('M2 × 8', '2', '天板 → フロントの上の耳 → 前の上の柱', '8'),
  ('M2 × 8', '2', '天板 → ハッチの上の耳 → 後ろの上の柱', '9'),
  ('M2 × 15', '4', '床の裏 → 下の柱（前の 2 本はフロントの下の耳を通る）', '9'),
  ('M2 × 6', '1', '床の裏 → ハッチの足', '9'),
  ('M2 × 6', '2', 'つまみの島 → 天板', '6'),
  ('M2', '2', '会話ボタンのスイッチ → バスタブ', '6'),
  ('M2', '2', '会話ボタンのバスタブ → 天板の腕', '6'),
  ('M2 × 4', '2', 'スピーカーのバスタブ → 天板の手', '6'),
  ('トグルのナット', '1', 'トグル（ハッチの外から）', '9'),
  ('E リング 呼び 6', '1', 'つまみの軸の溝', '6'),
 ],
}
NUTS = {
 'nylon': [('M2', '3', 'PCB の柱', '手順 2'), ('M2', '3', '上の柱（左前は無し）', '手順 2（右前は OLED より先）'),
           ('M2', '1', '蓋の足（口は後ろ）', '手順 8 の最初'), ('M2', '2', 'つまみの台座の裏', '手順 1'),
           ('M2', '4', '会話ボタン（バスタブ 2・天板の腕 2）', '手順 1'), ('M2', '2', 'スピーカーの手', '手順 1')],
 'resin': [('M2', '4', 'PCB の柱', '手順 1（電池より先）'), ('M2', '4', '下の柱', '手順 5（壁を立ててから）'),
           ('M2', '4', '上の柱', '手順 5（壁を立ててから）'), ('M2', '1', 'ハッチの足', '手順 9'),
           ('M2', '2', 'つまみの台座の裏', '手順 6'), ('M2', '4', '会話ボタン', '手順 6'), ('M2', '2', 'スピーカーの手', '手順 6')],
}
PARTS = {
 'nylon': [('底パーツ', '1', 'MJF PA12・hardware/stl/v61n/v61n_shell.stl'), ('蓋', '1', 'MJF PA12・v61n_lid.stl'),
           ('つまみ・島', '各 1', 'v61n_knob.stl・v61n_island.stl（⚠ つまみの軸は短いまま・手順 1）'),
           ('スピーカーのバスタブ', '1', 'v61n_spktub.stl'), ('会話ボタンの押し子・バスタブ', '各 1', 'v61n_btn_piston.stl・v61n_btn_tub.stl')],
 'resin': [('床・天板・左の壁・右の壁・フロント・ハッチ', '各 1', '⚠ v6.1 レジンの STL は書き出していない（case_v6_1.scad の print_* で出す）'),
           ('つまみ・島', '各 1', 'parts/knob_v61.scad（⚠ 軸は短いまま・手順 6）'),
           ('スピーカーのバスタブ', '1', 'parts/spk_v61.scad'), ('会話ボタンの押し子・バスタブ', '各 1', 'parts/btn_v61.scad')],
}
BUY = ('<p>ほかに: PCB（katanori61）・XIAO のライザーと OLED のライザー（どちらも別の小さな板）・ReSpeaker Lite（XIAO 付き）・OLED・'
       '電池（1000mAh）・スピーカー・マイクロスイッチ・リードスイッチ・磁石 φ4 × 2・トグル MTS-102。</p>')

CHECKS = {
 'nylon': [
  ('3', 'n_hub_case', 'PCB を 0.8 左で真上から（case の path_hub と同じ）', '当たりが出る = この動きでは入らない。⭐ 2026-09-17 夜: case 側は道を 4 段（前へ 1.8 逃がす → 右へ → 下ろす → '
   '後ろへ 1.8 押して USB-C を口へ）で書き直して path_hub 0.00。この掃引は「真上から降ろす」古い動きのまま'),
  ('3', 'n_hub_dn', 'PCB を 0.8 左・5.5 前で真上から柱の頭まで', 'マニュアルの動き'),
  ('3', 'n_hub_back', '柱の頭の上で後ろへ 5.5', 'マニュアルの動き'),
  ('3', 'n_hub_right', '右へ 0.8 押す', 'マニュアルの動き。0.01 は充電の USB-C の角（CASE-V61N.md の sk_hub と同じ）'),
  ('4', 'n_tgl', 'トグルを箱の中から背面の穴へ（まっすぐ）', '当たりはレバーが穴の縁に掛かる分（X 42〜45・Z 46〜48）。レバーは必ずどちらかへ 12° 倒れているので、傾けて通す（手順 4）'),
  ('5', 'n_rsp', 'ReSpeaker＋ライザーを真上から', ''),
  ('6', 'n_oled', 'OLED＋ライザーを真上から', 'OLED の裏のフィルムが ReSpeaker の D1 を擦る分。case の path_oled と同じ値'),
  ('7', 'n_bat', '電池を左の窓から（0.5 浮かせて）', ''),
  ('8', 'n_lid', '蓋を真上から 14 → 0.3（左の板は 1.5 たわんだ姿）', 'この刻み（0.5）では 0。case の path_lid（14 段）では 0.07（模型の殻の角が口の R に触れる分）'),
  ('8', 'n_lid_seat', '最後の 0.3（板が戻った姿）', '0.3 の所の当たりは ReSpeaker の押さえ（設計どおり）'),
 ],
 'resin': [
  ('2', 'r_hub', 'PCB を真上から柱へ', ''),
  ('3', 'r_rsp', 'ReSpeaker＋ライザーを真上から', ''),
  ('4', 'r_oriser', 'OLED のライザーだけ真上から', ''),
  ('5', 'r_lwall', '左の壁を左から', ''),
  ('5', 'r_rwall', '右の壁を右から', '0.02 は最後の 0.5 だけ（切り分けていない・かけら）'),
  ('7', 'r_top', '天板の小組を真上から', 'T=0 の当たりは ReSpeaker の押さえ 0.3（設計どおり）'),
  ('7', 'r_top_after_front', '（比べる用）フロントの後で天板を真上から', '当たりが出る = 天板はフロントより先'),
  ('8', 'r_front', 'OLED を嵌めたフロントを前から', '当たりは OLED の 4 ピンがライザーのメスに入る分（X 39〜47・Z 46.2〜46.8・模型のメスの壁とピン）。挿さる動きそのもの'),
  ('9', 'r_hatch', 'トグル付きのハッチを後ろから', '1.18 は最後の 0.5 だけ。ハッチの格子と左右の壁の格子の端（Y 49.4〜49.75）が重なる。v5 と同じ現象で、押し込むか格子の端をやすりで一往復'),
 ],
}
PCBMOVE = ('<b>板を 1.5 持ち上げて、左の窓から差し入れる。</b>右の壁の手前（充電の USB-C の出のぶんだけ手前）で止め、'
           '<b>そのまま垂直に 1.5 下ろして柱の頭に載せ</b>、<b>最後に右へ押して</b>充電の USB-C を右の壁の穴へ入れる。'
           '🔒 ユーザー 2026-09-16 夕「ずらしておろしてからスライドするという 2 動作が必要なんだよ」。'
           '<b>1.5 持ち上げるのは、板の裏の電池の口（J10）が電池のケーシングの天板を越えるため</b>。'
           '上は背面のトグルの座（φ14）まで 13.4 空くので、傾ける必要は無い。'
           '⭐ 2026-09-17 夜: 充電の USB-C が後ろの縁へ移ったので、<b>差し込む間だけ板を前へ 1.8 逃がし、'
           '下ろしてから後ろへ 1.8 押して口へ挿す</b>（case の path_hub 51.4 → 0.00・docs/CASE-V61N.md 9.8）。')



BODY = """
<div class="wrap">
<header class="mast">
  <p class="eyebrow">__EYEBROW__</p>
  <h1>__H1__</h1>
  <p class="sub">__SUB__</p>
  <nav class="rail">__NAV__</nav>
</header>

<section class="sec"><h2>始める前に</h2>
<ul>__BEFORE__</ul></section>

<section class="sec"><h2>全体</h2>
<figure class="wide"><img src="__EXP__" alt="分解図"><figcaption>__EXPCAP__</figcaption></figure>
</section>

<section class="sec"><h2>部品の呼び名</h2>
<p>この手順で使う呼び名。絵の赤い部分がその物。</p>
<div class="gloss">__GLOSS__</div>
</section>

<section class="sec"><h2>手順</h2>
__STEPS__
</section>

<section class="sec"><h2>線</h2>
<figure class="wide"><img src="__WIRES__" alt="線の全体"><figcaption>5 本の道（黄色）。case_v6_1.scad の wires（🔒 ユーザー 2026-09-14「5 本の線の経路は良いと思いますよ」）。</figcaption></figure>
<p>切る長さは手順 0 の表。</p>
</section>

<section class="sec"><h2>ビスとナット</h2>
<div class="tw"><table><thead><tr><th>ビス</th><th>本数</th><th>どこ</th><th>手順</th></tr></thead><tbody>__SCREWROWS__</tbody></table></div>
<div class="tw"><table><thead><tr><th>ナット</th><th>個数</th><th>どこ</th><th>いつ入れる</th></tr></thead><tbody>__NUTROWS__</tbody></table></div>
</section>

<section class="sec"><h2>刷る部品</h2>
<div class="tw"><table><thead><tr><th>部品</th><th>数</th><th>備考</th></tr></thead><tbody>__PARTROWS__</tbody></table></div>
__BUY__
</section>

<section class="sec"><h2>動きの検査</h2>
<p>手順の動きを、動く物を道に沿って少しずつずらした姿と、その手順の時点で箱に在る物との重なり（体積）で当てた。0 が正。
道具は <b>hardware/tools/manual_v61/_asm_chk_v61.py</b>（マニュアルの道具・筐体の検査 stl_v61n.py --check とは別）。
⚠ 平行移動しか当てていない。線（圧着した殻）は相手に入れていない。</p>
__CHECKS__
</section>

__AFTER__
</div>
"""

TEXT = {
 'nylon': dict(
  h1='カタノリ v6.1n<br><em>組み立て（ナイロン）</em>',
  sub='底パーツ＋蓋（天板と左の板）の 2 部品を MJF で刷った版。上から順にやれば組める。<b>順番を変えると入らない物がある</b>ので、理由を各手順の「注意」「なぜ」に書いた。'
      '図面は <b>hardware/case_v6_1.scad</b>（MAT="nylon"）、組む順の出どころは <b>docs/CASE-V61N.md 8.3</b> と <b>docs/MECH-V61N-HANDOFF.md 3 章</b>。',
  before=['<b>向き</b>: 「前」は OLED の側、「後ろ」はトグルの側。「左右」は OLED を正面に見て言う。左に大きな窓がある。',
          '<b>入れる物は全部、蓋が無いうちに上か左から</b>: PCB（上から・最後に右へ 0.8）→ トグル → ReSpeaker（ライザーごと上から）→ OLED（ライザーごと上から）→ 電池（左の窓から）→ 蓋（真上から）。',
          '<b>ナットは空の底パーツに先に入れる。</b>ナイロンの溝は緩いので、ねじを締めるまで箱を傾けない。',
          '<b>電池の J10 は極性をテスタで確かめてから挿す</b>（PCB-V61.md 8 章）。',
          '<b>蓋は真上から</b>。左の板はたわんで XIAO の USB-C をかわす。回さない・ずらさない。'],
  expcap='case_v6_1.scad の explode（MAT="nylon"）。底パーツは置いたまま、蓋は小組ごと上へ、PCB と電池は左の窓から外へ、ReSpeaker と OLED はライザーごと上へ（ライザーは口の向きどおりに離してある）。',
  after='<section class="sec"><h2>電池の交換（組んだ後）</h2><ol class="acts">'
        '<li>床の裏の <span class="d">M2×15</span>（左後ろ）と天板のねじ 4 本を外す。</li>'
        '<li>蓋を真上へ持ち上げる（左の板はまたたわむ）。蓋の線は挿したまま、箱の脇へ置く（線の余り 40 はこのため）。</li>'
        '<li>左の窓から J10 のプラグを抜き、電池を左へ引き出す（J10 の下端は電池の天面の 1.2 上・CASE-V61N.md 8.2）。</li>'
        '<li>新しい電池を同じ向き（タブが左）で入れ、<b>極性をテスタで確かめてから</b> J10 に挿し、蓋を真上から戻す。</li>'
        '</ol><p>🔒 工具なしの交換は捨てた（ユーザー 2026-09-15・CASE-V61N.md 6 章）。</p></section>'),
 'resin': dict(
  h1='カタノリ v6.1<br><em>組み立て（レジン）</em>',
  sub='板 6 枚（床・天板・左右の壁・フロント・ハッチ）を光造形で刷った版。上から順にやれば組める。<b>順番を変えると入らない物がある</b>ので、理由を各手順の「注意」「なぜ」に書いた。'
      '図面は <b>hardware/case_v6_1.scad</b>（MAT="resin"）。'
      '⚠ <b>v6.1 レジンの組む順を書いた資料は無かった。</b>この順は 2026-09-16 夜に v5 の組み方と case の形から私（Claude）が起こし、下の「動きの検査」で当てた物で、ユーザーが決めた順ではない。',
  before=['<b>向き</b>: 「前」は OLED の側、「後ろ」はハッチの側。「左右」は OLED を正面に見て言う。',
          '<b>PCB と ReSpeaker は壁より先</b>（充電の USB-C・XIAO の USB-C・ジャックが壁の口に入る）。<b>壁は横から当てる</b>。',
          '<b>天板はフロントより先</b>（L のダボが前から OLED の穴へ入る）。OLED はフロントに嵌めて前から差す。',
          '<b>フロントとハッチは耳で留まる。</b>天板と床のねじが耳を通って柱へ入るので、そのねじはフロントとハッチを差してから締める。',
          '<b>電池の J10 は極性をテスタで確かめてから挿す</b>（PCB-V61.md 8 章）。'],
  expcap='case_v6_1.scad の explode（MAT="resin"）。',
  after='<section class="sec"><h2>電池の交換（組んだ後）</h2><p>v6.1 に電池のハッチは無い（🔒 ユーザー 2026-09-15）。'
        '左の壁を外して左から抜く: 天板の左の 2 本（M2×8）と床の裏の左の 2 本（M2×15）を外し、左の壁を左へまっすぐ引く（手順 5 の逆）。'
        'J10 のプラグを抜き、電池を PCB の下から左へ引き出す。戻すときは極性をテスタで確かめてから J10 に挿す。'
        '⚠ この道は検査していない（壁を外すとき、天板・フロント・ハッチの耳が柱から抜けるかは当てていない）。</p></section>'),
}


def step_html(mat, s, IM):
    fig = ''
    if s.get('img'):
        fig += '<figure class="sheet"><img src="{}" alt="手順 {}">{}</figure>'.format(
            IM(s['img']), s['n'], '<figcaption>%s</figcaption>' % s['cap'] if s.get('cap') else '')
    if s.get('img2'):
        fig += '<figure class="sheet"><img src="{}" alt="{}"><figcaption>{}</figcaption></figure>'.format(
            IM(s['img2']), s.get('cap2', ''), s.get('cap2', ''))
    bits = []
    if s.get('warn'):
        bits.append('<p class="cal warn"><span class="tag">注意</span>{}</p>'.format(s['warn']))
    if s.get('note'):
        bits.append('<p class="cal note"><span class="tag">なぜ</span>{}</p>'.format(s['note']))
    acts = s['acts']() if callable(s['acts']) else s['acts']
    acts = [a.replace('__CUTTABLE__', cuttable(mat)).replace('__PCBMOVE__', PCBMOVE) for a in acts]
    return ('<section class="step" id="s{n}" data-n="{n}">\n<div class="num"><span>{n}</span></div>\n<div class="body">\n'
            '<h3>{t}</h3>\n{fig}\n<ol class="acts">{acts}</ol>\n{bits}\n</div>\n</section>').format(
                n=s['n'], t=s['t'], fig=fig, acts='\n'.join('<li>%s</li>' % x for x in acts), bits=''.join(bits))


def build(mat):
    IM = lambda k: img(mat, k)
    steps = STEPS_N if mat == 'nylon' else STEPS_R
    T = TEXT[mat]
    gloss = '\n'.join('<figure class="g"><img src="{}" alt="{}"><figcaption><b>{}</b> — {}</figcaption></figure>'
                      .format(IM(k), nm, nm, d) for nm, d, k in GLOSS[mat])
    body = (BODY.replace('__EYEBROW__', MAT[mat]['eyebrow']).replace('__H1__', T['h1']).replace('__SUB__', T['sub'])
            .replace('__NAV__', ' '.join('<a href="#s{0}">{0}</a>'.format(s['n']) for s in steps))
            .replace('__BEFORE__', ''.join('<li>%s</li>' % b for b in T['before']))
            .replace('__EXP__', IM('explode')).replace('__EXPCAP__', T['expcap'])
            .replace('__GLOSS__', gloss).replace('__WIRES__', IM('wires'))
            .replace('__STEPS__', '\n'.join(step_html(mat, s, IM) for s in steps))
            .replace('__SCREWROWS__', '\n'.join('<tr><td class="d">{}</td><td class="n">{}</td><td>{}</td><td class="n">{}</td></tr>'.format(*r) for r in SCREWS[mat]))
            .replace('__NUTROWS__', '\n'.join('<tr><td class="d">{}</td><td class="n">{}</td><td>{}</td><td>{}</td></tr>'.format(*r) for r in NUTS[mat]))
            .replace('__PARTROWS__', '\n'.join('<tr><td><b>{}</b></td><td class="n">{}</td><td>{}</td></tr>'.format(*r) for r in PARTS[mat]))
            .replace('__BUY__', BUY).replace('__CHECKS__', chk_table(CHECKS[mat])).replace('__AFTER__', T['after']))
    head = ('<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            '<title>' + MAT[mat]['title'] + '</title>\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=BIZ+UDPGothic:wght@400;700&family=JetBrains+Mono:wght@400;700&display=swap">\n'
            '<style>' + V4.CSS + '\n.gloss{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}'
            '.gloss figure.g{margin:0;background:#fff;border:1px solid #e3e6ea;border-radius:10px;padding:8px}'
            '.gloss figure.g img{width:100%;height:auto;display:block}.gloss figcaption{font-size:.92em;margin-top:6px;color:#14171c}'
            'figure.sheet figcaption{font-size:.92em;color:#4a5560;margin-top:6px}</style>\n')
    out = os.path.join(ROOT, 'docs', 'manual', MAT[mat]['out'])
    with open(out, 'w', encoding='utf-8') as f:
        f.write(head + body + V4.RAILJS)
    print(out, os.path.getsize(out), 'bytes')


if __name__ == '__main__':
    mats = [a for a in sys.argv[1:] if a in MAT] or ['resin', 'nylon']
    for m in mats:
        if '--no-render' not in sys.argv:
            render(m)
        build(m)
