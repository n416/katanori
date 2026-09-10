// OLED の左右のダボの間隔のゲージ（🔒 ユーザー 2026-09-10「OLED の左右のダボの幅のゲージもいくつか欲しい。
// 現状、左右をごくごくわずかに削って入れた。今後天板を再度刷る時用に正しい状態にしておきたい」「ダボ自体のサイズはあってる」）
//
// 天板の L の足のダボは φ2.8・長さ 2.0・先の面取り 0.6（case_v5.scad OLED_PEG_*）。径は実物で合っているので変えない。
// 間隔は今 66.1 で、これは穴−穴の実測ではなく 板幅 70.1 − 4.0 の計算値（parts.scad:963・⬜ OLED_L 未確定）。
// ユーザー「間隔の幅だけごくごくわずかに広い」なので、ここでは 65.4〜66.1 を 0.1 刻みで 8 組並べる。OLED の板を上から落として、両方のダボが力なしで入る組が正。
// 数字は 10 倍（"661" = 66.1）で各組の左に 0.4 彫る。前提: ボトム公差補償 OFF。
// ⚠ 実物のダボは横向き（−Y）に刷られるが、間隔（X）は LCD の画素が決めるので、ここでは上向きで刷る（80 層で済む）。

GAPS   = [for (i = [0 : 7]) 65.4 + 0.1 * i];   // 65.4〜66.1。🔒 ユーザー「間隔の幅だけごくごくわずかに広い」なので 66.1 より下だけ。66.1 は今の値（削らずには入らないはず）
PEG_D  = 2.8; PEG_L = 2.0; PEG_CH = 0.6;
PITCH  = 6.0;                    // 組の間隔（Y）
BASE_T = 2.0;
PLATE_L = 84; PLATE_W = 4 + PITCH * len(GAPS);
CX = PLATE_L / 2;
TXT = 2.0; TXT_D = 0.4;

difference() {
    union() {
        cube([PLATE_L, PLATE_W, BASE_T]);
        for (i = [0 : len(GAPS) - 1]) let (g = GAPS[i], y = 5 + PITCH * i)
            for (sx = [-1, 1]) translate([CX + sx * g / 2, y, BASE_T - 0.01]) {
                cylinder(d = PEG_D, h = PEG_L - PEG_CH + 0.01, $fn = 32);
                translate([0, 0, PEG_L - PEG_CH]) cylinder(d1 = PEG_D, d2 = PEG_D - 2 * PEG_CH, h = PEG_CH, $fn = 32);
            }
    }
    for (i = [0 : len(GAPS) - 1]) let (y = 5 + PITCH * i)
        translate([CX, y, BASE_T - TXT_D]) linear_extrude(TXT_D + 0.01)
            text(str(round(GAPS[i] * 10)), size = TXT, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
    translate([-0.01, -0.01, BASE_T - 1]) cube([2, 2, 1.01]);
    for (x0 = [13, 45]) translate([x0, 3, -1]) cube([24, PLATE_W - 6, BASE_T + 2]);   // 窓 2 つ。接地を LCD の 30% 以下に（docs/PRINT.md 冒頭: 大きい平面は土台がたわむ）。レール 0〜13 / 71〜84 にダボ、真ん中の背骨 37〜45 に数字   // 小さい方（65.4）の端の目印
}
