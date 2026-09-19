# -*- coding: utf-8 -*-
# 組み立てマニュアル v6.1（レジン・板 6 枚）と v6.1n（ナイロン・底パーツ＋蓋）を case_v6_1.scad から作る道具（2026-09-16）。
#
#   python hardware/tools/manual_v61/_asm_manual_v61.py              挿絵を出し直して HTML を 2 枚書く
#   python hardware/tools/manual_v61/_asm_manual_v61.py --no-render  挿絵はそのままで HTML だけ書き直す
#   python hardware/tools/manual_v61/_asm_manual_v61.py nylon        片方だけ（resin / nylon）
#
# 手順の文は下の STEPS_R / STEPS_N にしか無い。段の絵は _asm_sim_v61.scad、呼び名の絵は _asm_gloss_v61.scad。
# 動きの当たりは _asm_chk_v61.py の結果（hardware/check/asm/<SW>.txt の MAX 行）をそのまま表に写す。先に回しておくこと。
# 判定ファイルには模型の刻印（tools/check_stamp.py）が付いていて、今の模型と違えば表に「古い」と出す（値は隠さない）。
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
CHK = os.path.join(HW, 'check', 'asm')          # _asm_chk_v61.py の判定（git に入る）
sys.path.insert(0, os.path.join(HW, 'tools')); import check_stamp            # noqa: E402  判定の刻印を今の模型と比べる
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
    'resin': [('r%d' % n, SIM, 'ST', 'r%d' % n, CAM_D, False) for n in (1, 2, 3, 4, 5, 6, 7, 9, 10, 11)] + [
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
    'nylon': [('n%d' % n, SIM, 'ST', 'n%d' % n, CAM_D, False) for n in (2, 3, 4, 5, 6, 7)] + [   # ⭐ 2026-09-19 トグルの段（旧 n4）を外して繰り上げた
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
 ('スピーカー IN', 'spkin', 2, 'J4（縦・プラグは上から挿す）', '1 SPK+・2 SPK−',
  'ReSpeaker の J2（PH2.0 の 2 極プラグ）', '1 青（仮）・2 白（仮）'),
 ('会話ボタン', 'btn2', 2, 'J6（縦・プラグは上から挿す）', '1 GND・2 D2',
  'マイクロスイッチの <b>C</b>（GND）と <b>NO</b>（D2）に<b>直はんだ</b>。NC は空き', '1 黒（白でも可）・2 紫'),
 ('リード', 'reed', 2, 'J7（縦・上から挿す 2 極の殻）', '1 EN・2 GND',
  'つまみの台座のリードスイッチの足に<b>直はんだ</b>（無極性）', '1 橙・2 黒'),
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
            '<b>リードは J7 の 2 極の殻</b>（⭐ 2026-09-19 にトグルをやめて 4 極 → 2 極・gen_sch.py）。</p>'
            '<p><b>電池は切らない。</b>電池のリードの JST-PH のプラグをそのまま板の裏の J10 に挿す（模型の道の実長 %.0f mm。手持ちの電池のリードがこれより短いと届かない）。</p>'
            '<p>色は v5 の決まり（🔒 2026-09-06: GND ＝ 黒か白・会話ボタンの信号 D2 ＝ 紫・EN ＝ 橙）を、v6.1 の同じネットに当てた。スピーカーの ± は v5 と同じく決めていない「仮」。</p>' % bat)


# ---------------------------------------------------------------- 当たりの表（_asm_chk_v61.py の結果）
def chk_max(sw):
    """(MAX の値, 刻印の状態 ok/old/none)。ファイルが無ければ None"""
    p = os.path.join(CHK, sw + '.txt')
    if not os.path.exists(p):
        return None
    txt = open(p, encoding='utf-8').read()
    m = re.search(r'MAX ([0-9.]+) mm3', txt)
    return (float(m.group(1)) if m else None, check_stamp.state(check_stamp.parse_line(txt)))


def sweep_verdict(mat, key):
    """tools/sweep_chk.py の判定（hardware/check/<mat>/sweep/<key>.json）。判定と、了承済み／新しい当たりの数、刻印の状態、了承の理由
    理由は台帳 hardware/sweep_accept.json から id で引く（ここに書き写さない。台帳を直せば表が付いてくる）"""
    import json
    p = os.path.join(HW, 'check', mat, 'sweep', key + '.json')
    if not os.path.exists(p):
        return None
    r = json.load(open(p, encoding='utf-8'))
    why = {a['id']: a['why'] for a in json.load(open(os.path.join(HW, 'sweep_accept.json'), encoding='utf-8'))['accept']}
    ids = sorted(set(o['acc'] for o in r.get('ok', []) if o.get('acc')))
    acc = ''.join('<br><span class="d">%s</span>: %s' % (i, why.get(i, '（台帳に無い）')) for i in ids)
    return ('<b>%s</b>（了承済み %d・新 %d）' % (r['verdict'], len(r.get('ok', [])), len(r.get('new', []))), check_stamp.state(r.get('src')), acc)


STALE = {'ok': '', 'old': ' <span class="old">古い（模型が変わった。回し直す）</span>', 'none': ' <span class="old">刻印無し</span>'}


def chk_table(rows, mat='nylon'):
    out = []
    for step, sw, what, note in rows:
        if sw.startswith('sweep:'):
            v = sweep_verdict(mat, sw[6:])
            s = '（未実行: python hardware/tools/sweep_chk.py --mat %s %s）' % (mat, sw[6:]) if v is None else v[0] + STALE[v[1]]
            acc = '' if v is None else v[2]
            out.append('<tr><td class="n">%s</td><td class="d">%s</td><td>%s</td><td class="n hi">%s</td><td>%s</td></tr>' % (step, sw, what, s, note + acc))
            continue
        v = chk_max(sw)
        s = '（未実行）' if v is None else (('<b>0</b>' if v[0] < 0.005 else '<b>%.2f</b> mm³' % v[0]) + STALE[v[1]])
        out.append('<tr><td class="n">%s</td><td class="d">%s</td><td>%s</td><td class="n hi">%s</td><td>%s</td></tr>' % (step, sw, what, s, note))
    return ('<div class="tw"><table><thead><tr><th>手順</th><th>検査</th><th>動き</th><th>重なりの最大</th><th>読み</th></tr></thead><tbody>'
            + ''.join(out) + '</tbody></table></div>')


# ---------------------------------------------------------------- 共通の文（天板の小組・線）
def acts_topsub(mat):
    ny = mat == 'nylon'
    return [
     '<b>天板を裏返して机に置く。</b>' + ('蓋は天板と左の板が 1 部品なので、左の板が上へ立つ向きで置く。' if ny else ''),
     '<b>リードスイッチ</b>: 足を両端とも下へ曲げてから、つまみの台座の裏の穴へ<b>平らな細い棒</b>で天井に突き当たるまで押し込む（knob_v61.scad の組む順 ⓪）。'
     '台座の裏の後ろの縁は 1 段掘り上げてあり、押し込む距離は入口から 4.5（圧入の座 3.5 ＋ 呼び込み 1.0・⭐ 2026-09-19 に 8.0 から。🔒 ユーザー「もう少し入れやすくしたい」）。'
     + ('⚠ ナイロンは穴の天井が 0.5 厚い（<span class="d">REED_TOP</span> −1.0・CASE-V61N.md 5.1）。磁石に反応する距離は実機で見る。' if ny else ''),
     '<b>つまみ</b>: 島をへこみに置き（タブの向きを合わせるだけ）、<span class="d">M2×6</span> 2 本を上から締める。ナットは台座の裏の六角ポケット（天板が裏返しなので口が上を向いて落ちない）。'
     'つまみを軸ごと上から挿し、<b>天板の裏から軸の溝に E リング（呼び 6）を ' + ('2 枚' if ny else '1 枚') + '、左右（±X）から横に差す</b>'
     + ('（🔒 ユーザー 2026-09-15「溝も広げて 2 個入れればいい」）' if ny else '') + '。',
     '<b>磁石</b>: つまみの軸の先に φ4 × 2 を入れる' + ('（ナイロンは穴 φ4.50 に入れて<b>瞬間接着剤</b>で留める・CASE-V61N.md 2 章）' if ny else '（レジンは φ4.10 に圧入）') + '。'
     '磁石は PCB の AS5600 の真上 1.1 に来る（case_v6_1.scad の knob61）。'
     '🔴 <b>v6.1 のつまみの軸は、天板の裏から PCB の上まで伸びた長い軸</b>（🔒 ユーザー 2026-09-14「ノブはながーーい棒を備える事になりますがそれで良い」）。'
     + ('発注用の hardware/stl/v61n/v61n_knob.stl は長い軸（高さ 42.0・⭐ 2026-09-19）。' if ny else
        'レジンの v6.1 のつまみは case_v6_1.scad の <span class="d">print_knob61</span> を <span class="d">-D MAT="resin"</span> で書き出す（長い軸・⭐ 2026-09-19）。'),
     '<b>会話ボタン</b>: <b>先に天板の裏の腕（ブロック 2 つ）の溝へ <span class="d">M2</span> ナットを 2 個、<u>バスタブ側（内側）の口</u>から差す</b>（🔒 ユーザー 2026-09-18「ナットの入口を内側に」。バスタブを付けると外壁が口を塞ぐ）。'
     'バスタブにマイクロスイッチを <span class="d">M2</span> 2 本で留め、押し子を上から通し、腕へ耳の下から <span class="d">M2</span> 2 本。',
     '<b>スピーカー</b>: <b>先に手（倒した板 2 枚）の溝へ <span class="d">M2</span> ナットを 1 個ずつ、座の側（内側）から差す</b>（🔒 ユーザー 2026-09-18「スピーカーを入れる前にナット入れるだけでしょ」。入れたスピーカーの胴が口を塞ぐ）。'
     'スピーカーを天板の裏の小判の座へ<b>真下から真っすぐ</b>落とす（グリル側が天板側）。リードを後ろの縁から逃がしてバスタブを被せ、<b>バスタブの裏から上向きに</b> <span class="d">M2×4</span> を 2 本（⭐ 2026-09-18 横ねじをやめて上向きに・spk_v61.scad）。',
     '<b>直はんだ 3 か所</b>（手順 0 で作った線の、殻の無い側）: 会話ボタン → スイッチの <b>C（黒）と NO（紫）</b>（端子はレバーの根元から C・NO・NC）、スピーカー OUT → スピーカーのリード、リード → リードスイッチの足。',
     '<b>OLED の L には何も付けない。</b>' + ('ナイロンの L にダボは無い（CASE-V61N.md 8.2）。' if ny else '足の前面のダボ（φ2.8）が折れていないかだけ見る。'),
    ]


# ---------------------------------------------------------------- 手順（ナイロン）
STEPS_N = [
 dict(n='0', t='線を 4 本作る（机の上で）', acts=[
   '<b>v6.1 は 1 枚の PCB に口が集まった</b>ので、v5 の 12 束は無い。線は 4 本で、<b>板の側は全部 JST-PH 2.0 の殻</b>（⭐ 2026-09-19 にトグルの 2 本が消えた。電源の押しボタンは板に直に付く）。',
   '__CUTTABLE__',
   '<b>板の側だけ先に圧着して殻に入れる。</b>逆の端はスピーカー IN（PH のプラグ）以外は裸のまま（手順 1 ではんだ）。',
   '⚠ 殻の 1 番の向きは、板のシルクと <span class="d">hardware/pcb/v61_map.svg</span> で確かめる。表のピンの並びは gen_sch.py の割り当てを写した物。',
 ], note='口の場所と向きは PCB-V61.md 2 章・case_v6_1.scad の PCB_PARTS。'),

 dict(n='1', t='蓋の小組を机の上で作る', img='ntop', cap='蓋を裏から見た図。つまみ・会話ボタン・スピーカーと、羊羹とマッチ棒・OLED の L。',
      acts=lambda: acts_topsub('nylon')),

 dict(n='2', t='底パーツにナットを入れる（空のうちに）', img='n2', acts=[
   '<b>PCB の柱 3 本</b>（電池のケーシングの天板の上に立つ φ7）に <span class="d">M2</span> ナットを横から差す: <b>左前</b>は口が<b>右（+X）</b>、<b>右前・右後ろ</b>は口が<b>斜め 45° 内側</b>（🔒 ユーザー 2026-09-16 夕。真横に開けると溝も口も柱の左へ伸びすぎる）。',
   '<b>左後ろの柱（床から立つ大きい柱）にナットは入れない。</b>ここだけは床の裏からのねじで、相手のナットは<b>蓋の座</b>に入る（手順 7）。',
   '<b>上の柱 4 本</b>: 後ろの 2 本は溝の口が<b>前（−Y）</b>、前の 2 本は<b>箱の内側（X）</b>。左前の柱は前の壁へ 0.8 食い込んでいて、溝は Y −0.15〜4.45（前の肉 1.65・後ろの肉 0.85）。',
   '<b>右前の上の柱のナットは、必ず OLED より先。</b>溝の口の前 1.25 に OLED の板の右端が来る。',
   '左前の柱の奥行きが短いのは、ReSpeaker のボタン K1 が真上から降りる道を空けるため（CASE-V61N.md 8.2）。',
 ], warn='ナイロンの溝は呼び ＋0.5（MJF の穴の公差 ±0.3）でナットは緩い。<b>ねじを締めるまで底パーツを傾けない・伏せない。</b>',
    note='v6.1n の柱はどれも横差しの溝で、口の前に物が来ると入らない（2026-09-08「入れられないナット入れ」）。空の底パーツがいちばん手が入る。'),

 dict(n='3', t='押しボタンにキャップを差し、PCB を左の窓から入れて後ろへ押す', img='n3', acts=[
   '<b>机の上で、つまみの軸のガイドを PCB に付ける。</b>ガイドは光造形で刷った物（case_v6_1.scad の <span class="d">print_kguide</span>）。裏の口を U4（AS5600）の胴に被せて位置を決め、3 本の足を板の上から <span class="d">M2×8</span> で、基板の裏のナットへ締める。ねじは押さえるだけで、位置は口が決める（足の穴は φ2.8 と大きめ）。締めるときにガイドが U4 から浮いていないか見る（⭐ 2026-09-19・PCB を箱に入れた後では基板の裏に手が入らない）。',
   '<b>机の上で、PCB の電源の押しボタン（SW2・板の後ろの縁）の押し子にキャップを差す。</b>キャップは光造形で刷った物（case_v6_1.scad の <span class="d">print_pwrcap</span>。形は付ける箱の材料で長さが違うので、ナイロンの箱には <span class="d">-D MAT="nylon"</span> で書き出した高さ 3.6 の物）。電源の記号の切れ目を上にして、押し子の先の段まで押し込む。キャップの丸は押し子より 1.3 下へずれて付く（顔の中心を USB-C の口の中心の高さに揃えるため）。鍔（上と左右に出る板）が壁の内側に掛かって抜け止めになる（⭐ 2026-09-19 ハッチのトグルをやめて板の押しボタンにした・PCB-V61.md 3 章）。',
   '<b>板の裏の口（J10・電池）には、まだ何も挿さない</b>（電池は手順 6）。',
   '__PCBMOVE__',
   '板の上から <span class="d">M2×6</span> を <b>2 本</b>（<b>左前・右前</b>）。<b>後ろの 2 本はここでは締めない</b>── 左後ろは最後に床の裏から 1 本で、床・柱・板・蓋 をまとめて締める（手順 7）。右後ろも床の裏から（手順 7・<span class="d">M2×12</span>・柱の頭のナット。板は柱の頭に載るだけ。🔒 ユーザー 2026-09-18「こっちも下から入れる形にしようかね」: 上からだと頭の 26 上に底パーツの上の柱が居てドライバーが入らない）。',
 ], warn='<b>キャップは PCB を箱に入れる前に。</b>鍔が壁の穴より大きいので、箱に入れてから外からは差せない（押し子から抜けても外へ落ちないのはこのため）。',
    note='PCB の欠きは無くなった（2026-09-16 夕）。上から降りてくる物（旧の蓋の足）をやめ、左後ろを**床から立つ柱**にしたため。板に開いているのは留めの穴 4 つと、後ろのレールの逃げ 0.3 だけ。'),

 dict(n='4', t='ReSpeaker をライザーごと真上から', img='n4', img2='rspsub',
      cap2='机の上の小組: ReSpeaker（XIAO 付き）の XIAO のピンに、ライザーの前向きのメス 2 個を挿した物。', acts=[
   '<b>机の上で</b>、XIAO のライザーの前向きのメスを XIAO のピンへ挿す。<b>USB-C を左にして数えて</b>、下の列は 3〜6 本目（D2・D3・SDA・SCL）、上の列は 1〜3 本目（5V・GND・3V3）。'
   '🔴 7 本のピンに 4 連・3 連のメスは 2 通り以上の位置で入る。1 本ずれると上の列は 5V が GND に乗る。挿したらライザーの左端が XIAO の USB-C 側の端と揃っているか見る。',
   '<b>机の上で</b>、手順 0 のスピーカー IN の片端を ReSpeaker のスピーカーソケット J2 へ挿す。',
   '<b>ReSpeaker とライザーを一緒に持ち、真上から降ろす。</b>ライザーの裏の L 字のメスが PCB の J1（1x07 のオス）に入り、ReSpeaker の板は床の座（台と前の唇）に落ちる。右端は床の<b>止め</b>（右の壁の内側の柱）が受ける。',
   'スピーカー IN の逆の端を PCB の J4 へ、上から挿す（J4 は縦・2026-09-16 夕）。',
 ], warn='<b>XIAO の USB-C の殻は左の窓から 1.22 外へ出る。</b>いまは左の板（蓋）が無いので当たらない。ジャックの筒と右の壁の空きは 0.20（⚠ MJF の ±0.3 より小さい。触れば筒は口へ滑り落ちる・CASE-V61N.md 8.4）。',
    note='羊羹とマッチ棒（蓋の裏）が手順 7 で ReSpeaker の頭を 0.3 押さえる。ReSpeaker にねじは無い。'),

 dict(n='5', t='OLED をライザーごと真上から', img='n5', img2='oledsub',
      cap2='机の上の小組: OLED の裏の 4 ピンに、OLED のライザーの前向きのメスを挿した物。', acts=[
   '<b>机の上で</b>、OLED のライザーの前向きのメスを OLED の裏の 4 ピンへ挿す。',
   '<b>OLED とライザーを一緒に持ち、真上から降ろす。</b>ライザーの前向きのメスが ReSpeaker の頭の上を跨ぎ、裏の L 字のメスが PCB の J2（1x04 のオス）に入る。OLED の板の左右の縁は床の<b>ガイド 2 本</b>（内側の上の角が落としてある）に落ち、下辺はリブの前に立つ。',
   'ガラスの面は前の壁の内面の 0.2 後ろ（外面からの奥まり 1.8）。OLED にダボもねじも無い（CASE-V61N.md 8.2）。',
 ], warn='<b>ReSpeaker の後。</b>OLED のライザーのメスが ReSpeaker の頭を跨ぐので、逆の順では入らない。OLED の裏のフィルムが ReSpeaker のマイク面の部品 D1 を 0.4 擦る（⚠ フィルムの高さは写真から置いた値。フィルムは押せば凹む・2026-08-24 ユーザー）。'),

 dict(n='6', t='電池を左の窓から入れて J10 に挿す', img='nbat_in', img2='n6',
      cap='電池を左の窓から入れる途中。', cap2='電池が座った所。', acts=[
   '<b>タブ（線の出る短い辺）を<u>右</u>にして</b>（🔒 ユーザー 2026-09-16 夕「バッテリを Z 軸 180 度回転」。J10 が右へ移ったので線が短い）、左の窓から床の上を右へ滑らせて PCB の下へ入れる。',
   '<b>床と天井の膨らみ（ガイド）を乗り越える。</b>半円断面で角が無いので、電池を押しつければ入る（🔒 ユーザー「電池は膨らみますし、隙間は多少あっても良い」）。余る分はスポンジで詰める。',
   '🔴🔴 <b>挿す前に、電池のプラグの 2 本をテスタの電圧レンジで当たる。</b>3.7〜4.2V が出る側が ＋。<b>J10 の 2 番が ＋・1 番が GND</b>（POWER.md 222 行）。プラグの色では判断しない（2026-09-11 に赤が黒に当たる個体があった）。',
   'J10 は板の裏の<b>右</b>で、<b>縦（トップ型・B2B-PH-K）の下向き</b>。線は電池から真上へ上げて、ケーシングの天板の窓を抜けてそのまま挿さる。',
   '挿したら、通電の前に板の上の VBAT と GND のあいだをテスタで当たり、ショートしていないことを見る。',
 ], warn='ここを逆にすると INA226 から煙が出る。2026-09-11 に実機で起きている（PCB-V61.md 8 章・POWER.md）。'),

 dict(n='7', t='蓋の線を挿して、真上から降ろす', img='nlid_in', img2='n7',
      cap='蓋を降ろす途中（8 上）。左の板は外へ 1.5 たわんで XIAO の USB-C の殻をかわす。', cap2='閉じた所。', acts=[
   '<b>先に蓋の<u>座</u>（左の板の後ろに付く塊）の溝へ <span class="d">M2</span> ナットを後ろから差す。</b>降ろすとハッチの内面が口の 0.8 先を塞ぐので、降ろしている途中も落ちない（🔒 ユーザー「入り口を背面側に付けておけばテープすら不要」）。<b>ナットは座の底（1.6）の上に載る</b>── 下からのねじなのでこの向きでないと蓋を引けない。',
   '<b>蓋を箱の上に持ち、蓋の線を PCB に挿す</b>: スピーカー OUT → <b>J5</b>（板の左の縁・左から）、会話ボタン → <b>J6</b>（縦・上から）、リードの 2 極 → <b>J7</b>（縦・上から）。',
   '<b>蓋を真上から降ろす。</b>左の板は途中で外へ約 1.5 たわみ、口が XIAO の USB-C の殻に来た所で戻って嵌まる（🔒 ユーザー 2026-09-16・約 8N・ひずみ 0.6%）。板の前後の縁は底パーツの<b>レール</b>に沿って降り、<b>座は PCB の表（Z 13.6）に載る</b>（座は板の面を横切らないので、PCB に欠きは無い）。つまみの軸は ReSpeaker の後ろを通って AS5600 の上へ降りる。',
   '羊羹とマッチ棒が ReSpeaker の頭に当たって蓋が 0.3 浮く。<b>天板のねじ 4 本で引き下ろす</b>: 4 本とも <span class="d">M2×6</span>（ナットは手順 2）。',
   '<b>最後に箱を横に倒し、床の裏から 2 本。</b>左後ろは <span class="d">M2×18</span>: <b>床 → 左後ろの柱 → PCB → 蓋の座のナット</b> をまとめて締める。右後ろは <span class="d">M2×12</span>: 床 → 柱の頭のナット（板は締めない）。底パーツと板と蓋が同じねじで留まる（🔒 ユーザー「PCB の留めは上から 3 本、下から 1 本」「板の上の座を持つのはフラップなんだよ」）。',
 ], warn='蓋を<b>回して閉じない</b>。左下の稜を軸にしても右上の稜を軸にしても、左の板が殻と帯に当たる（CASE-V61N.md 8.2 の掃引）。横へずらして押す動きも捨てた（🔒 2026-09-16）。',
    note='たわんで戻る板の縁はレールが受け、下の角はねじが引き戻す（引継ぎ MECH-V61N-HANDOFF.md 3 章）。'),
]

# ---------------------------------------------------------------- 手順（レジン）
# 🔒 ユーザー 2026-09-18 の組む順（docs/SWEEP.md 9 章）: ① 電池 ② PCB ③ 手前のねじ ④ 壁を後ろに嵌めて仮締め ⑤ 45° 開く
#   ⑥ ReSpeaker・OLED のライザー ⑦ 壁を閉じる ⑧ 奥のねじを本締め ⑨ 天板 ⑩ OLED 付きのフロント ⑪ ハッチ
#   後ろの PCB ねじは床の裏から（🔒 同日「組み立てづらくなるけど a で行こう」）。2026-09-16 版（壁を横から当てる）はこの順に置き換えた
STEPS_R = [
 dict(n='0', t='線を 5 本作る（机の上で）', acts=STEPS_N[0]['acts'], note=STEPS_N[0]['note']),

 dict(n='1', t='電池を床に置く', img='r1', acts=[
   '<b>電池をタブ（線の出る短い辺）を右にして床に置く</b>（🔒 ユーザー 2026-09-16 夕「バッテリを Z 軸 180 度回転」。J10 が右にあるので線が短い）。電池にねじも受けも無く、PCB（Z 8.0）が上 2.0 で蓋をする。',
   '<b>床の裏にはまだ何も入れない。</b>PCB の前 2 本のナットは手順 2 で、ねじを締めるときに床の裏の六角へ指で当てる（床を伏せて先に入れると、起こしたときに落ちる）。',
 ], note='🔒 ユーザー 2026-09-14「リポ電池を PCB 基板の下へ」。前の 2 本の管（φ5）は床から立っているだけで、電池の左右を通る。'),

 dict(n='2', t='押しボタンにキャップを差し、PCB を前の管 2 本に載せ、手前 2 本を締め、電池を J10 に挿す', img='r2', acts=[
   '<b>机の上で、つまみの軸のガイドを PCB に付ける。</b>ガイドは光造形で刷った物（case_v6_1.scad の <span class="d">print_kguide</span>）。裏の口を U4（AS5600）の胴に被せて位置を決め、3 本の足を板の上から <span class="d">M2×8</span> で、基板の裏のナットへ締める。ねじは押さえるだけで、位置は口が決める（足の穴は φ2.8 と大きめ）。締めるときにガイドが U4 から浮いていないか見る（⭐ 2026-09-19・PCB を箱に入れた後では基板の裏に手が入らない）。',
   '<b>机の上で、PCB の電源の押しボタン（SW2・板の後ろの縁）の押し子にキャップを差す。</b>キャップは光造形で刷った物（case_v6_1.scad の <span class="d">print_pwrcap</span>。形は付ける箱の材料で長さが違うので、レジンの箱には <span class="d">-D MAT="resin"</span> で書き出した高さ 4.8 の物）。電源の記号の切れ目を上にして、押し子の先の段まで押し込む。キャップの丸は押し子より 1.3 下へずれて付く（顔の中心を USB-C の口の中心の高さに揃えるため）。鍔（上と左右に出る板）が壁の内側に掛かって抜け止めになる（⭐ 2026-09-19 ハッチのトグルをやめて板の押しボタンにした・PCB-V61.md 3 章）。',
   '<b>真上から</b>、板の前の 2 穴を床の管 2 本（φ5）の頭に合わせて降ろす。<b>後ろの 2 角はまだ何にも載らない</b>（手順 3 で壁の羽が下に入る）。板に欠きは無い。',
   '板の上から <span class="d">M2×6</span> を <b>前の 2 本</b>。ナットは<b>床の裏の六角</b>（底から 0.6 引っ込んだ所）に指で当てて締める。ゴム足はこの上に貼る。<b>後ろの 2 本は板の上からは締めない</b>（手順 7 で床の裏から）。',
   '🔴🔴 <b>電池のプラグの 2 本をテスタの電圧レンジで当たり、3.7〜4.2V が出る側が ＋。J10 の 2 番が ＋・1 番が GND</b>（POWER.md 222 行）。板の裏の <b>J10</b>（右・縦の下向き）へ、線を電池から真上に上げて挿す。色では判断しない。挿したら通電の前に VBAT と GND のあいだを当たる（PCB-V61.md 8 章）。',
 ], warn='J10 を逆に挿すと INA226 から煙が出る（2026-09-11 実機）。<b>壁より先</b>——壁が立つと板の裏に手が入らない。',
    note='後ろの 2 本を板の上から締める形は捨てた: 頭の 23 上に同じ壁の上の柱が同軸で居て、壁の格子も頭に掛かり、ドライバーが入らない（tools/nutpath_chk.py・🔒 ユーザー 2026-09-18「組み立てづらくなるけど a で行こう」）。'),

 dict(n='3', t='左右の壁を後ろに嵌め、床の裏から仮締め', img='r3', acts=[
   '<b>机の上で、壁の柱の溝へ <span class="d">M2</span> ナットを 1 枚に 4 個</b>: 下の柱の前（口は<b>前 −Y</b>）・下の柱の後ろ＝羽（口は<b>後ろ +Y</b>）・上の柱の後ろ（口は<b>前 −Y</b>）・上の柱の前（口は<b>箱の内側 X</b>）。<b>壁を持って入れるのはこのときだけ</b>（箱に付けてからは前後の口の前に板が来る）。',
   '<b>壁の後ろの羽（下の柱）を PCB の後ろの角の下へ入れる。</b>板の後ろは前の 2 本で留まっているだけなのでたわむ。羽の頭に角が載る。',
   '<b>箱を横に倒し、床の裏から <span class="d">M2×15</span> を後ろの 2 本</b>（床 → 羽の頭のナット。先は板の穴を抜けて 1.0 出る）。<b>仮締め</b>——次の手順でこのねじを軸に壁を回す。',
 ], warn='壁の前をまだ締めない（前の下の柱のねじはフロントの耳を通す・手順 10）。',
    note='後ろのねじが支点になる（🔒 ユーザー 2026-09-18「左右の壁は当該ねじを支点として」）。'),

 dict(n='4', t='壁を 45° 開く', img='r4', acts=[
   '<b>右の壁は反時計回り、左の壁は時計回りに、後ろのねじを軸に前を 45° 開く。</b>壁の前を 2.5 浮かせながら（床と壁の角の 45° の切り合わせが同じ高さにあるので、浮かせないと交わる・docs/SWEEP.md 9 章の表）。',
 ], note='開けるのは ReSpeaker の XIAO の USB-C の殻（左の口へ 1.22 出る）と、右のジャックの筒が、壁の口に横から入るため。壁を閉じた箱には上から入らない。'),

 dict(n='5', t='ReSpeaker をライザーごと真上から', img='r5', img2='rspsub',
      cap2='机の上の小組: ReSpeaker（XIAO 付き）の XIAO のピンに、ライザーの前向きのメス 2 個を挿した物。', acts=[
   STEPS_N[4]['acts'][0], STEPS_N[4]['acts'][1],
   '<b>ReSpeaker とライザーを一緒に持ち、真上から降ろす。</b>ライザーの裏の L 字のメスが PCB の J1 に入り、ReSpeaker の板は床の座（台と前の唇）に落ちる。',
   'スピーカー IN の逆の端を PCB の J4 へ、上から挿す（J4 は縦）。',
 ], warn='壁が 45° 開いているうちに。'),

 dict(n='6', t='OLED のライザーだけを J2 に立てる', img='r6', acts=[
   '<b>OLED は付けない。</b>OLED のライザーだけを、前向きのメスが ReSpeaker の頭を跨ぐ向きで真上から PCB の J2（1x04 のオス）に挿す。',
   'OLED は手順 10 でフロントと一緒に前から差し、そのときピンがこのメスに入る。',
 ], note='ライザーと OLED を一緒に前から入れると ReSpeaker を 472mm³ 削る（docs/SWEEP.md 9 章）。ライザーは先に立てておく。'),

 dict(n='7', t='壁を閉じ、後ろのねじを本締め', img='r7', acts=[
   '<b>壁を閉じる。</b>45° → 20° は 2.5 浮かせたまま、10° と 5° は 1.5、2° は 1.0、最後に 0（case の PATH_LWALL・PATH_RWALL）。左の口が XIAO の USB-C の殻に、右の口がジャックの筒に被さる。',
   '<b>床の裏の後ろ 2 本（<span class="d">M2×15</span>）を本締め。</b>PCB の後ろの 2 角は羽の頭に載るだけで、この 2 本は板を締めない（締めるのは前の 2 本）。',
 ], warn='閉じ切る手前で壁の口が ReSpeaker のコネクタに乗るなら、そこだけ 1.0 浮かせて下ろす（docs/SWEEP.md 9 章「閉じ際」）。'),

 dict(n='8', t='天板の小組を机の上で作る', img='rtop', cap='天板を裏から見た図。つまみ・会話ボタン・スピーカーと、羊羹とマッチ棒・OLED の L（赤）。',
      acts=lambda: acts_topsub('resin')),

 dict(n='9', t='天板の線を挿し、天板を真上から降ろす', img='r9', acts=[
   '<b>天板を箱の上に持ち、線を PCB に挿す</b>: スピーカー OUT → <b>J5</b>（左から）、会話ボタン → <b>J6</b>（縦・上から）、リードの 2 極 → <b>J7</b>（縦・上から）。',
   '<b>天板を真上から降ろす。</b>羊羹とマッチ棒が ReSpeaker の頭を 0.3 押す。',
   '<b>ねじはまだ締めない。</b>前の 2 本はフロントの耳、後ろの 2 本はハッチの耳を挟んでから（手順 10・11）。',
 ], warn='<b>天板はフロントより先。</b>フロントの後だと天板が上から入らない（🔒 ユーザー 2026-09-18・docs/SWEEP.md 9 章）。'),

 dict(n='10', t='OLED をフロントに嵌めて、前から差す', img='r10', img2='frontsub',
      cap2='フロントの裏に OLED を嵌めた小組。', acts=[
   '<b>フロントを裏返し、OLED の黒枠を内側から窓へ押し込む。</b>窓は黒枠より縦に 0.15・横に 1.0 大きい（v5 の 🔒 2026-09-07 実機と同じ窓）。',
   '<b>フロントを前からまっすぐ差す</b>（🔒 ユーザー 2026-09-18「壁を閉じている状態で正面から入れるんだよ」）。OLED の裏の 4 ピンが手順 6 のライザーのメスへ入る。上の耳は前の上の柱の上（天板の下）、下の耳は前の下の柱の下の隙間へ。',
   '上は天板の前の 2 本 <span class="d">M2×8</span>（天板 → 耳 → 柱のナット）。下は床の裏から <span class="d">M2×15</span> を前の 2 本（床 → フロントの下の耳 → 前の下の柱のナット）。',
 ]),

 dict(n='11', t='ハッチを後ろから押し込んで閉じる', img='r11', acts=[
   '<b>ハッチの足（下の縁の真ん中）の横穴へ <span class="d">M2</span> ナットを前から差す。</b>',
   '<b>ハッチを垂直のまま、真後ろから押し込む。</b>上の耳 2 つが後ろの上の柱の上（天板の下）へ、足が床の上を滑る。電源の押しボタンのキャップは顔の丸がハッチの丸穴に入り、鍔は内側に残る（tools/sweep_chk.py --mat resin の hatch で確かめた）。押し込むと足の口の 0.5 先に電池が来て、ナットが落ちなくなる。',
   '天板の後ろの 2 本 <span class="d">M2×8</span>。',
   '<b>最後に箱を倒して床の裏から</b>: ハッチの足へ <span class="d">M2×6</span> を 1 本。これで床の裏は 前 2（M2×15）・後ろ 2（M2×15）・足 1（M2×6）の 5 本。',
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
  ('PCB の管', '床から立つ φ5 の管 2 本（前だけ）。ねじは板の上から通して床の裏のナットへ。後ろの 2 角は壁の羽（下の柱）の頭に載る。', 'g_hposts'),
  ('柱', '左右の壁の内面の下の柱 4 本（床の裏から M2×15・後ろの 2 本は PCB の座も兼ねる羽）と上の柱 4 本（天板から M2×8）。ナットは横差し。', 'g_rposts'),
  ('耳と足', 'フロントの上 2・下 2 の耳、ハッチの上 2 の耳と下の足 1。ねじが耳を通って柱へ、足へは床から。', 'g_ears'),
  ('座', 'ReSpeaker の板の台と前の唇、OLED の下辺のリブ。', 'g_seat'),
  ('羊羹とマッチ棒・L', '天板の裏から下りて ReSpeaker の頭を 0.3 押す 2 本と、OLED の裏に当たる L の足（前面にダボ φ2.8）。', 'g_press'),
  ('ライザー', 'XIAO のピンを受けて PCB の J1 に立つ板と、OLED のピンを受けて J2 に立つ板。', 'g_riser'),
 ],
}

SCREWS = {
 'nylon': [
  ('M2 × 6', '2', 'PCB → 柱（上から・左前と右前。ナットは柱の横差しの溝）', '3'),
  ('M2 × 12', '1', '床の裏 → 右後ろの柱の頭のナット（板は締めない）', '7'),
  ('M2 × 6', '4', '天板 → 上の柱（4 本ともナットは横差し）', '7'),
  ('M2 × 18', '1', '床の裏 → 左後ろの柱 → PCB → 蓋の座のナット', '7'),
  ('M2 × 6', '2', 'つまみの島 → 天板（ナットは台座の裏の六角）', '1'),
  ('M2', '2', '会話ボタンのスイッチ → バスタブ', '1'),
  ('M2', '2', '会話ボタンのバスタブ → 天板の腕', '1'),
  ('M2 × 4', '2', 'スピーカーのバスタブ → 天板の手（バスタブの裏から上向き）', '1'),
  ('M2 × 8', '3', 'つまみの軸のガイドの足 → PCB（ナットは板の裏・押さえるだけ）', '3'),
  ('E リング 呼び 6', '2', 'つまみの軸の溝（ナイロンは 2 枚）', '1'),
 ],
 'resin': [
  ('M2 × 6', '2', 'PCB → 前の管（上から。ナットは床の裏）', '2'),
  ('M2 × 15', '2', '床の裏 → 壁の羽の頭のナット（後ろ。板は締めない）', '3・7'),
  ('M2 × 8', '2', '天板 → フロントの上の耳 → 前の上の柱', '10'),
  ('M2 × 15', '2', '床の裏 → フロントの下の耳 → 前の下の柱', '10'),
  ('M2 × 8', '2', '天板 → ハッチの上の耳 → 後ろの上の柱', '11'),
  ('M2 × 6', '1', '床の裏 → ハッチの足', '11'),
  ('M2 × 6', '2', 'つまみの島 → 天板', '8'),
  ('M2', '2', '会話ボタンのスイッチ → バスタブ', '8'),
  ('M2', '2', '会話ボタンのバスタブ → 天板の腕', '8'),
  ('M2 × 4', '2', 'スピーカーのバスタブ → 天板の手（バスタブの裏から上向き）', '8'),
  ('M2 × 8', '3', 'つまみの軸のガイドの足 → PCB（ナットは板の裏・押さえるだけ）', '2'),
  ('E リング 呼び 6', '1', 'つまみの軸の溝', '8'),
 ],
}
NUTS = {
 'nylon': [('M2', '3', 'PCB の柱（右後ろは床の裏からのねじの相手）', '手順 2'), ('M2', '3', '上の柱（左前は無し）', '手順 2（右前は OLED より先）'),
           ('M2', '1', '蓋の座（口は後ろ）', '手順 7 の最初'), ('M2', '2', 'つまみの台座の裏', '手順 1'),
           ('M2', '4', '会話ボタン（バスタブ 2・天板の腕 2 は内側から・バスタブの前）', '手順 1'), ('M2', '2', 'スピーカーの手（座の側から・スピーカーの前）', '手順 1'),
           ('M2', '3', 'つまみの軸のガイドの足（板の裏）', '手順 3（PCB を箱に入れる前）')],
 'resin': [('M2', '2', 'PCB の前 2 本（床の裏の六角）', '手順 2（締めるとき指で当てる）'), ('M2', '4', '下の柱（前 2・羽 2）', '手順 3（壁を机に持っているとき）'),
           ('M2', '4', '上の柱', '手順 3（同じとき）'), ('M2', '1', 'ハッチの足', '手順 11'),
           ('M2', '2', 'つまみの台座の裏', '手順 8'), ('M2', '4', '会話ボタン（腕 2 は内側から・バスタブの前）', '手順 8'), ('M2', '2', 'スピーカーの手（座の側から・スピーカーの前）', '手順 8'),
           ('M2', '3', 'つまみの軸のガイドの足（板の裏）', '手順 2（PCB を箱に入れる前）')],
}
PARTS = {
 'nylon': [('底パーツ', '1', 'MJF PA12・hardware/stl/v61n/v61n_shell.stl'), ('蓋', '1', 'MJF PA12・v61n_lid.stl'),
           ('つまみ・島', '各 1', 'v61n_knob.stl（長い軸・高さ 42.0）・v61n_island.stl'),
           ('スピーカーのバスタブ', '1', 'v61n_spktub.stl'), ('会話ボタンの押し子・バスタブ', '各 1', 'v61n_btn_piston.stl・v61n_btn_tub.stl'),
           ('電源の押しボタンのキャップ', '1', '<b>光造形（レジン）</b>・case_v6_1.scad の print_pwrcap を <b>MAT="nylon"</b> で書き出す（高さ 3.6）。MJF では電源の記号の彫り（0.4）が出ないので刷らない'),
           ('つまみの軸のガイド', '1', '<b>光造形（レジン）</b>・case_v6_1.scad の print_kguide（板を下・支柱なし）')],
 'resin': [('床・天板・左の壁・右の壁・フロント・ハッチ', '各 1', '⚠ v6.1 レジンの STL は書き出していない（case_v6_1.scad の print_* で出す）'),
           ('つまみ・島', '各 1', 'つまみは case_v6_1.scad の print_knob61（長い軸）・島は parts/knob_v61.scad'),
           ('つまみの軸のガイド', '1', 'case_v6_1.scad の print_kguide（板を下・支柱なし）'),
           ('スピーカーのバスタブ', '1', 'parts/spk_v61.scad'), ('会話ボタンの押し子・バスタブ', '各 1', 'parts/btn_v61.scad'),
           ('電源の押しボタンのキャップ', '1', 'case_v6_1.scad の print_pwrcap（MAT="resin"・高さ 4.8）')],
}
BUY = ('<p>ほかに: PCB（katanori61）・XIAO のライザーと OLED のライザー（どちらも別の小さな板）・ReSpeaker Lite（XIAO 付き）・OLED・'
       '電池（1000mAh）・スピーカー・マイクロスイッチ・リードスイッチ・磁石 φ4 × 2。電源の押しボタン XKB5858-Z-E（LCSC C780038）は PCB に手はんだで付く。</p>'
       '<p><b>XIAO のライザーは板厚 1.2 で頼む</b>（OLED のライザーは 1.6）。裏の L 字のメスは、<b>胴と板の間にはがき 2 枚（計 0.4 前後）を挟んだまま</b>手はんだする。'
       '足が固まったら、はがきは抜いても残してもよい。L 字の軸を PCB の J1 に合わせ、垂らした板の下の端とピンヘッダーの樹脂の間を 0.4 空けるため（case_v6_1.scad の XRISER_T・LSOCK_SHIM）。'
       'コピー用紙は 1 枚 0.09 前後なので 2 枚では足りない。</p>')

CHECKS = {
 'nylon': [
  ('3', 'n_hub_case', 'PCB を 0.8 左で真上から（case の path_hub と同じ）', '当たりが出る = この動きでは入らない。⭐ 2026-09-17 夜: case 側は道を 4 段（前へ 1.8 逃がす → 右へ → 下ろす → '
   '後ろへ 1.8 押して USB-C を口へ）で書き直して path_hub 0.00。この掃引は「真上から降ろす」古い動きのまま'),
  ('3', 'sweep:hub', 'PCB（キャップ付き）を前へ 3.6・上へ 3.5 ずらして左の窓から → 下ろす → 後ろへ 3.6（case の PATH_HUB）', 'マニュアルの動き（tools/sweep_chk.py の判定）。'
   '⚠ _asm_chk_v61.py の n_hub_dn・n_hub_back・n_hub_right は 2026-09-17 より前の動き（前へ 5.5・最後に右へ 0.8）なので表に出さない'),
  ('4', 'n_rsp', 'ReSpeaker＋ライザーを真上から', ''),
  ('5', 'n_oled', 'OLED＋ライザーを真上から', 'OLED の裏のフィルムが ReSpeaker の D1 を擦る分。case の path_oled と同じ値'),
  ('6', 'sweep:bat', '電池を左の窓から（0.5 浮かせて）', ''),
  ('7', 'n_lid', '蓋を真上から 14 → 0.3（左の板は 1.5 たわんだ姿）', 'この刻み（0.5）では 0。case の path_lid（14 段）では 0.07（模型の殻の角が口の R に触れる分）'),
  ('7', 'n_lid_seat', '最後の 0.3（板が戻った姿）', '0.3 の所の当たりは ReSpeaker の押さえ（設計どおり）'),
 ],
 # レジンは 2026-09-18 から tools/sweep_chk.py --mat resin の判定（hardware/check/resin/sweep/<key>.json）を読む。
 #   _asm_chk_v61.py の r_* は 2026-09-16 版の動き（壁を横から当てる）なので使わない
 'resin': [
  ('1', 'sweep:bat', '電池を床へ', ''),
  ('2', 'sweep:hub', 'PCB を真上から管へ', ''),
  ('5', 'sweep:rsp', 'ReSpeaker＋ライザーを真上から（壁は 45° 開いていて相手に居ない）', ''),
  ('7', 'sweep:lwall', '左の壁を後ろのねじを軸に閉じる', ''),
  ('7', 'sweep:rwall', '右の壁を閉じる', ''),
  ('9', 'sweep:top', '天板の小組を真上から', ''),
  ('10', 'sweep:front', 'OLED を嵌めたフロントを前から', ''),
  ('11', 'sweep:hatch', 'ハッチを後ろから（キャップの顔が丸穴に入る）', ''),
 ],
}
PCBMOVE = ('<b>板を前へ 3.6 ずらし、3.5 持ち上げた姿勢で、左の窓から差し入れる。</b>そのまま右の奥まで滑らせ、'
           '<b>垂直に 3.5 下ろして柱の頭に載せ</b>、<b>最後に後ろへ 3.6 押して</b>充電の USB-C と電源の押しボタンのキャップを後ろの壁の口へ挿す（case の PATH_HUB）。'
           '🔒 ユーザー 2026-09-16 夕「ずらしておろしてからスライドするという 2 動作が必要なんだよ」。'
           '<b>3.5 持ち上げるのは、板の裏で一番低い物（OLED のライザーの足・下端 9.0）が柱の頭（12.0）を越えるため</b>（3.0 ＋ 逃げ 0.5・case の PCB_LIFT）。'
           '<b>前へ 3.6 ずらすのは、板の後ろの縁から出ている物が、まっすぐ差すと後ろの壁の中を通るため</b>: 押しボタンのキャップの顔が 3.1・USB-C の胴が 1.3。大きい方 ＋ 逃げ 0.5（case の pcb_fwd・⭐ 2026-09-19 にキャップで 1.8 → 3.6）。'
           '傾ける必要は無い。右へ押す手順は無い（USB-C は右の壁ではなく後ろの壁にある）。')



BODY = """
<div class="wrap">
<header class="mast">
  <p class="eyebrow">__EYEBROW__</p>
  <h1>__H1__</h1>
  <p class="sub">__SUB__</p>
  <p class="stamp">__STAMP__</p>
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
<p>判定は <b>hardware/check/</b> の物（git に入る・模型の刻印つき）。値の横に「古い」と付いた行は、模型が変わってから回していない。</p>
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
  before=['<b>向き</b>: 「前」は OLED の側、「後ろ」は USB-C と電源の押しボタンの側。「左右」は OLED を正面に見て言う。左に大きな窓がある。',
          '<b>入れる物は全部、蓋が無いうちに上か左から</b>: PCB（押しボタンにキャップを差してから・左の窓から入れて下ろし、後ろへ押す）→ ReSpeaker（ライザーごと上から）→ OLED（ライザーごと上から）→ 電池（左の窓から）→ 蓋（真上から）。',
          '<b>ナットは空の底パーツに先に入れる。</b>ナイロンの溝は緩いので、ねじを締めるまで箱を傾けない。',
          '<b>電池の J10 は極性をテスタで確かめてから挿す</b>（PCB-V61.md 8 章）。',
          '<b>蓋は真上から</b>。左の板はたわんで XIAO の USB-C をかわす。回さない・ずらさない。'],
  expcap='case_v6_1.scad の explode（MAT="nylon"）。底パーツは置いたまま、蓋は小組ごと上へ、PCB と電池は左の窓から外へ、ReSpeaker と OLED はライザーごと上へ（ライザーは口の向きどおりに離してある）。',
  after='<section class="sec"><h2>電池の交換（組んだ後）</h2><ol class="acts">'
        '<li>床の裏の <span class="d">M2×15</span>（左後ろ）と天板のねじ 4 本を外す。</li>'
        '<li>蓋を真上へ持ち上げる（左の板はまたたわむ）。蓋の線は挿したまま、箱の脇へ置く（線の余り 40 はこのため）。</li>'
        '<li>左の窓から J10 のプラグを抜き、電池を左へ引き出す（J10 の下端は電池の天面の 1.2 上・CASE-V61N.md 8.2）。</li>'
        '<li>新しい電池を同じ向き（タブが右）で入れ、<b>極性をテスタで確かめてから</b> J10 に挿し、蓋を真上から戻す。</li>'
        '</ol><p>🔒 工具なしの交換は捨てた（ユーザー 2026-09-15・CASE-V61N.md 6 章）。</p></section>'),
 'resin': dict(
  h1='カタノリ v6.1<br><em>組み立て（レジン）</em>',
  sub='板 6 枚（床・天板・左右の壁・フロント・ハッチ）を光造形で刷った版。上から順にやれば組める。<b>順番を変えると入らない物がある</b>ので、理由を各手順の「注意」「なぜ」に書いた。'
      '図面は <b>hardware/case_v6_1.scad</b>（MAT="resin"）。'
      '組む順は 🔒 ユーザー 2026-09-18（docs/SWEEP.md 9 章）。⚠ 2026-09-16 版（壁を横から当てる順）は捨てた。',
  before=['<b>向き</b>: 「前」は OLED の側、「後ろ」はハッチの側。「左右」は OLED を正面に見て言う。',
          '<b>壁は後ろのねじを軸に 45° 開いて、その間に ReSpeaker と OLED のライザーを上から入れ、閉じる。</b>XIAO の USB-C とジャックが壁の口に横から入る形。',
          '<b>PCB を締めるのは前の 2 本だけ</b>（上から）。後ろの 2 角は壁の羽に載り、羽のねじは床の裏から。',
          '<b>天板はフロントより先</b>（フロントの後だと天板が上から入らない）。OLED はフロントに嵌めて前から差す。',
          '<b>フロントとハッチは耳で留まる。</b>天板と床のねじが耳を通って柱へ入るので、そのねじはフロントとハッチを差してから締める。',
          '<b>電池の J10 は極性をテスタで確かめてから挿す</b>（PCB-V61.md 8 章）。'],
  expcap='case_v6_1.scad の explode（MAT="resin"）。',
  after='<section class="sec"><h2>電池の交換（組んだ後）</h2><p>v6.1 に電池のハッチは無い（🔒 ユーザー 2026-09-15）。'
        '左の壁を外して左から抜く: 天板の左の 2 本（M2×8）と床の裏の左の 2 本（M2×15）を外し、左の壁を後ろを軸に開いてから外す（手順 3・4 の逆）。'
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
    st = check_stamp.stamp()
    stamp_p = ('模型 <span class="d">%s</span>（git %s）から %s に焼いた。判定は hardware/check/ の刻印と突き合わせている。'
               % (st['sha'], st['git'], st['ran']))
    body = (BODY.replace('__EYEBROW__', MAT[mat]['eyebrow']).replace('__H1__', T['h1']).replace('__SUB__', T['sub'])
            .replace('__STAMP__', stamp_p)
            .replace('__NAV__', ' '.join('<a href="#s{0}">{0}</a>'.format(s['n']) for s in steps))
            .replace('__BEFORE__', ''.join('<li>%s</li>' % b for b in T['before']))
            .replace('__EXP__', IM('explode')).replace('__EXPCAP__', T['expcap'])
            .replace('__GLOSS__', gloss).replace('__WIRES__', IM('wires'))
            .replace('__STEPS__', '\n'.join(step_html(mat, s, IM) for s in steps))
            .replace('__SCREWROWS__', '\n'.join('<tr><td class="d">{}</td><td class="n">{}</td><td>{}</td><td class="n">{}</td></tr>'.format(*r) for r in SCREWS[mat]))
            .replace('__NUTROWS__', '\n'.join('<tr><td class="d">{}</td><td class="n">{}</td><td>{}</td><td>{}</td></tr>'.format(*r) for r in NUTS[mat]))
            .replace('__PARTROWS__', '\n'.join('<tr><td><b>{}</b></td><td class="n">{}</td><td>{}</td></tr>'.format(*r) for r in PARTS[mat]))
            .replace('__BUY__', BUY).replace('__CHECKS__', chk_table(CHECKS[mat], mat)).replace('__AFTER__', T['after']))
    head = (check_stamp.stamp_line(st, html=True) + '\n'
            '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            '<title>' + MAT[mat]['title'] + '</title>\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=BIZ+UDPGothic:wght@400;700&family=JetBrains+Mono:wght@400;700&display=swap">\n'
            '<style>' + V4.CSS + '\n.old{color:#b00;font-weight:normal;font-size:.85em}\n.mast .stamp{font-size:.85em;color:var(--ink2);margin:4px 0 0}\n.gloss{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}'
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
