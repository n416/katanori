// btn_v3 の当たり検査（🔒 「空」と「失敗」と「数値」を分ける。空なら STL が出ない）
//   WHAT = "piston"  … 押し子が上下する軌跡 ↔ 天板側の肉（0 が正）
//   WHAT = "tubway"  … バスタブが下から上がってくる道 ↔ 天板側の肉（0 が正）
//   WHAT = "pt"      … 押し子 ↔ バスタブ（0 が正）
//   WHAT = "block"   … ブロック ↔ ツバの部屋（0 が正・2026-08-30 の「押し子にあたってんじゃん」）
include <btn_v3.scad>
part = "none"; BTN3_SOLO = false;
WHAT = "piston";
STEP = 0.15;

module station() difference() { btn3_station_add(); btn3_station_cut(); }
module sweep_z(from, to) for (i = [from : STEP : to]) translate([0, 0, i]) children();

intersection() {
    if (WHAT == "piston")      sweep_z(-B3_TRAVEL, 0) btn3_piston();
    // 🔴 バスタブは**下から**上がってくる。上へ抜く向きで掃くと、耳とブロックが当たって当然
    //   （それは掴んでいる証拠であって不具合ではない）。座る直前 -0.05 まで見る。
    else if (WHAT == "tubway") sweep_z(-14, -0.05) btn3_tub();
    else if (WHAT == "pt")     btn3_piston();
    else if (WHAT == "block")  for (sx = [0, 1]) mirror([sx, 0, 0]) btn3_block();

    if (WHAT == "pt") btn3_tub();
    else if (WHAT == "block")
        translate([0, 0, B3_Z_WIN_B]) b3_box(B3_WIN_L, B3_WIN_W, 1.4, B3_Z_LIP_B - B3_Z_WIN_B);
    else station();
}
