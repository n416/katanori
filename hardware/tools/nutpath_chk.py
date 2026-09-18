# -*- coding: utf-8 -*-
u"""ナット／ねじの口の検査。口から外へ道を掃き、**その口を使う場面の世界**と交わりを取る。0 が正。

  python hardware/tools/nutpath_chk.py --mat resin          # 全部の口
  python hardware/tools/nutpath_chk.py --mat nylon pt0 fs   # 口を選ぶ
  python hardware/tools/nutpath_chk.py --mat resin --all    # 使う場面以外も全部の場面に当てる（どこで空くかを探す）
  python hardware/tools/nutpath_chk.py --mat resin --dd 3.8 # ドライバー／頭の柱の径を変える（既定は座ぐり φ4.4）

口の表・場面・世界は tools/_nutpath_v61.scad（箱と先に入っている物は case_v6_1.scad の world_for_*）。
判定: 口ごとに「使う場面」のどれか 1 つで空いていれば正。塞がっている口は、部品 1 つずつに当て直して
      誰が・口の面から何 mm の所で・断面の何 % を塞いでいるかを出す。
了承済みの当たりは hardware/nutpath_accept.json（mat・口・場面・体積の上限・理由）。新しい当たりがあれば終了コード 1。

測り方の約束（2026-09-18 に何度も間違えた所）
  - bbox を形として使わない。ここでは一切使っていない（距離は道の向きへの射影で出す）
  - OpenSCAD は中身が空だと STL を書かない。空かどうかは**ログの `top level object is empty`** で判定する
  - ERROR は stdout/stderr と -o x.echo の両方を見る
  - 部品ファイル（btn_v61 / knob_v61）の数は、部品を単体で開いて echo させて -D で渡す（写しを持たない）
"""
import json, math, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np, trimesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_stamp import stamp, out_dir                                            # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # hardware/
SCAD = os.path.join(ROOT, "tools", "_nutpath_v61.scad")
OPENSCAD = os.environ.get("OPENSCAD", r"C:\Program Files\OpenSCAD (Nightly)\openscad.exe")
ACCEPT_F = os.path.join(ROOT, "nutpath_accept.json")
VOL_MIN = 0.05      # これ未満の交わりは数えない。同一平面の皮と、$fn の違う円どうしの角の食い違い（dspk で 0.03 出る）。φ4.4 の断面 15mm² に対して厚み 0.003mm
SCENES_ALL = {"resin": ["deskWL", "deskWR", "deskH", "desk0", "desk1", "desk2", "bat", "hub", "s3", "rsp", "oled",
                        "lwall", "rwall", "top", "front", "hatch", "done"],
              "nylon": ["desk0", "desk1", "desk2", "hub", "rsp", "oled", "bat", "lid", "done"]}
MAT, TMP, DD = "nylon", "", None


def run(args, out, src=SCAD, mat_var="MAT"):
    cmd = [OPENSCAD, "--backend=manifold"] + ([] if out.endswith(".echo") else ["--export-format", "binstl"]) \
        + ["-o", out, "-D", 'part="__none__"', "-D", '%s="%s"' % (mat_var, MAT)] + args + [src]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    txt = r.stdout + r.stderr
    if out.endswith(".echo") and os.path.exists(out):
        txt += open(out, encoding="utf-8", errors="replace").read()
    if "ERROR" in txt:
        sys.exit("OpenSCAD ERROR (%s):\n%s" % (" ".join(args), "\n".join(l for l in txt.splitlines() if "ERROR" in l)[:2000]))
    return txt


def part_consts():
    u"""部品ファイルを単体で開いて、口の位置に要る数を echo させる（use した部品の変数は case から見えない）"""
    out = {}
    for key, part, expr in [
        ("NP_BTN", "btn_v61", "[B3_BLK_DY[0], B3_NUT_Z0, B3_NUT_T, B3_NUT_AF + B3_SHRINK, B3_SCR_X, B3_SW_DX, B3_Z_SCR, B3_SEAT_H, b3_ear_foot_z0(0)]"),
        ("NP_KNB", "knob_v61", "[SCREW_ANG, SCREW_R, Z_BOSS_BOT, NUT_POCK_AF, Z_WALL_T - SCR_CB_T]")]:
        f = os.path.join(TMP, "_c_%s.scad" % part)
        open(f, "w", encoding="utf-8").write("include <%s>\necho(NPC = %s);\n"
                                             % (os.path.join(ROOT, "parts", part + ".scad").replace("\\", "/"), expr))
        ec = os.path.join(TMP, "_c_%s.echo" % part)
        txt = run([], ec, src=f, mat_var="$mat")            # 部品の単体は $mat で材料を受ける（parts/mat.scad）
        m = re.search(r"NPC = (\[.*\])", txt)
        if not m:
            sys.exit("%s の数が読めない" % part)
        out[key] = m.group(1)
    return out


def load(f):
    g = trimesh.load(f, process=True)
    return g if len(g.faces) else None


def volume(g):
    v = 0.0
    for c in g.split(only_watertight=False) or [g]:
        if c.is_watertight and math.isfinite(c.volume):
            v += abs(c.volume)
    return v


def main():
    global MAT, TMP, DD
    args, every = sys.argv[1:], False
    i = 0
    ids = []
    while i < len(args):
        a = args[i]
        if a == "--mat": MAT = args[i + 1]; i += 2
        elif a.startswith("--mat="): MAT = a.split("=", 1)[1]; i += 1
        elif a == "--dd": DD = float(args[i + 1]); i += 2
        elif a == "--all": every = True; i += 1
        else: ids.append(a); i += 1
    if MAT not in ("resin", "nylon"):
        sys.exit("--mat は resin か nylon")
    TMP = os.path.join(ROOT, "_tmp_nutpath", MAT)
    os.makedirs(TMP, exist_ok=True)
    t0 = time.time()
    base = []
    for k, v in part_consts().items():
        base += ["-D", "%s=%s" % (k, v)]
    if DD is not None:
        base += ["-D", "NP_DD=%s" % DD]

    txt = run(base + ["-D", 'NP_MODE="list"'], os.path.join(TMP, "list.echo"))
    probes = {p[0]: {"kind": p[1], "org": p[2], "dir": p[3], "len": p[4], "when": p[5], "what": p[6]}
              for p in json.loads(re.search(r"NPLIST = (\[.*\])", txt).group(1))}
    toks = json.loads(re.search(r"NPTOKS = (\[.*\])", txt).group(1))
    taps = json.loads(re.search(r"NPTAP = (\[.*\])", txt).group(1))
    if ids:
        bad = [k for k in ids if k not in probes]
        if bad:
            sys.exit("そんな口は無い: %s（あるのは %s）" % (bad, " ".join(probes)))
        probes = {k: probes[k] for k in ids}
    accept = [a for a in (json.load(open(ACCEPT_F, encoding="utf-8")).get("accept", []) if os.path.exists(ACCEPT_F) else [])
              if a.get("mat") == MAT]

    def probe_area(k):
        f = os.path.join(TMP, "probe_%s.stl" % k)
        if os.path.exists(f): os.remove(f)
        log = run(base + ["-D", 'NP_MODE="probe"', "-D", 'NP_ID="%s"' % k], f)
        if "top level object is empty" in log or not os.path.exists(f):
            sys.exit("口 %s の道が空（口の表が壊れている）" % k)
        return k, volume(load(f))

    def hit(k, s, tok=""):
        f = os.path.join(TMP, "hit_%s__%s%s.stl" % (k, s, "__" + tok.replace(":", "_") if tok else ""))
        if os.path.exists(f): os.remove(f)
        log = run(base + ["-D", 'NP_MODE="hit"', "-D", 'NP_ID="%s"' % k, "-D", 'NP_SCENE="%s"' % s, "-D", 'NP_TOK="%s"' % tok], f)
        if "top level object is empty" in log or not os.path.exists(f):
            return None
        g = load(f)
        if g is None:
            return None
        vol = volume(g)
        if vol < VOL_MIN:
            return None
        r = {"vol": round(vol, 3), "stl": os.path.basename(f)}
        p = probes[k]
        if p["org"]:                                           # 口の面から最初に当たる所まで（道の向きへの射影）
            sv = (np.asarray(g.vertices, float) - np.array(p["org"], float)) @ np.array(p["dir"], float)
            span = max(float(sv.max() - sv.min()), 1e-9)
            r.update(d0=round(float(sv.min()), 3), d1=round(float(sv.max()), 3),
                     frac=round(vol / (pvol[k] / p["len"] * span), 3))      # その区間で断面の何割を塞ぐか
        return r

    with ThreadPoolExecutor(4) as ex:
        pvol = dict(ex.map(probe_area, probes))
        jobs = [(k, s) for k, p in probes.items() for s in (SCENES_ALL[MAT] if every else p["when"])]
        res = dict(zip(jobs, ex.map(lambda j: hit(*j), jobs)))
        # 塞がっている（使う場面に空きが 1 つも無い）口だけ、誰が塞いでいるかを部品ごとに当て直す
        blocked = [k for k, p in probes.items() if all(res[(k, s)] for s in p["when"])]
        bj = [(k, s, t) for k in blocked for s in probes[k]["when"] for t in toks]
        who = dict(zip(bj, ex.map(lambda j: hit(*j), bj)))

    print(u"材料 %s ／ 口 %d ／ 頭と工具の柱 φ%s ／ %.0f 秒（判定は hardware/check/%s/nutpath.json・当たりの形は hardware/_tmp_nutpath/%s/）"
          % (MAT, len(probes), DD if DD is not None else "座ぐり", time.time() - t0, MAT, MAT))
    news, rep = [], {}
    for k, p in probes.items():
        free = [s for s in p["when"] if not res[(k, s)]]
        rep[k] = {"what": p["what"], "kind": p["kind"], "when": p["when"], "free": free,
                  "scenes": {s: res[(k, s)] for (kk, s) in res if kk == k}}
        if free:
            print(u"  空  %-7s %s ── %s で空いている" % (k, p["what"], "・".join(free)))
            continue
        for s in p["when"]:
            r = res[(k, s)]
            acc = next((a for a in accept if a["id"] == k and a["scene"] == s and r["vol"] <= a["vol"] + 1e-6), None)
            d = "" if "d0" not in r else u"・口から %.2f〜%.2fmm・断面の %.0f%%" % (r["d0"], r["d1"], r["frac"] * 100)
            print(u"  %s  %-7s %s ── 場面 %s で %.2fmm³%s%s" % (u"済" if acc else u"塞", k, p["what"], s, r["vol"], d,
                                                              u"  （了承: %s）" % acc["why"] if acc else ""))
            for t in toks:
                w = who.get((k, s, t))
                if w:
                    dd = "" if "d0" not in w else u" 口から %.2fmm・%.0f%%" % (w["d0"], w["frac"] * 100)
                    print(u"        %-9s %.2fmm³%s" % (t, w["vol"], dd))
                    rep[k].setdefault("who", {}).setdefault(s, {})[t] = w
            if not acc:
                news.append((k, s, r))
    for k in taps:
        print(u"  ⚠   %-7s ナットの口が無い（タッピング TAP_D）。🔒「留めは必ずナット」に反する" % k)
    if every:
        print(u"\n全部の場面（mm³・空きは ─）")
        print("  %-7s " % "" + " ".join("%7s" % s for s in SCENES_ALL[MAT]))
        for k in probes:
            print("  %-7s " % k + " ".join("%7s" % (u"─" if not res[(k, s)] else "%.2f" % res[(k, s)]["vol"]) for s in SCENES_ALL[MAT]))
    json.dump({"mat": MAT, "dd": DD, "src": stamp(), "probes": rep, "tap": taps},         # src: どの模型から出た判定か
              open(os.path.join(out_dir(MAT), "nutpath.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(u"\n==== [%s] 塞がっている口 %d 件（新）／ 了承済みの台帳 %d 件 ／ タッピング %d 件"
          % (MAT, len(news), len(accept), len(taps)))
    if news:
        print(u"見て「これでよい」と判じたら、理由を書いて hardware/nutpath_accept.json の accept に足す:")
        for k, s, r in news:
            print("  " + json.dumps({"id": k, "scene": s, "mat": MAT, "vol": round(r["vol"] + 0.05, 2),
                                     "why": u"（なぜ了承するかを書く）", "since": time.strftime("%Y-%m-%d")}, ensure_ascii=False))
    raise SystemExit(1 if news or taps else 0)


if __name__ == "__main__":
    main()
