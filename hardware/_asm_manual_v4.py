# -*- coding: utf-8 -*-
# 組み立てマニュアル v4（hardware/assembly_v4.html）を case_v4.scad から作り直す道具。
#
#   python hardware/_asm_manual_v4.py             挿絵を出し直して HTML を書く
#   python hardware/_asm_manual_v4.py --no-render 挿絵はそのままで HTML だけ書き直す
#
# 手順は 1 か所（下の STEPS）にしか無い。段の中身の正は hardware/_asm_sim_v4.scad の upto()。
# 当たりの数字は同じファイルの CHK=... を manifold で回した実測（下の CHECKS に出典を書いた）。
# 挿絵は openscad の --render を PNG にして、背景の一色を縁から塗りつぶして透過にし、
# 12 枚を同じ枠で切って倍率を揃えている（段を並べたときに大きさが飛ばないように）。
# 🔴 2026-08-25 OpenSCAD Nightly は --render に値が要る（'--render' だけだと次の引数を食う）。'--render=full' で渡すこと
import base64, os, subprocess, sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
IMGDIR = os.path.join(HERE, '_manual_img_v4')
OUT = os.path.join(HERE, 'assembly_v4.html')
OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.exe')

N_STEPS = 12
# 段の 12 枚は同じカメラ（後ろ上から。OLED が正面を塞ぐので中が見える向き）
CAM = ['--projection=p', '--camera=43,36,22,58,0,205,330', '--imgsize=1100,850']
SEQ = ['st%d' % n for n in range(1, N_STEPS + 1)]
# 全体図（それぞれ viewall。こちらは正面右上から）
#   全体図は viewall なので倍率は揃わない。カメラは 1 枚ずつ選ぶ（wires だけ後ろから）
WIDE = [('explode', 'case_v4.scad', 'part', 'explode', '0,0,0,62,0,42,0'),
        ('look',    'case_v4.scad', 'part', 'look',    '0,0,0,60,0,25,0'),
        ('wires',   '_asm_sim_v4.scad', 'ST', 'wires', '0,0,0,58,0,205,0')]


def render():
    os.makedirs(IMGDIR, exist_ok=True)
    for st in SEQ:
        subprocess.run([OPENSCAD, '--backend=manifold', '--render=full'] + CAM +
                       ['-o', os.path.join(IMGDIR, st + '.png'), '-D', 'ST="%s"' % st,
                        os.path.join(HERE, '_asm_sim_v4.scad')],
                       check=True, capture_output=True)
        print('  ', st)
    for name, scad, var, val, cam in WIDE:
        subprocess.run([OPENSCAD, '--backend=manifold', '--render=full', '--projection=p',
                        '--autocenter', '--viewall', '--camera=' + cam,
                        '--imgsize=1200,950', '-o', os.path.join(IMGDIR, name + '.png'),
                        '-D', '%s="%s"' % (var, val), os.path.join(HERE, scad)],
                       check=True, capture_output=True)
        print('  ', name)


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
    for n in SEQ:                                     # 12 枚を同じ枠で切る = 倍率が揃う
        im = Image.fromarray(data[n][y0:y1, x0:x1], 'RGBA')
        if im.width > 900:
            im = im.resize((900, round(im.height * 900 / im.width)), Image.LANCZOS)
        im.save(os.path.join(IMGDIR, 'c_' + n + '.png'), optimize=True)
    for n, *_ in WIDE:                           # 全体図はそれぞれ自前の枠で切る
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
# 番号は hardware/_asm_sim_v4.scad の upto() と同じ。段の絵は「その手順を終えた状態」。
STEPS = [
 dict(n='1', t='床にハブ基板を留める', img='st1', acts=[
   '🆕 床を<b>台か机の端</b>に載せる。裏にドライバが入る高さが要る（手順 4 と同じ条件）。<b>机にベタ置きにしない。</b>',
   '🆕 <b><span class="d">M3×8</span> は 1 本ずつ入れる。</b>下から穴へ通し（頭は裏のザグリ <span class="d">φ6.0 × 2.2</span> に沈む）、'
   'ハブ基板を柱（<span class="d">φ7 × 2.5</span>）に載せて、その穴を通したところで上から <span class="d">M3</span> ナットを掛ける。'
   '🔴 <b>床を裏返して 4 本まとめて通してから起こすと、4 本とも落ちる。</b>ザグリは丸くて掴む物が無く、通し穴 <span class="n">φ3.4</span> は胴 3.0 より広い。',
   '🆕 締めるときは<b>下からドライバ（φ3.2）でビスの頭を押さえ</b>、上からナットを回す。<b>ザグリが丸いので回り止めが無い。</b>',
   '🆕 🔒 <b>後ろ左 <span class="n">[9.0, 64.9]</span> の 1 本だけ、ナットは<b>先の薄いピンセット</b>で押さえて下からビスを回す。</b>'
   'ナットの上に <span class="d">φ7.19</span> しか道が無いため（Type-C 基板の受けの補強の三角・'
   '<span class="n">tc_seat4()</span> がナットの高さで <span class="n">X 5.408</span> まで寄っている）。'
   '📄 5.5mm のナットドライバはボックスの外径が <span class="d">9.0mm</span>（HOZAN D-840-5.5）で<b>入らない</b>。'
   '掴み代は<b>片側 <span class="d">0.845mm</span></b>（ナットの二面幅 5.5 を挟むため）で、<b>ラジオペンチは入らない</b>。'
   '他の 3 本は片側 5.7 / 5.5 / 2.3 で、ナットドライバでも締まる。'
   '横からのスパナは入らない（左から <span class="d">5.5mm</span>・後ろから <span class="d">7.1mm</span> 手前で止まる）。',
   '穴の位置は <span class="n">[9.0, 18.9] / [9.0, 64.9] / [77.0, 18.9] / [77.0, 64.9]</span>。ハブは箱の X 中央（<span class="n">X 6.0〜80.0</span>）に座る。',
 ], note='床の裏はスタンドに載る面。ビスの頭が出ていると座らない。v3 と同じ流儀。',
    open_='🔒 2026-08-26 ユーザー決定: <b>後ろ左は工具を足さず、手持ちのピンセット（先は片側 0.8mm 以下）で押さえる。</b>'
          '受けの三角は欠かない（<b>CASE-V4-OPEN.md</b> T-6）。'),

 dict(n='2', t='ReSpeaker を立てる', img='st2', acts=[
   'ReSpeaker を床の溝に上から差す。<b>ビスは無い。</b>頭は手順 10 で天面のリブ 2 本が <span class="d">0.3mm</span> 押さえる。',
   '向きは、イヤホンジャックと ReSpeaker 自身の USB-C が<b>左の壁</b>側、XIAO の USB-C が<b>右の壁</b>側。左の壁に開いているのはイヤホンジャックの丸い口（<span class="d">φ6.05</span>）だけで、ReSpeaker 自身の USB-C は 🔒 外に出さず、壁の内側の盲ポケットが受ける。',
 ], warn='<b>壁より先に入れる。</b>壁を降ろした後で ReSpeaker を入れようとすると <span class="d">444.4mm³</span> 当たって入らない（<span class="n">CHK="rsp_after"</span>）。',
    open_='🔴 2026-08-25 <b>Type-C 基板はこの手順では入れない</b>。手順 4 で左の壁と一緒に降ろす（<b>CASE-V4-OPEN.md</b> A-13）。'),

 dict(n='3', t='ハブの口 10 本を全部挿して、低い車線に寝かせる', img='st3', acts=[
   '<span class="w">XIAO</span> 7・<span class="w">PHIN</span> 2・<span class="w">OLED</span> 4・<span class="w">AS5600</span> 5・<span class="w">BTN2</span> 2・<span class="w">REED</span> 2・<span class="w">PHOUT</span> 2・<span class="w">PWR</span> 3・<span class="w">INA</span> 4・<span class="w">TOGGLE</span> 2 の 10 束を、ハブ側だけ全部挿す。',
   '<b>低い車線（Z 19）に寝かせるのは 5 束</b>: <span class="w">XIAO</span>・<span class="w">AS5600</span>・<span class="w">BTN2</span>・<span class="w">PHIN</span>・<span class="w">PHOUT</span>。皿と帯の下を通る道は、いましか通せない。',
   '<b>上へ登る 5 束</b>（<span class="w">OLED</span>・<span class="w">INA</span>・<span class="w">TOGGLE</span>・<span class="w">REED</span>・<span class="w">PWR</span>）は、ハブに挿すだけにして左の溝と後ろの縦穴に寝かせておく。上げるのは手順 9。<b>充電の 2 本はハブには挿さらない</b>——ハブの口は上の 10 本で全部で、充電は Type-C 基板と PowerBoost をつなぐ線（手順 4 と 9）。',
   '🆕 <b>スピーカー IN（<span class="w">PHIN</span>）は、ReSpeaker の J2 側もここで挿す。</b>手順 5 でブリッジの皿（<span class="n">X 9〜49・Z 21.4〜23.4</span>）が J2 の真上に載るので、後からでは届かない（真上からピンセット φ5 が <span class="d">22.6mm</span>＝口の頭の <span class="d">3.9mm</span> 上で止まる）。',
   'XIAO 側は ReSpeaker に直付けした XIAO の上のピンヘッダへ。<b>使うのは 7 本だけ</b>で、残り 7 ピンは裸のまま。',
 ], note='この後ブリッジの皿（<span class="n">Z 21.4〜23.4・X 9〜49</span>）と壁〜壁の帯（<span class="n">Y 50.5〜62.9・全幅</span>）がこの上に載る。皿の真下・帯の真下に口がある束（XIAO・つまみ・BTN2・スピーカー IN/OUT）は、載せた後では届かない。',
    warn='逆に、上へ登る 5 束を<b>いま上げてしまうと</b>ブリッジが降ろせない（<span class="d">1037mm³</span>・<span class="n">CHK="brg_bad"</span>）。'),

 dict(n='4', t='左右の壁を降ろし、床の裏から 3 本で留める', img='st4', acts=[
   '🆕 <b>壁を寝かせたまま、ブリッジの棚に <span class="d">M2</span> ナットを 3 個、横から差す。</b>棚は'
   '<b>左の壁に 2 つ</b>（<span class="n">Y 30.5〜36.5</span> と <span class="n">Y 45.0〜50.4</span>）・'
   '<b>右の壁に 1 つ</b>（<span class="n">Y 56.9〜62.9</span>）。'
   '🔴 <b>口の向きは 1 つだけ逆</b>: 左前と右は棚の<b>ハッチ側（+Y）の面</b>（溝は <span class="n">Z 18.1〜19.8</span>）、'
   '<b>左の <span class="n">Y 45.0〜50.4</span>（3 本目の棚）だけは前（−Y ＝ OLED 側）の面</b>（溝は <span class="n">Z 21.1〜22.8</span>）。'
   'この 1 つを +Y から差そうとしても、帯（<span class="n">Z 21.4〜</span>）が通路の天井を塞いでいて入らない。'
   '奥まで押すと上下の肉に挟まれ、<b>壁を立てても落ちない</b>。',
   '🆕 <b>3 個とも、Type-C 基板を持つ前に入れる。</b>充電の 2 本を挿した後だと、前の口（左の <span class="n">Y 45.0</span>）へ差す道を '
   '<span class="w">CHG</span> の登り（<span class="n">X 5.05〜6.55・Y 43.0</span>）が跨ぐ。',
   '🆕 🔴 <b>Type-C 基板に充電の 2 本を挿すのは、板を手に持っているうち。</b>口は <span class="n">X 4.52〜7.07・Y 48.67〜58.67</span> の縦 2 段（<span class="n">Z 3.99〜9.07</span> と <span class="n">14.15〜19.23</span>）で、<b>下の口は上の口の真下</b>。壁を降ろした後は真上から届くのが上の口の頭までで、下の口には触れない。手順 5 でブリッジの帯（<span class="n">Y 50.5〜62.9・全幅</span>）が載ると、上の口も <span class="d">23.6mm</span>（頭の <span class="d">7.2mm</span> 上）で止まる。線は左の溝へ垂らしたまま降ろし、PowerBoost 側は手順 9 で挿す。',
   '🔴 <b>左の壁は Type-C 基板を抱いて降ろす。</b>基板の板の裏を左の壁の内面に当て、口の鼻先を<b>ハッチ側（後ろ）</b>へ向けたまま、壁と基板を一緒にまっすぐ下ろす。板の下端が床の受け（前の当て・後ろの控え・底の座）に入れば座る。<b>先に立てることも、壁の後から真上に落とすことも出来ない</b>——前者は板の裏を受ける面が左壁の内面そのものなので <span class="d">−X</span> へ倒れ、後者は天面の後ろ左のボスが板の真上を <span class="d">75.6mm³</span> 塞ぐ（<span class="n">close_tc</span>）。',
   '壁はまっすぐ <b>Z で</b>降ろす。傾けない。',
   '🆕 <b>壁が立ってから</b>、<span class="d">M2</span> ナット 3 個を壁の下の柱の頭（<span class="n">Z 10.2〜12.0</span>）へ上から落とす。'
   '<b>ここは上向きのポケット</b>（<span class="n">bottom_boss</span> の <span class="n">hex_pocket</span>）なので、'
   '<b>寝かせた壁に先に入れておくことは出来ない</b>——横を向いて落ちる。',
   '箱は<b>伏せずに</b>机の端か台に載せ、下から <span class="d">M2×15</span> ×3。前の 2 本 <span class="n">[4.2, 4.75] / [81.8, 4.75]</span>、後ろ右 1 本 <span class="n">[82.0, 69.5]</span>（ハブの角を欠いた L 形のボス）。',
   '<b>後ろ左のビスは無い。</b>v3 と同じ 3 本構成で、後ろの床はこの 1 本とハッチの爪 2 つ・トグルの外ナットが持つ。',
 ], warn='ナットは落とし込んだだけで、六角のポケットは <span class="d">4.3</span>・ナットは <span class="d">4.0</span> で <b>0.3 の遊びがある</b>。箱を伏せると落ちる。',
    note='前の 2 本のボスは <b>L 形</b>。ReSpeaker の部品の真上を全高で欠いてあるので（2026-08-25 の直し）、右のナットの座は後ろ左が開いている。開口は <span class="d">3.77</span> で二面幅 <span class="d">4.3</span> より狭く、横へは抜けない。'),

 dict(n='5', t='ブリッジを上から降ろす', img='st5', acts=[
   '前の脚（1 枚板・厚み <span class="d">2.0</span>・<span class="n">X 21.5〜44.5</span>）を床の受け溝へ入れながら、まっすぐ <b>Z で</b>降ろす。',
   '皿（電池の受け・<span class="n">X 9〜49</span>。🔒 2026-08-26 に<b>前左の角だけ <span class="n">X 10.2</span> まで欠いた</b>——ReSpeaker の J2 のソケットを逃がすため）が下、壁〜壁の帯（<span class="n">Y 50.5〜62.9</span>）が後ろ。皿から左右の壁へ<b>腕</b>が伸びていて、手順 4 で入れたナットの上に載る。',
   '🆕 <b>載ったら上から 3 本締める</b>: <span class="n">[4.2, 33.5]</span>（左・前・<span class="d">M2×6</span>）/ <span class="n">[4.2, 47.7]</span>（左・帯の前＝OLED 側・<b>この 1 本だけ <span class="d">M2×4</span></b>）/ <span class="n">[81.9, 59.9]</span>（右・<span class="d">M2×6</span>）。頭は座ぐり（<span class="d">φ3.4 × 1.6</span>）に沈む。締まる順は <b>頭 → 腕 2.4 → 棚の肉 1.6 → ナット</b>。<b>電池より先に締める。</b>',
   '帯の裏の左端に <b>Type-C 基板の押さえ</b>（<span class="n">X 1.694〜3.9・Y 58.6〜62.2</span>・下端 <span class="n">Z 20.7</span>）が付いている。ここが基板の Z の抜け止めなので、<b>ブリッジを載せるまで基板は上へ抜ける。</b>',
 ], warn='🔴 <b>ブリッジは OLED より先。</b>OLED を先に立てると受け皿が OLED の線の帯（<span class="n">X 37.9〜48.1・Z 45〜48</span>）を通り、ヘッダのピン先とも当たる（<span class="n">close_desk</span> 156mm³ ・<b>CASE-V4-LOG.md</b> §10）。',
    note='✅ 2026-08-26 <b>3 本目は帯の前（OLED 側・<span class="n">X 4.194, Y 47.7</span>）へ移した。</b>'
         '後ろの耳（旧 <span class="n">[4.2, 66.2]</span>）だと頭から真上 <span class="d">13.0mm</span> で天面の後ろ左の柱に当たり、まっすぐなドライバが入らなかった。'
         'いまは <span class="n">chk_t1</span> が 0（ドライバ φ3.2 × 24 が頭から立つ）。この 1 本だけ <span class="d">M2×4</span>。'
         '前の脚はビス無しで床の溝に座るだけ（片持ち 20mm・たわみ ⚠ 概算 0.013mm）。'),

 dict(n='6', t='留め帯 A・B・C を横から差す', img='st6', acts=[
   '<span class="d">M2</span> ナット 6 個を、帯の面に開いた<b>横穴</b>へ差し込む（6 か所とも横穴。上下を肉で挟むので、差したらどう向けても落ちない）。',
   '🆕 <b>1 本ずつ、つまみ側（右）へ <span class="d">2.0mm</span> ずらした位置に置いてから、まっすぐ <span class="d">−X</span> へ 2.0 押し込む。</b>⊓ の足が皿の縁のレールの切れ目（<span class="n">Y 15.45〜21.45 / 33.2〜42.2 / 52.6〜58.6</span>）に落ち、足の裏の<b>ツバ</b>（前後へ <span class="d">2.0</span>・高さ <span class="n">Z 23.4〜25.4</span>）が土手を貫通している溝へ入る。',
   '🔴 <b>上からは入らない。</b>ツバの上に土手の肉が <span class="d">1.8</span> あるので、かぶせようとすると当たる（<span class="n">CHK="strap_top"</span> で 75mm³）。<b>電池より先。</b>電池が居ると横へ 2.0 動けない（<span class="n">CHK="strap_bad"</span> で 221mm³）。',
   '⚠ <b>帯 A を差すときだけ、右の溝の <span class="w">XIAO</span> の束を指でよけておく。</b>右足が通る場所（<span class="n">X 53.85〜55.0・Y 17.54〜21.45</span>）に束が立ち上がっている。剛体との当たりは 3 本とも 0。',
   'A は電流計の前穴、B は電流計の後穴と PowerBoost の前 2 穴、C は PowerBoost の後ろ 2 穴を受ける。',
 ], note='通路は帯の一番近い面へ抜けている（前へ 0.85 / 1.93、後ろへ 0.61 / 1.47 / 2.58 / 2.76）。六角の二面幅を通路の壁が挟むので回り止めにもなる。'),

 dict(n='7', t='電池を後ろから差し込む', img='st7', acts=[
   'タブ（JST の線）が<b>後ろ＝ハッチ側</b>に来る向きで、ハッチ口から <span class="d">−Y</span> へまっすぐ差し込む。皿が床・足が左右・帯の天板が天井の、<b>+Y にだけ開いた鞘</b>を滑らせる。前は電池ガードが受ける。',
   '座る場所は <span class="n">X 11.5〜46.5・Y 13.9〜63.9・Z 23.4〜29.4</span>（厚み 6 が高さ）。',
   '🔴 <b>入れた電池がそのまま帯の楔になる。</b>足と電池の隙間は左右 <span class="d">0.5</span>、ツバの掛かりは <span class="d">2.0</span>。電池が居る限り帯は横へ戻せず、ツバが外れない。ビスは 1 本も要らない。',
 ], note='後で交換するときも同じ道を逆に通る（このページの最後）。もう上からは落とせない。'),

 dict(n='8', t='電流計と PowerBoost を座に締める', img='st8', acts=[
   '座は板の裏と同じ面。<b>傾きも浮きも 2 枚で別</b>で、PowerBoost は <b>10°・浮き 0.5</b>、電流計は 🔒 2026-08-26 から <b>水平（0°）・浮き 1.0</b>。'
   '板を全面で当てて、<span class="d">M2</span> 6 本を<b>鉛直に</b>締める（PowerBoost は板に直角ではない）。',
   '電流計は 2 穴（帯 A と B）、PowerBoost は 4 穴（帯 B と C）。',
   '<b>6 本とも <span class="d">M2×4</span>。</b>ナットの居場所（横穴の天井）が板の裏の近くにあるので、長さは 1 種類で足りる。',
   '掛かりは <span class="n">1.37 / 1.56 / 1.56 / 1.6 / 1.6 / 1.6mm</span>（ナットの厚み 1.6 に対して）。先はどの穴も帯の天板の裏（＝電池の上面）の内側で止まる。'
   '余裕は電流計が <span class="n">0.6mm</span>（🔒 2026-08-26 に板の浮きを 0.5 → 1.0 にして 0.1 から広げた）、PowerBoost が <span class="n">0.54〜3.63mm</span>。',
 ], warn='上限を超えると先が天板の裏を抜けて<b>電池の頭を突く</b>（天板の裏＝電池の上面で、隙間はゼロ）。🔴 2026-08-25 夜の板の 0.5 持ち上げ（<b>CASE-V4-LOG.md</b> §13.7）で、先が出る穴は無くなった。2026-08-26 に電流計を水平にして残り <span class="n">0.1mm</span> まで詰まったが、🔒 板の浮きを 1.0 にして <span class="n">0.6mm</span> へ戻した（<b>CASE-V4-LOG.md</b> §15.5）。長い物に替えないこと。',
    note='<b>PowerBoost の L 字 3 ピン（5V・GND・EN）は縁の外＝後ろ（ハッチ側）向き。</b>USB のピンは上向き。'
         '🔒 2026-08-26 <b>電流計の INPUT/OUT 4 ピンは L 字をやめて上向き（直立て）</b>にした。板を締める前に向きを確かめる。'),

 dict(n='9', t='OLED を立て、上の車線 5 束と電源系 7 本を通す', img='st9', acts=[
   'OLED を上から降ろし、下辺の後ろのリブに当てる。この時点ではまだ宙ぶらりんで、手順 10・11 で L と窓が挟む。',
   '<b>上の車線</b>: <span class="w">OLED</span> 4 本は左の溝（<span class="n">X 9</span>）を <span class="n">Z 45.2</span> まで上がって前を右へ。<span class="w">INA</span> の I2C 4 本は後ろの縦穴から <span class="n">X 52.8</span> を上がり、座の板の下（<span class="n">Z 39.5 / 41.0</span>）を前へ。<span class="w">TOGGLE</span> 2 本は <span class="n">Z 46.8</span>、<span class="w">REED</span> 2 本は <b>🔒 コネクタ無しの直はんだ</b>でつまみのデッキの足元へ。充電 2 本は左の壁ぎわから天井の下（<span class="n">Z 47.3</span>）を通って PowerBoost の USB ピンへ。',
   '<b>電源系 7 本</b>: 電池のタブ → 電流計の <span class="w">INPUT</span>、電流計の <span class="w">OUT</span> → PowerBoost の JST、PowerBoost の L 字 3 ピン → ハブの <span class="w">PWR</span>。ハブ側は手順 3 で挿してあるので挿すのは PowerBoost 側だけで、道は蓋の増し肉の上の 3 車線（<span class="n">Z 35.2 / 36.7 / 38.2</span>）を右へ走ってから後ろの縦穴を下りる。',
 ], warn='PowerBoost の L のハウジングの後端は <span class="n">Y 69.7</span>。ハッチの内面まで <span class="d">2.3mm</span> しかない。'),

 dict(n='10', t='天面の小組と、天面側の配線', img='st10', acts=[
   '天面を<b>裏返して</b>置き、AS5600 の基板をつまみの島の 4 本の柱へ <span class="d">M2×6</span> ×4（下から・ナットは柱の小判のスロット）。',
   '会話ボタンの受けとキャップ、スピーカー（両面テープ・枠が天板の座に <span class="d">0.6mm</span> 沈む）、リードスイッチ（デッキのポケットへ直はんだ）。',
   '線をつなぐ: <span class="w">AS5600</span> 5・<span class="w">BTN2</span> 2・<span class="w">PHOUT</span> 2・<span class="w">REED</span> 2。天面は線でつながったまま <b>箱の奥（ハッチ側）に、手前から奥へ裏返して</b>置く（外の面を机に着け、左へ <span class="n">25mm</span> ずらす。天面の外形は <span class="n">X −27〜61・Y 77〜153</span>）。机に置くので<b>両手が空く</b>——はんだ付けが 3 束あるので、持ったままでは出来ない。',
 ], note='置き場で要る線の長さが変わる。🆕 2026-08-26 に角度と位置を掃いて一番短い置き方を出した（<b>hardware/_asm_wirepose.py</b> の <span class="n">best()</span>）。奥へ返して置くと 4 束とも <b>+29〜+40mm</b> で収まる。同じ天面を<b>左</b>に倒すと <span class="w">REED</span> が <b>+120mm</b> 要る（裏返しは横の 1 軸を鏡にするので、軸から遠い端子ほど 2 倍動く）。v3 が左を最短としたのは v3 の配置の話。'),

 dict(n='11', t='天面を降ろし、OLED を留め、フロントを差す', img='st11', acts=[
   '先に <span class="d">M2</span> ナット 4 個を落とす。後ろの 2 個は左右の壁の柱の頭（<span class="n">Z 46.65〜48.454</span>）、前の 2 個は耳兼用の柱。<b>この 4 個は天面を載せる前にしか入らない。</b>',
   '天面＋つまみ＋スピーカー＋会話ボタンをまっすぐ <b>Z で</b>降ろす。ReSpeaker の頭を前リブ（<span class="n">X 31.4〜37.4</span>）と腕（<span class="n">X 50.0〜52.4</span>）が <span class="d">0.3mm</span> 押さえる。',
   'OLED を<b>前から</b> <span class="d">M2×6</span> ×2 で天面の L に締める。ビスの道は左右とも外まで開いている。',
   'ナットは L の裏のポケットへ<b>後ろから差す</b>。L の後ろの空きは<b>左が <span class="d">3.4mm</span>・右が <span class="d">4.45mm</span></b>（ナットの厚み <span class="d">1.6</span> に対して）。'
   '✅ 2026-08-26 まではここが <span class="d">1.3mm</span> しか無くて入らなかった（塞いでいたのはスピーカーの右前の丸み）。つまみとスピーカーを内側へ 4 動かして解決（<b>CASE-V4-OPEN.md</b> の T-2）。',
   'フロントを<b>前から +Y に</b>差し込む。',
   '四隅を <span class="d">M2×6</span> ×4 で締める。前の 2 本は 天面 → フロントの耳 → 壁の耳柱 の <b>3 枚</b>を通る。',
 ], warn='入れ忘れたナットは、天面を外さないと入らない。'),

 dict(n='12', t='トグル・ハッチ・電池の蓋・尻尾', img='st12', acts=[
   'トグルはハッチの穴にネジ部を通し、<b>外から六角ナット</b>で締める。アンテナ線はトグルの下のスリットへ。',
   '🆕 <b>トグルの 2 本は、ハッチを箱から離したまま繋ぐ。</b>天面もフロントも既に載っていて中から手は入らないので、ここだけは「箱の外での配線」になる。<b>ハッチは外の面を下にして、上下を返して（トグルが箱側に来るように）箱の後ろの机へ置く</b>——そのとき要る長さは <span class="d">71.6mm</span>（組んだ姿勢 57.4 の <span class="d">+14.3</span>）で、線の増し <span class="d">+40</span> の中に収まる。<b>そのまま（レバーが奥）置くと <span class="d">+45.1</span> 要って足りない。</b>数字は <b>hardware/_asm_wirepose.py</b> の <span class="n">hatch()</span>。',
   '🆕 <b>ロックの <span class="d">M2</span> ナット 1 個を、ハッチを離しているうちに落とし込む。</b>ハッチの<b>内側</b>のボスの頭に'
   '溝が彫ってあり（<span class="n">sw4_lock_cut</span>）、そこから六角のポケットへ滑らせる。'
   '🔴 <b>ハッチを箱に付けた後では、このボスは箱の中で手が届かない。</b>ハッチを外の面を下にして置いた姿勢なら、'
   'ポケットは上を向いているので入れたまま起こせる（ビスは外から入る）。',
   '電池の蓋: 磁石（<span class="d">φ6 × 2.0</span>）を蓋に 2 個・ハッチ側の座に 2 個。蓋を彫り込み帯の逃がし口へ入れて<b>左へ <span class="d">5.5</span> ずらし</b>、門形のロックを <span class="d">M2×6</span> ×1 で締める。🔒 2026-08-26 に下スライドをやめて<b>横スライド</b>にした（下だと自重が開く向きに効いて、ロックのビスが構造材になっていた）。外すときは右へ 5.5。',
   'ハッチは下の爪 2 つを床の後ろのバーへ <span class="d">−Y</span> にまっすぐ滑り込ませる。上はトグルの外ナットが押さえる。<b>ハッチ自体のビスは無い。</b>',
   '尻尾をトグルのレバーのボアに挿す。アンテナ線は尻尾の中の溝へ。',
 ]),
]

# 線: 束 / 本数 / 模型の折れ線長（最長）/ 通した道
# 出どころ: _v4_core.scad の w_*() の点列を wire() を差し替えて echo させた実測（2026-08-25）
WIRES = [
 ('XIAO',       '7', '62.2', 'Z19 → 右の溝 X55.35 →（上段）島の下 /（下段）X73 で Z11.9 へ下りる'),
 ('PHIN',       '2', '87.8', 'J2 の確保空間 → 皿の下を Z19.6 / 18.0 の 2 段で右へ（Y 26.0・つまみの口の南を 0.2 で躱す）'),
 ('OLED',       '4', '79.2', 'Z19 → 左の溝 X9 → Z45.2 で前を右へ → 線の帯で上がる'),
 ('AS5600',     '5', '51.6', 'Z19 → X58 で Z13.3 → 島の下を Y36.8 へ横断'),
 ('BTN2',       '2', '74.7', 'Z19 → X11.75 → Y17.4 で上がる → タクトの足'),
 ('REED',       '2', '51.3', '縦穴 → Z41 で潜る → デッキの足へ <b>直はんだ</b>'),
 ('PHOUT',      '2', '96.5', '帯の前へ抜けて右の壁ぎわ X83.3 → 天井の下 → スピーカーの下'),
 ('TOGGLE',     '2', '57.4', '縦穴 → Z46.8 の車線 → 端子の真上'),
 ('INA (I2C)',  '4', '80.0', '縦穴 Y67.5（Z 22.3・口の曲がりの上）→ X52.8 で上がる → 座の板の下 Z40.6 を前へ'),
 ('PWR',        '3', '67.5', '蓋の増し肉の上 Z35.2 / 36.7 / 38.2 を右へ → 縦穴を Z21.9 まで下りる（口の曲がりの上で止める）'),
 ('BAT → INA',  '2', '78.9', '縦穴 → 左の壁ぎわ X2.75 / 4.15 を前へ'),
 ('INA → PB',   '2', '60.4', '左の壁ぎわ → 棚の上（Z42 / 43.5）を右へ → JST のプラグ'),
 ('CHG',        '2', '72.2', '左の壁ぎわ → 天井の下 Z47.3 → PowerBoost の USB ピン'),
]

SCREWS = [
 ('M3 × 8',  '4', 'ハブ基板 → 床（頭は床の裏のザグリ・ナットは基板の上）', '1'),
 ('M2 × 15', '3', '床の裏 → 左右の壁の下の柱（前 2・後ろ右 1）', '4'),
 ('M2 × 4',  '6', '電流計 / PowerBoost → 留め帯の座（<b>6 穴とも同じ長さ</b>・掛かり 1.34〜1.6mm）', '8'),
 ('M2 × 6',  '2', 'ブリッジ → 壁の棚（左前・右。上から。<b>ナットは棚に横から差す</b>）', '5'),
 ('M2 × 4',  '1', 'ブリッジ → 帯の前の棚（左・OLED 側 <span class="n">[4.2, 47.7]</span>）。🔴 M2×6 だと先が棚の底から 2.0mm 出る', '5'),
 ('M2 × 6',  '4', 'AS5600 の基板 → つまみの島の柱（下から）', '10'),
 ('M2 × 6',  '2', 'OLED → 天面の L（前から・ナットは L の後ろ）', '11'),
 ('M2 × 6',  '4', '天面の四隅（後ろ 2 = 壁の柱 / 前 2 = 天面＋耳＋耳柱の 3 枚）', '11'),
 ('M2 × 6',  '1', '電池の蓋のロック', '12'),
 ('六角ナット', '1', 'トグル（ハッチの外から）', '12'),
]

NUTS = [
 ('M3',  '4', 'ハブ基板の上（上向き）', '🔴 <b>後ろ左だけ工具の道が φ7.19</b>（T-6）'),
 ('M2',  '3', '壁の下の柱の頭（上向き・<span class="n">Z 10.2〜12.0</span>）', '<b>箱を伏せると落ちる</b>'),
 ('M2',  '6', '留め帯の座の<b>横穴</b>（帯の面から差す）', '差したら落ちない'),
 ('M2',  '3', 'ブリッジの棚の<b>横穴</b>（左 2・右 1。左前と右は +Y の面、<b>左の Y 45.0〜50.4 だけ −Y ＝ 前</b>の面から差す）',
  '<b>壁を寝かせているうち・充電線より先</b>'),
 ('M2',  '4', 'つまみの島の柱の小判スロット（横向き・v5 の設計）', '天面が裏返しのうちに'),
 ('M2',  '2', 'OLED の L の後ろ（横向き・残り 0.2）', '<b>ピンセット</b>'),
 ('M2',  '4', '天面の後ろの柱 2・前の耳柱 2（上向き）', '天面を載せる前だけ'),
 ('M2',  '1', '電池の蓋のロック（ハッチの<b>内側</b>のボス・頭の溝から落とす）', '<b>ハッチを箱に付ける前だけ</b>'),
]

# 実測（2026-08-26 に全部回し直した・openscad --backend=manifold）。0 が正。数字は _asm_sim_v4.scad の CHK / case_v4.scad の part
# 🔴 この表は手書きで、図面に自動で追従しない。2026-08-26 に「静止は 0 なのに組む順の掃引が 60mm³」を見落としていた（CASE-V4-LOG.md §17）。
#    図面を触ったら _asm_sim_v4.scad の CHK を回し直して、ここの数字を書き換えること。
CHECKS = [
 ('壁を上から降ろす', 'CHK="wall_l" / "wall_r"', '<b>0 / 0.01mm³</b>', 'ok',
  '✅ 2026-08-26 に回し直して <b>0.01</b>（0 厚の膜）。2026-08-25 に前の床ボスを L 形にして解消（旧 3.1 / 29.0）。かつて右へ出ていた 25mm³ は、'
  'ブリッジを留める棚が <span class="w">PHOUT</span> の<b>天井下の区間</b>（<span class="n">X 82.55〜84.05・Z 44.35〜47.35</span>）を通る分。'
  'この 2 本はスピーカー（天面の部品）に付いたまま最後に降りてくるので、壁を降ろす時点では箱に居ない'),
 ('ブリッジを上から降ろす', 'CHK="brg"', '<b>46.4</b>（剛体は 0）', 'warn',
  '🔴 2026-08-26、<b>このマニュアルの検算でここが 60.5mm³ になっているのが見つかった。</b>静止の検査（<span class="n">chk_all</span> ほか）は全部 0 のままで、'
  '<b>組む順の掃引だけ回し直していなかった</b>ので素通りしていた。皿の左縁 <span class="n">X 9.00</span> が ReSpeaker の '
  '<b>J2（スピーカーのソケット・右端 <span class="n">X 10.08</span>）</b>に 1.08 入っていた（実体と 7mm³）。'
  '出どころは 🔒 同日の「帯ごと左に 4mm」（<span class="n">BAT_DX</span> +1 → −3）で、<b>4 のうち最後の 1.08 が J2 に乗った</b>もの。'
  '🔒 ユーザーの選択①で<b>皿の前左の角を欠いた</b>（<span class="n">X 9.0 → 10.2</span> を <span class="n">Y 12.9〜16.9</span>・<span class="n">brg_j2_cut()</span>）。ソケットとの当たりは 0 になった。'
  '残る 46.4 の内訳は <b>BTN2 の足へ渡る最後の枝 28.8mm³</b>（タクトは手順 10）と <b>J2 のプラグ＋線の確保空間 17.6mm³</b>（⬜ 下の行）。詳細は <b>CASE-V4-LOG.md</b> §17。'
  '🔴 2026-08-26、右の腕をまっすぐな 1 枚で作ったときは <span class="w">XIAO</span> の車線（<span class="n">上段 Y 29.9・Z 27.13</span>）を上から踏んで 99mm³ 出た。'
  '腕を 2 段（内側は <span class="n">Y 32.0</span> から・壁ぎわだけ幅を戻す）にして 0 にした'),
 ('ブリッジを箱へ留める（棚・ビス・本体）', 'W="brgldg" / "brghw" / "brgchk"', '<b>0 / 0 / 16.3</b>', 'warn',
  '棚 3 つ ↔ 中身、M2×6 とナットの現物 ↔ 周り、ブリッジ本体 ↔ 全部。'
  '⬜ <span class="n">brgchk</span> の 16.3mm³ は <b>J2 のプラグ＋線の確保空間</b>（<span class="n">X 9.00〜10.08・Y 16.9〜25.03</span>）。'
  'あれは「基板面から 15」の仮の包絡なので、<b>PHR-2 の尻の実測が出るまで保留</b>する——というのが 🔒 ユーザーの選択①の中身。'
  '🔴 初版はナットを棚の<b>上面</b>に落とす形で、締めても棚が挟まらず逆さで抜けた（ユーザー指摘）。横から差す捕捉溝に直した'),
 ('（反例）上の車線を先に通した場合', 'CHK="brg_bad"', '1037mm³', 'stop',
  '手順 3 の分け方が効いていることの裏取り'),
 ('留め帯 3 本を横から差す（−X へ 2.0）', 'CHK="strap" / "strap_dry"', '<b>0.57 / 0.57</b>', 'warn',
  '🔒 2026-08-26 にツバと溝を付けて、上から入れる形をやめた。'
  '✅ 同日に線を引き直して、かつて残っていた <span class="w">XIAO</span> の束との 20.6mm³ は消えた。'
  '残る 0.57mm³ は帯 A の左足の角が J2 のソケットの頭に <b>0.09mm</b> 触れる分で、手の精度 0.3mm の下なので<b>項目にしない</b>（<b>CASE-V4-LOG.md</b> §17）。'
  '差す向きは右（つまみ側）から。左からにすると <span class="w">BTN2</span> の束を通る'),
 ('（反例）帯を上からかぶせた場合 / 電池を先に入れた場合', 'CHK="strap_top" / "strap_bad"', '81 / 201mm³', 'stop',
  'ツバが土手の肉に当たる／電池が居て横へ 2.0 動けない。どちらも<b>成立しないことの裏取り</b>'),
 ('留め帯の Z の抜け止め（ツバ ↔ 土手）', 'W="—"（case_v4 の掃引）', '<b>0.2mm</b>', 'ok',
  '真上へ <span class="n">+0.20</span> では当たり 0、<span class="n">+0.25</span> から当たる。3 本とも同じで、残る遊びは溝の逃げ <span class="n">TAB_CL = 0.2</span> ちょうど。'
  '帯 A は前にツバが無い（前に土手が無い）が、後ろのツバを軸に前を持ち上げる向きも <b>0.5°（前が 0.05mm）で当たる</b>'),
 ('電池を後ろから差し込む（留め帯の入った鞘）', 'CHK="bat"', '<b>0</b>', 'ok',
  '手順 6 の帯 3 本が入った状態で <span class="d">−Y</span> へ 55mm 通す掃引。交換のときの引き出しと同じ道'),
 ('電流計と PowerBoost を座へ降ろす', 'CHK="boards"', '<b>12.0 → 0.6mm³</b>', 'warn',
  '11.4mm³ は BTN2 の<b>足へ渡る枝</b>（相手のタクトは手順 10 の部品で、この時点では箱に居ない）。それを除いても <b>0.6mm³</b> 残る。電流計の板の縁 ↔ 帯 A の座（<span class="n">X 15.48〜16.12・Y 19.60〜20.38・Z 33.51〜34.51</span>）で、静止でも同じ値が出る'),
 ('OLED を上から降ろす', 'CHK="oled"', '<b>0</b>', 'ok', ''),
 ('上の車線と電源系（静止）', 'CHK="whigh"', '<b>0</b>', 'ok',
  '2026-08-25 夜、ハブの口の実測（曲がり 3.6 → 4.5）で 8 束が当たったので 9 束を引き直した。'
  '前列は出発点を 0.45 外へ、後列は口の真上を通る高さを 21.1 の上へ'),
 ('天面一式を降ろす', 'part="close_top"', '<b>0</b>', 'ok', 'OLED を天面に付けて一緒に降ろす形（v3 の流儀）でも 0'),
 ('フロントを前から差す', 'part="close_front"', '<b>0.13mm³</b>', 'ok',
  '0 厚の膜 2 枚（<span class="n">Y 1.00〜1.01</span>）。実体の重なりではない'),
 ('ハッチ（トグル・蓋ごと）を閉じる', 'part="close_hatch"', '<b>0.02mm³</b>', 'ok',
  '充電の口の細片 2 つ（<span class="n">X 6.44〜6.55・Y 72.0〜73.2・Z 6.03 と 14.86</span>・各 0.11mm 角）。'
  '<b>口は殻の大きさ</b>で逃げゼロの設計なので、下の <span class="n">chk_all</span> に出るのと同じ物。手の精度 0.3mm の下'),
 ('組み上がった静止（皮 6 枚 ↔ 中身）', 'part="chk_all"', '<b>0.03mm³</b>', 'ok',
  '4 つの細片（XIAO の口に 2・充電の口に 2）。どちらも <b>口は殻の大きさ</b>で逃げゼロの設計。🔴 2026-08-26 に塊へ割って測ったら <b>0 厚の膜ではなく 0.11mm 角の実体</b>だった（XIAO は <span class="n">X 84.35〜85.43</span>、充電は <span class="n">X 6.44〜6.55</span>）。手の精度 0.3mm の下'),
 ('ReSpeaker の押さえ', 'part="chk_press"', '4.7mm³', 'ok',
  '<b>これは 0 だと不合格。</b>押し代 0.3 が板に届いている証拠。'
  '内訳は前リブ <span class="n">X 31.40〜37.40</span> が 3.33mm³、腕 <span class="n">X 50.00〜52.40</span> が 1.33mm³。'
  '🔴 2026-08-26 につまみとスピーカーを内側へ 4 動かしたぶん腕の当たりが 4.7 → 2.4mm 幅に減り、合計は 6 → 4.7mm³ になった'),
 ('電池の交換の道（組んだ後）', 'chk_shut_slide / chk_lock_out / chk_shut_out / chk_swap', '<b>0 / 0 / 0 / 0</b>', 'ok',
  '🆕 2026-08-26 に初めて当てた。蓋を右へ 5.5 ずらす・ロックを後ろへ外す・蓋を後ろへ抜く・電池を後ろへ 45 引き出す、の 4 本とも 0。'
  '下の「電池の交換」の手順はこの 4 本が裏取り'),
]

BLANKS = [
 ('① ⚠ 板を 0.5 持ち上げた代金',
'ナット 6 個を横穴にするため、板（電流計・PowerBoost）の蝶番を天板の面から <span class="d">0.5</span> 浮かせた。代金は 2 つ: <b>天面の裏の局所ポケット</b>（PB の USB の逃げ）が深さ 1.27 → 1.77 になり<b>板の残りが 0.73</b>、<b>INA の I2C の前走り</b>が 1.5×2 本では入らなくなり 2.2 の束 1 本に戻って <b>X の余裕が 0.35 → 0</b>。どちらも実物で効くかは刷ってから',
  '⚠ 要観察'),
 ('② ブリッジと留め帯を、どの向きで刷るか',
  '出力は 2026-08-26 に付いた（<span class="n">print_bridge</span> / <span class="n">print_strap</span> / <span class="n">print_btn</span>・どれも底の Z は 0）。'
  '<b>留め帯の向きは同日に決まった</b>（足とツバを下・ツバの上面が 45° なので支えが要らない）。残っているのは<b>ブリッジ</b>で、皿から後ろが宙に浮く',
  '⬜ ブリッジの向きが未決'),
 ('③ 支えが無い所',
  'ブリッジの帯の左右の端の受け・脚の Z の留め・電池の Z の抜け止め'
  '（Type-C 基板の保持は 2026-08-25 に受けを作り、🔒 同日ユーザー検収済み。'
  '<b>留め帯の Z の抜け止めは 2026-08-26 にツバと溝で解決した</b>）',
  '<b>CASE-V4-OPEN.md</b> A-3〜A-6'),
 ('④ 線の長さ（置いた姿勢）',
  '✅ 2026-08-26 に測った（<b>hardware/_asm_wirepose.py</b>）。手順 10 の置き場を角度と位置で掃いて、'
  '一番短い置き方（奥へ返して左へ 25）で <b>4 束とも +29〜+40mm</b>。作る長さは実長 ＋65mm。'
  '✅ 同日、閉じた後に戻る<b>最大 40mm の余り</b>の行き場も測った。箱の中の空きは <b>195,910mm³</b>（内寸の 2/3）で、'
  '1mm の格子で塊に割ると <b>186,185mm³ が 1 つながり</b>（残り 142 個は合計 1,000mm³ 足らずの隅）。'
  '4 束ぶんの余りは 2.2mm の束 × 40mm × 4 ＝ <b>約 600mm³</b> なので、行き場はある。'
  '🔴 ただし空いていても<b>置いてはいけない道</b>が 3 本ある——電池の抜き道・蓋の横スライド・ハッチの爪。'
  'たるみは後ろの縦穴（27,865mm³）と右の溝（65,944mm³）へ逃がす。'
  '🆕 2026-08-27 に<b>手順 12（ハッチの姿勢）</b>も測った——<span class="w">TOGGLE</span> は上下を返して置けば <b>+14.3mm</b>、'
  'そのまま置くと <b>+45.1mm</b> で足りない。残る ⬜ はアンテナ線（同軸の実物が未取得）だけ',
  '✅ 測った'),
 ('⑤ 部品の実測',
  '<b>Type-C 基板（秋月 115426）が未注文</b>（2026-08-24 時点）。ハブの実装の最高点、DuPont を横に倒したときの膨らみ（3.6 は既定値）、PH2.0 がトップ型かサイド型かも未取得。'
  '🔴 INA226 は <b>2026-08-24 に着荷・実測済み</b>（穴 φ3.0・端から 16.6・シャント R010）。ここに「未着荷」と書いていたのは古い行の引き写しだった',
  '2026-08-25 に確認'),
]

PARTS = [
 ('床', 'p_floor / print_floor', '外面を下'),
 ('左の壁', 'p_lwall / print_lwall', '外面を下'),
 ('右の壁', 'p_rwall / print_rwall', '外面を下'),
 ('天面', 'p_top / print_top', '外面を下'),
 ('フロント', 'p_front / print_front', '外面を下'),
 ('ハッチ', 'p_hatch / print_hatch', '外面を下'),
 ('電池の蓋', 'p_shutter / print_shutter', '外面を下'),
 ('蓋のロック', 'p_lock / print_lock', '外面を下'),
 ('尻尾', 'p_tail / print_tail', 'ボアを上'),
 ('ブリッジ', 'print_bridge', '⬜ 向きが未決（いまは模型のまま。皿から後ろが宙に浮く）'),
 ('留め帯 A / B / C', 'print_strap_a / _b / _c', '足とツバを下（ツバの上面が 45° なので支え無し。天板が足の間 36mm を渡る）'),
 ('会話ボタンのキャップ', 'print_btn', '天面を伏せる'),
 ('つまみ一式', '<b>knob_v5.scad</b> が別に持つ（この表の外）', 'v5 の指定'),
]

CSS = """
:root {
  --paper:#e8ebef; --card:#ffffff; --sunk:#f3f5f7; --ink:#14171c; --ink2:#525b66;
  --rule:#ccd3db; --rule2:#dfe4ea; --accent:#8f5405; --mark:#c98a1e;
  --stop:#a62f28; --open:#20607f; --good:#2f6f4f; --sheet:#f7f8fa; --sheetdim:1;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --paper:#0f1216; --card:#181c22; --sunk:#13171c; --ink:#e3e8ee; --ink2:#98a2ae;
    --rule:#2a323c; --rule2:#222932; --accent:#f0aa33; --mark:#f0aa33;
    --stop:#e0776f; --open:#69b6d8; --good:#7fc3a0; --sheet:#e6e9ed; --sheetdim:.86;
  }
}
:root[data-theme="dark"] {
  --paper:#0f1216; --card:#181c22; --sunk:#13171c; --ink:#e3e8ee; --ink2:#98a2ae;
  --rule:#2a323c; --rule2:#222932; --accent:#f0aa33; --mark:#f0aa33;
  --stop:#e0776f; --open:#69b6d8; --good:#7fc3a0; --sheet:#e6e9ed; --sheetdim:.86;
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
.n { font-size:.9em; }
.w { font-size:.86em; font-weight:700; letter-spacing:.04em; }

header.mast { padding:28px 0 28px; border-bottom:2px solid var(--ink); }
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
td.ok  { color:var(--good); font-weight:700; }
td.stop { color:var(--stop); font-weight:700; }
td.warn { color:var(--mark); font-weight:700; }
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
  <p class="eyebrow">katanori &middot; enclosure v4</p>
  <h1>カタノリ v4<br><em>組み立て</em></h1>
  <p class="sub">印刷部品 14 点・ビス 27 本・線 13 束 39 本を、この順番で組む。
  順番は入れ替えられない。ナットを入れられる段と、皿と帯の下を通る線の車線と、留め帯が横からしか入らないことで決まっているため。</p>
  <div class="meta">
    <span><b>外寸</b> 86.65 &times; 75.0 &times; 52.95 mm</span>
    <span><b>内寸</b> 84.35 &times; 72 &times; 48.45 mm</span>
    <span><b>2026-08-26</b> 版</span>
    <span>形は <b>docs/CASE-V4.md</b>・判断待ちは <b>CASE-V4-OPEN.md</b></span>
    <span>まだ 1 度も組んでいない机上の手順</span>
  </div>
</header>

<nav class="jump"><span>手順</span>__NAV__</nav>

<div class="callout">
  <h2>始める前に</h2>
  <ul>
    <li><b>ハブの口 10 本は手順 3 で全部挿す。</b>手順 5 でブリッジの皿と帯が上に載ると、その下の口には届かなくなる。</li>
    <li><b>線には低い車線と上の車線がある。</b>低い方（<span class="n">Z 19</span>・5 束）はブリッジより先、上の方（5 束）はブリッジより後。逆にすると入らない。</li>
    <li><b>留め帯の 6 個のナットは横穴。</b>差したらどう向けても落ちない。他は全部上向きのポケットで、落としてから締めるまで箱を傾けない。</li>
    <li>🔴 <b>留め帯は電池より先。</b>帯は横から差すので、電池が先に入っていると差せない。上からも入らない。</li>
    <li><b>ドライバは先端 φ3.2 以下。</b>座ぐりが <span class="d">φ3.4</span> なので、それより太いと頭に届かない。ほかに<b>ピンセット</b>と、トグル用の<b>六角のスパナ</b>。</li>
    <li>この順番は CAD の軌跡検査から起こしたもので、<b>①〜⑫の原文をユーザーが書いたものではない</b>（<b>CASE-V4-OPEN.md</b> の A-1 がまだ空いている）。数字の裏取りは「検査」の節。</li>
  </ul>
</div>

<h2 class="sec">全体</h2>
<div class="two">
  <div>
    <figure class="wide"><img src="__EXP__" alt="分解図"></figure>
    <figcaption>組む向きにばらした図。床 → 壁 → ブリッジ → 留め帯 → 電池 → 基板 → 天面 → フロント → ハッチ の順に重なる。</figcaption>
  </div>
  <div>
    <figure class="wide"><img src="__LOOK__" alt="完成図"></figure>
    <figcaption>組み上がった姿。つまみは OLED から見て右（🔒 最上位の条件）。左の壁にイヤホンジャック、右の壁に XIAO の USB-C、ハッチに充電の Type-C。</figcaption>
  </div>
</div>
<figure class="wide" style="margin-top:22px"><img src="__WIRES__" alt="線の図"></figure>
<figcaption>皮を全部外して中だけ見たところ。線 13 束の通り道は 4 本 —— 左の溝（<span class="n">X 5.4〜13</span>）・右の溝（<span class="n">X 53〜80</span>）・後ろの縦穴（<span class="n">Y 62.9〜72</span>）・帯の上の棚（<span class="n">Z 31.4〜43</span>）。</figcaption>

<h2 class="sec">手順</h2>
__STEPS__

<h2 class="sec">検査（この順番の裏取り）</h2>
<p class="cal note"><span class="tag">読み</span>すべて <b>openscad --backend=manifold</b> の当たり体積。「相手」はその手順の<b>直前まで</b>に箱の中に在る物。
<b>0 が正</b>で、<span class="n">chk_press</span> だけは 4.7mm³ が正。「<b>9.8 → 0</b>」は、素で回すと出るが<b>まだ存在しない相手</b>を除くと 0 になる、という意味。走らせ方は <b>hardware/_asm_sim_v4.scad</b> の頭のコメント。</p>
<div class="tw"><table>
<thead><tr><th>何を動かすか</th><th>走らせ方</th><th>結果</th><th>読み</th></tr></thead>
<tbody>__CHECKROWS__</tbody>
</table></div>

<h2 class="sec">工具と手の道（2026-08-26 に初めて当てた）</h2>
<p class="cal warn"><span class="tag">経緯</span>ここまでの検査は<b>部品が通るかどうか</b>しか見ていなかった。
「順として物理的に成立することは検査済み」と書いていたが、<b>ドライバ・ナット・指を一度も当てていない</b>状態だった（ユーザー指摘）。
その手順のときに箱の中に在る物へ向けて、円筒を撃って真っ直ぐ何 mm 入るかを測り直した
（<b>hardware/_asm_access.py</b>・v3 の <span class="n">_asm_probe.py</span> の光線をそのまま使う）。
ドライバの先端は <span class="d">φ3.2</span>、M2 ナットは二面幅 <span class="d">4.3</span>、ピンセットは <span class="d">φ5</span>、指は <span class="d">φ12</span> で撃っている。
<b>この表はマニュアルを作り直すたびに測り直す</b>ので、古くならない。
🆕 2026-08-27 に<b>コネクタを挿す道</b>を足した（4 度目の机上の通し）。それまでは<b>ビスとナットと指</b>だけで、
「口に挿す」動きを一度も当てていなかった。口の座標は手で写さず、<b>hardware/_asm_plugs.scad</b> が口だけを STL に出し、その bbox から取る。
<b>挿し代</b>はピンの長さ <span class="d">6.0</span>（<span class="n">parts.scad</span> の足の出）を要る mm にしている。
🆕 2026-08-26 の <b>5 度目</b>に 2 つ足した。① <b>口を「持つ」道</b>——④ までは口を<b>口そのものの太さ</b>（φ3.6）でしか
撃っておらず、それを摘まむ道具では撃っていなかった（2026-08-26 に OLED の L のナットで同じ間違いをしている）。
手順 3 のハブの口 10 本と手順 9 の 9 か所を φ5 と φ12 で撃ち直して、19 行とも通った。
② <b>手順 1 の M3 まわり</b>——ハブの 4 本だけはビスの頭が丸いザグリで回り止めが無いので、
<b>ナットを回す工具の外径</b>ぶんの縦の道が要る。<b>後ろ左だけ φ7.19</b> で止まった（<b>CASE-V4-OPEN.md</b> T-6）。
<b>止まる（反例）</b>と書いた行は<b>止まるのが正</b>で、「その手順でしか挿せない」ことの裏取り。</p>
<div class="tw"><table>
<thead><tr><th>何を入れるか</th><th>手順</th><th>道具</th><th>φ</th><th>要る mm</th><th>通った mm</th><th>結果</th><th>備考</th></tr></thead>
<tbody>__ACCESS__</tbody>
</table></div>
<p class="cal ok"><span class="tag">結果</span>__ACCESSSUM__
2026-08-26 に当てた 3 か所が止まっていて、どれも同日に片付いた。
① <b>ブリッジの 3 本目</b>は、頭から真上 <span class="d">13.0mm</span> で天面の後ろ左の柱に当たっていた
→ 🔒 ユーザー「OLED 側から留めれば上には何もありません」で留め金ごと帯の前（<span class="n">X 4.194, Y 47.7</span>）へ移して解決。
② <b>OLED の右のナット</b>は、L の後ろの空きが <span class="d">1.3mm</span> しか無くナット（厚み <span class="d">1.6</span>）が入らなかった。
塞いでいたのは<b>スピーカーの右前の丸み</b>（初版は「天面のつまみの島」と書いたが取り違えで、島は <span class="n">Y 22.3</span> より奥にしか無い）。
→ 🔒 ユーザー「両方を +4 移動させてください」で<b>つまみとスピーカーを内側（−X）へ 4</b> 動かし、
そのぶん <b>電池・皿・脚・帯・座・両基板も丸ごと −4</b>、<b>電流計は水平＋電源の口を直立て</b>にして解決。
空きは <span class="d">1.3 → 15.7mm</span> になった（<b>CASE-V4-OPEN.md</b> の「済んだもの」）。
③ <b>OLED の左のナット</b>は、②を φ2.0 の円筒で撃っていたせいで見落としていた。<b>二面幅 4.3 で撃ち直すと 0.19mm で止まる</b>——L の裏 0.19 のところに会話ボタンの受け（前面 <span class="n">Y 6.8</span>・底 <span class="n">Z 47.1</span>）が立っていて、ナットの上の角（<span class="n">X 9.5〜12.15・Z 47.1〜48.25</span>）が中に入る。→ 受けの<b>手前左の角</b>（<span class="n">X 9.3〜12.4・Y 6.7〜10.0</span>・受けの厚みの全部）を欠いて <b>0.19 → 3.4mm</b>。タクトの胴は <span class="n">X 19〜25</span>、皿の縁は <span class="n">X 12.4</span> なので、どちらにも掛かっていない（絵は <b>hardware/_t3_blocker.png</b>）。</p>

<h2 class="sec">線</h2>
<div class="tw"><table>
<thead><tr><th>束</th><th>本数</th><th>模型の実長</th><th>通した道</th></tr></thead>
<tbody>__WIREROWS__</tbody>
</table></div>
<p class="cal note"><span class="tag">読み</span>「模型の実長」は <b>_v4_core.scad</b> の <span class="n">w_*()</span> の折れ線長（束の中で一番長い 1 本・mm）。
端子の手前で切ってあるので、<b>作る長さは実長 ＋ 65mm</b> を見る（端末処理 <span class="n">25</span> ＋ 手順 10 の置き場の増し <span class="n">40</span>）。🆕 2026-08-26 に増しを測った（<b>hardware/_asm_wirepose.py</b>）。手順 10 の置き方（奥へ返して左へ 25）で、<span class="w">AS5600</span> +39.5・<span class="w">REED</span> +38.3・<span class="w">PHOUT</span> +31.1・<span class="w">BTN2</span> +29.0。🔴 旧版の「＋40mm」は端末処理込みの数字で、置き場の増しを 15 と見ていた。<b>置き方を間違えると 3 倍要る</b>（左に倒すと REED が +120）。
✅ 2026-08-26 に測った。天面を<b>奥へ返して置く</b>姿勢での増しは 4 束とも +29〜+40mm（<b>hardware/_asm_wirepose.py</b>）。
🆕 2026-08-27 に <span class="w">TOGGLE</span> も測った。この束だけは<b>手順 12</b>（ハッチを箱から離したまま繋ぐ）で引かれる。ハッチを外の面を下に、
<b>上下を返して</b>箱の後ろへ置くと <b>+14.3mm</b>（一番短い置き方で +11.4）。<b>そのまま（レバーが奥）置くと +45.1mm で、+40 の増しに入らない。</b></p>

<h2 class="sec">ビスとナット</h2>
<div class="tw"><table>
<thead><tr><th>ビス</th><th>本数</th><th>どこ</th><th>手順</th></tr></thead>
<tbody>__SCREWROWS__</tbody>
</table></div>
<p class="cal note"><span class="tag">読み</span>樹脂にネジは切らない。全部<b>貫通＋ナット</b>（<b>docs/DIMENSIONS.md</b> の方針）。長さは <span class="d">M2×4</span>・<span class="d">M2×6</span>・<span class="d">M2×15</span>・<span class="d">M3×8</span> の 4 種類。ナットは <span class="d">M3</span> ×4・<span class="d">M2</span> ×23。</p>
<div class="tw" style="margin-top:18px"><table>
<thead><tr><th>ナット</th><th>数</th><th>どこ・向き</th><th>入れ方</th></tr></thead>
<tbody>__NUTROWS__</tbody>
</table></div>

<h2 class="sec">印刷部品</h2>
<div class="tw"><table>
<thead><tr><th>部品</th><th>part=</th><th>刷る向き</th></tr></thead>
<tbody>__PARTROWS__</tbody>
</table></div>
<p class="cal note"><span class="tag">読み</span><span class="n">print_*</span> は外面を下・底 <span class="n">Z0</span> に置いた姿勢で出る。
刷る前に <b>底の Z が 0 か</b>と<b>最薄肉が 0.42 を超えるか</b>を機械で見る（<b>docs/PRINT.md</b>）。</p>

<h2 class="sec">電池の交換（組んだ後）</h2>
<div class="tw"><table>
<thead><tr><th>順</th><th>すること</th></tr></thead>
<tbody>
<tr><td class="n">1</td><td>ハッチの外の <span class="d">M2</span> を 1 本外し、門形のロックを外す</td></tr>
<tr><td class="n">2</td><td>蓋を<b>右へ 5.5mm</b> ずらして、後ろへ抜く（磁石だけの保持で運用するなら工具は要らない）</td></tr>
<tr><td class="n">3</td><td>電池の JST を抜く</td></tr>
<tr><td class="n">4</td><td>電池を<b>後ろへ</b>引き出す（レールと留め帯は +Y にだけ開いた鞘）。留め帯は外さない——電池が抜けると帯の楔も外れるので、交換のあいだは帯を横へ動かさないこと</td></tr>
</tbody>
</table></div>
<p class="cal open"><span class="tag">未定</span>蓋の裏 ↔ 電池の尻の遊び <span class="d">8.35mm</span> の詰め物（v3 のスポンジの流儀）と、ロックを常時締める運用にするかは未決。</p>

<h2 class="sec">まだ埋まっていない</h2>
<div class="tw"><table>
<thead><tr><th>もの</th><th>何が足りないか</th><th>いつ</th></tr></thead>
<tbody>__BLANKROWS__</tbody>
</table></div>

<footer>
  作り直すには <b>python hardware/_asm_manual_v4.py</b>。段の中身と軌跡検査は <b>hardware/_asm_sim_v4.scad</b>、
  形と数字の出どころは <b>docs/CASE-V4.md</b>（判断待ちは <b>CASE-V4-OPEN.md</b>、経緯は <b>CASE-V4-LOG.md</b>）。線の長さは <b>_v4_core.scad</b> の <span class="n">w_*()</span> の点列から出した折れ線長。
</footer>
</div>
"""


ACCESS_STOPS = []


def access_rows():
    """工具・ナット・指の道を毎回測り直す（hardware/_asm_access.py）。数字は手で写さない。"""
    sys.path.insert(0, HERE)
    import _asm_access
    out = []
    ACCESS_STOPS.clear()
    for what, step, tool, dia, need, got, ok, note in _asm_access.run():
        cex = ok.startswith('止まる（反例）')   # 止まるのが正の行（その手順でしかできないことの裏取り）
        if not cex and ok != '通る': ACCESS_STOPS.append((what, step, got))
        cls = 'ok' if ok == '通る' or cex else 'stop'
        mark = ('<b>通る</b>' if ok == '通る' else
                '止まる（<b>反例</b>）' if cex else '<b>🔴 止まる</b>')
        out.append('<tr><td>{}</td><td class="n">{}</td><td>{}</td><td class="n">φ{}</td>'
                   '<td class="n">{}</td><td class="n {}">{}</td><td class="{}">{}</td><td>{}</td></tr>'
                   .format(what, step, tool, dia, need, cls, got, cls, mark, note))
    return chr(10).join(out)


def build():
    IM = {k: img('c_' + k + '.png') for k in SEQ + [w[0] for w in WIDE]}

    def step_html(s):
        fig = ('<figure class="sheet"><img src="{}" alt="手順 {} を終えた状態"></figure>'
               .format(IM[s['img']], s['n'])) if s.get('img') else ''
        bits = []
        if s.get('warn'):
            bits.append('<p class="cal warn"><span class="tag">注意</span>{}</p>'.format(s['warn']))
        if s.get('open_'):
            bits.append('<p class="cal open"><span class="tag">未定</span>{}</p>'.format(s['open_']))
        if s.get('note'):
            bits.append('<p class="cal note"><span class="tag">なぜ</span>{}</p>'.format(s['note']))
        return ('<section class="step" id="s{n}">\n'
                '  <div class="num"><span>{n}</span></div>\n'
                '  <div class="body">\n'
                '    <h3>{t}</h3>\n'
                '    {fig}\n'
                '    <ol class="acts">{acts}</ol>\n'
                '    {bits}\n'
                '  </div>\n'
                '</section>').format(
                    n=s['n'], t=s['t'], fig=fig,
                    acts='\n'.join('<li>{}</li>'.format(x) for x in s['acts']),
                    bits=''.join(bits))

    body = (BODY
            .replace('__NAV__', ' '.join('<a href="#s{0}">{0}</a>'.format(s['n']) for s in STEPS))
            .replace('__EXP__', IM['explode'])
            .replace('__LOOK__', IM['look'])
            .replace('__WIRES__', IM['wires'])
            .replace('__STEPS__', '\n'.join(step_html(s) for s in STEPS))
            .replace('__ACCESS__', access_rows())
            .replace('__ACCESSSUM__',
                     '<b>いまは全部通る（止まったもの 0）。</b>' if not ACCESS_STOPS else
                     '🔴 <b>いま %d か所で止まっている。</b>' % len(ACCESS_STOPS) +
                     '・'.join('%s（手順 %s・%s mm で止まる）' % r for r in ACCESS_STOPS) + '。')
            .replace('__CHECKROWS__', '\n'.join(
                '<tr><td>{}</td><td class="n">{}</td><td class="n {}">{}</td><td>{}</td></tr>'
                .format(r[0], r[1], r[3], r[2], r[4]) for r in CHECKS))
            .replace('__WIREROWS__', '\n'.join(
                '<tr><td class="w">{}</td><td class="n">{}</td><td class="n hi">{}</td>'
                '<td>{}</td></tr>'.format(*r) for r in WIRES))
            .replace('__SCREWROWS__', '\n'.join(
                '<tr><td class="d">{}</td><td class="n">{}</td><td>{}</td>'
                '<td class="n">{}</td></tr>'.format(*r) for r in SCREWS))
            .replace('__NUTROWS__', '\n'.join(
                '<tr><td class="d">{}</td><td class="n">{}</td><td>{}</td>'
                '<td>{}</td></tr>'.format(*r) for r in NUTS))
            .replace('__PARTROWS__', '\n'.join(
                '<tr><td><b>{}</b></td><td class="n">{}</td><td>{}</td></tr>'.format(*r) for r in PARTS))
            .replace('__BLANKROWS__', '\n'.join(
                '<tr><td><b>{}</b></td><td>{}</td><td class="n">{}</td></tr>'.format(*r) for r in BLANKS)))

    html = ('<title>カタノリ v4 組み立て</title>\n'
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
