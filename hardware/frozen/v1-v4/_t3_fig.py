# -*- coding: utf-8 -*-
# T-3（OLED の左のナットが入らない）の断面図を作る。
#   python hardware/_t3_fig.py
# _t3_blocker.scad を真横（−X）から正射影でレンダーし、その上に文字を書く。
# 文字の位置は模型の座標（Y, Z）で指定して、**緑のナットの実寸から画素の縮尺を割り出して**変換する。
# （viewall で撮るので画素の原点は毎回変わる。手で画素を書くと図を作り直すたびにずれる）
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.exe')
RAW = os.path.join(HERE, '_t3_raw.png')
OUT = os.path.join(HERE, '_t3_blocker.png')
FONT = r'C:\Windows\Fonts\meiryo.ttc'

INK = (20, 23, 28); DIM = (82, 91, 102); RED = (198, 32, 24); WHITE = (255, 255, 255)
NUT_Y0, NUT_Y1, NUT_Z0, NUT_Z1 = 4.8, 6.4, 44.1, 48.1   # 緑のナット（座った位置）の実寸


def render():
    subprocess.run([OPENSCAD, '--backend=manifold', '--render=full', '--projection=o',
                    '--autocenter', '--viewall', '--camera=0,0,0,90,0,270,0',
                    '--imgsize=1500,1000', '-o', RAW,
                    os.path.join(HERE, '_t3_blocker.scad')], check=True, capture_output=True)


def green_bbox(im):
    """緑（座ったナット）の画素の外接。ここから縮尺と原点を出す。
       レンダーの陰影は面が 1 つ（真横から見た切り口）なので、色は 1 種類に潰れる"""
    from collections import Counter
    cnt = Counter(im.convert('RGB').get_flattened_data() if hasattr(im, 'get_flattened_data')
                  else list(im.convert('RGB').getdata()))
    cand = [(n, c) for c, n in cnt.items() if n > 300 and c[1] - c[0] > 30 and c[1] - c[2] > 15]
    if not cand: raise SystemExit('緑が見つからない（_t3_blocker.scad の色を変えた?）')
    green = max(cand)[1]
    px = im.load(); w, h = im.size
    xs = [x for y in range(h) for x in range(w) if px[x, y][:3] == green]
    ys = [y for y in range(h) for x in range(w) if px[x, y][:3] == green]
    return min(xs), min(ys), max(xs), max(ys)


def main():
    if '--no-render' not in sys.argv: render()
    im = Image.open(RAW).convert('RGB')
    x0, y0, x1, y1 = green_bbox(im)
    sy = (y1 - y0) / (NUT_Z1 - NUT_Z0)          # 画素 / mm（縦・ナットの 4.0mm から）
    sx = (x1 - x0) / (NUT_Y1 - NUT_Y0)          # 同（横・1.6mm）
    s = sy                                       # 正射影なので縦横同じ。精度の高い縦を使う
    PX = lambda Y: x1 + (NUT_Y0 - Y) * s        # 画面の左が +Y（奥）
    PZ = lambda Z: y0 + (NUT_Z1 - Z) * s
    d = ImageDraw.Draw(im)
    f  = ImageFont.truetype(FONT, 24)
    fs = ImageFont.truetype(FONT, 20)
    fl = ImageFont.truetype(FONT, 22)
    ft = ImageFont.truetype(FONT, 33)

    d.text((46, 34), 'T-3　OLED の左のナットが入らない', font=ft, fill=INK)
    d.text((46, 80), '断面 X 10.0（左の L のビス穴）を真横から見たところ。画面の左が奥（ハッチ側）、右が手前（OLED 側）。',
           font=fs, fill=DIM)
    d.text((46, 106), '※ これは直す前の姿。2026-08-26 に受けの手前左の角（X 9.3〜12.4・Y 6.7〜10.0）を欠いて、空きは 0.19 → 3.4mm になった。',
           font=fs, fill=DIM)

    # 図の中に置く短い名前（白抜き）
    d.text((PX(13.4), PZ(49.7)), '天板', font=f, fill=WHITE, anchor='lm')
    d.text((PX(13.4), PZ(47.8)), '会話ボタンの受け', font=f, fill=WHITE, anchor='lm')

    # 当たりの指し（図の上の空きから真下へ）
    d.text((PX(8.6), PZ(51.5)), 'ナットの上の角が受けの中に入る', font=f, fill=RED, anchor='md')
    d.line([(PX(7.4), PZ(51.3)), (PX(7.4), PZ(47.9))], fill=RED, width=2)

    # 0.19mm の隙間（天板の中に白で書いて、隙間へ短く引く）
    d.text((PX(4.2), PZ(51.6)), 'L の裏と受けの間は 0.19mm', font=f, fill=(198, 24, 88), anchor='la')
    d.line([(PX(4.3), PZ(51.6) + 32), (PX(6.75), PZ(48.35))], fill=(216, 27, 96), width=2)

    # 縮尺
    bx, bz = PX(13.4), PZ(42.6)
    d.line([(bx, bz), (bx + 5 * s, bz)], fill=INK, width=3)
    for t in (0, 5 * s): d.line([(bx + t, bz - 7), (bx + t, bz + 7)], fill=INK, width=3)
    d.text((bx + 5 * s / 2, bz + 12), '5mm', font=fs, fill=INK, anchor='ma')

    # 凡例（図の下の空き）
    LEG = [((36, 86, 61),    'ナット（L のポケットに座った位置）'),
           ((174, 107, 36),  '会話ボタンの受け（前面 Y 6.8・底 Z 47.1）'),
           ((182, 141, 134), 'ナット（差し込む直前・L の裏から 0.01）'),
           ((144, 151, 159), '天板と L（OLED を留める板・厚み 2）'),
           ((179, 27, 20),   '受けの中に入ってしまう角 ＝ 入らない理由'),
           ((47, 67, 85),    'OLED')]
    for i, (col, txt) in enumerate(LEG):
        lx = 100 + (i % 2) * 700; ly = 826 + (i // 2) * 46
        d.rectangle([lx, ly, lx + 26, ly + 26], fill=col)
        d.text((lx + 40, ly + 13), txt, font=fl, fill=INK, anchor='lm')

    im.save(OUT)
    print(OUT, im.size, 'scale %.2f px/mm' % s)


if __name__ == '__main__':
    main()
