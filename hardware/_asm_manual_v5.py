# -*- coding: utf-8 -*-
# 組み立てマニュアル v5（docs/manual/assembly_v5.html）を case_v5.scad から作る道具。
#
#   python hardware/_asm_manual_v5.py             挿絵を出し直して HTML を書く
#   python hardware/_asm_manual_v5.py --no-render 挿絵はそのままで HTML だけ書き直す
#
# 手順は 1 か所（下の STEPS）にしか無い。段の絵は hardware/_asm_sim_v5.scad の upto()。
# 呼び名の絵は hardware/_asm_gloss_v5.scad。線の長さは case_v5 の束（WIRE_LEN=true の echo）から取る。
# ハブの口の図と表は v4 の道具（frozen/v1-v4/_asm_manual_v4.py の hub_map_svg / pin_table / xiao_svg）を借りる
# ——ハブ基板そのものは v4 と同じ板なので、口の並びと相手は変わらない。
import base64, math, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, 'parts'))              # hub_ports
sys.path.insert(0, os.path.join(HERE, 'frozen', 'v1-v4'))    # _asm_manual_v4（CSS・口の表）
import hub_ports
import _asm_manual_v4 as V4

IMGDIR = os.path.join(ROOT, 'docs', 'manual', '_manual_img_v5')
OUT = os.path.join(ROOT, 'docs', 'manual', 'assembly_v5.html')
TMP = os.path.join(HERE, '_tmp_v5')
OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.com')

N_STEPS = 13
CAM = ['--projection=p', '--camera=43,36,22,58,0,205,330', '--imgsize=1100,850']
SEQ = ['st%d' % n for n in range(1, N_STEPS + 1)]
WIDE = [('explode', 'case_v5.scad', 'part', 'explode', '0,0,0,62,0,42,0'),
        ('look',    'case_v5.scad', 'part', 'look',    '0,0,0,60,0,25,0'),
        ('wires',   '_asm_sim_v5.scad', 'ST', 'wires', '0,0,0,58,0,205,0'),
        ('door',    '_asm_sim_v5.scad', 'ST', 'door',  '0,0,0,60,0,25,0'),
        ('knob',    'parts/knob_v5.scad', 'part', 'explode', '0,0,0,62,0,35,0')]
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
 ('XIAO',          'xiao',   7, '7 連',                 'XIAO の上のピンヘッダ（<b>1 連・2 連・4 連</b> の 3 個。5V は 1 連で単独）', 'branch'),
 ('スピーカー IN', 'phin',   2, 'PH2.0 の 2 極プラグ',    'ReSpeaker のスピーカーソケット J2（PH2.0 の 2 極プラグ）', 'ph'),
 ('OLED',          'oled',   4, '4 連',                 'OLED の 4 本ヘッダ（<b>4 連</b>）', 'single'),
 ('つまみ',        'as5600', 5, '4 連（GND は二股）',     'AS5600 の基板の裏の 5 本（<b>1 連 × 5</b>）', 'branch'),
 ('会話ボタン',    'btn2',   2, '2 連',                 'マイクロスイッチの両端の端子（<b>直はんだ</b>）', 'sum'),
 ('スピーカー OUT','phout',  2, 'PH2.0 の 2 極プラグ',    'スピーカーのリード（<b>直はんだ</b>）', 'ph'),
 ('電源',          'pwr',    3, '4 連（3 本目は空き）',   'PowerBoost の L 字ピン EN・GND・5Vo（<b>1 連 × 3</b>）', 'bundle'),
 ('電流計',        'ina',    4, '4 連',                 '電流計の後ろの L 字 4 本（<b>4 連</b>）', 'bundle'),
 ('トグル',        'tgl',    2, '2 連',                 'トグルの端子 2 つ（<b>直はんだ</b>・中と下）', 'single'),
 ('充電',          'chg',    2, '（ハブには挿さらない）', 'Type-C 基板の L 字 1・2 本目 → PowerBoost の USB・GND2（<b>両端とも 1 連 × 2</b>）', 'bundle'),
 ('電池→電流計',   'bat',    2, '（ハブには挿さらない）', '電池の JST-PH の受け → 電流計の INPUT ±（<b>1 連 × 2</b>・「延長」）', 'single'),
 ('電流計→JST',    'batout', 2, '（ハブには挿さらない）', '電流計の OUT ± （<b>1 連 × 2</b>）→ PowerBoost の JST に挿す JST-PH のプラグ', 'bundle'),
]


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
        rows.append((disp, n, shell, far, int(round(ln)), cut))
    return rows


def cuttable(segs):
    rows = ['<tr><td class="w">{}</td><td class="n">{}</td><td class="n">{}</td><td>{}</td>'
            '<td class="n">{}</td><td class="n hi"><b>{} mm</b></td></tr>'.format(*r) for r in cut_rows(segs)]
    return ('<div class="tw"><table><thead><tr><th>束</th><th>線の本数</th><th>ハブ側の殻</th>'
            '<th>逆の端</th><th>模型の実長</th><th>切る長さ</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')


# ---------------------------------------------------------------- 手順
STEPS = [
 dict(n='0', t='線を 12 束作る（箱を組む前に・机の上で）', acts=[
   '<b>ハブ基板側は 10 束すべて 2.54mm の DuPont</b>（殻＝プラスチックのハウジングと、線に圧着して殻へ挿す金属のピン）。'
   '🔒 2026-08-07「DuPont のまま＋抜け止め。はんだ付けはしない」——分解できるようにするため。',
   '🔴 <b>殻のピン数は線の本数と同じとは限らない</b>——<span class="w">つまみ</span>は線 5 本に殻は 4 連（GND が二股で DIR へ）、'
   '<span class="w">電源</span>は線 3 本に殻は 4 連（3 本目は空き）。本数どおりに作ると手順 3 で 1 本ずつずれて挿さる。',
   '⚠ <b>XIAO の逆側は 7 連が使えない</b>（7 本が XIAO の 2 列にまたがる）。🔒 <b>1 連・2 連・4 連の 3 個</b>——5V だけ 1 連で単独、GND と 3V3 が 2 連、D2〜D5 が 4 連。<b>5V と GND を同じ殻に入れない。</b>',
   '<b>ハブに挿さらない束が 3 つある</b>——<span class="w">充電</span>（Type-C 基板 ↔ PowerBoost）、'
   '<span class="w">電池→電流計</span>（電池の JST の受け ↔ 電流計の INPUT）、<span class="w">電流計→JST</span>（電流計の OUT ↔ PowerBoost の JST に挿すプラグ）。'
   '電池の線は電流計を通ってから PowerBoost へ入る。',
   '<b>切る長さはこれ。</b>模型の実長（case_v5 の束）に 65（端末処理 25 ＋ 天面を机に置くための余り 40）を足して 5mm 単位に上げた。'
   '__CUTTABLE__',
   '<b>逆の端が直はんだなのは 3 束</b>——会話ボタン 2・トグル 2・スピーカー OUT 2。ハブ側だけ圧着して、反対側は裸のまま（手順 12・13 で付ける）。',
   '<b>リードスイッチの口は空けたまま</b>（置き場所が決まっていない・2026-09-05）。',
 ], warn='<b>ここを飛ばすと手順 3 で止まる。</b>手順 3 は「ハブの口を全部挿す」から始まる。',
    note='箱の外でしか出来ない作業を、箱の外にいるうちに全部済ませるため。'),

 dict(n='1', t='床にハブ基板を留める', img='st1', acts=[
   '床を<b>台か机の端</b>に載せる。裏からドライバを入れるので、机にベタ置きにしない。'
   '床には最初から <span class="g">座</span>（ReSpeaker の台と唇）・OLED のリブ・Type-C の受け・ハッチの爪の帯が生えている。',
   '<span class="d">M3×8</span> は <b>1 本ずつ</b>入れる。床の裏から穴へ通し（頭は裏のザグリに沈む）、ハブ基板をその軸に載せ、上から <span class="d">M3</span> ナットを掛ける。'
   '<b>4 本まとめて通してから床を起こすと全部落ちる。</b>',
   '締めるときは<b>下からドライバでビスの頭を押さえ</b>、上からナットを回す（ザグリが丸いので押さえないと空回りする）。ナットは 5.5mm のナットドライバ。',
   '<b>板の向き</b>: いちばん長い 7 本の口（XIAO）が<b>手前（OLED 側）</b>、口が 4 つ並んだ縁が<b>奥（ハッチ側）</b>。',
 ], note='床の裏はスタンドに載る面。ビスの頭が出ていると座らない。'),

 dict(n='2', t='ReSpeaker を床の座に立て、XIAO の口を挿す', img='st2', acts=[
   'ReSpeaker を床の <span class="g">座</span> へ上から差す。板の下端が台に乗り、前の唇と後ろの振れ止め 2 つに挟まれる。<b>ビスは無い。</b>頭は手順 12 で天板の <span class="g">羊羹</span> と <span class="g">マッチ棒</span> が 0.3 押さえる。',
   '向きは、<b>イヤホンジャックと ReSpeaker 自身の USB-C が左の壁側</b>、<b>XIAO の USB-C が右の壁側</b>。左の壁に開いているのはジャックの丸い口だけで、ReSpeaker 自身の USB-C は外へ出さない。',
   '<b>この段で XIAO の上のピンヘッダに 1 連・2 連・4 連を挿す。</b>左の列の 3〜6 本目に 4 連、右の列の 1 本目に 1 連（5V）、2・3 本目に 2 連（GND・3V3）。'
   '⚠ ピン名は基板の裏に印刷されていて読めない。<b>USB-C を上にして数える</b>（手順 3 の図）。壁が立った後では右の壁が口の真横に来て、ピンセットが入らない。',
 ], warn='<b>壁より先に入れる。</b>壁を当てた後では、ReSpeaker は上から入らない（壁の押さえと天板の羊羹の席が真上に来る）。'),

 dict(n='3', t='ハブの口を全部挿して、線を寝かせる', img='st3',
      extra=lambda: V4.hub_map_svg() + V4.xiao_svg() + V4.pin_table(), acts=[
   '<span class="w">XIAO</span> 7・<span class="w">スピーカー IN</span> 2・<span class="w">OLED</span> 4・<span class="w">つまみ</span> 4・'
   '<span class="w">会話ボタン</span> 2・<span class="w">スピーカー OUT</span> 2・<span class="w">電源</span> 3・<span class="w">電流計</span> 4・'
   '<span class="w">トグル</span> 2 の 9 束を<b>ハブ側だけ全部挿す</b>（リードの口は空けたまま）。'
   '<b>どの口の何本目に何が来るかは、この手順の下の図と表に全部書いてある。</b>',
   '🔴 <b>数え始めは口ごとに違う。</b>手前と奥の縁の口は<b>左から</b>、左右の縁の口は<b>前（OLED 側）から</b>数える。表の「数え始め」を読む。',
   '<b>XIAO と スピーカー IN は逆側もここで挿す。</b>XIAO は手順 2 で挿した 3 個の殻へ、スピーカー IN は ReSpeaker のスピーカーソケット J2 へ。'
   'J2 は板の左端の裏にあって、手順 6 で <span class="g">皿</span> が真上に載ると届かない。',
   '<b>残りの束は、逆の端を挿す相手がまだ無いので寝かせておく。</b>寝かせる道は決まっている（この後の手順の絵に黄色で出ている）:'
   '<span class="w">OLED</span> は右へ回って <span class="g">皿</span> の下（Z 22〜24）を左から右へ抜け、右前で上へ（相手は手順 11 の OLED）。'
   '<span class="w">つまみ</span> は皿の下を右へ（相手は手順 12 のつまみの基板の裏）。<span class="w">会話ボタン</span> は左の溝を前へ（相手は手順 12 のスイッチ）。'
   '<span class="w">スピーカー OUT</span> はハブの右端の上を前へ、右の壁ぎわを上へ（相手は手順 12 のスピーカー）。'
   '<span class="w">電源</span>・<span class="w">電流計</span>・<span class="w">トグル</span> は後ろの帯（ハブの口の頭の上・Y 70 前後）に寝かせる。',
   '<b>皿の下を通る 2 束（OLED・つまみ）は、いましか通せない。</b>皿が載った後の隙間は 4.8mm で、手も工具も入らない。',
   '<b>後ろに並ぶ 4 本（電流計・トグル・リード・電源）はピンセットで挿す。</b>箱の後ろぎわに 1 列で、隣の口の線が上へ立ち上がるので指の腹が下りない。',
 ], warn='<b>先に上へ持ち上げてしまうと、ブリッジ（皿）が降ろせない。</b>皿の下を通る束は皿より下に寝かせたままにする。',
    note='この後、皿と壁〜壁の <span class="g">腕</span> がこの上に載る。<b>その真下に口がある束は、載せた後では届かない。</b>'),

 dict(n='4', t='左右の壁を横から当て、床の裏から 3 本で留める', img='st4', acts=[
   '<b>壁を寝かせたまま、ナットを 4 個差す。</b>ブリッジの <span class="g">腕</span> を受ける <span class="g">棚</span> の横穴に <span class="d">M2</span> を左右 1 個ずつ（棚の内側の面から差す）、'
   '天板を受ける後ろの <span class="g">柱</span> の頭の横穴に左右 1 個ずつ（前＝箱の内側から差す）。奥まで押すと上下の肉に挟まれ、壁を立てても落ちない。',
   '<b>前の柱の頭のナット 2 個は、壁を立ててから箱の内側（X の面）から差す。</b>前の柱は幅 5 で、溝が横（箱の中央）へ開いている。',
   '<b>壁は横から当てる</b>——左の壁を左から、右の壁を右から、ReSpeaker を挟むように<b>まっすぐ X に</b>寄せる。上から降ろさない。'
   '右の壁は XIAO の USB-C の殻が口を通り、殻の面が外面の 0.8 裏に来る。左の壁はジャックの筒が丸い口へ入る。',
   '<b>壁が立ってから</b>、下の柱の頭の上向きポケットへ <span class="d">M2</span> ナットを 3 個落とす（左前・右前・右後ろ）。',
   '<b>床の裏のビス（<span class="d">M2×15</span> 3 本）はこの手順ではまだ入れない。</b>下の柱は 3 本とも床から 3.2 浮いていて、その隙間に耳が入ってからビスが 床・耳・柱 を通る——前の 2 本はフロントの下の耳（手順 12）、後ろ右の 1 本はハッチの下の耳（手順 13）。'
   '<b>後ろ左のビスは無い</b>——そこは Type-C 基板の席。ここまでは壁は棚（手順 6 のブリッジのねじ）と天板で持つ。',
 ], warn='落としたナットには 0.3 の遊びがあり、置いてあるだけ。<b>締めるまで箱を伏せない。</b>'),

 dict(n='5', t='Type-C 基板を後ろから差し込む', img='st5', acts=[
   '<b>基板を手に持っているうちに、充電の 2 本（1 連 × 2）を L 字ピンの 1・2 本目（上から。VBUS・GND）へ挿す。</b>差した後は左の壁の押さえが口の上に被さって届かない。',
   '基板の裏を左の壁の内面に当て、L 字ピンを箱の中（右）へ向けて、<b>ハッチ側から前へ滑り込ませる</b>。床の <span class="g">受け</span>（底の座・前の当て・返し・後ろの控え）と左の壁の押さえのレールの間を、前の当てに当たるまで。',
   '充電の 2 本は左の溝（X 9.5）を上へ寝かせ、後ろの帯へ。PowerBoost 側は手順 12。',
 ], note='受けは床と一体（v5）。押さえは左の壁と一体。基板にビスは無く、前後は当てと控え、上は押さえ、横は壁とハッチが持つ。'),

 dict(n='6', t='前板を皿に留めてから、ブリッジを降ろす', img='st6', acts=[
   '<b>先に <span class="g">前板</span>（電池の返しと前の脚）を皿の溝に差し、上から <span class="d">M2 皿ねじ</span> 1 本で皿に留める</b>（ナットは前板のフランジの下の箱）。',
   '<b>ブリッジ（<span class="g">皿</span> と左右の <span class="g">腕</span>）をまっすぐ下へ降ろす。</b>腕が手順 4 の棚のナットの上に載る。',
   '<b>上から 2 本締める。</b>左右とも <span class="d">M2×6</span>、頭は座ぐりに沈む。<b>電池より先に締める。</b>',
   '腕の上面には反り止めの格子が立っている（右の腕だけ。左は座ぐりで区間が短くて立たない）。',
 ], warn='<b>前板はブリッジより先。</b>ブリッジを降ろした後では前板の溝に手が入らない。'),

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
   '<b>トグルはここでは付けない</b>（ハッチに付く・手順 13）。',
 ], img2='knob', cap2='つまみまわりの分解（hardware/knob_v5.scad の explode）。'),

 dict(n='11', t='OLED を立てる', img='st11', acts=[
   'OLED を上から降ろし、下辺を床の後ろのリブ（OLED の裏の 0.2 後ろ・中央はフィルムの切り欠き）に当てる。この時点ではまだ宙ぶらりんで、手順 12 の L と窓が挟む。',
   '<b>手順 3 で寝かせた <span class="w">OLED</span> の 4 連を、OLED の裏の上のヘッダへ挿す。</b>線は右へ回って皿の下を通っている。',
 ]),

 dict(n='12', t='上の道の線を挿し、天板を載せ、フロントを差す', img='st12', acts=[
   '<b>天板の小組を箱の上に浮かせて持ち、先に線を挿す。</b>'
   '<span class="w">電源</span> の 1 連 × 3 → PowerBoost の L 字 EN・GND・5Vo。<span class="w">充電</span> の 1 連 × 2 → USB・GND2。'
   '<span class="w">電流計→JST</span> のプラグ → PowerBoost の JST。<span class="w">つまみ</span> の 1 連 × 5 → AS5600 の裏のピン（左 2・右 3。右 3 はリレーの真上なので前へ逃がして下りる）。',
   '<b>直はんだの 2 束</b>: <span class="w">会話ボタン</span> の 2 本をマイクロスイッチの両端の端子へ、<span class="w">スピーカー OUT</span> の 2 本をスピーカーのリードへ。',
   '<b>天板を降ろす。</b>羊羹とマッチ棒が ReSpeaker の頭を 0.3 押し、L が OLED の裏に当たり、つまみの台座の前の欠きに電流計の電源の口の先が入る。'
   '<b>後ろの 2 本はまだ締めない</b>——ハッチの上の耳を挟んでから（手順 13）。',
   '<b>OLED の上の 2 穴に前から <span class="d">M2×6</span>。</b>ナットは L の後ろの六角（ピンセットで入れる）。フロントより先。',
   '<b>フロントを前から差す。</b>窓が OLED を、ヒゲがマイクを受ける。上の耳が前の上の柱の上に載り、<b>下の耳が前の下の柱の下の隙間（3.2）へ入る</b>。'
   '上は天板の前の 2 本 <span class="d">M2×8</span> を上から（天板 2.5 ＋ 耳 3.2 ＋ 柱の肉 1.6 を通ってナット）、<b>下は床の裏から前の 2 本 <span class="d">M2×15</span></b>（床 2 ＋ 下の耳 3.2 ＋ 柱 8.8 を通って柱の頭のナット）。<b>フロントは上下 4 本で留まる。</b>',
 ], warn='<b>PowerBoost の JST の頭と会話ボタンの筒の間は 1.2mm。</b>プラグの線は出てすぐ右へ逃がす（線の絵のとおり）。'),

 dict(n='13', t='ハッチに蓋とトグルを付け、爪を掛けて閉じる', img='st13', img2='claw',
      cap2='ハッチの下の爪 2 つと床の帯（バーの下に唇が入る）、天板の裏のトグルの受け。', acts=[
   '<b>蓋の床の板</b>をハッチの裏の彫り込みへ接着する（のりしろは上下 4 個ずつ）。ロックのナットは<b>板の右の縁から溝へ差す</b>（閉じたポケット。裏から押さえなくてよい）。'
   '<b>蓋</b>を横から溝へ入れ、<b>ロック</b>を <span class="d">M2×6</span> で締める。',
   '<b>トグル</b>をハッチの穴に通し、外のナットで締める（胴が縦・端子が下向きの列）。<span class="w">トグル</span> の 2 本を端子の中（COM）と下へはんだ付けし、線は端子の脇から真下へ。',
   '<b>ハッチは下から掛ける。</b>内面の下端の <span class="g">爪</span> 2 つの唇を、床の後ろの帯のポケットへ前向きに滑り込ませ（バーの下へ）、上を倒す。'
   'トグルの胴が天板の裏の <span class="g">受け</span> に弧で入り、<b>上の耳 2 つが天板と後ろの上の柱の間の隙間（3.2）へ、右下の耳が床と後ろ右の下の柱の間へ</b>入る。',
   '<b>ハッチのねじ 3 本。</b>天板の後ろの 2 本 <span class="d">M2×8</span> を上から（天板 2.5 ＋ 耳 3.2 ＋ 柱の肉 1.6 → ナット）、床の裏から後ろ右の <span class="d">M2×15</span>（床 2 ＋ 耳 3.2 ＋ 柱 8.8 → 柱の頭のナット）。'
   '左下は Type-C 基板の席で柱が無いので、爪だけ。',
   'ハッチには充電の Type-C の口（左下）が開いている。Type-C 基板の殻の面は外面の 0.8 裏。',
 ], note='ハッチは 下＝爪 2・上＝耳 2 のねじ・右下＝耳のねじ、で留まる。トグルの受けは胴の X と前を持つ。'),
]


# ---------------------------------------------------------------- 呼び名
GLOSS = [
 ('皿と腕', 'ブリッジ。電池が乗る皿と、左右の壁の棚へ伸びる腕が一体。腕にねじ 2 本。', 'sara'),
 ('帯', '電池を上から押さえる ⊓ が 3 本（太さ 6.9・等間隔）。足のツバが土手の溝に入る。奥の 1 本が電流計の座。', 'obi'),
 ('前板', '皿の前に立つ板。電池の返しと前の脚。M2 皿ねじ 1 本で皿に留める。', 'maeita'),
 ('土手', '皿の縁に立つ壁。帯のツバが入る溝がある。', 'dote'),
 ('羊羹とマッチ棒', '天板の裏から下りて ReSpeaker の板の頭を 0.3 押さえる 2 本。', 'yokan'),
 ('座', '床に生えている ReSpeaker の台と前の唇、後ろの振れ止め。手前の低い畝は OLED の下辺のリブ。', 'za'),
 ('L', '天板から下りて OLED の裏の上の 2 穴を受ける足。ねじは前から、ナットは足の後ろの六角。', 'L'),
 ('爪と帯', 'ハッチの内面の下端の脚と唇。床の後ろの帯のポケットのバーの下へ入る。', 'tsume'),
 ('受け', '天板の裏から下りてトグルの胴を持つ箱。両側の壁と、端子の両脇の前の当て。', 'uke'),
 ('蓋・ロック・蓋の床の板', '電池の口を塞ぐ横スライドの蓋、ねじで止めるロック、ハッチの裏に接着する床の板。', 'futa'),
 ('柱と棚', '壁の内面。下の柱（床からのねじ）・上の柱（天板からのねじ）・腕を受ける棚。ナットは横穴。', 'hashira'),
 ('耳', 'フロントの四隅とハッチの上 2・右下 1。天板と床のねじがここを通って柱へ入る。', 'mimi'),
 ('バスタブと腕', '会話ボタン。スイッチを抱く筒（バスタブ）と、その耳を受ける天板の裏のブロック（腕）。', 'tub'),
 ('Type-C の受けと押さえ', '床の受け（座・当て・返し・控え）と左の壁の押さえ（レールと前の足）。基板は後ろから滑り込む。', 'uke_tc'),
]

SCREWS = [
 ('M3 × 8',  '4', 'ハブ基板 → 床（頭は床の裏のザグリ・ナットは基板の上）', '1'),
 ('M2 × 15', '3', '床の裏 → 左右の壁の下の柱。<b>前の 2 本はフロントの下の耳を通して手順 12、後ろ右はハッチの下の耳を通して手順 13</b>', '12 / 13'),
 ('M2 × 6',  '2', 'ブリッジの腕 → 壁の棚（上から。ナットは棚の横穴）', '6'),
 ('M2 皿',   '1', '前板 → 皿（上から。ナットはフランジの下の箱）', '6'),
 ('M2',      '2', '会話ボタンのスイッチ → バスタブ（机の上で）', '10'),
 ('M2',      '2', '会話ボタンのバスタブ → 天板の腕（耳の下から。ナットはブロックの横穴）', '10'),
 ('M2 × 6',  '2', 'つまみの島 → 天板（knob_v5 の組む順）', '10'),
 ('M2 × 6',  '2', 'OLED → 天板の L（前から。ナットは L の後ろの六角）', '12'),
 ('M2 × 8',  '2', '天板の後ろ 2 本 → ハッチの上の耳 → 後ろの柱（上から。3 枚を通す）', '13'),
 ('M2 × 8',  '2', '天板の前 2 本 → フロントの耳 → 前の柱（上から。3 枚を通す）', '12'),
 ('M2 × 6',  '1', '電池の蓋のロック（ナットは床の板の閉じたポケット・右から差す）', '13'),
 ('六角ナット', '1', 'トグル（ハッチの外から）', '13'),
]
NUTS = [
 ('M3', '4', 'ハブ基板の上（上向き）', '手順 1'),
 ('M2', '2', '壁の棚の横穴（左右 1 つずつ・棚の内側の面から）', '壁を寝かせているうち（手順 4）'),
 ('M2', '2', '後ろの上の柱の頭の横穴（前＝箱の内側から）', '壁を寝かせているうち（手順 4）'),
 ('M2', '2', '前の上の柱の頭の横穴（箱の内側の X の面から）', '壁を立ててから（手順 4）'),
 ('M2', '3', '下の柱の頭（上向き・置いてあるだけ）', '壁を立ててから・締めるまで伏せない（手順 4）'),
 ('M2', '1', '前板のフランジの下の箱', '手順 6'),
 ('M2', '4', '会話ボタン（バスタブの壁 2・天板の腕のブロック 2）', '手順 10'),
 ('M2', '2', 'つまみの島', '手順 10'),
 ('M2', '2', 'OLED の L の後ろ（六角・ピンセット）', '手順 12'),
 ('M2', '1', '蓋の床の板の閉じたポケット（右の縁の溝から差す）', '手順 13'),
 ('E リング 呼び 1.5', '6', '帯の軸 2（電流計）・天板のダボ 4（PowerBoost）', '手順 9・10'),
 ('E リング 呼び 6 / 3', '1 / 3', 'つまみの軸と基板（knob_v5）', '手順 10'),
]
PARTS = [
 ('床', '1', 'ハブの柱・座・OLED のリブ・Type-C の受け・ハッチの爪の帯・ねじ穴込み'),
 ('天板', '1', 'つまみと会話ボタンの台座・スピーカーの座と縁・PowerBoost のダボ・OLED の L・羊羹とマッチ棒・トグルの受け込み'),
 ('左の壁', '1', '柱と棚・Type-C の押さえ・ジャックの口・反り止めの格子'),
 ('右の壁', '1', '柱と棚・XIAO の USB-C の口・反り止めの格子'),
 ('フロント', '1', '窓・ヒゲ・耳・反り止めの格子'),
 ('ハッチ', '1', 'Type-C の口・トグルの穴・蓋の彫り込み・爪 2 つ・耳 3 つ・反り止めの格子'),
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
  図面は <b>hardware/case_v5.scad</b>、線は同じファイルの束、この手順の絵は <b>hardware/_asm_sim_v5.scad</b>。</p>
  <nav class="rail">__NAV__</nav>
</header>

<section class="sec"><h2>始める前に</h2>
<ul>
<li><b>向き</b>: 「前」は OLED の側、「後ろ」はハッチの側。「左右」は OLED を正面に見て言う。</li>
<li><b>樹脂にねじを切らない。</b>ねじは全部貫通してナットで受ける。ナットはほぼ横穴（差してから上下の肉に挟まれる）。</li>
<li><b>壁は横から当てる</b>（上から降ろさない）。<b>Type-C 基板と電池はハッチ側から</b>入れる。<b>帯は右から横に</b>差す。</li>
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
<p>切る長さは手順 0 の表。道は手順 3・5・8・9・12・13 に書いた。</p>
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


def build():
    IM = {k: img(k + '.png') for k in SEQ + [w[0] for w in WIDE] + [f[0] for f in FIXED]}
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
        acts = [a.replace('__CUTTABLE__', cuttable(segs)) for a in s['acts']]
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
