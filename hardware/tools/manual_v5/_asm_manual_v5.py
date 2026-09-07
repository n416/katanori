# -*- coding: utf-8 -*-
# 組み立てマニュアル v5（docs/manual/assembly_v5.html）を case_v5.scad から作る道具。
#
#   python hardware/tools/manual_v5/_asm_manual_v5.py             挿絵を出し直して HTML を書く
#   python hardware/tools/manual_v5/_asm_manual_v5.py --no-render 挿絵はそのままで HTML だけ書き直す
#
# 手順は 1 か所（下の STEPS）にしか無い。段の絵は同じ場所の _asm_sim_v5.scad の upto()。
# 呼び名の絵は _asm_gloss_v5.scad。この場所（hardware/tools/manual_v5/）はマニュアルの道具だけ。筐体の部品ではない。線の長さは case_v5 の束（WIRE_LEN=true の echo）から取る。
# ハブの口の表は v4 の道具（frozen/v1-v4/_asm_manual_v4.py の pin_table）を借りる——ハブ基板そのものは v4 と同じ板なので、口の並びと相手は変わらない。
# 図は v5 で向きを変えた（下の hub_map_svg / xiao_svg。ハブは OLED が上・XIAO は USB-C が左＝箱の後ろから見た向き）。
import base64, math, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))          # hardware/tools/manual_v5
HW = os.path.dirname(os.path.dirname(HERE))                  # hardware
ROOT = os.path.dirname(HW)
sys.path.insert(0, os.path.join(HW, 'parts'))                # hub_ports
sys.path.insert(0, os.path.join(HW, 'frozen', 'v1-v4'))      # _asm_manual_v4（CSS・口の表）
import hub_ports
import _asm_manual_v4 as V4

IMGDIR = os.path.join(ROOT, 'docs', 'manual', '_manual_img_v5')
OUT = os.path.join(ROOT, 'docs', 'manual', 'assembly_v5.html')
TMP = os.path.join(HW, '_tmp_v5')
OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.com')

N_STEPS = 13
CAM = ['--projection=p', '--camera=43,36,22,58,0,205,330', '--imgsize=1100,850']
SEQ = ['st%d' % n for n in range(1, N_STEPS + 1)]
WIDE = [('explode', os.path.join(HW, 'case_v5.scad'), 'part', 'explode', '0,0,0,62,0,42,0'),
        ('look',    os.path.join(HW, 'case_v5.scad'), 'part', 'look',    '0,0,0,60,0,25,0'),
        ('wires',   '_asm_sim_v5.scad', 'ST', 'wires', '0,0,0,58,0,205,0'),
        ('door',    '_asm_sim_v5.scad', 'ST', 'door',  '0,0,0,60,0,25,0'),
        ('knob',    os.path.join(HW, 'parts', 'knob_v5.scad'), 'part', 'explode', '0,0,0,62,0,35,0')]
FIXED = [('topsub', '_asm_sim_v5.scad', 'ST', 'topsub', '43,36,22,120,0,25,330'),
         ('claw',   '_asm_sim_v5.scad', 'ST', 'claw',   '64,70,10,70,0,200,120')]
GLOSS_IMGS = ['sara', 'obi', 'maeita', 'dote', 'yokan', 'za', 'L', 'tsume', 'uke', 'futa', 'hashira', 'mimi', 'tub', 'uke_tc']


def run(args):
    subprocess.run([OPENSCAD, '--backend=manifold', '--render=full'] + args, check=True, capture_output=True)


def render():
    os.makedirs(IMGDIR, exist_ok=True)
    for st in SEQ:
        run(CAM + ['-o', os.path.join(IMGDIR, st + '.png'), '-D', 'ST="%s"' % st, os.path.join(HERE, '_asm_sim_v5.scad')]); print('  ', st)
    for name, scad, var, val, cam in WIDE:
        run(['--projection=p', '--autocenter', '--viewall', '--camera=' + cam, '--imgsize=1600,1250',
             '-o', os.path.join(IMGDIR, name + '.png'), '-D', '%s="%s"' % (var, val), os.path.join(HERE, scad)]); print('  ', name)
    for name, scad, var, val, cam in FIXED:
        run(['--projection=p', '--camera=' + cam, '--imgsize=1100,850',
             '-o', os.path.join(IMGDIR, name + '.png'), '-D', '%s="%s"' % (var, val), os.path.join(HERE, scad)]); print('  ', name)
    for g in GLOSS_IMGS:
        run(['--projection=p', '--autocenter', '--viewall', '--camera=0,0,0,60,0,25,0', '--imgsize=1200,900',
             '-o', os.path.join(IMGDIR, 'g_' + g + '.png'), '-D', 'G="%s"' % g, os.path.join(HERE, '_asm_gloss_v5.scad')]); print('  ', g)


def img(name):
    p = os.path.join(IMGDIR, name)
    if not os.path.exists(p):
        return ''
    return 'data:image/png;base64,' + base64.b64encode(open(p, 'rb').read()).decode('ascii')


# ---------------------------------------------------------------- 線の長さ（case_v5 の束の実長）
def wire_lengths():
    """_asm_sim_v5.scad を WIRE_LEN=true で評価して、束ごとの実長 [mm] を集める。"""
    r = subprocess.run([OPENSCAD, '--backend=manifold', '-D', 'ST="wires"', '-D', 'WIRE_LEN=true',
                        '-o', os.path.join(TMP, 'wl.stl'), os.path.join(HERE, '_asm_sim_v5.scad')],
                       capture_output=True, text=True)
    segs = {}
    for m in re.finditer(r'wlen = \["(\w+)", (\d+), ([0-9.]+)\]', r.stderr + r.stdout):
        segs.setdefault(m.group(1), []).append((int(m.group(2)), float(m.group(3))))
    return segs


WIRE_MARGIN = 65   # 端末処理 25 ＋ 天面を机に置くための余り 40（v4 と同じ）
FAN = 7.0          # 口の頭から合流点まで（扇の 1 本ぶん・3 ＋ 4）

# 束: (表示名, 束の名, 線の本数, ハブ側の殻, 逆の端, 1 本の実長の出し方)
#   実長 = 束の道の合計 ＋ 扇。xiao と as5600 は枝が 2 つあるので長い方を取る
BUNDLES = [
 ('XIAO',          'xiao',   7, '1 連（D2）＋ 4 連（SDA・SCL・3V3・GND）＋ 2 連（D3・5V）', 'XIAO の上のピンヘッダ（<b>6 連 × 2</b>。上の列に 5V・GND・3V3＋空き 3、下の列に 空き 2＋D2・D3・SDA・SCL）', 'branch'),
 ('スピーカー IN', 'phin',   2, 'PH2.0 の 2 極プラグ',    'ReSpeaker のスピーカーソケット J2（PH2.0 の 2 極プラグ）', 'ph'),
 ('OLED',          'oled',   4, '4 連',                 'OLED の 4 本ヘッダ（<b>4 連</b>）', 'single'),
 ('つまみ',        'as5600', 5, '4 連（GND は二股）',     'AS5600 の基板の裏の 5 本（<b>1 連 × 5</b>）', 'branch'),
 ('会話ボタン',    'btn2',   2, '2 連',                 'マイクロスイッチの C と NO（<b>直はんだ</b>・NC は空き）', 'sum'),
 ('スピーカー OUT','phout',  2, 'PH2.0 の 2 極プラグ',    'スピーカーのリード（<b>直はんだ</b>）', 'ph'),
 ('電源',          'pwr',    3, '4 連（3 本目は空き）',   'PowerBoost の L 字ピン EN・GND・5Vo（<b>1 連 × 3</b>）', 'bundle'),
 ('電流計',        'ina',    4, '4 連',                 '電流計の後ろの L 字 4 本（<b>4 連</b>）', 'bundle'),
 ('トグル',        'tgl',    2, '2 連',                 'トグルの端子 2 つ（<b>直はんだ</b>・中と下）', 'single'),
 ('充電',          'chg',    2, '（ハブには挿さらない）', 'Type-C 基板の L 字 1・2 本目 → PowerBoost の USB・GND2（<b>両端とも 1 連 × 2</b>）', 'bundle'),
 ('電池→電流計',   'bat',    2, '（ハブには挿さらない）', '電池の JST-PH の受け → 電流計の INPUT ±（<b>1 連 × 2</b>・「延長」）', 'single'),
 ('電流計→JST',    'batout', 2, '（ハブには挿さらない）', '電流計の OUT ± （<b>1 連 × 2</b>）→ PowerBoost の JST に挿す JST-PH のプラグ', 'bundle'),
]


# 線の色（ネットごと・全部の口で同じ）。🔒 2026-09-02 ユーザー: SCL＝緑・SDA＝黄色。🔒 2026-09-06 ユーザー: 会話ボタンの信号＝紫・3V3＝赤・GND＝黒か白・EN＝橙・5V＝茶。
# 「仮」はユーザーが指定していない線。D3（ミュートリレーの駆動）・スピーカー ±（秋月 112495 のリードが青/白）・電池 ±（JST-PH のリードが赤/黒）。
COLOR = {'SCL': '緑', 'SDA': '黄', 'BTN': '紫', 'V33': '赤', 'GND': '黒（白でも可）', 'EN': '橙', 'V5': '茶',
         'IN': '灰（仮）', 'SPKP': '青（仮・スピーカーのリードと同じ）', 'SPKO': '青（仮・同）', 'SPKM': '白（仮・同）',
         'BATP': '赤（仮・電池のリードと同じ）', 'BATM': '黒（仮・同）'}
# 束 → 線の一覧 [(名前, ネット)]。ハブに挿さる束は hub_ports から、挿さらない 3 束はここに書く
HUB_PORT_OF = {'xiao': 'XIAO', 'phin': 'PHIN', 'oled': 'OLED', 'as5600': 'AS5600', 'btn2': 'BTN2',
               'phout': 'PHOUT', 'pwr': 'PWR', 'ina': 'INA', 'tgl': 'TOGGLE'}
OFFBOARD_WIRES = {'chg': [('5V', 'V5'), ('GND', 'GND')],
                  'bat': [('＋', 'BATP'), ('−', 'BATM')], 'batout': [('＋', 'BATP'), ('−', 'BATM')]}


def bundle_wires(key):
    """束の線を [(名前, ネット)] で返す。つまみは GND が二股なので DIR 行を足す（線は 5 本）。電源の空きは線ではない。"""
    if key in HUB_PORT_OF:
        p = {q.id: q for q in hub_ports.ports()}[HUB_PORT_OF[key]]
        ws = [(hub_ports.disp(fn, net), net) for h, fn, net, x, y in p.pins if net]
        if key == 'as5600':
            ws.append(('GND の二股 → DIR', 'GND'))
        return ws
    return OFFBOARD_WIRES[key]


def wire_cells(key):
    return '・'.join('<b>%s</b> %s' % (nm, COLOR[net]) for nm, net in bundle_wires(key))


# 線の色 → 絵の色
COLOR_HEX = {'緑': '#2e9e44', '黄': '#e2c200', '紫': '#7b3fa0', '赤': '#d0342c', '黒': '#26292c', '橙': '#f08a24',
             '茶': '#7a4a1e', '灰': '#8a8f95', '青': '#2a6fd6', '白': '#f4f4f2'}
FAR_KIND = {'xiao': 'dupont', 'phin': 'ph', 'oled': 'dupont', 'as5600': 'dupont', 'btn2': 'bare', 'phout': 'bare',
            'pwr': 'dupont', 'ina': 'dupont', 'tgl': 'bare', 'chg': 'dupont', 'bat': 'dupont', 'batout': 'ph'}
NEAR_KIND = {'chg': 'dupont', 'bat': 'jst', 'batout': 'dupont'}   # ハブに挿さらない 3 束の「ハブ側」の端


# 殻の分け方。束 → [(括りの名前, [(殻の名札, [穴ごとの線の名前]), ...]), ...]。'空' は殻の空きの穴（線は無い）。
# 🔒 XIAO（2026-09-06 ユーザー。7 連の殻は無い）
#    ハブ側: D2 の 1 連 ＋ SDA・SCL・3V3・GND の 4 連 ＋ D3・5V の 2 連（口の並びのまま）
#    XIAO 側: 6 連 × 2。上の列 1〜6 本目＝5V・GND・3V3・空・空・空、下の列 1〜6 本目＝空・空・D2・D3・SDA・SCL。7 本目は裸。
#    ハブの並び（D2 SDA SCL 3V3 GND D3 5V）と XIAO の並びが違うので、線は途中で交差する。
#    'each' は 1 連 × n（線ごとに殻 1 個）。無い束は殻 1 個。
NEAR_GROUPS = {'xiao': [('1 連', ['D2']), ('4 連', ['SDA', 'SCL', '3V3', 'GND']), ('2 連', ['D3', '5V'])]}
FAR_GROUPS = {
 'xiao': [('下の列', [('6 連（1〜6 本目。1・2 は空き）', ['空', '空', 'D2', 'D3', 'SDA', 'SCL'])]),
          ('上の列', [('6 連（1〜6 本目。4〜6 は空き）', ['5V', 'GND', '3V3', '空', '空', '空'])])],
 'as5600': 'each', 'pwr': 'each', 'chg': 'each', 'bat': 'each'}


def cut_fig(segs):
    """手順 0 の切り出し図。束ごとに線を実寸比（1mm = 3px）の色で描く。左がハブ側、右が逆の端。殻ごとに箱、空きの穴は「空」。
    右端は殻の穴の順に並ぶので、ハブの並びと違う束（XIAO）は線が途中で交差する。両端の銅色は被覆をむく所。"""
    SC = 3.0            # px / mm
    STRIP = 3.0         # 被覆をむく長さ [mm]（絵の上だけ・端末処理 25 の内）
    X0, XL = 240, 30    # 線の左端の X・名札の X
    PITCH = 17          # 線の間隔
    GAP_SHELL, GAP_GRP, GAP = 6, 12, 30   # 殻と殻・括りと括り・束と束の間
    rows = {r[0]: r for r in cut_rows(segs)}
    maxcut = max(r[5] for r in rows.values())
    W = X0 + maxcut * SC + 470
    y = 34
    o = []
    for disp, key, n, shell, far, how in BUNDLES:
        r = rows[disp]; cut = r[5]; wires = bundle_wires(key)
        names = [nm for nm, net in wires]
        near = shell if key in HUB_PORT_OF else {'chg': 'Type-C 基板側は 1 連 × 2', 'bat': '電池側は JST-PH の受け',
                                                'batout': '電流計側は 1 連 × 2'}[key]
        o.append('<text x="%d" y="%d" font-size="15" font-weight="700" fill="%s">%s</text>'
                 '<text x="%d" y="%d" font-size="13" fill="%s">%d 本・<tspan font-weight="700" fill="#b8860b">%d mm</tspan>'
                 '（模型の実長 %d）・左の殻: %s</text>'
                 % (XL, y, hub_ports.PAL['edge'], disp, XL + 150, y, hub_ports.PAL['sub'], n, cut, r[4], re.sub(r'<[^>]+>', '', near)))
        y += 14
        top = y
        x1 = X0 + cut * SC
        # 逆の端の括りと殻
        fg = FAR_GROUPS.get(key)
        if fg == 'each':
            groups = [('', [('1 連' if i == 0 else '', [nm])]) for i, nm in enumerate(names)]
            g_shell, g_grp = 3, 3
        elif fg:
            groups = fg; g_shell, g_grp = GAP_SHELL, GAP_GRP
        else:
            groups = [('', [('', names)])]; g_shell, g_grp = 0, 0
        flat = [nm for gname, shells in groups for lab, ns in shells for nm in ns if nm != '空']
        assert sorted(flat) == sorted(names), (key, flat, names)
        yl = {nm: top + i * PITCH + PITCH / 2 for i, nm in enumerate(names)}     # 左（ハブ側）の Y
        yr, yy, empties, shell_span = {}, top + PITCH / 2, [], []                # 右（逆の端）の Y・空きの穴の Y・殻の上下
        for gi, (gname, shells) in enumerate(groups):
            for si, (lab, ns) in enumerate(shells):
                st = yy - PITCH / 2
                for nm in ns:
                    if nm == '空':
                        empties.append(yy)
                    else:
                        yr[nm] = yy
                    yy += PITCH
                shell_span.append((gname if si == 0 else '', lab, st, yy - PITCH / 2, len(shells) > 1))
                if si < len(shells) - 1:
                    yy += g_shell
            if gi < len(groups) - 1:
                yy += g_grp
        bot_l, bot_r = top + len(names) * PITCH, yy - PITCH / 2
        xa, xb = X0 + (x1 - X0) * 0.50, X0 + (x1 - X0) * 0.68                  # 斜めに渡る区間
        # 線。交差する線が上に来るよう、右端の Y が左端と違う線を後に描く
        order = sorted(wires, key=lambda w: yl[w[0]] != yr[w[0]])
        for nm, net in order:
            cname = COLOR[net]; hexc = COLOR_HEX[cname[0]]
            y0, y1 = yl[nm], yr[nm]
            o.append('<text x="%d" y="%.1f" font-size="12" fill="%s" text-anchor="end"><tspan font-weight="700" fill="%s">%s</tspan>　%s</text>'
                     % (X0 - 36, y0 + 4, hub_ports.PAL['sub'], hub_ports.PAL['edge'], nm, cname.split('（')[0]))
            pts_cu = [(X0, y0), (xa, y0), (xb, y1), (x1, y1)] if y0 != y1 else [(X0, y0), (x1, y1)]
            pts_in = [(X0 + STRIP * SC, y0), (xa, y0), (xb, y1), (x1 - STRIP * SC, y1)] if y0 != y1 \
                else [(X0 + STRIP * SC, y0), (x1 - STRIP * SC, y1)]
            d_cu = 'M ' + ' L '.join('%.1f %.1f' % p for p in pts_cu)
            d_in = 'M ' + ' L '.join('%.1f %.1f' % p for p in pts_in)
            o.append('<path d="%s" fill="none" stroke="#b87333" stroke-width="3"/>' % d_cu)      # 銅
            if cname[0] == '白':
                o.append('<path d="%s" fill="none" stroke="#9a9a96" stroke-width="9" stroke-linejoin="round" stroke-opacity="0.45"/>' % d_in)
            o.append('<path d="%s" fill="none" stroke="%s" stroke-width="7" stroke-linejoin="round"/>' % (d_in, hexc))   # 被覆
        # ハブ側の端（左）: 殻 1 個か、NEAR_GROUPS の分け方で複数
        ng = NEAR_GROUPS.get(key, [('', names)])
        for lab, ns in ng:
            o.append(_end_box(X0 - 2, yl[ns[0]] - PITCH / 2 + 1, yl[ns[-1]] + PITCH / 2 - 1, NEAR_KIND.get(key, 'dupont'), '', left=True))
            if lab:
                o.append('<text x="%.1f" y="%.1f" font-size="9" fill="#d5dbe0" text-anchor="middle" '
                         'transform="rotate(-90 %.1f %.1f)">%s</text>'
                         % (X0 - 15, (yl[ns[0]] + yl[ns[-1]]) / 2 + 3, X0 - 15, (yl[ns[0]] + yl[ns[-1]]) / 2 + 3, lab))
        # 逆の端（右）: 殻ごとに箱と名札。空きの穴は「空」。括りが 2 つ以上の殻を持つときは縦線で括る
        kind = FAR_KIND[key]
        bw = 26 if kind == 'dupont' else 22 if kind in ('ph', 'jst') else 0
        for gname, lab, st, sb, multi in shell_span:
            o.append(_end_box(x1 + 2, st, sb, kind, '', left=False))
            txt = ('<tspan font-weight="700" fill="%s">%s</tspan>　' % (hub_ports.PAL['edge'], gname) if gname else '') + lab
            if txt:
                o.append('<text x="%.1f" y="%.1f" font-size="11" fill="%s">%s</text>'
                         % (x1 + 2 + bw + (14 if multi else 6), (st + sb) / 2 + 4, hub_ports.PAL['sub'], txt))
        for ye in empties:
            o.append('<text x="%.1f" y="%.1f" font-size="10" fill="#c9c4b8" text-anchor="middle">空</text>' % (x1 + 2 + bw / 2, ye + 4))
        for gname, shells in groups:
            if len(shells) > 1:
                g_top = min(st for g, l, st, sb, m in shell_span if g == gname); g_bot = max(sb for g, l, st, sb, m in shell_span if g == gname)
                bx = x1 + 2 + bw + 7
                o.append('<path d="M %.1f %.1f L %.1f %.1f L %.1f %.1f L %.1f %.1f" fill="none" stroke="%s" stroke-width="1.4"/>'
                         % (bx - 3, g_top + 2, bx, g_top + 2, bx, g_bot - 2, bx - 3, g_bot - 2, hub_ports.PAL['edge']))
        # 逆の端の説明（束の右）
        tx = x1 + 2 + bw + (230 if fg and fg != 'each' else 60 if fg == 'each' else 8)
        o.append(_end_box(tx, top, max(bot_l, bot_r), 'none', re.sub(r'<[^>]+>', '', far), left=False))
        y = max(bot_l, bot_r) + GAP
    H = y
    o.insert(0, '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
                'preserveAspectRatio="xMidYMid meet" font-family="system-ui, sans-serif">' % (W, H, W, H))
    o.insert(1, '<text x="%d" y="18" font-size="12" fill="%s">← ハブ側（殻に圧着して挿す）　　線は実寸比（%d mm ＝ %d px）。両端の銅色は被覆をむく所　　逆の端 →</text>'
             % (X0, hub_ports.PAL['sub'], 100, int(100 * SC)))
    o.append('</svg>')
    return ('<figure class="wide">' + ''.join(o) +
            '<figcaption>束ごとの線の色と切る長さ。<b>同じ束の線は全部同じ長さ</b>。左がハブ側の殻、右が逆の端の殻で、「空」は殻の空きの穴（線を入れない）。'
            '<b>XIAO はハブ側が 1 連＋4 連＋2 連、XIAO 側が 6 連 × 2</b>（上の列 5V・GND・3V3＋空き 3、下の列 空き 2＋D2・D3・SDA・SCL）で、並びが違うので線が途中で交差する。'
            '色は全部の口で同じ（GND は黒か白のどちらでもよい）。「仮」の線（D3・スピーカー ±・電池 ±）はユーザーの指定がなく、相手のリードの色に合わせて置いた。</figcaption></figure>')


def _end_box(x, top, bot, kind, label, left):
    """線の端の形。dupont＝黒い殻、ph／jst＝白いプラグ、bare＝殻なし（直はんだ）、none＝文だけ。label はその横の文（24 字で折る）。"""
    h = max(bot - top, 14)
    txt = re.sub(r'\s+', ' ', label).replace('<br>', ' ')
    parts = []
    if kind == 'dupont':
        bw = 26
        bx = x - bw if left else x
        parts.append('<rect x="%.1f" y="%.1f" width="%d" height="%.1f" rx="3" fill="#2f3a43"/>' % (bx, top + 1, bw, h - 2))
    elif kind in ('ph', 'jst'):
        bw = 22
        bx = x - bw if left else x
        parts.append('<rect x="%.1f" y="%.1f" width="%d" height="%.1f" rx="3" fill="#f4f4f2" stroke="#9a9a96" stroke-width="1.2"/>' % (bx, top + 1, bw, h - 2))
    else:
        bw = 0
    tx = (x - bw - 6) if left else (x + bw + 8)
    anc = 'end' if left else 'start'
    if txt:
        lines, rest = [], txt
        while len(rest) > 24:                       # 空白・「・」・「（」の手前で折る（無ければ 24 字で）
            k = max(rest.rfind(c, 8, 24) for c in (' ', '・', '（', '→'))
            k = 24 if k < 0 else k
            lines.append(rest[:k].rstrip()); rest = rest[k:].lstrip()
        lines.append(rest)
        y0 = top + h / 2 + 4 - 13 * (len(lines) - 1) / 2
        for k, ln in enumerate(lines):
            parts.append('<text x="%.1f" y="%.1f" font-size="11" fill="%s" text-anchor="%s">%s</text>'
                         % (tx, y0 + 13 * k, hub_ports.PAL['sub'], anc, ln))
    return ''.join(parts)


def cut_rows(segs):
    rows = []
    for disp, key, n, shell, far, how in BUNDLES:
        ss = segs.get(key, [])
        bund = [l for k, l in ss if k > 1]; sing = [l for k, l in ss if k == 1]
        if how == 'branch':   # 幹 ＋ 長い枝
            main = max(bund) if bund else 0
            rest = max([l for l in bund if l != main] + sing + [0])
            ln = main + rest + FAN * 2
        elif how == 'single':
            ln = max(sing + [0]) + FAN
        elif how == 'sum':
            ln = sum(bund) + max(sing + [0]) + FAN
        elif how == 'ph':
            ln = sum(bund)
        else:
            ln = sum(bund) + FAN * 2
        cut = int(math.ceil((ln + WIRE_MARGIN) / 5.0) * 5)
        assert len(bundle_wires(key)) == n, (key, n)
        rows.append((disp, n, shell, far, int(round(ln)), cut, wire_cells(key)))
    return rows


def cuttable(segs):
    rows = ['<tr><td class="w">{}</td><td class="n">{}</td><td>{}</td><td class="n">{}</td><td>{}</td>'
            '<td class="n">{}</td><td class="n hi"><b>{} mm</b></td></tr>'.format(r[0], r[1], r[6], r[2], r[3], r[4], r[5])
            for r in cut_rows(segs)]
    return ('<div class="tw"><table><thead><tr><th>束</th><th>本数</th><th>線と色（束の中の全部）</th><th>ハブ側の殻</th>'
            '<th>逆の端</th><th>模型の実長</th><th>切る長さ（束の全部の線）</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'
            '<p>🔒 <b>線の色</b>: SCL＝緑・SDA＝黄・会話ボタンの信号（D2）＝紫・3V3＝赤・GND＝黒（白でも可）・EN＝橙・5V＝茶（全部の口で同じ）。'
            '「仮」は決めていない線で、ここでは相手のリードの色に合わせて置いた。'
            '<b>同じ束の線は全部同じ長さに切る</b>（二股・枝分かれは長い方に合わせてある）。'
            '端末処理の 25mm は両端の被覆むきと圧着のぶんで、切る長さに入っている。</p>')


# ---------------------------------------------------------------- 手順
STEPS = [
 dict(n='0', t='線を 12 束作る（箱を組む前に・机の上で）', acts=[
   '<b>ハブ基板側は 10 束すべて 2.54mm の DuPont</b>（殻＝プラスチックのハウジングと、線に圧着して殻へ挿す金属のピン）。'
   '🔒 2026-08-07「DuPont のまま＋抜け止め。はんだ付けはしない」——分解できるようにするため。',
   '🔴 <b>殻のピン数は線の本数と同じとは限らない</b>——<span class="w">つまみ</span>は線 5 本に殻は 4 連（GND が二股で DIR へ）、'
   '<span class="w">電源</span>は線 3 本に殻は 4 連（3 本目は空き）。本数どおりに作ると手順 3 で 1 本ずつずれて挿さる。',
   '⚠ <b>7 連の殻は無い。</b>🔒 XIAO の束の殻（2026-09-06 ユーザー）——ハブ側は <b>D2 の 1 連・SDA・SCL・3V3・GND の 4 連・D3＋5V の 2 連</b>の 3 個、XIAO 側は <b>6 連 × 2</b>——上の列に <b>5V・GND・3V3＋空き 3</b>、下の列に <b>空き 2＋D2・D3・SDA・SCL</b>。空きの穴には何も入れない。I2C の 4 本の並びは他の口と同じ SDA・SCL・3V3・GND。',
   '<b>ハブに挿さらない束が 3 つある</b>——<span class="w">充電</span>（Type-C 基板 ↔ PowerBoost）、'
   '<span class="w">電池→電流計</span>（電池の JST の受け ↔ 電流計の INPUT）、<span class="w">電流計→JST</span>（電流計の OUT ↔ PowerBoost の JST に挿すプラグ）。'
   '電池の線は電流計を通ってから PowerBoost へ入る。',
   '<b>切る長さはこれ。</b>模型の実長（case_v5 の束）に 65（端末処理 25 ＋ 天面を机に置くための余り 40）を足して 5mm 単位に上げた。'
   '__CUTFIG__',
   '__CUTTABLE__',
   '<b>逆の端が直はんだなのは 3 束</b>——会話ボタン 2・トグル 2・スピーカー OUT 2。ハブ側だけ圧着して、反対側は裸のまま（手順 12・13 で付ける）。',
   '<b>リードスイッチの口は空けたまま</b>（置き場所が決まっていない・2026-09-05）。',
 ], warn='<b>ここを飛ばすと手順 3 で止まる。</b>手順 3 は「ハブの口を全部挿す」から始まる。',
    note='箱の外でしか出来ない作業を、箱の外にいるうちに全部済ませるため。'),

 dict(n='1', t='床にハブ基板を留める', img='st1', acts=[
   '床を裏返して置く。裏の 4 つの<b>六角のポケット</b>に <span class="d">M3</span> ナットを 1 つずつ落とす（二面幅 5.5・ポケットは 5.8）。'
   '床には最初から <span class="g">座</span>（ReSpeaker の台と唇）・OLED のリブ・Type-C の受け・前板の脚の溝が生えている。',
   'ナットを指で押さえたまま床を起こして台に載せ、ハブ基板を穴に合わせて置き、<span class="d">M3×8</span> を<b>基板の上から</b>通してナットに掛ける。<b>1 本ずつ</b>。'
   '<b>ポケットは下向きなので、ねじが掛かるまでナットは押さえていないと落ちる。</b>',
   '締めるのは上からドライバだけ。ナットは六角の中で回らない。'
   '<b>板の向き</b>: いちばん長い 7 本の口（XIAO）が<b>手前（OLED 側）</b>、口が 4 つ並んだ縁が<b>奥（ハッチ側）</b>。',
 ], note='床の裏はスタンドに載る面。ナットは裏の六角に沈む（深さ 2.6・ナット厚 2.4）。🔒 2026-09-05 ユーザー「ここが丸である利点はなんだ」で、丸いザグリ＋上のナットからこの形に変えた。'),

 dict(n='2', t='ReSpeaker を床の座に立て、XIAO の口を挿す', img='st2', acts=[
   'ReSpeaker を床の <span class="g">座</span> へ上から差す。板の下端が台に乗り、前の唇と後ろの振れ止め 2 つに挟まれる。<b>ビスは無い。</b>頭は手順 12 で天板の <span class="g">羊羹</span> と <span class="g">マッチ棒</span> が 0.3 押さえる。',
   '向きは、<b>イヤホンジャックと ReSpeaker 自身の USB-C が左の壁側</b>、<b>XIAO の USB-C が右の壁側</b>。左の壁に開いているのはジャックの丸い口だけで、ReSpeaker 自身の USB-C は外へ出さない。',
   '<b>この段で XIAO の上のピンヘッダに 6 連を 2 個挿す。どちらも USB-C 側の端（1 本目）に突き当てる。</b>上の列: 5V・GND・3V3＋空き 3（1〜6 本目）。下の列: 空き 2＋D2・D3・SDA・SCL（1〜6 本目）。挿し終わると<b>両列とも反対側の端（7 本目）だけ裸</b>。🔴 6 連は 7 本のピンに 2 通りの位置で入る。1 本ずれると上の列は <b>5V の線が GND のピンに乗る</b>。'
   '⚠ ピン名は基板の裏に印刷されていて読めない。<b>USB-C を左にして数える</b>（手順 3 の図・箱の後ろから見た向き）。壁が立った後では右の壁が口の真横に来て、ピンセットが入らない。',
 ], warn='<b>壁（手順 6）より先に入れる。</b>壁を当てた後では、ReSpeaker は上から入らない（壁の押さえと天板の羊羹の席が真上に来る）。'),

 dict(n='3', t='ハブの口を全部挿して、線を寝かせる', img='st3',
      extra=lambda: hub_map_svg() + xiao_svg() + pin_table(), acts=[
   '<span class="w">XIAO</span> 7・<span class="w">スピーカー IN</span> 2・<span class="w">OLED</span> 4・<span class="w">つまみ</span> 4・'
   '<span class="w">会話ボタン</span> 2・<span class="w">スピーカー OUT</span> 2・<span class="w">電源</span> 3・<span class="w">電流計</span> 4・'
   '<span class="w">トグル</span> 2 の 9 束を<b>ハブ側だけ全部挿す</b>（リードの口は空けたまま）。'
   '<b>どの口の何本目に何が来るかは、この手順の下の図と表に全部書いてある。</b>',
   '🔴 <b>数え始めは口ごとに違う。</b>手前（ハッチ側）と奥（OLED 側）の縁の口は<b>ジャックの壁側（図の右）から</b>、左右の壁側の縁の口は<b>奥（OLED 側）から</b>数える。表の「数え始め」を読む。',
   '<b>XIAO と スピーカー IN は逆側もここで挿す。</b>XIAO は手順 2 で挿した 3 個の殻へ、スピーカー IN は ReSpeaker のスピーカーソケット J2 へ。'
   'J2 は板の左端の裏にあって、手順 5 で <span class="g">皿</span> が真上に載ると届かない。',
   '<b>残りの束は、逆の端を挿す相手がまだ無いので寝かせておく。</b>寝かせる道は決まっている（この後の手順の絵に黄色で出ている）:'
   '<span class="w">OLED</span> は右へ回って <span class="g">皿</span> の下（Z 22〜24）を左から右へ抜け、右前で上へ（相手は手順 11 の OLED）。'
   '<span class="w">つまみ</span> は皿の下を右へ（相手は手順 12 のつまみの基板の裏）。<span class="w">会話ボタン</span> は左の溝を前へ（相手は手順 12 のスイッチ）。'
   '<span class="w">スピーカー OUT</span> はハブの右端の上を前へ、右の壁ぎわを上へ（相手は手順 12 のスピーカー）。'
   '<span class="w">電源</span>・<span class="w">電流計</span>・<span class="w">トグル</span> は後ろの帯（ハブの口の頭の上・Y 70 前後）に寝かせる。',
   '<b>皿の下を通る 2 束（OLED・つまみ）は、いましか通せない。</b>皿が載った後の隙間は 4.8mm で、手も工具も入らない。',
   '<b>後ろに並ぶ 4 本（電流計・トグル・リード・電源）はピンセットで挿す。</b>箱の後ろぎわに 1 列で、隣の口の線が上へ立ち上がるので指の腹が下りない。',
 ], warn='<b>先に上へ持ち上げてしまうと、ブリッジ（皿）が降ろせない。</b>皿の下を通る束は皿より下に寝かせたままにする。',
    note='この後、皿と壁〜壁の <span class="g">腕</span> がこの上に載る。<b>その真下に口がある束は、載せた後では届かない。</b>'),

 dict(n='4', t='Type-C 基板を上から床の受けへ落とす', img='st4', acts=[
   '<b>基板を手に持っているうちに、充電の 2 本（1 連 × 2）を L 字ピンの 1・2 本目（上から。VBUS・GND）へ挿す。</b>手順 5 でブリッジの腕が真上に来ると口へ届かない。',
   '基板の裏を左（壁が来る側）、L 字ピンを箱の中（右）へ向け、<b>まっすぐ上から</b>床の <span class="g">受け</span> へ落とす。'
   '板の下端が底の座に乗り、前縁が前の当てに、L 字ヘッダの樹脂の列が前の返しと後ろの控えの間（前 0.3・後ろ 0.8）に入る。USB-C の口は後ろ（ハッチ側）。',
   '充電の 2 本は左の溝（X 9.5）を上へ寝かせ、後ろの帯へ。PowerBoost 側は手順 12。',
 ], warn='<b>壁（手順 6）より先。</b>壁が立った後では、押さえのレールが板の 0.2 上に被さって上から入らず、後ろから滑り込ませると L 字ヘッダの一番下の樹脂（Z 4.2〜6.8）が後ろの控え（高さ 6）に 1.8 食い込んで止まる。',
    note='受けは床と一体（v5）。押さえは手順 6 の左の壁と一体。基板にビスは無く、前後は当てと控え、上は押さえ、横は壁とハッチが持つ。'),

 dict(n='5', t='前板を皿に留めてから、ブリッジを置く', img='st5', acts=[
   '<b>先に <span class="g">前板</span>（電池の返しと前の脚）を皿の溝に差し、上から <span class="d">M2 皿ねじ</span> 1 本で皿に留める</b>（ナットは前板のフランジの下の箱）。',
   '<b>ブリッジ（<span class="g">皿</span> と左右の <span class="g">腕</span>）をまっすぐ下へ降ろす。</b>前板の脚が床の溝（脚の前後 0.25 の空き・深さ 2.5）に入り、皿はハブの口の頭の 1.8 上に浮く。<b>腕を受ける棚はまだ無い</b>（手順 6 の壁に付いている）ので、ブリッジは前板の脚で前だけ支えられ、後ろは放すと下がる。手順 6 で壁を寄せるときに持ち上げる。',
   '皿の下を通る 2 束（OLED・つまみ）と Type-C の充電の 2 本が、皿と腕の下に寝ていることを見る。',
 ], warn='<b>前板はブリッジより先。</b>ブリッジを降ろした後では前板の溝に手が入らない。<b>ブリッジは壁より先。</b>壁が立った後では、腕が壁のリブの格子（腕の席の上に横 3 段）を通れない。'),

 dict(n='6', t='左右の壁を横から当て、ブリッジを棚に留める', img='st6', acts=[
   '<b>壁を寝かせたまま、ナットを 4 個差す。</b>ブリッジの <span class="g">腕</span> を受ける <span class="g">棚</span> の横穴に <span class="d">M2</span> を左右 1 個ずつ（棚の内側の面から差す）、'
   '天板を受ける後ろの <span class="g">柱</span> の頭の横穴に左右 1 個ずつ（前＝箱の内側から差す）。奥まで押すと上下の肉に挟まれ、壁を立てても落ちない。',
   '<b>壁は横から当てる</b>——左の壁を左から、右の壁を右から、ReSpeaker を挟むように<b>まっすぐ X に</b>寄せる。上から降ろさない。'
   '<b>ブリッジの後ろを指で持ち上げ、腕の先を棚の高さに保ちながら</b>寄せる。棚が腕の下へ滑り込み、壁のリブの空き（腕の席）に腕の先が入る。'
   '右の壁は XIAO の USB-C の殻が口を通り、殻の面が外面の 0.8 裏に来る。左の壁はジャックの筒が丸い口へ入り、押さえのレールが Type-C 基板の上に被さる。',
   '<b>腕を上から 2 本締める。</b>左右とも <span class="d">M2×6</span>、頭は座ぐりに沈む。<b>電池より先に締める。</b>これが壁を最初に持つねじ。',
   '<b>前の柱の頭のナット 2 個は、壁を立ててから箱の内側（X の面）から差す。</b>前の柱は幅 5 で、溝が横（箱の中央）へ開いている。',
   '<b>壁が立ってから</b>、下の柱の頭の横穴へ <span class="d">M2</span> ナットを 3 個差す（左前・右前は前板側の面の穴へ前から、右後ろはハッチ側の面の穴へ後ろから）。穴の上に肉が 1.6 あるので、床の裏からねじを入れてもナットは上へ逃げない。',
   '<b>床の裏のビス（<span class="d">M2×15</span> 3 本）はこの手順ではまだ入れない。</b>前の 2 本の下の柱は床から 3.2 浮いていて、その隙間にフロントの下の耳が入ってからビスが 床・耳・柱 を通る——前の 2 本はフロントの下の耳（手順 12）、後ろ右の 1 本はハッチの下の耳（手順 13）。'
   '<b>後ろ左のビスは無い</b>——そこは Type-C 基板の席。',
   '腕の上面には反り止めの格子が立っている（右の腕だけ。左は座ぐりで区間が短くて立たない）。',
 ], warn='落としたナットには 0.3 の遊びがあり、置いてあるだけ。<b>締めるまで箱を伏せない。</b>'),

 dict(n='7', t='留め帯 3 本を横から差す', img='st7', acts=[
   '<span class="g">帯</span> は 3 本とも同じ形（太さ 6.9・⊓）。<b>1 本ずつ、右（つまみ側）へ 2mm ずらした位置に置いてから、まっすぐ左へ 2mm 押し込む。</b>'
   '⊓ の足が皿の縁のレールの切れ目に落ち、足の裏の<b>ツバ</b>（三角）が <span class="g">土手</span> を貫く溝へ入る。',
   '押すのは<b>細い棒（φ3.2）で、右の壁側から</b>。',
   '<b>奥の帯の天板には電流計のピンの足の逃げ（1.5 掘り）と E リングの軸 2 本</b>が付いている。向きを間違えると手順 9 で電流計が浮く。',
 ], warn='<b>上からはかぶせられない</b>（ツバの上に土手の肉がある）。<b>電池より先</b>——電池が居ると横へ 2mm 動かせない。',
    note='入れた電池が帯の楔になる。電池が居る限り帯は横へ戻せず、ツバが外れない。'),

 dict(n='8', t='電池を後ろから差し込む', img='st8', acts=[
   '<b>タブ（JST の線）が後ろ（ハッチ側）に来る向き</b>で、ハッチ口からまっすぐ押し込む。皿が床・帯の足が左右・帯の天板が天井の、後ろにだけ開いた鞘を滑らせる。前は前板の返しが受ける。',
   '<b>座ってから</b>、電池の JST に「延長」（JST-PH の受け → 1 連 × 2）を嵌める。延長の 2 本は左の溝と右の X 53 の道へ分けて寝かせる（手順 9 で電流計へ）。',
 ], warn='電池は<b>後ろからしか入らない</b>。交換も同じ道（このページの最後）。'),

 dict(n='9', t='電流計を帯に載せ、電源の線を挿す', img='st9', acts=[
   '電流計は<b>板を箱の軸に平行</b>にして、奥の帯の E リングの軸 2 本に穴を通し、帯の天板に全面で当てる。<b>電源の L 字 4 本が前（OLED 側）、I2C の L 字が後ろ（ハッチ側）。</b>'
   '<b>E リング（呼び 1.5）2 個</b>を軸の溝に嵌める。ねじは無い。',
   '<b>電源の口の一番左のピン（INPUT の 1 本目）だけ、根元で左（−X）へ 90° 曲げてある。</b>この 1 本は左の溝から来る延長を受け、残り 3 本は前を向く。',
   '挿すのは 3 束: <span class="w">電池→電流計</span> の延長 2 本 → INPUT ±（1 本目は左向きの口、2 本目は前向きの口の 2 本目）。'
   '<span class="w">電流計→JST</span> の 1 連 × 2 → OUT ±（前向きの 3・4 本目）。プラグ側は手順 12 で PowerBoost へ。'
   '<span class="w">電流計</span>（I2C 4 連）→ 後ろの L 字（手順 3 で寝かせた束を後ろの帯から上げる）。',
 ], note='電流計は電池と PowerBoost の間に居る。電池の線は必ず電流計を通る。'),

 dict(n='10', t='天板の小組を机の上で作る', img='topsub',
      cap='天板を裏返して見た図。PowerBoost（4 本のダボ）・つまみ・会話ボタンのバスタブ・スピーカー・OLED の L・羊羹とマッチ棒・トグルの受け', acts=[
   '<b>PowerBoost</b>: 天板の裏から下りている <span class="d">φ4</span> のダボ 4 本に板の穴を通し、<b>部品面を天板側</b>にして当て、下から <b>E リング（呼び 1.5）4 個</b>。JST が前（OLED 側）・L 字ピンが後ろ向きになる。',
   '<b>つまみ</b>: 順は hardware/knob_v5.scad の「組む順」が正（下の分解図）。台座は天板と一体。AS5600 の基板の裏の 5 本のピンが下を向いて出る——ここへ手順 12 で <span class="w">つまみ</span> の 1 連 × 5 を挿す。',
   '<b>会話ボタン</b>: バスタブにマイクロスイッチを <span class="d">M2</span> 2 本で留め、押し子を上から通し、天板の裏の <span class="g">腕</span>（ブロック 2 つ・ナット入り）へ耳の下から <span class="d">M2</span> 2 本。<b>耳は左右とも同じ Y・同じ厚み</b>（v5）。',
   '<b>スピーカー</b>: 天板の裏の小判の座に振動板を上（グリル側）にして両面テープで貼る。裏の位置出しの縁に落とし込む。リードは後ろの長辺の縁から出る。',
   '<b>OLED の <span class="g">L</span> には何も付けない。</b>ねじもナットも無い。足の前面のダボ 2 本（φ2.8・長さ 2.0）が折れていないかだけ見る。',
   '<b>トグルはここでは付けない</b>（ハッチに付く・手順 13）。',
 ], img2='knob', cap2='つまみまわりの分解（hardware/knob_v5.scad の explode）。'),

 dict(n='11', t='OLED をフロントに嵌める', img='st11', acts=[
   '<b>フロントを裏返し、OLED の黒枠を内側から窓へ押し込む。</b>窓は黒枠より縦に 0.15・横に 1.0 大きく、縦の締まりで少しの力で外れる程度に留まる（🔒 2026-09-07 実機）。'
   'ヘッダのピンの尻（1.8）がフロントの内面に当たる所まで押す。黒枠の下辺の張り出しは窓の下の逃げに入る。',
   'OLED はこの後フロントと一緒に前から差す（手順 12）。<b>線はまだ挿さない。</b>',
 ]),

 dict(n='12', t='上の道の線を挿し、天板を載せ、フロントを差す', img='st12', img2='pb_pins',
      cap2='PowerBoost の 5 本の L 字ピンと JST の行き先。8 ピン列は micro-USB に近い端が USB、遠い端が 5Vo。micro-USB と USB-A の足跡には何も付けない。', acts=[
   '<b>天板の小組を箱の上に浮かせて持ち、先に線を挿す。</b>'
   '<b>PowerBoost の L 字ピン 5 本は 1 本ずつ相手が違う</b>（下の図）: '
   '<span class="w">電源</span> の 1 連 × 3 → <b>EN</b>（橙・ハブ PWR の 1 本目）・<b>EN の隣の GND</b>（黒・PWR の 2 本目）・<b>5Vo</b>（茶・PWR の 4 本目）。'
   '<span class="w">充電</span> の 1 連 × 2 → <b>USB</b>（茶・Type-C 基板の L 字 1 本目 VBUS）・<b>5Vo の隣の GND</b>（黒・Type-C 基板の L 字 2 本目）。'
   'LiPo・Vs・LBO にはピンが無い。micro-USB には何も挿さず、USB-A の足跡にもピンを立てない（5V 出力は 5Vo のピンから）。',
   '<span class="w">電流計→JST</span> のプラグ → PowerBoost の JST。<span class="w">つまみ</span> の 1 連 × 5 → AS5600 の裏のピン（左 2・右 3。右 3 はリレーの真上なので前へ逃がして下りる）。',
   '<b>直はんだの 2 束</b>: <span class="w">会話ボタン</span> の 2 本をマイクロスイッチの <b>C と NO</b> へ（GND＝黒か白 → C・D2＝紫 → NO。端子はレバーの根元側から C・NO・NC の順で、いちばん先の NC には何も付けない）、<span class="w">スピーカー OUT</span> の 2 本をスピーカーのリードへ。',
   '<b>天板を降ろす。</b>羊羹とマッチ棒が ReSpeaker の頭を 0.3 押し、つまみの台座の前の欠きに電流計の電源の口の先が入る。OLED の L はまだ何にも当たらず、足の前面（Y 4.4）のダボ 2 本が前を向いて待つ。'
   '<b>後ろの 2 本はまだ締めない</b>——ハッチの上の耳を挟んでから（手順 13）。',
   '<b>手順 11 の OLED 入りのフロントを箱の前に持ち、手順 3 で寝かせた <span class="w">OLED</span> の 4 連を OLED の裏の上のヘッダへ挿す。</b>線は右へ回って皿の下を通っている。箱の前で挿すので、線はフロントの奥行きぶん前へ出る。',
   '<b>フロントを前から差す。</b>L のダボ 2 本が OLED の上の 2 穴に入り（ダボの先の面取りが窓の横の遊び 1.0 を寄せる）、L の足が OLED の裏を受ける。ヒゲがマイクを受ける。上の耳が前の上の柱の上に載り、<b>下の耳が前の下の柱の下の隙間（3.2）へ入る</b>。'
   '上は天板の前の 2 本 <span class="d">M2×8</span> を上から（天板 2.5 ＋ 耳 3.2 ＋ 柱の肉 1.6 を通ってナット）、<b>下は床の裏から前の 2 本 <span class="d">M2×15</span></b>（床 2 ＋ 下の耳 3.2 ＋ 柱を通って柱の横穴のナット。穴の口はフロントの内面が塞ぐ）。<b>フロントは上下 4 本で留まる。</b>',
 ], warn='<b>PowerBoost の JST の頭と会話ボタンの筒の間は 1.2mm。</b>プラグの線は出てすぐ右へ逃がす（線の絵のとおり）。'),

 dict(n='13', t='ハッチに蓋とトグルを付け、後ろから押し込んで閉じる', img='st13', img2='claw',
      cap2='ハッチの下の足 2 つ（中に M2 ナットの横穴）と床の裏の座ぐり、天板の裏のトグルの受け。', acts=[
   '<b>蓋の床の板</b>をハッチの裏の彫り込みへ接着する（のりしろは上下 4 個ずつ）。ロックのナットは<b>板の右の縁から溝へ差す</b>（閉じたポケット。裏から押さえなくてよい）。'
   '<b>蓋</b>を横から溝へ入れ、<b>ロック</b>を <span class="d">M2×6</span> で締める。',
   '<b>トグル</b>をハッチの穴に通し、外のナットで締める（胴が縦・端子が下向きの列）。<span class="w">トグル</span> の 2 本を端子の中（COM）と下へはんだ付けし、線は端子の脇から真下へ。',
   '<b>先にハッチの下の 2 つの <span class="g">足</span> の横穴へ <span class="d">M2</span> ナットを前から差す。</b>'
   '<b>ハッチは垂直のまま、真後ろから真っ直ぐ押し込む。</b>足 2 つが床の上を滑り、'
   'トグルの胴が天板の裏の <span class="g">受け</span> へ後ろから、<b>上の耳 2 つが天板の裏を滑って後ろの上の柱の頭の上へ</b>入る。'
   '同時に Type-C 基板の殻がハッチの口へ、基板の後縁がハッチの裏のスリットへ入る。<b>天板の後ろの 2 本が緩んでいること</b>（耳と天板の遊びは 0）。',
   '最後の 0.35 で右の壁の横リブ 3 本の端がハッチのリブに乗る。押し込むか、リブの端をやすりで一往復。',
   '<b>ハッチのねじ 4 本。</b>天板の後ろの 2 本 <span class="d">M2×8</span> を上から（天板 2.5 ＋ 耳 3.2 ＋ 柱の肉 1.6 → ナット）、床の裏から <span class="d">M2×6</span> 2 本（床 2 → 足の横穴のナット。頭は床の裏の座ぐり）。'
   '床の裏の後ろ右の <span class="d">M2×15</span> は右の壁を床に留めるだけで、ハッチは通らない。',
   'ハッチには充電の Type-C の口（左下）が開いている。Type-C 基板の殻の面は外面の 1.6 裏（ハッチを 2.0 → 2.8 に厚くしたぶん・2026-09-07）。',
 ], warn='<b>倒して掛けない。</b>唇を軸に 1° 倒しただけで、ハッチの下端が床の後ろの縁に、耳が柱の頭に、トグルの胴が天井に当たる（hardware/_asm_chk_v5.scad の st13r）。真っ直ぐ押す動きは 14mm 手前から最後まで当たり 0（同 st13y）。',
    note='ハッチは 上＝耳 2 のねじ・下＝足 2 のねじ、の 4 本で留まる。床の爪は印刷で出なかったので v5 で廃止（2026-09-07）。トグルの受けは胴の X と前を持つ。'),
]


# ---------------------------------------------------------------- 呼び名
GLOSS = [
 ('皿と腕', 'ブリッジ。電池が乗る皿と、左右の壁の棚へ伸びる腕が一体。腕にねじ 2 本。', 'sara'),
 ('帯', '電池を上から押さえる ⊓ が 3 本（太さ 6.9・等間隔）。足のツバが土手の溝に入る。奥の 1 本が電流計の座。', 'obi'),
 ('前板', '皿の前に立つ板。電池の返しと前の脚。M2 皿ねじ 1 本で皿に留める。', 'maeita'),
 ('土手', '皿の縁に立つ壁。帯のツバが入る溝がある。', 'dote'),
 ('羊羹とマッチ棒', '天板の裏から下りて ReSpeaker の板の頭を 0.3 押さえる 2 本。', 'yokan'),
 ('座', '床に生えている ReSpeaker の台と前の唇、後ろの振れ止め。手前の低い畝は OLED の下辺のリブ。', 'za'),
 ('L', '天板から下りて OLED の裏に当たる足。前面のダボ φ2.8 が OLED の上の 2 穴に入る。ねじは無い（2026-09-07）。', 'L'),
 ('足', 'ハッチの内面の下端のブロック 2 つ。中に M2 ナットの横穴。床の裏からのねじがここへ入る。', 'tsume'),
 ('受け', '天板の裏から下りてトグルの胴を持つ箱。両側の壁と、端子の両脇の前の当て。', 'uke'),
 ('蓋・ロック・蓋の床の板', '電池の口を塞ぐ横スライドの蓋、ねじで止めるロック、ハッチの裏に接着する床の板。', 'futa'),
 ('柱と棚', '壁の内面。下の柱（床からのねじ）・上の柱（天板からのねじ）・腕を受ける棚。ナットは横穴。', 'hashira'),
 ('耳', 'フロントの四隅とハッチの上 2。天板と床のねじがここを通って柱へ入る。', 'mimi'),
 ('バスタブと腕', '会話ボタン。スイッチを抱く筒（バスタブ）と、その耳を受ける天板の裏のブロック（腕）。', 'tub'),
 ('Type-C の受けと押さえ', '床の受け（座・当て・返し・控え）と左の壁の押さえ（レールと前の足）。基板は壁より先に上から落とす。', 'uke_tc'),
]

SCREWS = [
 ('M3 × 8',  '4', 'ハブ基板 → 床（上から。ナットは床の裏の六角）', '1'),
 ('M2 × 15', '3', '床の裏 → 左右の壁の下の柱。<b>前の 2 本はフロントの下の耳を通して手順 12。後ろ右は右の壁を床に留めるだけ</b>', '12 / 6'),
 ('M2 × 6',  '2', '床の裏 → ハッチの下の足（ナットは足の横穴）', '13'),
 ('M2 × 6',  '2', 'ブリッジの腕 → 壁の棚（上から。ナットは棚の横穴）', '6'),
 ('M2 皿',   '1', '前板 → 皿（上から。ナットはフランジの下の箱）', '5'),
 ('M2',      '2', '会話ボタンのスイッチ → バスタブ（机の上で）', '10'),
 ('M2',      '2', '会話ボタンのバスタブ → 天板の腕（耳の下から。ナットはブロックの横穴）', '10'),
 ('M2 × 6',  '2', 'つまみの島 → 天板（knob_v5 の組む順）', '10'),
 ('M2 × 8',  '2', '天板の後ろ 2 本 → ハッチの上の耳 → 後ろの柱（上から。3 枚を通す）', '13'),
 ('M2 × 8',  '2', '天板の前 2 本 → フロントの耳 → 前の柱（上から。3 枚を通す）', '12'),
 ('M2 × 6',  '1', '電池の蓋のロック（ナットは床の板の閉じたポケット・右から差す）', '13'),
 ('六角ナット', '1', 'トグル（ハッチの外から）', '13'),
]
NUTS = [
 ('M3', '4', '床の裏の六角のポケット（下向き。ねじが掛かるまで押さえる）', '手順 1'),
 ('M2', '2', '壁の棚の横穴（左右 1 つずつ・棚の内側の面から）', '壁を寝かせているうち（手順 6）'),
 ('M2', '2', '後ろの上の柱の頭の横穴（前＝箱の内側から）', '壁を寝かせているうち（手順 6）'),
 ('M2', '2', '前の上の柱の頭の横穴（箱の内側の X の面から）', '壁を立ててから（手順 6）'),
 ('M2', '3', '下の柱の頭の横穴（前の 2 本は前板側・後ろ右はハッチ側から差す）', '壁を立ててから（手順 6）'),
 ('M2', '2', 'ハッチの下の足の横穴（前から差す）', '手順 13'),
 ('M2', '1', '前板のフランジの下の箱', '手順 5'),
 ('M2', '4', '会話ボタン（バスタブの壁 2・天板の腕のブロック 2）', '手順 10'),
 ('M2', '2', 'つまみの島', '手順 10'),
 ('M2', '1', '蓋の床の板の閉じたポケット（右の縁の溝から差す）', '手順 13'),
 ('E リング 呼び 1.5', '6', '帯の軸 2（電流計）・天板のダボ 4（PowerBoost）', '手順 9・10'),
 ('E リング 呼び 6 / 3', '1 / 3', 'つまみの軸と基板（knob_v5）', '手順 10'),
]
PARTS = [
 ('床', '1', 'ハブの柱・座・OLED のリブ・Type-C の受け・前板の脚の溝・ねじ穴込み'),
 ('天板', '1', 'つまみと会話ボタンの台座・スピーカーの座と縁・PowerBoost のダボ・OLED の L・羊羹とマッチ棒・トグルの受け込み'),
 ('左の壁', '1', '柱と棚・Type-C の押さえ・ジャックの口・反り止めの格子'),
 ('右の壁', '1', '柱と棚・XIAO の USB-C の口・反り止めの格子'),
 ('フロント', '1', '窓・ヒゲ・耳・反り止めの格子'),
 ('ハッチ', '1', 'Type-C の口・トグルの穴・蓋の彫り込み・足 2 つ・耳 2 つ・反り止めの格子'),
 ('ブリッジ（皿と腕）', '1', '腕の上に格子'),
 ('前板', '1', ''),
 ('帯', '3', '同じ形'),
 ('蓋（シャッター）', '1', '磁石 2 個を圧入'),
 ('ロック', '1', ''),
 ('蓋の床の板', '1', 'ハッチの裏へ接着。ロックのナットのポケット・磁石 2 個'),
 ('つまみ一式', '1 組', 'hardware/knob_v5.scad'),
 ('会話ボタンの押し子とバスタブ', '1 組', 'hardware/parts/btn_v3.scad'),
]


# ---------------------------------------------------------------- HTML
BODY = """
<div class="wrap">
<header class="mast">
  <p class="eyebrow">katanori &middot; enclosure v5</p>
  <h1>カタノリ v5<br><em>組み立て</em></h1>
  <p class="sub">上から順にやれば組める。<b>順番を変えると入らない物がある</b>ので、その理由を各手順の「なぜ」に書いた。
  図面は <b>hardware/case_v5.scad</b>、線は同じファイルの束、この手順の絵は <b>hardware/tools/manual_v5/_asm_sim_v5.scad</b>。</p>
  <nav class="rail">__NAV__</nav>
</header>

<section class="sec"><h2>始める前に</h2>
<ul>
<li><b>向き</b>: 「前」は OLED の側、「後ろ」はハッチの側。「左右」は OLED を正面に見て言う。</li>
<li><b>樹脂にねじを切らない。</b>ねじは全部貫通してナットで受ける。ナットはほぼ横穴（差してから上下の肉に挟まれる）。</li>
<li><b>Type-C 基板とブリッジは壁より先に置く</b>（壁が立った後では、押さえとリブが邪魔で入らない）。<b>壁は横から当てる</b>（上から降ろさない）。<b>電池はハッチ側から</b>入れる。<b>帯は右から横に</b>差す。</li>
<li><b>ハッチは垂直のまま真後ろから押し込む。</b>倒して掛けない（1° 倒すだけで床の縁・柱の頭・天井に当たる）。</li>
<li><b>フロントとハッチは耳で留まる。</b>天板と床のねじが耳を通って柱へ入るので、<b>その 7 本はフロントとハッチを差してから</b>締める。</li>
<li>皿の下を通る線（OLED・つまみ）は<b>皿より先</b>に寝かせる。皿が載った後では通らない。</li>
</ul></section>

<section class="sec"><h2>全体</h2>
<figure class="wide"><img src="__EXP__" alt="分解図"><figcaption>ブリッジまわりの分解（前板は下へ、帯・電池・電流計は上へ）。</figcaption></figure>
<figure class="wide"><img src="__LOOK__" alt="組んだ中身"><figcaption>皮を外した中身。</figcaption></figure>
</section>

<section class="sec"><h2>部品の呼び名</h2>
<p>この手順で使う呼び名。絵の赤い部分がその物。</p>
<div class="gloss">__GLOSS__</div>
</section>

<section class="sec"><h2>手順</h2>
__STEPS__
</section>

<section class="sec"><h2>線</h2>
<figure class="wide"><img src="__WIRES__" alt="線の全体"><figcaption>12 束の道（黄色）。皮を外して後ろ上から。</figcaption></figure>
<p>切る長さは手順 0 の表。道は手順 3・4・8・9・12・13 に書いた。</p>
</section>

<section class="sec"><h2>ビスとナット</h2>
<div class="tw"><table><thead><tr><th>ビス</th><th>本数</th><th>どこ</th><th>手順</th></tr></thead><tbody>__SCREWROWS__</tbody></table></div>
<div class="tw"><table><thead><tr><th>ナット</th><th>個数</th><th>どこ</th><th>いつ入れる</th></tr></thead><tbody>__NUTROWS__</tbody></table></div>
</section>

<section class="sec"><h2>印刷部品</h2>
<div class="tw"><table><thead><tr><th>部品</th><th>数</th><th>備考</th></tr></thead><tbody>__PARTROWS__</tbody></table></div>
<figure class="wide"><img src="__DOOR__" alt="蓋の一式"><figcaption>電池の蓋の一式（蓋・ロック・蓋の床の板）。</figcaption></figure>
</section>

<section class="sec"><h2>電池の交換（組んだ後）</h2>
<ol class="acts">
<li>ロックの <span class="d">M2×6</span> を外し、蓋を横へ滑らせて開ける。</li>
<li>電池の JST から延長を抜き、電池を後ろへ引き出す。帯の楔が外れるが、帯はツバで土手に掛かったまま。</li>
<li>新しい電池を同じ向き（タブが後ろ）で押し込み、延長を嵌め、蓋を戻してロックを締める。</li>
</ol></section>
</div>
"""


# ---------------------------------------------------------------- 手順 3 の図と表（v5 の向き）
# 🔒 2026-09-06 ユーザー「上が OLED であってほしい・XIAO の図も左が USB であってほしい」。
#    どちらも箱の後ろ（ハッチ側）から覗いた向き。v4 の図を紙の上で回しただけで、鏡ではない
#    （ハブ: 180°・XIAO: 90°）。XIAO の「左の列／右の列」はこの向きでは上下に並ぶので「上の列／下の列」と呼ぶ。
# 線の色: docs（2026-09-02）SCL＝緑・SDA＝黄色。図の直下に出す（ユーザー 2026-09-06）。
WIRE_COLORS = '🔒 <b>線の色: SCL ＝ 緑・SDA ＝ 黄色</b>（全部の口で同じ）。'


def hub_map_svg():
    return ('<figure class="wide">' + hub_ports.board_svg(oled_top=True) +
            '<figcaption>' + WIRE_COLORS + '<br>'
            'ハブ基板を<b>上から</b>見た図。<b>上が OLED（前）・下がハッチ（後ろ）</b>で、箱の後ろから覗いた向き。'
            'だから板の<b>左（ジャックの壁）が図の右</b>、<b>右（USB-C の壁）が図の左</b>に来る。'
            'ピンの中の数字が「何本目」で、<b>数え始めは口ごとに違う</b>（表の「数え始め」と図の数字のとおり）。'
            '色は信号の別（<b>赤</b>=5V・<b>黒</b>=GND・<b>橙</b>=3V3・<b>青</b>=SDA/SCL）。'
            '実物の板に行や列の刻印は無いので、口は縁と並び順で見分ける。</figcaption></figure>')


# 🔒 XIAO 側の殻の配置（2026-09-06 ユーザー。7 連の殻は無い）。(列, 始まり, 終わり)。何本目は USB-C 側から。
#    上の列 1〜6 に 6 連（5V・GND・3V3・空・空・空）、下の列 1〜6 に 6 連（空・空・D2・D3・SDA・SCL）。7 本目は裸。
#    どちらも USB-C 側の端に突き当てる。1 本ずれると上の列は 5V の線が GND のピンに乗る。
XIAO_SHELLS = [('下', 1, 6), ('上', 1, 6)]


def xiao_svg():
    """XIAO を USB-C を左にして、XIAO の面を見た図（箱の後ろから見た向き）。v4 の xiao_svg を 90° 回したもの。
    USB-C が上の図で右の列（5V…）だったものが上の列、左の列（D0…）だったものが下の列。"""
    hub = {hub_ports.disp(fn, net): i + 1
           for p in hub_ports.ports() if p.id == 'XIAO'
           for i, (h, fn, net, x, y) in enumerate(p.pins)}
    P = hub_ports.PAL
    NC = {'5V': P['v5'], 'GND': P['gnd'], '3V3': P['v33'],
          'SDA': P['i2c'], 'SCL': P['i2c'], 'D2': P['ink'], 'D3': P['ink']}
    pitch, x0 = 132, 150            # ピンの間隔・1 本目の X
    W, H = x0 + pitch * 7 + 40, 420
    y_top, y_bot = 150, 320         # 上の列・下の列の Y
    bx, by = x0 - 40, y_top - 36    # 板
    bw, bh = pitch * 6 + 80, y_bot - y_top + 72
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" '
         'height="%d" preserveAspectRatio="xMidYMid meet" '
         'font-family="system-ui, sans-serif">' % (W, H, W, H)]
    o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="9" fill="#2f3a43"/>' % (bx, by, bw, bh))
    o.append('<rect x="%d" y="%d" width="22" height="52" rx="5" fill="#9aa5ad"/>' % (bx - 20, (y_top + y_bot) / 2 - 26))
    o.append('<text x="%d" y="%d" font-size="11" font-weight="700" fill="#1b2227" text-anchor="middle" '
             'transform="rotate(-90 %d %d)">USB-C</text>' % (bx - 9, (y_top + y_bot) / 2, bx - 9, (y_top + y_bot) / 2))
    o.append('<text x="%d" y="%d" font-size="12" font-weight="700" fill="#9aa5ad" text-anchor="middle">XIAO</text>'
             % (bx + bw / 2, (y_top + y_bot) / 2 + 4))
    o.append('<text x="%d" y="%d" font-size="13" font-weight="700" fill="#9aa5ad" text-anchor="middle">USB-C 側から数える →</text>'
             % (bx + bw / 2, (y_top + y_bot) / 2 + 26))
    # 殻（ピンの下に描く）: 6 連 × 2。USB-C 側の端に突き当てる
    for row, a_, b_ in XIAO_SHELLS:
        cy = y_top if row == '上' else y_bot
        xa, xb = x0 + (a_ - 1) * pitch - 24, x0 + (b_ - 1) * pitch + 24
        o.append('<rect x="%d" y="%d" width="%d" height="48" rx="5" fill="#55636f" stroke="#9aa5ad" stroke-width="1.6"/>'
                 % (xa, cy - 24, xb - xa))
        o.append('<text x="%d" y="%d" font-size="10" fill="#c9c4b8" text-anchor="middle">%d 連（%d〜%d 本目・USB-C 側の端に突き当てる）</text>'
                 % ((xa + xb) / 2, cy + (37 if row == '上' else -29), b_ - a_ + 1, a_, b_))
    for row, names, cy in (('上', V4.XIAO_R, y_top), ('下', V4.XIAO_L, y_bot)):
        up = row == '上'
        o.append('<text x="%d" y="%d" font-size="15" font-weight="700" fill="%s" text-anchor="start">%sの列</text>'
                 % (bx + bw + 14, cy + 5, P['sub'], row))
        for i, nm in enumerate(names):
            cx = x0 + i * pitch
            use = V4.XIAO_ALT.get(nm, nm)
            n = hub.get(use)
            col = NC.get(use, P['sub']) if n else P['sub']
            o.append('<rect x="%d" y="%d" width="26" height="26" rx="3" fill="%s" stroke="%s" stroke-width="1.6"/>'
                     % (cx - 13, cy - 13, '#ffffff' if n else '#e6e3dc', col))
            o.append('<text x="%d" y="%.1f" font-size="12" font-weight="700" fill="%s" text-anchor="middle">%d</text>'
                     % (cx, cy + 4.5, col, i + 1))
            lab = nm + ('（%s）' % V4.XIAO_ALT[nm] if nm in V4.XIAO_ALT else '')
            if n:
                sub1, sub2 = 'ハブの %d 本目' % n, ''
            elif nm in V4.XIAO_STOP:
                sub1, sub2 = '殻の空き（🔴 触らない）', '（%s）' % {'RGB LED のデータ線': 'RGB LED', 'XMOS のリセット': 'XMOS リセット'}.get(V4.XIAO_STOP[nm], V4.XIAO_STOP[nm])
            else:
                sub1, sub2 = ('殻の空き（使わない）' if i < 6 else '裸（使わない）'), '（%s）' % V4.XIAO_BUSY.get(nm, '')
            # 上の列は板の上へ（下から 名前・sub1・sub2 の順に積む）、下の列は板の下へ
            ys = (cy - 74, cy - 58, cy - 44) if up else (cy + 46, cy + 62, cy + 76)
            o.append('<text x="%d" y="%d" font-size="14" font-weight="700" fill="%s" text-anchor="middle">%s</text>'
                     % (cx, ys[0], col if n else P['sub'], lab))
            o.append('<text x="%d" y="%d" font-size="11.5" fill="%s" text-anchor="middle">%s</text>'
                     % (cx, ys[1], P['sub'], sub1))
            if sub2:
                o.append('<text x="%d" y="%d" font-size="11" fill="%s" text-anchor="middle">%s</text>'
                         % (cx, ys[2], P['sub'], sub2))
    o.append('</svg>')
    return ('<figure class="wide">' + ''.join(o) +
            '<figcaption>' + WIRE_COLORS + '<br>'
            'XIAO を <b>USB-C が左</b>になるように置いて、XIAO の面を見た図（箱の後ろから見た向き。手順 2 で ReSpeaker を立てると XIAO の面は後ろを向き、USB-C は右の壁へ出る）。'
            'ピンの中の数字は <b>USB-C 側から何本目か</b>。'
            'ハブから来る 7 本は色が付いていて、その下に<b>ハブの口の何本目か</b>が入っている。'
            '⚠ XIAO のピン名は基板の裏に印刷されていて、'
            'ReSpeaker に直付けした今は読めない——<b>数えるしかない</b>。🔒 <b>殻は 6 連 × 2</b>（2026-09-06 ユーザー。7 連は無い）——上の列 1〜6 本目に 5V・GND・3V3＋空き 3、下の列 1〜6 本目に 空き 2＋D2・D3・SDA・SCL。空きの穴には線を入れない。<b>どちらも USB-C 側の端に突き当て、7 本目だけ裸</b>。1 本ずれると上の列は 5V の線が GND のピンに乗る。</figcaption></figure>')


# ハブのどの口か。挿す人が見る向き（箱の後ろ・ハッチ側から。上の hub_map_svg と同じ）で書く。
# 「左右」は挿す人の左右＝図の左右。壁の名前を錨にする（USB-C の壁が図の左・ジャックの壁が図の右）。
# 🔴 ピン番号は口ごとに数え始めが違う。数え始めは必ず文に入れる。相手側（線の逆の端）は v4 の MATE をそのまま使う。
PLACE = {
 'XIAO':   '奥の縁（OLED 側）に 1 列。板でいちばん長い口。<b>ジャックの壁側（図の右）から</b>数える',
 'AS5600': 'XIAO の口より 1 列手前、板の中ほど。<b>ジャックの壁側（図の右）から</b>数える',
 'BTN2':   'ジャックの壁側の縁（図の右）の手前寄り（2 つあるうち<b>手前・ハッチ側</b>）。<b>奥（OLED 側）から</b>数える',
 'PHIN':   'USB-C の壁側の縁（図の左）の<b>奥寄り</b>の白いコネクタ。<b>奥（OLED 側）から</b>数える',
 'PHOUT':  'USB-C の壁側の縁（図の左）の<b>手前寄り</b>の白いコネクタ。<b>奥（OLED 側）から</b>数える',
 'OLED':   'ジャックの壁側の縁（図の右）の奥寄り（2 つあるうち<b>奥・OLED 側</b>）。<b>奥（OLED 側）から</b>数える',
 'INA':    '手前の縁（ハッチ側）に並ぶ 4 つのうち、<b>ジャックの壁側から 1 つ目</b>（図のいちばん右）。<b>ジャックの壁側（図の右）から</b>数える',
 'TOGGLE': '手前の縁（ハッチ側）に並ぶ 4 つのうち、<b>ジャックの壁側から 2 つ目</b>。<b>ジャックの壁側（図の右）から</b>数える',
 'REED':   '手前の縁（ハッチ側）に並ぶ 4 つのうち、<b>ジャックの壁側から 3 つ目</b>。<b>ジャックの壁側（図の右）から</b>数える',
 'PWR':    '手前の縁（ハッチ側）に並ぶ 4 つのうち、<b>ジャックの壁側から 4 つ目</b>（USB-C の壁側の端・図のいちばん左）。<b>ジャックの壁側（図の右）から</b>数える',
}


# 表の注。v4 の MATE_NOTE を使い、XIAO だけ v5 の殻の分け方（D2＋D3／I2C 束／5V）に差し替える
# 相手側の文。v4 の MATE を使うが、会話ボタンだけ差し替える——v4 の「対角の足」は 4 本足のタクトの語で、
# 現行はレバー式マイクロスイッチ（3 端子・docs/DIMENSIONS.md「レバーの根本側から C, NO, NC」）。
MATE = dict(V4.MATE)
MATE['BTN2'] = ['マイクロスイッチの <b>C</b>（レバーの根元・ヒンジ側の端の端子。<b>直はんだ</b>・手順 12）',
                'その隣の <b>NO</b>（真ん中の端子。<b>直はんだ</b>・手順 12）。いちばん先の NC は空き']
MATE_NOTE = dict(V4.MATE_NOTE)
MATE_NOTE['XIAO'] = '🔴 <b>この 7 本は XIAO の 2 つの列にまたがる</b>（上の図）。🔒 <b>殻</b>（2026-09-06 ユーザー。7 連の殻は無い）——ハブ側は <b>D2 の 1 連＋SDA・SCL・3V3・GND の 4 連＋D3・5V の 2 連</b>の 3 個。XIAO 側は <b>6 連 × 2</b>——上の列 1〜6 本目に <b>5V・GND・3V3＋空き 3</b>、下の列 1〜6 本目に <b>空き 2＋D2・D3・SDA・SCL</b>。I2C の 4 本の並びは他の口と同じ <b>SDA・SCL・3V3・GND</b>。🔴 <b>6 連は 7 本のピンに 2 通りの位置で入る。USB-C 側の端に突き当てて、反対側（7 本目）だけ裸が正。</b>1 本ずれると上の列は <b>5V の線が GND のピンに乗り</b>、下の列は D2 の線が D3 に、SCL の線が D6（I2S DIN）に乗る。'


def pin_table():
    """口の表。ハブ側の「どの口の何本目か」は hub_ports.py、場所の文は上の PLACE（後ろから見た向き）、
    相手側の文は v4 の MATE / MATE_NOTE（XIAO の列の呼び名だけ USB-C が左の向きに直す）。"""
    ps = {p.id: p for p in hub_ports.ports()}
    rows = []
    for pid in V4.PORT_ORDER:
        p = ps[pid]
        mates = MATE[pid]
        for i, (h, fn, net, x, y) in enumerate(p.pins):
            cells = []
            if i == 0:
                cells.append('<td class="w" rowspan="%d"><b>%s</b><br>'
                             '<span class="n">%d 本</span></td>' % (p.n, p.bundle, p.n))
                cells.append('<td rowspan="%d">%s</td>' % (p.n, PLACE[pid]))
            cells.append('<td class="n hi"><b>%d 本目</b></td>' % (i + 1))
            cells.append('<td class="n">%s</td>' % hub_ports.disp(fn, net))
            cells.append('<td>%s</td>' % mates[i])
            rows.append('<tr%s>%s</tr>'
                        % (' class="bs"' if i == 0 else '', ''.join(cells)))
        if MATE_NOTE.get(pid):
            rows.append('<tr><td colspan="5" class="pn">%s</td></tr>' % MATE_NOTE[pid])
    html = ('<div class="tw"><table class="pins"><thead><tr><th>束</th>'
            '<th>ハブ基板のどの口か（数え始め・後ろから見た向き）</th><th>何本目</th><th>信号</th>'
            '<th>線の逆の端は、相手の何本目か</th></tr></thead><tbody>'
            + '\n'.join(rows) + '</tbody></table></div>')
    return (html.replace('左の列', '下の列').replace('右の列', '上の列').replace('左の 4 連', '下の 4 連')
            .replace('2 つとも右の縁にある', '2 つとも USB-C の壁側の縁（図の左）にある'))


def build():
    IM = {k: img(k + '.png') for k in SEQ + [w[0] for w in WIDE] + [f[0] for f in FIXED] + ['pb_pins']}   # pb_pins は _pb_pins_fig.py（PIL）で描く 2D の図
    segs = wire_lengths()

    def step_html(s):
        fig = ''
        if s.get('img'):
            fig += '<figure class="sheet"><img src="{}" alt="手順 {}">{}</figure>'.format(
                IM[s['img']], s['n'], '<figcaption>%s</figcaption>' % s['cap'] if s.get('cap') else '')
        if s.get('img2'):
            fig += '<figure class="sheet"><img src="{}" alt="{}"><figcaption>{}</figcaption></figure>'.format(
                IM[s['img2']], s.get('cap2', ''), s.get('cap2', ''))
        bits = []
        if s.get('warn'):
            bits.append('<p class="cal warn"><span class="tag">注意</span>{}</p>'.format(s['warn']))
        if s.get('note'):
            bits.append('<p class="cal note"><span class="tag">なぜ</span>{}</p>'.format(s['note']))
        extra = s.get('extra'); extra = extra() if callable(extra) else (extra or '')
        acts = [a.replace('__CUTTABLE__', cuttable(segs)).replace('__CUTFIG__', cut_fig(segs)) for a in s['acts']]
        return ('<section class="step" id="s{n}" data-n="{n}">\n<div class="num"><span>{n}</span></div>\n<div class="body">\n'
                '<h3>{t}</h3>\n{fig}\n<ol class="acts">{acts}</ol>\n{extra}\n{bits}\n</div>\n</section>').format(
                    n=s['n'], t=s['t'], fig=fig, extra=extra, acts='\n'.join('<li>%s</li>' % x for x in acts), bits=''.join(bits))

    gloss = '\n'.join('<figure class="g"><img src="{}" alt="{}"><figcaption><b>{}</b> — {}</figcaption></figure>'
                      .format(img('g_%s.png' % k), nm, nm, d) for nm, d, k in GLOSS)
    body = (BODY.replace('__NAV__', ' '.join('<a href="#s{0}">{0}</a>'.format(s['n']) for s in STEPS))
            .replace('__EXP__', IM['explode']).replace('__LOOK__', IM['look']).replace('__WIRES__', IM['wires']).replace('__DOOR__', IM['door'])
            .replace('__GLOSS__', gloss)
            .replace('__STEPS__', '\n'.join(step_html(s) for s in STEPS))
            .replace('__SCREWROWS__', '\n'.join('<tr><td class="d">{}</td><td class="n">{}</td><td>{}</td><td class="n">{}</td></tr>'.format(*r) for r in SCREWS))
            .replace('__NUTROWS__', '\n'.join('<tr><td class="d">{}</td><td class="n">{}</td><td>{}</td><td>{}</td></tr>'.format(*r) for r in NUTS))
            .replace('__PARTROWS__', '\n'.join('<tr><td><b>{}</b></td><td class="n">{}</td><td>{}</td></tr>'.format(*r) for r in PARTS)))
    head = ('<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            '<title>カタノリ v5 組み立て</title>\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=BIZ+UDPGothic:wght@400;700&family=JetBrains+Mono:wght@400;700&display=swap">\n'
            '<style>' + V4.CSS + '\n.gloss{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}'
            '.gloss figure.g{margin:0;background:#fff;border:1px solid #e3e6ea;border-radius:10px;padding:8px}'
            '.gloss figure.g img{width:100%;height:auto;display:block}.gloss figcaption{font-size:.92em;margin-top:6px}'
            'figure.sheet figcaption{font-size:.92em;color:#4a5560;margin-top:6px}</style>\n')
    html = head + body + V4.RAILJS
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print(OUT, os.path.getsize(OUT), 'bytes')


if __name__ == '__main__':
    if '--no-render' not in sys.argv:
        render()
    build()
