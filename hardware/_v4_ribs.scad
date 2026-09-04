// 反り対策のリブ（2026-09-04）。docs/CASE-V4-OPEN.md「反り対策のリブ」が決めた形。
//   🔒 ユーザー「リブつけてみましょ。3mmになるように」「鞍型ですね」
//   ⇒ 板 2.0 の内面に 0/90 の格子。丈 2.0（front だけ 1.0）・幅 1.6・ピッチ 8。等価板厚 2.95。
//
// 🔴 手で座標を置いていない。リブ ＝ 格子のパターン ∩「内面の空き」で、空きは
//    〈リブ帯 ∩ 板の輪郭〉−〈中身を面内 ±RIB_MARG 太らせた物〉−〈他の皮〉として毎回その場で出す。
//    ⇒ 中身が動けばリブが勝手に短くなる。**当たりは構成上ゼロで、検査は要らない。**
//
// ⚠ 4 枚とも外面を下にして刷るのでリブは上を向く。支柱は要らず、接地面積も LCD 比も変わらない。
// ⚠ 素の板だけ見たいときは -D RIBS_OFF=true（中身を引く分だけ重いので、当たり検査の下ごしらえにも使う）

RIBS_OFF  = false;
RIB_H     = 2.0;    // リブの丈（板からの高さ）。板 2.0 ＋ 2.0 ＝ 局所 4.0mm
RIB_H_FR  = 1.0;    // 🔴 front だけ。窓の裏の OLED と ReSpeaker で 1.5 も立たない（空き 59% → 24%）
RIB_W     = 1.6;    // リブの幅
RIB_P     = 8.0;    // ピッチ（縦横とも）
RIB_MARG  = 0.4;    // 中身との面内の逃げ
RIB_CLR   = 0.5;    // 中身との深さの逃げ（帯はリブ丈 ＋ これで見る）
RIB_OPEN  = 1.5;    // 空きの「開き」半径。これより細い空きは消す ＝ 切れ端が出ない
RIB_THIN  = 0.4;    // 空きの縁をこれだけ削る。格子の線が縁をかすって出る薄片（0.1mm 等）を落とす
RIB_BIG   = 400;
// 🔴 2026-09-04 組む動きの掃引。壁は上から降ろすので、リブは**降りてくる途中も**中身を避ける必要がある。
//    静止の当たり（chk_all）だけ見て出したリブは close_lwall 60.3 / close_rwall 267.6 を出した。
//    障害物は case_v4 の stage_walls（手順 4 の時点で箱に入っている物）と同じ物を使う。
RIB_DROP  = 30;     // 壁を持ち上げる高さ（case_v4 の close_lwall / close_rwall と同じ）
RIB_DSTEP = 0.5;    // 掃引の刻み

function rib_h(k)    = k == "front" ? RIB_H_FR : RIB_H;
function rib_band(k) = rib_h(k) + RIB_CLR;
// 板ごとの [厚み軸(0=X,1=Y), 内面の値, 内向きの符号, 板厚]
function rib_p(k) =
      k == "lwall" ? [0, LW_X,  +1, WALL]
    : k == "rwall" ? [0, IN_X,  -1, WALL]
    : k == "hatch" ? [1, IN_Y,  -1, HATCH_T]
    :                [1, FY_IN, +1, BEZ_T];
function rib_v(axis, d) = axis == 0 ? [d, 0, 0] : [0, d, 0];
// 🔴 front は入れない。2026-09-04、板厚を 2.0 → 2.8 に上げた（case_base の BEZ_T）ので要らない。
//    リブでは 3 本 30mm しか入らず（空き 990mm²）、効きが +1% しか無かった。
function has_rib(k) = k == "lwall" || k == "rwall" || k == "hatch";

// リブ帯: 内面から rib_band(k) の層
module rib_slab(k) {
    p = rib_p(k); b = rib_band(k); lo = p[2] > 0 ? p[1] : p[1] - b;
    if (p[0] == 0) translate([lo, -RIB_BIG/2, -RIB_BIG/2]) cube([b, RIB_BIG, RIB_BIG]);
    else           translate([-RIB_BIG/2, lo, -RIB_BIG/2]) cube([RIB_BIG, b, RIB_BIG]);
}
// 板を内向きへ掃いて、輪郭（穴は穴のまま）を帯の深さまで伸ばす
module rib_sweep(k) {
    p = rib_p(k); b = rib_band(k);
    for (s = [p[3] : 0.25 : p[3] + b]) translate(rib_v(p[0], p[2] * s)) skin1(k, false);
}
module rib_zone(k) intersection() { rib_slab(k); rib_sweep(k); }
module rib_fat() {
    innards4();
    for (a = [0, 1, 2], s = [-1, 1])
        translate([a == 0 ? s*RIB_MARG : 0, a == 1 ? s*RIB_MARG : 0, a == 2 ? s*RIB_MARG : 0]) innards4();
}
// 🔴 通す必要のある「道」は全部ここへ入れる。case_v4 の検査で **0 が正** と書いてある物と対にする。
//    ここに書き漏らすと、静止では 0 なのに組めないリブが出来る（実際 close_lwall 60.3 を出した）。
module rib_path(k) {
    // 🔴 ① 「壁を上から 30mm 降ろす」は入れない（2026-09-04・一度入れて外した）。
    //    ✅ ユーザー「手で持って左右の壁で ReSpeaker をサンドイッチするんですよ。ねじは下からでしょ?」
    //    ⇒ 壁は箱へ落とすのではなく **±X から挟む**。case_v4 の close_lwall / close_rwall が見ている
    //      垂直の並進は、計算が楽なだけで実際の組み方ではない（ユーザー「垂直におろしたことなど1度もない」）。
    //    ⇒ しかも横から来るなら**リブは進行方向の先端**で、壁自身がこれから埋める空間を先に通るだけ。
    //      新しい所は通らないので、静止の空き（rib_zone − 中身 − 他の皮）以上の制約にならない。
    //      裏取りは _v4_ribspace.scad の side_lwall / side_rwall（±X の掃引・0 が正）。
    //    ⚠ これを入れると右の壁のリブが 608 → 340mm に半減する。捨てていたのは全部この制約のため。
    // ② ドライバの道（chk_t1・3 点目のビス。φ3.2 × 24 の軸）
    t1_driver();
    // ③ 充電基板を左の壁のポケットへ後ろから滑り込ませる道（chk_tc_pocket）
    if (k == "lwall") for (t = [0 : RIB_DSTEP : 18]) translate([0, t, 0]) tcb_v4_bare();
}
module rib_free(k) difference() { rib_zone(k); rib_fat(); skin_except(k, false); rib_path(k); }

// ---- リブ本体 ----
// 🔴 線は自動生成（`python hardware/_v4_ribs.py`）。_v4_props.scad と同じ型。
//    生成側が「幅ぜんぶが空いている・8mm 以上」の区間だけを切り出すので、
//    **薄片・切れ端は構造上できない**（格子を空きで切る作り方だと 0.1mm の紙片が残った）。
//    ⚠ 中身（innards4）を動かしたら生成し直すこと。忘れるとリブが古い空きのまま。
include <_v4_ribs_gen.scad>

// seg = [板, 向き(0=面内の第1軸に走る / 1=第2軸), 線の位置, 始点, 終点]
module rib_one(k, seg) {
    p = rib_p(k); ax = p[0]; h = rib_h(k);
    f  = p[2] > 0 ? p[1] : p[1] - h;      // 厚み方向の始まり
    d = seg[1]; c = seg[2]; a = seg[3]; b = seg[4];
    // 面内の軸: ax=0（厚み X）→ [Y, Z]  ／  ax=1（厚み Y）→ [X, Z]
    if (ax == 0) {
        if (d == 0) translate([f, a, c - RIB_W/2]) cube([h, b - a, RIB_W]);   // Y に走る
        else        translate([f, c - RIB_W/2, a]) cube([h, RIB_W, b - a]);   // Z に走る
    } else {
        if (d == 0) translate([a, f, c - RIB_W/2]) cube([b - a, h, RIB_W]);   // X に走る
        else        translate([c - RIB_W/2, f, a]) cube([RIB_W, h, b - a]);   // Z に走る
    }
}
module panel_ribs(k) if (!RIBS_OFF && has_rib(k))
    color("#8fb8a0") for (s = RIB_SEGS) if (s[0] == k) rib_one(k, s);
