// 穴ゲージ ── AS5600 基板の取付穴に「印刷した何 φ なら入るか」を出す櫛
// ============================================================
// 2026-08-27 ユーザー「穴の実径どうやって計ったらいいんだこれ」への道具。
//   🔒 測るのは穴の実径ではなく **印刷した棒の径**。柱は印刷物なので、樹脂の収縮も
//      プリンタの癖も込みで答えが出る（ノギスで穴を測ってから収縮を足し引きすると、
//      補正を 2 回かけて外す）。
//   使い方: 4 つの穴それぞれに刺し、**通る最大の番号**を読む。それが柱の径。
//      根元 1mm は 0.4 細くしてあるので、台の付け根の丸みは判定に効かない。
//   実行: openscad --backend=manifold -o stl/hole_gauge.stl hardware/hole_gauge.scad
// ============================================================
$fn = 96;

D0    = 3.1;    // いちばん細い棒
DN    = 8;      // 本数（3.1 → 3.8）
DSTEP = 0.1;
PITCH = 8.0;    // 棒の間隔（指が入る）
PIN_H = 4.0;    // 棒の高さ（基板 1.6 より十分高い）
FOOT  = 1.0;    // 付け根の逃げの高さ
FOOT_UNDER = 0.4;   // 逃げのぶん細くする量
PLATE_T = 2.5;
PLATE_W = 16.0;
TXT_H   = 3.6;

module pin(d) {
    cylinder(d = d - FOOT_UNDER, h = FOOT + 0.01);              // 付け根（判定に使わない）
    translate([0, 0, FOOT]) cylinder(d = d, h = PIN_H - FOOT);  // ここで測る
}

PLATE_L = PITCH * DN;
difference() {
    union() {
        translate([0, 0, 0]) cube([PLATE_L, PLATE_W, PLATE_T]);
        for (i = [0 : DN - 1])
            translate([PITCH * (i + 0.5), PLATE_W - 5.0, PLATE_T]) pin(D0 + DSTEP * i);
        // 番号（棒の手前に浮き出し）。31 = φ3.1
        for (i = [0 : DN - 1])
            translate([PITCH * (i + 0.5), 3.2, PLATE_T])
                linear_extrude(0.6)
                    text(str(round((D0 + DSTEP * i) * 10)), size = TXT_H,
                         halign = "center", valign = "baseline");
    }
}
