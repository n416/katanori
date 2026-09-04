// リブの下ごしらえを外から覗くためのプローブ。
// 🔴 中身のロジックは持たない。_v4_ribs.scad の物をそのまま呼ぶ（二重持ちを作らないため）。
// 使い方: openscad --backend=manifold -D 'part="ribfree_rwall"' -o out.stl _v4_ribspace.scad
//   ribzone_<k>  リブ帯 ∩ 板の輪郭（空きを引く前）
//   ribfree_<k>  その空き（中身と他の皮を引いたもの）
//   ribs_<k>     実際に残るリブ
include <case_v4.scad>
part = "none";
// 「壁を降ろす道」の 4 本が、最終位置では何をどれだけ避けているか（＝本当に要る分）を出す。
//   箱そのものと交わる分だけが要る。残りは降ろすためだけの彫り。
module cut_l1() translate([0.274, 9.19, -0.5]) cube([LW_X - 0.274 + 0.01, 15.85 - 9.19, 12.2 + 0.5]);
module cut_l2() translate([1.17, 12.87, -0.5]) cube([LW_X - 1.17 + 0.01, 17.87 - 12.87, 11.9 + 0.5]);
module cut_l3() translate([0.99, 9.97, -0.5]) cube([LW_X - 0.99 + 0.01, 13.73 - 9.97, 35.03 + 0.5]);
module cut_r1() translate([IN_X - 0.01, XIAO_PORT_C[0] - USBC_PORT[0] / 2, -0.5]) cube([85.704 - IN_X + 0.01, USBC_PORT[0], XIAO_PORT_C[1] + 0.5]);
if (part == "cutneed_l1") intersection() { cut_l1(); innards4(); }
if (part == "cutneed_l2") intersection() { cut_l2(); innards4(); }
if (part == "cutneed_l3") intersection() { cut_l3(); innards4(); }
if (part == "cutneed_r1") intersection() { cut_r1(); innards4(); }
if (part == "cutvol_l1") cut_l1();
if (part == "cutvol_l2") cut_l2();
if (part == "cutvol_l3") cut_l3();
if (part == "cutvol_r1") cut_r1();

// 🔴 組み方の検査（side_lwall / side_rwall / wing_lwall）は case_v4.scad 本体へ移した。ここには置かない。

// 皮どうしの当たり（フロントを厚くしたとき、天板・壁と喧嘩していないかを見る）
SKIN_PAIRS = [["front","top"], ["front","lwall"], ["front","rwall"], ["front","floor"], ["top","hatch"]];
for (q = SKIN_PAIRS)
    if (part == str("chk_", q[0], "_", q[1])) intersection() { skin1(q[0]); skin1(q[1]); }

// フロントを部品に割って、どれが壁に当たっているかを見る
// リブが皮に当たっていないか（板ごと）
for (k = ["lwall", "rwall", "hatch"]) for (n = ["front", "top", "floor", "hatch", "lwall", "rwall"])
    if (k != n && part == str("chk_rib_", k, "_", n)) intersection() { panel_ribs(k); skin1(n, false); }

if (part == "chk_fplate_lwall") intersection() { front_plate_raw(); skin1("lwall", false); }
if (part == "chk_fears_lwall")  intersection() { front_ears_low(); skin1("lwall", false); }
if (part == "chk_fplate_rwall") intersection() { front_plate_raw(); skin1("rwall", false); }
if (part == "chk_fears_rwall")  intersection() { front_ears_low(); skin1("rwall", false); }

for (k = ["lwall", "rwall", "hatch", "front"]) {
    if (part == str("ribzone_", k)) rib_zone(k);
    if (part == str("ribfree_", k)) rib_free(k);
    if (part == str("ribs_", k))    panel_ribs(k);
}
