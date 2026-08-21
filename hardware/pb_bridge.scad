// ============================================================
// PowerBoost をブリッジの構造に組み込む案（2026-08-20 ユーザー案）の検討用
// ============================================================
// 🔒 **この案だけを見るための単体ファイル。**他の部品は一切出さない。
//    ブリッジと PowerBoost の 2 つだけ。
//
// 案：板は**立てたまま**（右の内壁に平行・JST 下向き）。ブリッジを削るのでも
//     無くすのでもなく、**板の下側のネジ列をブリッジの下面（Z 24）に合わせて**、
//     板をブリッジの構造の一部にする。板は右の支点に立つ縦のリブになる。
//
// 🔴 2026-08-20、一度これを「寝かせて下弦にする」と読み違えて作り直した。
//    板は寝かせない。
//
// 使い方（OpenSCAD Nightly）:
//   openscad --backend=manifold -D VIEW=2 -o hit.stl hardware/pb_bridge.scad
// ============================================================

include <case_v2.scad>
// 🔒 **include より後ろに書くこと。**OpenSCAD は同じスコープなら最後の代入が勝つ。
//    前に書くと case_v2.scad の 57 行に負けて、筐体が丸ごと描かれる
part = "none";

// ---- この案のつまみ ----
VIEW  = 0;        // 0=そのまま 1=右半分だけ 2=板とブリッジの当たりだけ
PBB_Y = 24.0;     // 板の手前端。ブリッジは Y 20〜59
// 🔒 下側のネジ列（局所 y = 20.32）をブリッジの下面 BR_ZB に合わせる。
//    局所 y → 箱 Z は「下端 + PB_W - y」なので、下端 = BR_ZB - (PB_W - 20.32)
PBB_Z = BR_ZB - (PB_W - 20.32);

// ---- 板（立てたまま・上下逆で JST は下向き。case_v2 と同じ回転）----
module pb_standing() {
    translate([IN_X, PBB_Y, PBB_Z + PB_W]) rotate([0, -90, 0]) rotate([0, 0, 90]) {
        powerboost_1000c();
        pb_jst_plug();
    }
}
// ネジの軸（右の壁を横向きに貫く）
module pb_screws() {
    color("#ffe08a") for (p = pb_mount())
        translate([IN_X - PB_TH - 3, PBB_Y + p[0], PBB_Z + PB_W - p[1]])
            rotate([0, 90, 0]) cylinder(d = pb_mount_d(), h = PB_TH + 8, $fn = 24);
}
module br() { color("#7f9ec4", 0.40) bridge_raw(); }

module scene() { br(); pb_standing(); pb_screws(); }

if (VIEW == 0) scene();
else if (VIEW == 1)
    intersection() { scene(); translate([60, -10, -10]) cube([40, 100, 80]); }
else
    color("#e03030") intersection() { pb_standing(); bridge_raw(); };

echo(str("板 X ", IN_X - PB_TH, "〜", IN_X,
         " / Y ", PBB_Y, "〜", PBB_Y + PB_L,
         " / Z ", PBB_Z, "〜", PBB_Z + PB_W));
echo(str("JST の先 Z ", PBB_Z - pb_jst_out(), "  ブリッジ Z ", BR_ZB, "〜", BR_ZT));
for (p = pb_mount())
    echo(str("ネジ 局所", p, " → Y ", PBB_Y + p[0], " / Z ", PBB_Z + PB_W - p[1]));
