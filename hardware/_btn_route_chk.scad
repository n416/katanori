// 押し子とカバーを入れる道の検査（2026-08-30・ユーザー案「ハット＋上からカバー」）。
//   押し子は**上から**皿へ落とす（ツバが天板の口を通る）。カバーはその上から皿のザグリへ落とす。
//   ⇒ 座った位置から上へ 12mm 引き抜く軌跡と、天板側の肉が当たるかを測る。**0 が正**。
include <btn_v2.scad>
part = "none"; BTN2_SOLO = false;
STEP = 0.25; LIFT = 12; WHAT = "piston";
module up(m) for (i = [0 : STEP : LIFT]) translate([0, 0, i]) children();
intersection() {
    if (WHAT == "cover") up() btn2_cover(); else up() btn2_piston();
    difference() { btn2_station_add(); btn2_station_cut(); }
}
