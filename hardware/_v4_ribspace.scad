// リブの下ごしらえを外から覗くためのプローブ。
// 🔴 中身のロジックは持たない。_v4_ribs.scad の物をそのまま呼ぶ（二重持ちを作らないため）。
// 使い方: openscad --backend=manifold -D 'part="ribfree_rwall"' -o out.stl _v4_ribspace.scad
//   ribzone_<k>  リブ帯 ∩ 板の輪郭（空きを引く前）
//   ribfree_<k>  その空き（中身と他の皮を引いたもの）
//   ribs_<k>     実際に残るリブ
include <case_v4.scad>
part = "none";
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
