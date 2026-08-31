# -*- coding: utf-8 -*-
"""刷るぞー ── ローカルサーバー。

  起動: python surugo/server.py           （既定 http://127.0.0.1:8731）

🔒 **API が本体で、画面はその客の 1 つ。**AI も同じ口を curl で叩く。
   UI の中にロジックを書くと、API を足したときに実装が二重になる。

  GET  /api/state              いまの番手・レジン・フィルムの摩耗・結果待ちの一覧
  GET  /api/stls               刷れる STL の一覧
  POST /api/measure  {paths}   接地面積・背・層数・島・持たれていない天井
  POST /api/arrange  {paths}   プレート 143x89 に並べる。当たりと注意を返す
  POST /api/export   {id,placements,out}  **結合した 1 つの STL** を書く
  POST /api/event    {ev,by}   ログに 1 件足す（by="ai" は term しか書けない）

⚠ by の判定は**規律のための柵**であって錠前ではない。自分で "human" と名乗れば通る。
  通してはいけないのは、通せないからではなく、通すと記録が死ぬからである。
"""
import json, os, sys, glob, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import measure as M     # noqa: E402
import store as S       # noqa: E402

import numpy as np      # noqa: E402

# 🔒 Mars 3 のプレート（PRINT.md §4）
PLATE_X, PLATE_Y = 143.0, 89.0
MARGIN = 3.0            # 縁から空ける
GAP = 3.0               # 部品どうしの間隔
# 🔴 実測: 45mm 離れた大きい板が、小さい板の厚みを +0.9 変えた（PRINT.md 冒頭）
INFLUENCE = 45.0
BIG_GRIP = 2000.0       # 「大きい板」とみなす接地面積

# 🔴 人が宣言する規則はここ 1 つ。**AI が幾何から推論して増やさない。**
#   一度それをやって、直置きで刷れている v4_shutter / v4_seat / v4_hatch を弾いた。
RULES = os.path.join(_HERE, "rules.json")


def rules():
    try:
        with open(RULES, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def lifted_names():
    return set(rules().get("lifted", []))


LCD_MM2 = 143.43 * 89.6      # Mars 3 の LCD = 12,851mm²


def alone_grip():
    """🔒 断面がこれ以上の部品は単独で刷る（他を一緒に置かない）。
       既定 3855mm² ＝ LCD の 30%。出典の原文:
       "if you print on support and you don't have any large cross-sections
        (let's say more than 30 % of the LCD surface) you should be fine"
       ⇒ 見るのは**接地ではなく断面**。しかも**その層に載っている合計**である
       （たわむ原因は剥離力で、力はプレート全体に効く）。"""
    return float(rules().get("alone_grip_mm2", 3855))


def pct(mm2):
    return 100.0 * mm2 / LCD_MM2


# ---------------- 並べる ----------------

# ⬜ Z まわりの 90° 回転を使う。**層の画像が回るだけで、断面も露光も変わらない**ので
#    造形そのものには影響しないはず。⚠ ただし剥離の向きが部品に対して変わる。
#    PRINT.md に向きの規則は書かれていない（＝未検証）。切りたければここを False に。
ALLOW_ROT = True


def _cands(p):
    w = p["bbox"][3] - p["bbox"][0]
    h = p["bbox"][4] - p["bbox"][1]
    c = [(w, h, 0)]
    if ALLOW_ROT and abs(w - h) > 1e-6:
        c.append((h, w, 90))
    return c


def arrange(parts):
    """棚に詰める。棚は使い回し、入らなければ 90° 回してもう一度試す。
       原点はプレート中央（CHITUBOX が bbox の中心をそこへ置くため）。"""
    # 🔒 大きい部品は単独で刷る。同居させると、離れていても隣の寸法が狂う
    #   （PRINT.md 冒頭・45mm 先の小さい板の厚みが +0.9 変わった実測）
    big = [p for p in parts if p.get("profile_max", p["grip"]) >= alone_grip()]
    if big and len(parts) > 1:
        return {"placements": [], "time": None, "used": None, "warn": [],
                "stop": "%s は断面 %.0fmm²（LCD の %.0f%%）で、単独で刷る決まりになっている"
                        "（rules.json の alone_grip_mm2 = %.0f ＝ LCD の 30%%）。"
                        "土台がたわむので、同じプレートに他を置くと離れていても"
                        "引きずられて寸法が狂う。⇒ この部品だけを選び直してください。"
                        % ("・".join(p["name"] for p in big),
                           max(p.get("profile_max", p["grip"]) for p in big),
                           pct(max(p.get("profile_max", p["grip"]) for p in big)),
                           alone_grip())}
    # 🔒 1 個ずつ線の下でも、同じ層に重なれば合計で超える（出典の "any large cross-sections"）
    tot, lay = _peak_layer(parts)
    if tot >= alone_grip() and len(parts) > 1:
        return {"placements": [], "time": None, "used": None, "warn": [],
                "stop": "この組み合わせは %d 層目（Z %.2fmm）で断面の合計が %.0fmm²"
                        "（LCD の %.0f%%）になる。1 個ずつは線の下でも、"
                        "同じ層に重なると土台がたわむ。⇒ 減らすか、分けて刷ってください。"
                        % (lay, lay * M.DZ, tot, pct(tot))}
    W = PLATE_X - 2 * MARGIN
    H = PLATE_Y - 2 * MARGIN
    # 大きい物から。長辺で並べる
    items = sorted(parts, key=lambda p: -max(p["bbox"][3] - p["bbox"][0],
                                             p["bbox"][4] - p["bbox"][1]))
    shelves = []          # [{"y":, "h":, "x":}]
    placed, over = [], []

    for p in items:
        cands = [c for c in _cands(p) if c[0] <= W and c[1] <= H]
        if not cands:
            w = p["bbox"][3] - p["bbox"][0]; h = p["bbox"][4] - p["bbox"][1]
            over.append("%s は %.1f x %.1f でプレート（%.0f x %.0f）に載らない"
                        % (p["name"], w, h, W, H))
            continue
        spot = None
        # ① 既にある棚に入るか（棚を伸ばさずに済む向きを優先）
        for sh in shelves:
            for w, h, rot in cands:
                if sh["x"] + w <= W and h <= sh["h"]:
                    spot = (sh, w, h, rot); break
            if spot: break
        # ② 棚を高くすれば入るか
        if spot is None:
            for sh in shelves:
                for w, h, rot in cands:
                    grow = max(0.0, h - sh["h"])
                    if sh["x"] + w <= W and sh["y"] + h <= H and _room(shelves, sh, grow, H):
                        spot = (sh, w, h, rot); break
                if spot: break
        # ③ 新しい棚
        if spot is None:
            y = (shelves[-1]["y"] + shelves[-1]["h"] + GAP) if shelves else 0.0
            for w, h, rot in cands:
                if y + h <= H:
                    sh = {"y": y, "h": h, "x": 0.0}
                    shelves.append(sh); spot = (sh, w, h, rot); break
        if spot is None:
            over.append("%s が載りきらない（この 1 回には収まらない）" % p["name"])
            continue

        sh, w, h, rot = spot
        placed.append({"path": p["path"], "name": p["name"], "w": w, "h": h,
                       "rot": rot, "x": sh["x"], "y": sh["y"], "grip": p["grip"],
                       "layers": p["layers"], "height": p["height"]})
        sh["x"] += w + GAP
        sh["h"] = max(sh["h"], h)

    if placed:
        lox = min(q["x"] for q in placed); hix = max(q["x"] + q["w"] for q in placed)
        loy = min(q["y"] for q in placed); hiy = max(q["y"] + q["h"] for q in placed)
        cx, cy = (lox + hix) / 2, (loy + hiy) / 2
        for q in placed:
            q["cx"] = round(q["x"] + q["w"] / 2 - cx, 3)
            q["cy"] = round(q["y"] + q["h"] / 2 - cy, 3)

    return {"placements": placed, "warn": _arrange_warn(placed) + over,
            "time": _time(placed), "used": _used(placed, W, H)}


def _peak_layer(parts):
    """層ごとに断面積を足し合わせ、一番大きい層とその値を返す。
       部品は全部 Z=0 に接地しているので、層の番号はそのまま揃う。"""
    n = max((len(p.get("profile") or []) for p in parts), default=0)
    if n == 0:
        return (sum(p["grip"] for p in parts), 0)
    tot = [0.0] * n
    for p in parts:
        for i, a in enumerate(p.get("profile") or []):
            tot[i] += a
    lay = max(range(n), key=lambda i: tot[i])
    return (tot[lay], lay)


def _room(shelves, target, grow, H):
    """target の棚を grow だけ高くしても、上の棚が押し出されないか"""
    if grow <= 0:
        return True
    seen = False
    for sh in shelves:
        if sh is target:
            seen = True; continue
        if seen and sh["y"] + sh["h"] + grow > H:
            return False
    return True


def _used(placed, W, H):
    if not placed:
        return None
    area = sum(q["w"] * q["h"] for q in placed)
    return {"parts": len(placed), "fill_pct": round(100 * area / (W * H), 1)}


def _arrange_warn(placed):
    w = []

    for a in placed:
        for b in placed:
            if a is b or a["grip"] < BIG_GRIP:
                continue
            d = ((a["cx"] - b["cx"]) ** 2 + (a["cy"] - b["cy"]) ** 2) ** 0.5
            if d < INFLUENCE:
                w.append("⚠ %s（接地 %.0fmm²）と %s が %.0fmm ── 実測では 45mm 離れた"
                         "大きい板が小さい板の厚みを +0.9 変えている"
                         % (a["name"], a["grip"], b["name"], d))
    return sorted(set(w))


def _time(placed):
    """🔒 印刷時間は一番背の高い部品だけが決める（PRINT.md §2.5）。"""
    if not placed:
        return None
    tall = max(placed, key=lambda q: q["layers"])
    return {"layers": tall["layers"], "by": tall["name"],
            "min_sec": tall["layers"] * 2.5,
            "note": "露光だけの下限。実測は CHITUBOX の見積り x 1.3"}


# ---------------- 結合して書き出す ----------------

def export(placements, out):
    """🔒 1 つの STL に結合する。別ファイルでは CHITUBOX が座標を捨てる（PRINT.md §3）。"""
    chunks = []
    for q in placements:
        t = M.load_tris(os.path.join(_ROOT, q["path"])).copy()
        if q.get("rot") == 90:
            x = t[:, :, 0].copy()
            t[:, :, 0] = -t[:, :, 1]     # (x, y) -> (-y, x)。Z は触らない
            t[:, :, 1] = x
        lo = t.reshape(-1, 3).min(axis=0)
        hi = t.reshape(-1, 3).max(axis=0)
        t[:, :, 0] += q["cx"] - (lo[0] + hi[0]) / 2
        t[:, :, 1] += q["cy"] - (lo[1] + hi[1]) / 2
        chunks.append(t)
    allt = np.concatenate(chunks, axis=0)
    lo = allt.reshape(-1, 3).min(axis=0)
    hi = allt.reshape(-1, 3).max(axis=0)
    outp = os.path.join(_ROOT, out)
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    n = M.write_binary_stl(outp, allt)
    return {"out": out, "facets": int(n),
            "bbox": [round(float(v), 3) for v in (lo[0], lo[1], hi[0], hi[1])],
            "bbox_center": [round(float((lo[0] + hi[0]) / 2), 3),
                            round(float((lo[1] + hi[1]) / 2), 3)],
            # CHITUBOX は bbox の中心を (0,0) に置く。ずらしたいときだけ人が入れる値
            "move_hint": [0.0, 0.0]}


# ---------------- HTTP ----------------

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        b = body if isinstance(body, bytes) else json.dumps(
            body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass

    def _measure(self, paths):
        """相対パスを測る。無いファイルは 500 ではなく、読める言葉で返す。"""
        out = []
        for p in paths:
            full = os.path.join(_ROOT, p)
            if not os.path.exists(full):
                raise FileNotFoundError("そのファイルが無い: %s" % p)
            out.append(M.measure(full))
        return out

    def do_GET(self):
        try:
            if self.path in ("/", "/index.html"):
                with open(os.path.join(_HERE, "app.html"), "rb") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8")
            if self.path == "/api/state":
                return self._send(200, S.state())
            if self.path == "/api/stls":
                out = []
                for p in sorted(glob.glob(os.path.join(_ROOT, "hardware", "stl", "**", "*.stl"),
                                          recursive=True)):
                    rel = os.path.relpath(p, _ROOT).replace("\\", "/")
                    out.append({"path": rel, "name": os.path.basename(p),
                                "size": os.path.getsize(p)})
                return self._send(200, {"stls": out})
            self._send(404, {"error": "no such path"})
        except Exception:
            self._send(500, {"error": traceback.format_exc()})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/api/measure":
                return self._send(200, {"parts": self._measure(req["paths"])})
            if self.path == "/api/arrange":
                parts = self._measure(req["paths"])
                lift = [p["name"] for p in parts if p["name"] in lifted_names()]
                if lift:
                    return self._send(200, {
                        "placements": [], "time": None,
                        "stop": "浮かせて刷る部品が入っている: " + "、".join(lift)
                                + "（surugo/lifted.json に宣言されている）。"
                                  "いまのパイプラインでは扱えない"})
                r = arrange(parts)
                # 部品ごとの注意（接地・島・天井）も一緒に返す
                if not r.get("stop"):
                    for p in parts:
                        for w in p["warn"]:
                            r["warn"].append("%s ── %s" % (p["name"], w))
                return self._send(200, r)
            if self.path == "/api/export":
                return self._send(200, export(req["placements"], req["out"]))
            if self.path == "/api/event":
                try:
                    ev = S.append(req["ev"], req.get("by", "human"))
                    return self._send(200, {"ok": True, "ev": ev})
                except S.Refused as e:
                    return self._send(403, {"error": str(e)})
            self._send(404, {"error": "no such path"})
        except (FileNotFoundError, KeyError) as e:
            self._send(400, {"error": str(e)})
        except Exception:
            self._send(500, {"error": traceback.format_exc()})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8731
    print("刷るぞー  http://127.0.0.1:%d/   （Ctrl-C で止める）" % port)
    print("ログ: %s" % S.LOG)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
