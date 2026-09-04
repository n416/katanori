// 刻印のクーポン（2026-09-04）
// ------------------------------------------------------------------
// 何を決めるためのものか:
//   🔴 実機で刻印が出ない／ヒビに見える。ユーザー「表面は埋まり、奥の方に小さな傷のような
//      稲妻が残った」。⇒ 溝の**口が塞がる**。深さは効かない（0.4 → 1.0 に上げても出た）。
//      効くのは溝の**幅**だけ。**塞がらない最小の幅の実績が無い**（0.5〜0.6 は塞がると分かっただけ）。
//   ⇒ 3 つの印を倍率違いで並べ、口が塞がらない最小の倍率を実物に決めさせる。
//
// 刷り方:
//   🔴 **彫った面を下（プレート側）にして刷る。** 実機の壁・ハッチと同じ向き。
//      上向きに刷ると層をまたぐ硬化の効き方が変わり、答えにならない。
//   板は 2.0mm（壁 WALL・ハッチ HATCH_T と同じ）。彫りは ICON_D（1.0mm）。
//   倍率の数字だけは**上面に浮かせて**ある（上向きの面は問題なく出るので、読むためだけ）。
//
// 使い方:
//   openscad --backend=manifold -o stl/icon_gauge.stl hardware/icon_gauge.scad
include <case_v4.scad>
part = "none";   // 🔴 include は case_v4 の既定 part="explode" を連れてくる。
                 //    これが無いと STL に筐体が丸ごと（28 個の物体・26MB）混ざる。

KS   = [1.5, 2.0, 2.5];   // 倍率。ICON_K の候補（置ける上限はハッチ 2.90 / 右の壁 4.00）
MARG = 1.2;               // 印のまわりに残す肉
GAP  = 2.5;               // 升と升のあいだ
RIB  = 3.0;               // 升をつなぐ帯の幅
T    = 2.0;               // 板の厚み（壁と同じ）
LBL  = 0.6;               // 上面に浮かせる数字の高さ

// ---- 印を倍率 k で描く（case_base / case_v4 の中身と同じ式。ICON_K には依らせない）----
module g_bolt(k) icon_round(ICON_R * k * ICON_BOLT_K) icon_bolt(TC_ICON_H * k * ICON_BOLT_K);
// 🔴 2026-09-04 原本（icon_wrench_u）に 90 度を焼き込んだので、ここで 90 度を取る。
//    クーポンは彫った面を**下**にして刷り、その面を見る。壁は外面を見る。見る側が逆なので、
//    原本 1 つの向きでは両方に合わない。壁が素のまま合うようにしたぶん、こちらで戻す。
module g_wrench(k) let(sc = 4.87 * k / icon_wrench_u_span())
    icon_round(ICON_R * k) rotate([0, 0, -90]) scale(sc) icon_wrench_u();
module g_phone(k) let(h  = 0.7 * LJACK_D * k,
                      sc = h / icon_headphone_size()[1],
                      sw = max(icon_headphone_sw() * ICON_HP_SW, SVC_MIN_W / sc))
    icon_round(icon_r_cap(sw * sc)) scale(sc) icon_headphone(sw);   // 線画なので丸めは頭打ち
module g_icon(r, k) { if (r == 0) g_bolt(k); else if (r == 1) g_wrench(k); else g_phone(k); }

// ---- 升の大きさ（印の外形 ＋ MARG）----
function bolt_wh(k)   = [TC_ICON_H * k * ICON_BOLT_K * 2.6 / 6, TC_ICON_H * k * ICON_BOLT_K];
function wrench_wh(k) = [4.87 * k, 4.87 * k];
function phone_wh(k)  = let(h = 0.7 * LJACK_D * k) [h * icon_headphone_size()[0] / icon_headphone_size()[1], h];
function icon_wh(r, k) = r == 0 ? bolt_wh(k) : r == 1 ? wrench_wh(k) : phone_wh(k);
function cell_w(c) = max([for (r = [0 : 2]) icon_wh(r, KS[c])[0]]) + 2 * MARG;
function cell_h(r) = max([for (c = [0 : len(KS) - 1]) icon_wh(r, KS[c])[1]]) + 2 * MARG;
function col_x(c) = c == 0 ? cell_w(0) / 2 : col_x(c - 1) + cell_w(c - 1) / 2 + GAP + cell_w(c) / 2;
function row_y(r) = r == 0 ? -cell_h(0) / 2 : row_y(r - 1) - cell_h(r - 1) / 2 - GAP - cell_h(r) / 2;

module pad(w, h) hull() for (a = [-1, 1], b = [-1, 1])
    translate([a * (w / 2 - 1.5), b * (h / 2 - 1.5)]) circle(r = 1.5, $fn = 24);

module skeleton() {
    for (r = [0 : 2], c = [0 : len(KS) - 1]) translate([col_x(c), row_y(r)]) pad(cell_w(c), cell_h(r));
    for (r = [0 : 2], c = [0 : len(KS) - 2])                                       // 横の帯
        translate([(col_x(c) + col_x(c + 1)) / 2, row_y(r)]) square([col_x(c + 1) - col_x(c), RIB], center = true);
    for (r = [0 : 1], c = [0 : len(KS) - 1])                                       // 縦の帯
        translate([col_x(c), (row_y(r) + row_y(r + 1)) / 2]) square([RIB, row_y(r) - row_y(r + 1)], center = true);
}

difference() {
    union() {
        linear_extrude(T) skeleton();
        // 倍率の数字（上面に浮かせる。上向きの面なので読める）
        for (c = [0 : len(KS) - 1]) translate([col_x(c), row_y(2) - cell_h(2) / 2 + 1.4, T])
            linear_extrude(LBL) offset(r = 0.35) text(str(KS[c]), size = 3.0, halign = "center", valign = "baseline", font = "DejaVu Sans");   // 🔴 素の文字は線が 0.27〜0.30 で下限割れ。太らせる
    }
    // 印を彫る（下面から ICON_D）
    for (r = [0 : 2], c = [0 : len(KS) - 1])
        translate([col_x(c), row_y(r), -0.01]) linear_extrude(ICON_D + 0.01)
            rotate([0, 0, r == 2 ? 180 : 0]) g_icon(r, KS[c]);
}

echo(str("クーポン: 升 ", [for (c = [0 : len(KS) - 1]) cell_w(c)], " x ", [for (r = [0 : 2]) cell_h(r)],
         " / 全体 ", col_x(len(KS) - 1) + cell_w(len(KS) - 1) / 2, " x ", -row_y(2) + cell_h(2) / 2));
