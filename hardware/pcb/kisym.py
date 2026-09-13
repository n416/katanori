# -*- coding: utf-8 -*-
"""KiCad の標準の記号ライブラリ（.kicad_sym）を読んで、記号の本文とピンの位置を取り出す。

gen_sch.py が回路図を組むのに使う。KiCad 本体の記号をそのまま埋め込むので、形は描かない。
"""

import pathlib
import re

HERE = pathlib.Path(__file__).parent
SYMDIR = pathlib.Path(r"C:\Program Files\KiCad\10.0\share\kicad\symbols")


# ---- S 式 ----
_tok = re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))')


def parse(text):
    stack, cur = [], []
    pos = 0
    while True:
        m = _tok.match(text, pos)
        if not m or m.end() == pos:
            break
        pos = m.end()
        if m.group(1):
            stack.append(cur)
            cur = []
        elif m.group(2):
            done = cur
            cur = stack.pop()
            cur.append(done)
        elif m.group(3) is not None:
            cur.append(Str(m.group(3)[1:-1].replace('\\"', '"').replace('\\\\', '\\')))
        else:
            cur.append(m.group(4))
    return cur


class Str(str):
    """引用符つきの文字列（書き戻すときに引用符を付ける）。"""


def dump(x, ind=0):
    if isinstance(x, list):
        if not x:
            return "()"
        simple = all(not isinstance(e, list) for e in x)
        if simple:
            return "(" + " ".join(dump(e) for e in x) + ")"
        head = []
        rest = []
        for i, e in enumerate(x):
            if isinstance(e, list):
                rest = x[i:]
                break
            head.append(e)
        pad = "\t" * (ind + 1)
        return "(" + " ".join(dump(e) for e in head) + "\n" + \
            "\n".join(pad + dump(e, ind + 1) for e in rest) + "\n" + "\t" * ind + ")"
    if isinstance(x, Str):
        return '"' + x.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return str(x)


def find(node, key):
    return [e for e in node if isinstance(e, list) and e and e[0] == key]


def find1(node, key):
    r = find(node, key)
    return r[0] if r else None


# ---- 記号 ----
_libs = {}


def _lib(name):
    if name not in _libs:
        # KiCad の標準に無い記号は、このファイルの隣の katanori.kicad_sym に置く
        f = HERE / f"{name}.kicad_sym"
        if not f.exists():
            f = SYMDIR / f"{name}.kicad_sym"
        tree = parse(f.read_text(encoding="utf-8"))
        root = tree[0]
        _libs[name] = {e[1]: e for e in find(root, "symbol")}
    return _libs[name]


def symbol(lib_id):
    """'Lib:Name' → 回路図の lib_symbols に埋め込める形（extends を解決済み）。"""
    lib, name = lib_id.split(":")
    syms = _lib(lib)
    s = syms[name]
    ext = find1(s, "extends")
    if ext:
        base = [e for e in syms[ext[1]]]
        # 親の本体（子記号とピン）に、子のプロパティを上書きしたもの
        props = {p[1]: p for p in find(s, "property")}
        out = [base[0], Str(lib_id)]
        for e in base[2:]:
            if isinstance(e, list) and e[0] == "property" and e[1] in props:
                out.append(props.pop(e[1]))
            elif isinstance(e, list) and e[0] == "symbol":
                sub = list(e)
                sub[1] = Str(sub[1].replace(ext[1], name, 1))
                out.append(sub)
            else:
                out.append(e)
        out.extend(props.values())
        return out
    out = list(s)
    out[1] = Str(lib_id)
    return out


def pins(lib_id, unit=1, style=1):
    """ピン番号 → (名前, x, y, 向き[度], 種類)。座標は記号の中（Y 上向き）。"""
    s = symbol(lib_id)
    res = {}
    for sub in find(s, "symbol"):
        m = re.search(r"_(\d+)_(\d+)$", sub[1])
        u, st = int(m.group(1)), int(m.group(2))
        if u not in (0, unit) or st not in (0, style):
            continue
        for p in find(sub, "pin"):
            at = find1(p, "at")
            nm = find1(p, "name")[1]
            num = find1(p, "number")[1]
            res[str(num)] = (str(nm), float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0, p[1])
    return res


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    for lid in sys.argv[1:]:
        print("==", lid)
        for num, (nm, x, y, a, t) in sorted(pins(lid).items(), key=lambda kv: (len(kv[0]), kv[0])):
            print(f"  {num:>3} {nm:12s} {t:14s} ({x:7.2f},{y:7.2f}) {a:.0f}")
