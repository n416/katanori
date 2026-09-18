# -*- coding: utf-8 -*-
"""自動配線（Freerouting）を回して、結果を板（.kicad_pcb）に入れる。

  python route.py            … DSN を渡して回し、SES を取り込む
  python route.py --ses      … 既にある SES を取り込むだけ
  python route.py --board katanori61_audio   … 音声の板（4 層）。穴の大きさは DSN から読む

配線と貫通穴は毎回すべて置き換える（前の配線が混ざると、どこまでが今回の結果か分からなくなる）。
"""

import math
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import kisym  # noqa: E402
from kisym import Str, find, find1  # noqa: E402
import dsn  # noqa: E402

NAME = sys.argv[sys.argv.index("--board") + 1] if "--board" in sys.argv else "katanori61"
OUT = HERE / NAME
# 自動配線の実行ファイルは v6 の所に展開したものを使う（git には入れない）
#   zip の解凍の仕方で 1 段深さが変わる（freerouting/freerouting/ でも freerouting/ の直下でもよい）
_FR_DIR = HERE.parents[0] / "frozen" / "v6" / "pcb" / "freerouting"
FR = next((p for p in (_FR_DIR / "freerouting" / "freerouting.exe", _FR_DIR / "freerouting.exe") if p.exists()),
          _FR_DIR / "freerouting" / "freerouting.exe")
from kicad_paths import CLI  # noqa: E402
_n = [0]


def uid():
    import uuid
    _n[0] += 1
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"katanori/route/{_n[0]}"))


# 🔴 **必ず gen_pcb.py を回してから回す。**route.py は生成済みの基板へ SES を混ぜるので、
#    配線が入った基板へ 2 回目を回すと結果が変わる（2026-09-13、未配線 1 本が出たり消えたり
#    して「自動配線は非決定的だ」と誤判定した。gen → route の順なら結果は毎回同じ）。
def run_freerouting():
    if not FR.exists():
        sys.exit(f"Freerouting が無い: {FR}")
    # 🔴 コマンドで渡した設定は Freerouting の共通の設定ファイル（%APPDATA%\freerouting\freerouting.json）に
    #    **保存されて次の回にも残る**（2026-09-15、統合基板で切った最適化が v6.1 にも効く状態になっていた）。
    #    ⇒ どちらの板でも、使う設定は毎回ぜんぶ明示する
    if NAME == "katanori61":
        # 🔴 2026-09-16: 最適化の段を切った。配線の段が **未接続 1 本**まで行ったのに、続く最適化の段が
        #    **未接続 6 本の別の版から始めて**それを SES に書き出した（配線 1 → 最適化 6 → 板の上で 5）。
        #    統合基板で 2026-09-15 に見たのと同じ Freerouting 2.4.1 の不具合。そのぶんパスを増やす。
        passes, extra = "80", ["--router.optimizer.enabled=false", "--router.automatic_neckdown=true"]
    else:
        # 統合基板:
        #  ・最適化の段を回さない。配線の段は「一番良い版（未接続 2 本）に戻す」と言いながら、続く最適化の段が
        #    未接続 9 本の別の版から始まり、その版が SES に書き出された（Freerouting 2.4.1）
        #  ・ネックダウン（細いピッチの手前で線を細くする）を切る。0.075 まで細くなり、後から太らせると隣に寄った
        #  ・パスは 15 まで。3・4 回目はどちらもパス 8〜11 で改善が止まり、残りは待つだけだった（ユーザー「遅すぎる」）
        passes = "15"
        extra = ["--router.optimizer.enabled=false", "--router.automatic_neckdown=true"]
    if "--incremental" in sys.argv:
        passes = "10"
    r = subprocess.run([str(FR), "-de", str(OUT / f"{NAME}.dsn"), "-do", str(OUT / f"{NAME}.ses"),
                        "-l", "en", "-mt", "1", "-mp", passes] + extra, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    for line in (r.stdout + r.stderr).splitlines():
        if "stage completed" in line or "stage interrupted" in line:
            print("  " + line.split("INFO")[-1].strip())
    if not (OUT / f"{NAME}.ses").exists():
        sys.exit("SES が出てこなかった:\n" + (r.stdout + r.stderr)[-2000:])


def seed_wiring():
    """--incremental: 今の板の配線と穴を DSN の wiring に入れて、未接続の分だけを自動配線に引かせる。

    2026-09-15、ユーザー「遅すぎる」。全部を最初から引き直すと 15〜30 分かかり、残りは数本だけだった。
    GND を縫うビア（stitch() が打つ φ0.6）は入れない（merge の後に打ち直す）。
    """
    pcb = kisym.parse((OUT / f"{NAME}.kicad_pcb").read_text(encoding="utf-8"))[0]
    names = {str(e[1]): str(e[2]) for e in find(pcb, "net")}
    txt = (OUT / f"{NAME}.dsn").read_text(encoding="utf-8")
    m = re.search(r"\(via (Via\[0-\d\]_\d+:\d+_um)\)", txt)
    vianame = m.group(1)
    rows = []
    for s in find(pcb, "segment"):
        a, b = find1(s, "start"), find1(s, "end")
        net = names.get(str(find1(s, "net")[1]), "")
        if not net or find1(s, "locked"):      # locked は gen_pcb.py が既に protect で渡している
            continue
        w = float(find1(s, "width")[1])
        rows.append(f'    (wire (path {find1(s, "layer")[1]} {round(w * dsn.SCALE)} '
                    f'{dsn._x(float(a[1]))} {dsn._y(float(a[2]))} {dsn._x(float(b[1]))} {dsn._y(float(b[2]))})'
                    f' (net "{net}") (type route))')
    nv = 0
    for v in find(pcb, "via"):
        # 🔴 縫いのビアと先に打ったビアは種にしない。**大きさで見分けない。**
        #    2026-09-16 夕: 「>= 0.59 なら縫い」が自動配線のビア（当時 φ0.8）まで落としていて未接続 40 本。
        #      ⇒ 「0.65 未満だけ落とす」に直した。
        #    2026-09-17 夜: 4 層にして自動配線のビアも φ0.6（gen_pcb.VIA4）になり、縫いと同じ大きさになった。
        #      0.65 未満 ＝ **全部**が落ち、「穴 0 個を DSN に入れた」と出て、浮いた穴が 6 個増えた。
        #    ⇒ stitch() が縫いのビアに (free yes) を付ける。locked（EP の放熱・幹の穴）は
        #      gen_pcb.py が protect で渡しているので、これも入れない（入れると二重になる）。
        if find1(v, "free") or find1(v, "locked"):
            continue
        at = find1(v, "at")
        net = names.get(str(find1(v, "net")[1]), "")
        rows.append(f'    (via {vianame} {dsn._x(float(at[1]))} {dsn._y(float(at[2]))} (net "{net}") (type route))')
        nv += 1
    # 🔴 2026-09-17 夜: 前は「空の wiring」("  (wiring\n  )") を置き換えていた。gen_pcb.py が
    #    先に引いた線を protect で wiring に書くようになってから空の形が無くなり、**黙って空振り**
    #    していた（種 0 本のまま全部を引き直し、前の穴と二重になって浮いた穴が出る）。
    #    ⇒ wiring の頭に差し込む。入らなければ止める。
    head = "  (wiring\n"
    if txt.count(head) != 1:
        sys.exit("DSN に wiring の節が 1 つだけ、という前提が崩れている（%d 個）" % txt.count(head))
    txt = txt.replace(head, head + "\n".join(rows) + "\n")
    (OUT / f"{NAME}.dsn").write_text(txt, encoding="utf-8")
    print(f"  引けている配線 {len(rows) - nv} 本・穴 {nv} 個を DSN に入れた（残りだけを引かせる）")


def merge():
    # 🔴 Freerouting は protect で渡した線を SES にそのまま返す。取り込むと、板に書いた手の線（locked）と
    #    二重になり、手の線を直した後は古い形が SES から戻ってくる。protect の物は捨てる
    #    （2026-09-16・統合基板が 2026-09-16 に同じ手当てをしている）
    ses = OUT / f"{NAME}.ses"
    txt = re.sub(r"\(wire\s*\(path[^()]*\)\s*\(type protect\)\s*\)", "", ses.read_text(encoding="utf-8"))
    txt = re.sub(r"\(via [^()]*\(type protect\)\s*\)", "", txt)
    ses.write_text(txt, encoding="utf-8")
    pcb = kisym.parse((OUT / f"{NAME}.kicad_pcb").read_text(encoding="utf-8"))[0]
    nets = {str(e[2]): e[1] for e in find(pcb, "net")}
    refs = {}
    for f in find(pcb, "footprint"):
        at = find1(f, "at")
        ref = [p for p in find(f, "property") if str(p[1]) == "Reference"]
        if ref:
            refs[str(ref[0][2])] = (float(at[1]), float(at[2]))
    wires, vias = dsn.read_ses(OUT / f"{NAME}.ses", refs)
    # 🔴 locked の線（gen_pcb.py の PRE_TRACKS で先に引いた物）は残す。ここで消すと、
    #    自動配線に protect で守らせた線が板から消えて、パッドが浮く（2026-09-16）
    # 🔴 2026-09-17 夜: --incremental のときは**板の上の配線と穴を残す**。Freerouting 2.4.1 は
    #    種で渡した線と穴（type route で渡しても）を SES に **type protect で返す**。上で protect を
    #    捨てているので、種はまるごと SES から消える ＝ 前のように全部を置き換えると、新しく引いた
    #    数本だけが残って未接続が 82 本出た。種は動かされない（protect 扱い）ので、板の物をそのまま使える。
    #    落とすのは縫いのビア（free）だけ。stitch() が後で打ち直す。
    if "--incremental" in sys.argv:
        body = [e for e in pcb if not (isinstance(e, list) and e[0] == "via" and find1(e, "free"))]
    else:
        body = [e for e in pcb if not (isinstance(e, list) and e[0] in ("segment", "via") and not find1(e, "locked"))]
    n_seg = 0
    for net, layer, w, pts in wires:
        if net not in nets:
            sys.exit(f"SES のネット '{net}' が基板に無い")
        for a, b in zip(pts, pts[1:]):
            # ⚠ 生の値ではなく**書き出す桁で**比べる。0.00001 違うだけの 2 点は 0.4f に丸めると
            #    同じ点になり、長さ 0 の配線が残って KiCad が「端が浮いている」と数える
            sa, sb = (f"{a[0]:.4f}", f"{a[1]:.4f}"), (f"{b[0]:.4f}", f"{b[1]:.4f}")
            if sa == sb:
                continue
            # 統合基板: Freerouting は細いピッチの手前で線を 0.15 の半分（0.075）まで細くする。
            #   JLCPCB の 4 層の下限 0.09 に揃える（2026-09-15・5 本。太らせた後の間隔は DRC が見る）
            ww = max(w, 0.09) if NAME != "katanori61" else w
            body.append(["segment", ["start", sa[0], sa[1]],
                         ["end", sb[0], sb[1]], ["width", f"{ww:.3f}"],
                         ["layer", Str(layer)], ["net", nets[net]], ["uuid", Str(uid())]])
            n_seg += 1
    # 穴の大きさは DSN に書いた物（v6.1 は Via[0-1]_800:400_um・統合基板は Via[0-3]_450:200_um）
    m = re.search(r"\(via Via\[0-\d\]_(\d+):(\d+)_um\)", (OUT / f"{NAME}.dsn").read_text(encoding="utf-8"))
    vsize, vdrill = (f"{int(m.group(1)) / 1000:g}", f"{int(m.group(2)) / 1000:g}") if m else ("0.8", "0.4")
    for net, x, y in vias:
        body.append(["via", ["at", f"{x:.4f}", f"{y:.4f}"], ["size", vsize], ["drill", vdrill],
                     ["layers", Str("F.Cu"), Str("B.Cu")], ["net", nets[net]], ["uuid", Str(uid())]])
    n_cut = prune_dangling(body, nets)
    (OUT / f"{NAME}.kicad_pcb").write_text(kisym.dump(body) + "\n", encoding="utf-8")
    print(f"  配線 {n_seg} 本・貫通穴 {len(vias)} 個を入れた（浮いた切れ端を {n_cut} 本落とした）")


def prune_dangling(body, nets):
    """どちらかの端が何にも触れていない配線を落とす（落として新たに浮く物も繰り返す）。

    自動配線は行き先の無い短い切れ端を残すことがある（KiCad の track_dangling）。
    端が「触れている」＝ 同じネットの 別の配線の端／貫通穴／パッド のどれかに乗っている。
    ⚠ locked（先に手で引いた線）は落とさない。片端がパッドの中で終わる作りだから。
    """
    num2net = {str(v): k for k, v in nets.items()}
    pads = {}          # ネット番号 → [(x0, y0, x1, y1), ...]
    for f in find(body, "footprint"):
        at = find1(f, "at")
        fx, fy = float(at[1]), float(at[2])
        fa = math.radians(-float(at[3])) if len(at) > 3 else 0.0
        for pad in find(f, "pad"):
            n = find1(pad, "net")
            if not n:
                continue
            pat, sz = find1(pad, "at"), find1(pad, "size")
            lx, ly = float(pat[1]), float(pat[2])
            x = fx + lx * math.cos(fa) - ly * math.sin(fa)
            y = fy + lx * math.sin(fa) + ly * math.cos(fa)
            w, h = float(sz[1]), float(sz[2])
            r = max(w, h) / 2 + 0.05
            pads.setdefault(str(n[1]), []).append((x - r, y - r, x + r, y + r))
    vias = {}
    for v in find(body, "via"):
        at = find1(v, "at")
        vias.setdefault(str(find1(v, "net")[1]), []).append((float(at[1]), float(at[2])))

    def on_pad_or_via(net, pt):
        for x0, y0, x1, y1 in pads.get(net, ()):
            if x0 <= pt[0] <= x1 and y0 <= pt[1] <= y1:
                return True
        return any(abs(vx - pt[0]) < 0.05 and abs(vy - pt[1]) < 0.05 for vx, vy in vias.get(net, ()))

    dropped = 0
    while True:
        segs = [e for e in body if isinstance(e, list) and e[0] == "segment"]
        ends = {}
        for e in segs:
            net = str(find1(e, "net")[1])
            for key in ("start", "end"):
                q = find1(e, key)
                ends.setdefault((net, round(float(q[1]), 3), round(float(q[2]), 3)), 0)
                ends[(net, round(float(q[1]), 3), round(float(q[2]), 3))] += 1
        kill = []
        for e in segs:
            if find1(e, "locked"):
                continue
            net = str(find1(e, "net")[1])
            for key in ("start", "end"):
                q = find1(e, key)
                pt = (float(q[1]), float(q[2]))
                k = (net, round(pt[0], 3), round(pt[1], 3))
                if ends.get(k, 0) < 2 and not on_pad_or_via(net, pt):
                    kill.append(e)
                    break
        if not kill:
            break
        for e in kill:
            body.remove(e)
        dropped += len(kill)
    return dropped


def stitch():
    """GND のベタを縫うビアを打つ（2026-09-13）。

    GND は自動配線に渡していない（gen_pcb.py の gnd_zone()）。表と裏に GND のベタを敷いているが、
    **表のベタは配線で島に割れる**ので、島ごとに裏のベタへ落とす穴が要る。
    空いている所を格子で探して、他のネットの銅から離れている点にだけ打つ。
    足りているかどうかは KiCad の DRC（unconnected_items）が言う。ここでは判定しない。
    """
    import check_pcb
    if NAME == "katanori61_audio":
        import gen_pcb_audio  # noqa: F401   # gen_pcb の板の寸法・穴・欠きを音声の板のものに差し替える
    import gen_pcb as G
    pcb = kisym.parse((OUT / f"{NAME}.kicad_pcb").read_text(encoding="utf-8"))[0]
    allobj = check_pcb.shapes(pcb)
    nets = {str(e[2]): e[1] for e in find(pcb, "net")}
    # 🔴 GND の銅からも 0.55 離す。GND なら電気的には触れてよいが、**穴どうしの間隔**は
    #    ネットに関係なく要る（JLCPCB の規則・DRC の hole_to_hole が 4 件出た）
    VIA, DRILL, CLR, PITCH = 0.6, 0.3, 0.55, 3.2
    put = []
    for i in range(int((G.BOARD_L - 2) / PITCH) + 1):
        for j in range(int((G.BOARD_W - 2) / PITCH) + 1):
            u, v = 1.0 + i * PITCH, 1.0 + j * PITCH
            if any(nx0 - 1 < u < nx1 + 1 and v > ny - 1 for nx0, nx1, ny in G.NOTCHES):
                continue
            if any((u - mx) ** 2 + (v - my) ** 2 < (G.MOUNT_D / 2 + G.MOUNT_KEEP + VIA / 2) ** 2
                   for mx, my in G.MOUNT):
                continue
            if any((u - px) ** 2 + (v - py) ** 2 < (d / 2 + G.POST_KEEP + VIA / 2) ** 2
                   for px, py, d in G.POSTS):
                continue
            # 2026-09-18: 角を丸めた外形から 0.5 以上内側だけ（JLCPCB の銅→外形は 0.2 以上・推奨 0.3〜0.5）。
            #   格子の端の 1.0 は直線の縁なら足りるが、丸めた隅では外形の外へ出る
            if G.edge_gap(u, v) < 0.5 + VIA / 2:
                continue
            X, Y = G.bx(u, v)
            me = ("circle", X, Y, VIA / 2)
            if all(check_pcb.gap(me, g) > CLR for _, _, g in allobj):
                put.append((X, Y))
    body = list(pcb)
    for X, Y in put:
        body.append(["via", ["at", f"{X:.4f}", f"{Y:.4f}"], ["size", f"{VIA}"],
                     ["drill", f"{DRILL}"], ["layers", Str("F.Cu"), Str("B.Cu")],
                     ["free", "yes"],      # 縫いのビアの印。seed_wiring() がこれで見分ける
                     ["net", nets["GND"]], ["uuid", Str(uid())]])
    (OUT / f"{NAME}.kicad_pcb").write_text(kisym.dump(body) + chr(10), encoding="utf-8")
    print(f"  GND を縫うビアを {len(put)} 個打った（格子 {PITCH}mm・φ{VIA}/{DRILL}）")


def drc():
    rpt = OUT / "drc.json"
    # 🔴 --refill-zones を付けないと、裏の GND のベタが埋まっていない状態で検査される
    #    （2026-09-13・GND を自動配線から外してベタに任せたら、45 パッドが未接続で出た）。
    #    ⚠ --save-board は付けない。KiCad に板を書き直させると、次の merge() が読めなくなる
    subprocess.run([CLI, "pcb", "drc", "--format", "json", "--severity-all",
                    "--refill-zones", "-o", str(rpt),
                    str(OUT / f"{NAME}.kicad_pcb")], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")   # ⚠ 既定は cp932 で、日本語の行で落ちる
    import collections
    import json
    d = json.loads(rpt.read_text(encoding="utf-8"))
    cnt = collections.Counter()
    for key in ("violations", "unconnected_items", "schematic_parity"):
        for v in d.get(key, []):
            cnt[(key, v["type"], v["severity"])] += 1
    for (key, typ, sev), n in sorted(cnt.items(), key=lambda kv: -kv[1]):
        print(f"  {key:20s} {typ:28s} {sev:8s} {n}")
    if not cnt:
        print("  DRC: 指摘なし")
    return d


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if "--incremental" in sys.argv:
        seed_wiring()
    if "--ses" not in sys.argv:
        run_freerouting()
    merge()
    stitch()
    drc()
