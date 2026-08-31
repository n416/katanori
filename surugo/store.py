# -*- coding: utf-8 -*-
"""刷るぞー ── ログ。追記だけの出来事の列（JSONL）。

🔒 **記録するのは印刷だけではない。**番手もレジンもフィルムも「出来事」として置く。
   そうすれば印刷の行に毎回打ち込む欄が消える（毎回手で入れる欄は必ず腐る）。
   変わったときだけ書けば、以後の印刷はそれを引き継ぐ。

   出来事の種類:
     term   … 印刷ターム（プレート 1 枚ぶん。刷る前に作る）
              🔒 同じ id で 2 度書いたら、**後の方が正**（改訂）。行は書き換えない
     drop   … 刷るのを辞めた。その ターム を閉じる。刷っていないので摩耗にも数えない
     plan   … これからやること（研ぎ直し・フィルム交換・レジン交換）を**予定に積む**
     did    … その予定を済ませた。⇒ このとき初めて plate / film / resin が書かれる
     order  … 列の並び順。⚠ ログは追記だけなので行は入れ替えず、**並びを 1 件足す**。
              読むときは一番新しい order を使い、そこに無い項目は積んだ順で後ろに付く
     placed … その ターム で移動指示を実際に適用したという確認
     result … 刷り上がりの結果（人が見たもの）
     film   … フィルム交換（摩耗の累積がここで 0 に戻る）
     plate  … プレートの研ぎ直し（番手が決まるのはここ）
     resin  … レジン交換

🔴 **AI が書いてよい種類は `term` だけ。**それ以外は物理の観測なので、人しか書けない。
   ここに推測が混ざると、勘を反証するために貯めている記録が最初から汚れる。
"""
import json, os, datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(os.path.dirname(_HERE), "hardware", "print_log.jsonl")

# 🔒 出どころの規則。ここを緩めない
#   plan は「これからやること」であって物理の観測ではないので、AI も積んでよい。
#   did（済ませた）は人にしか書けない。実際に手を動かしたかどうかは観測だから。
AI_MAY_WRITE = {"term", "plan", "order"}
ALL_KINDS = {"term", "drop", "placed", "result", "order",
             "plan", "did", "film", "plate", "resin"}


TERM_DIR = os.path.join(os.path.dirname(_HERE), "hardware", "stl", "term")
ARCHIVE_DIR = os.path.join(TERM_DIR, "archive")


class Refused(Exception):
    pass


def _live_outs(evs):
    """まだ生きている回が使っている書き出し先。取りやめより後に登録し直した回は生きている"""
    order, dropped = [], {}
    for i, e in enumerate(evs):
        k = e.get("t")
        if k == "term":
            order.append((i, e))
        elif k == "drop":
            dropped[e.get("term")] = i
        # ⚠ ここは term と drop しか見ない。**予定（plan / did / order）の枝を足さないこと。**
        #   2026-08-31、各ループへ一括で枝を足したときにここまで巻き込まれ、用意していない
        #   変数（plans / done / rank）を触って NameError で落ちた（取りやめが失敗した）
    last = {}
    for i, e in order:
        last[e.get("id")] = (i, e)
    return {e.get("out") for i, e in last.values()
            if dropped.get(e.get("id"), -1) < i and e.get("out")}


def remove_term_stl(term_id):
    """取りやめた回の書き出し STL を消す。消した相対パスを返す（消さなければ None）。

    🔒 消してよいのは hardware/stl/term/ の中だけ。**元の STL は絶対に消さない。**
    🔒 生きている回が同じ物を指していたら消さない。
    """
    evs = read_all()
    out = None
    for e in evs:
        if e.get("t") == "term" and e.get("id") == term_id:
            out = e.get("out")
    if not out or out in _live_outs(evs):
        return None
    root = os.path.dirname(_HERE)
    path = os.path.normpath(os.path.join(root, out))
    if os.path.normpath(os.path.commonpath([path, TERM_DIR])) != os.path.normpath(TERM_DIR):
        return None
    if os.path.exists(path):
        os.remove(path)
        return out
    return None


def archive_term_stl(term_id):
    """刷り終わった回の書き出し STL を archive/ へ移す。移した先の相対パスを返す。

    🔒 動かしてよいのは hardware/stl/term/ の中だけ。**元の STL は絶対に触らない。**
    🔒 移した先は result の行に書き残す。ログは追記だけなので、term の行の out は直さない。
       ⇒ 読むときは「out に無ければ archive/ を見る」ではなく、**result の archived を見る**。
    ⚠ 結果が付いた回の STL は消さない。焼き直しても同じ物は作れないからである
      （元の部品の STL は、そのあと変わっていることがある）。
    """
    evs = read_all()
    out = None
    for e in evs:
        if e.get("t") == "term" and e.get("id") == term_id:
            out = e.get("out")
    if not out:
        return None
    root = os.path.dirname(_HERE)
    src = os.path.normpath(os.path.join(root, out))
    if os.path.normpath(os.path.commonpath([src, TERM_DIR])) != os.path.normpath(TERM_DIR):
        return None
    if not os.path.exists(src):
        return None
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    dst = os.path.join(ARCHIVE_DIR, os.path.basename(src))
    if os.path.exists(dst):          # 既に同じ名前が居るなら動かさない（上書きしない）
        return None
    os.replace(src, dst)
    return os.path.relpath(dst, root).replace("\\", "/")


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def append(ev, by):
    """1 件書き足す。by は "human" か "ai"。"""
    kind = ev.get("t")
    if kind not in ALL_KINDS:
        raise Refused("知らない種類: %r" % kind)
    if by not in ("human", "ai"):
        raise Refused("by は human か ai")
    if by == "ai" and kind not in AI_MAY_WRITE:
        raise Refused(
            "AI は %r を書けない。番手・レジン・フィルム・結果は物理の観測なので人が書く" % kind)
    ev = dict(ev)
    ev["at"] = _now()
    ev["by"] = by
    # 🔒 刷り終わった回の STL は archive/ へ移す。**先に move してから書く。**
    #    逆にすると、移せなかったのに移したと書いたログが残る
    if kind == "result":
        ev["archived"] = archive_term_stl(ev.get("term"))
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    # 取りやめた回の書き出し STL は、残っていると紛らわしいので消す。
    # ⚠ 何を消したかは戻り値に載せる（ログの行はもう書いた後なので入らない）
    if kind == "drop":
        ev["removed"] = remove_term_stl(ev.get("term"))
    return ev


def read_all():
    if not os.path.exists(LOG):
        return []
    out = []
    with open(LOG, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    return out


def _queue(order, plans, done, placed, dropped):
    """これからやることの列。ログの並び順のまま、終わっていない物だけ。"""
    q = []
    for i, e in plans:
        if e.get("id") in done:
            continue
        q.append({"at": e["at"], "row": i, "type": "plan",
                  "id": e.get("id"), "kind": e.get("kind"),
                  "grit": e.get("grit"), "name": e.get("name"),
                  "reason": e.get("reason"), "note": e.get("note", "")})
    for i, e in order:
        q.append({"at": e["at"], "row": i, "type": "term",
                  "id": e.get("id"), "out": e.get("out"),
                  "parts": [p["name"] for p in e.get("parts", [])],
                  "detail": e.get("parts", []),
                  "placed": e.get("id") in placed})
    q.sort(key=lambda x: x["row"])
    return q


def state():
    """いまの状態を出来事から導く。人が打ち直す欄を作らないための関数。"""
    evs = read_all()
    grit = resin = None
    film_at = None                 # 最後にフィルムを替えた位置
    terms = {}
    order = []
    results = set()
    placed = set()
    dropped = {}          # ターム名 → 最後に取りやめた位置
    film_events = []
    plans = []            # 予定（研ぎ直し・フィルム交換・レジン交換）
    done = set()          # 済ませた予定の名前
    rank = {}             # 名前 → 並びの位置（一番新しい order だけが効く）

    for i, e in enumerate(evs):
        k = e.get("t")
        if k == "plate":
            grit = e.get("grit")
        elif k == "resin":
            resin = e.get("name")
        elif k == "film":
            film_at = i
            film_events.append(e)
        elif k == "term":
            terms[e.get("id")] = e
            order.append((i, e))
        elif k == "result":
            results.add(e.get("term"))
        elif k == "placed":
            placed.add(e.get("term"))
        elif k == "drop":
            dropped[e.get("term")] = i
        elif k == "plan":
            plans.append((i, e))
        elif k == "did":
            done.add(e.get("plan"))
        elif k == "order":
            rank = {v: n for n, v in enumerate(e.get("ids", []))}

    # 🔒 同じターム名で登録し直したら、後の方が正。ログは追記だけなので行は書き換えず、
    #    改訂を 1 件足して、読むときに最後のものだけを採る
    last = {}
    for i, e in order:
        last[e.get("id")] = (i, e)
    order = sorted(last.values())
    # 🔒 取りやめた回は刷っていない。摩耗にも結果待ちにも数えない。
    #    ⚠ ただし効くのは**その取りやめより前の登録**だけ。同じ名前で後から登録し直したら
    #    そちらが生きる（さもないと、取りやめた名前を使い回した回が黙って消える）
    order = [(i, e) for i, e in order if dropped.get(e.get("id"), -1) < i]

    # フィルムの摩耗（⚠ 代理値。剥離仕事そのものではない）
    wear = 0.0
    wear_terms = 0
    for i, e in order:
        if film_at is not None and i < film_at:
            continue
        for p in e.get("parts", []):
            wear += float(p.get("grip", 0)) * int(p.get("layers", 0))
        wear_terms += 1

    open_terms = [e for _, e in order if e.get("id") not in results]
    queue = _queue([(i, e) for i, e in order if e.get("id") not in results],
                   plans, done, placed, dropped)
    # 🔒 並べ替えは order で上書きする。order に無い物（後から積んだ物）は後ろへ
    big = len(rank) + len(queue) + 1
    queue.sort(key=lambda x: (rank.get(x["id"], big), x["row"]))

    return {
        "grit": grit,
        "resin": resin,
        "film_wear_mm2_layer": round(wear, 0),
        "film_wear_note": "⚠ 代理値（接地面積 × 層数の総和）。剥離仕事の測定ではない",
        "film_terms_since_change": wear_terms,
        "film_last_change": film_events[-1] if film_events else None,
        # ダッシュボードの本体はこの 2 つ ── 催促と、反証
        # ⚠ parts は名前だけの配列のまま置く（画面がそのまま並べているため）。
        #   詳細は detail に別で載せる。out は書き出した結合 STL の場所
        "open_terms": [{"id": e["id"], "at": e["at"],
                        "parts": [p["name"] for p in e.get("parts", [])],
                        "out": e.get("out"),
                        "move": e.get("move"),   # CHITUBOX に入れた移動量（フィルムを散らす）
                        "detail": e.get("parts", []),
                        "placed": e["id"] in placed} for e in open_terms],
        "n_terms": len(order),
        "n_results": len(results),
        "n_dropped": len(dropped),
        # 🔒 右の欄はスケジューラ。**これからやること**が、積んだ順に 1 本の列で並ぶ。
        #   印刷ターム も 研ぎ直し も フィルム交換 も、同じ列の項目である。
        #   ⚠ 画面の中だけに出すと リロード で消える。だからログから作る。
        "queue": queue,
    }
