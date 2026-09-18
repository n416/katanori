# -*- coding: utf-8 -*-
u"""検査の判定に押す刻印と、判定の置き場（hardware/check/）。

判定ファイルは git に入る証拠（基板の drc.json と同じ扱い）。だから「どの模型から出たか」を一緒に書く:
  src.sha     模型の元ファイル（hardware/ parts/ tools/ tools/manual_v61/ pcb/ の *.scad と pcb/v61_*3d.stl）の中身の sha256 の頭 12 桁
  src.newest  そのうちいちばん新しい更新時刻
  src.git     実行時の HEAD（短い）。作業ツリーが汚れていれば末尾に +
  ran         実行した時刻
読む側（tools/manual_v61/_asm_manual_v61.py）は今の模型の sha と比べ、違えば「古い」と表に出す。
マニュアルの HTML 自体にも同じ刻印を押す（1 行目の <!-- src … --> と見出しの下）。焼いた時の模型が辿れる。
値を隠さないのは、古い数字でも「前はこうだった」が読めるほうがよいから。無いのと古いのは区別する。

置き場
  hardware/check/<材料>/sweep/<key>.json   入れる道（tools/sweep_chk.py）
  hardware/check/<材料>/nutpath.json       ナット／ねじの口（tools/nutpath_chk.py）
  hardware/check/asm/<SW>.txt              組み立ての動き（tools/manual_v61/_asm_chk_v61.py）。SW の頭 r/n が材料
大きい中間物（OFF・STL・mp4・コマ）は今までどおり hardware/_tmp_*/ に置き、いつ消してもよい。
"""
import hashlib, os, re, subprocess, time

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # hardware/
CHECK = os.path.join(HW, "check")
SCAD_DIRS = ("", "parts", "tools", os.path.join("tools", "manual_v61"), "pcb")
# 🔴 2026-09-19: 基板の模型を入れていなかった。筐体は pcb/v61_parts.scad を include し、
#   pcb/v61_board3d.stl・pcb/v61_parts3d.stl を import する（case_v6_1.scad）。基板だけを直した日に
#   刻印も作り置きの判定も「変わっていない」と言い、掃引の検査と動画が 9/18 の基板の形のまま走った
MODEL_STL = (os.path.join("pcb", "v61_board3d.stl"), os.path.join("pcb", "v61_parts3d.stl"))
_SHA = None


def scad_files():
    u"""模型の元ファイル（*.scad と、筐体が import する基板の STL）"""
    out = []
    for d in SCAD_DIRS:
        p = os.path.join(HW, d)
        if os.path.isdir(p):
            out += [os.path.join(p, n) for n in sorted(os.listdir(p)) if n.endswith(".scad")]
    out += [os.path.join(HW, f) for f in MODEL_STL if os.path.exists(os.path.join(HW, f))]
    return out


def src_sha():
    u"""模型の元ファイル全部の中身の指紋。1 回計算したら覚える（マニュアルが行ごとに呼ぶ）"""
    global _SHA
    if _SHA is None:
        h = hashlib.sha256()
        for f in scad_files():
            h.update(os.path.relpath(f, HW).replace("\\", "/").encode("utf-8")); h.update(b"\0")
            h.update(open(f, "rb").read()); h.update(b"\0")
        _SHA = h.hexdigest()[:12]
    return _SHA


def src_newest():
    return max(os.path.getmtime(f) for f in scad_files())


def git_head():
    try:
        h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=HW, capture_output=True, text=True).stdout.strip()
        d = subprocess.run(["git", "status", "--porcelain", "--", "."], cwd=HW, capture_output=True, text=True).stdout.strip()
        return (h + ("+" if d else "")) or None
    except Exception:
        return None


def _t(sec):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(sec))


def stamp():
    u"""JSON に入れる刻印（"src" キーの値）"""
    return {"sha": src_sha(), "newest": _t(src_newest()), "git": git_head(), "ran": _t(time.time())}


def stamp_line(s=None, html=False):
    u"""txt の 1 行目に書く刻印（html=True なら HTML のコメント）"""
    s = s or stamp()
    body = "src sha=%s newest=%s git=%s ran=%s" % (s["sha"], s["newest"], s["git"], s["ran"])
    return "<!-- %s -->" % body if html else "# " + body


def parse_line(txt):
    m = re.search(r"(?:^# |<!-- )src sha=(\S+) newest=(\S+ \S+) git=(\S+) ran=(\S+ \S+)", txt, re.M)
    if not m:
        return None
    return {"sha": m.group(1), "newest": m.group(2), "git": m.group(3), "ran": m.group(4)}


def state(s):
    u"""刻印と今の模型を比べる。ok（同じ模型）／ old（模型が変わった）／ none（刻印が無い）"""
    if not s or not s.get("sha") or s["sha"] == "none":
        return "none"
    return "ok" if s["sha"] == src_sha() else "old"


def out_dir(*parts):
    p = os.path.join(CHECK, *parts)
    os.makedirs(p, exist_ok=True)
    return p
