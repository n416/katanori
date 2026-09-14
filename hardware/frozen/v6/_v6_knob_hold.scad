// つまみの抜け止め — 耐える断面の面積を測る（2026-09-13・機構担当）
//   高さ 1.0 で押し出すので、STL の体積 [mm3] がそのまま面積 [mm2] になる。
include <_v6_gear.scad>
RB = KN_BORE / 2;                        // 6.425 殻の穴の半径（親が持つ）
// ① ハブの歯車のうち、殻の穴の外に出ている分（＝引かれたとき壁に当たる断面）
if (part == "a_gear_catch") linear_extrude(1.0) intersection() {
    gear2d(GEAR_N);
    difference() { circle(r = 20); circle(r = RB); }
}
// ② 参考: 歯車の歯元円が穴より大きいか小さいか
echo(str("歯元円 φ", 2 * g_rf(GEAR_N), " ／ 歯先円 φ", 2 * g_ra(GEAR_N),
         " ／ 殻の穴 φ", KN_BORE, " ⇒ 歯元は穴より ",
         2 * g_rf(GEAR_N) - KN_BORE, "（負なら歯元は穴を素通りし、歯先だけが引っ掛かる）"));
// ③ 接着したときの継ぎ手の面積（皿の穴 φ8.70 × 掛かり 1.80 の筒）
echo(str("接着の筒: φ", KN_PEG + SLIP, " × ", KN_ENG, " = ",
         PI * (KN_PEG + SLIP) * KN_ENG, "mm2 ／ 隙間は片側 ", SLIP / 2));

// つまみの芯を通る X-Z 断面（皿・ハブ・前の壁だけ）。二面幅・堀・呼び込みの円錐が写る
module front_wall_only() color("#d9c98a") difference() {
    translate([0, 0, WALL_IN]) cube([BODY_X, BODY_Y, WALL]);
    shell_cut();
}
// 🔴 色は部品ごとに切らないと消える（intersection は子の色を持たない）
module gslab() translate([KN_C[0] - 20, KN_C[1] - 0.01, 18.0]) cube([40, 20, 9]);
if (part == "gknob") {
    color("#2f3237") intersection() { knob_dish();       gslab(); }   // 皿（外）
    color("#e0564a") intersection() { knob_hub();        gslab(); }   // ハブ（内）
    color("#c9c2a8") intersection() { front_wall_only(); gslab(); }   // 前の壁
}

// ④ 柱の天面の面積（栓と溶ける面）。高さ 1.0 で押し出すので体積＝面積
if (part == "a_peg_top") linear_extrude(1.0) intersection() {
    circle(d = KN_PEG);
    square([2 * KN_PEG, KN_FLAT], center = true);
}

// ⑤ ブラケットが板に触れている面積（板の面から 0.1 の薄板で切る。体積 ÷ 0.1 ＝ 面積）
if (part == "a_brk_seat") intersection() {
    brk();
    translate([0, 0, PCB_TOP]) cube([BODY_X, BODY_Y, 0.10]);
}
// ⑥ ねじの穴のまわりだけ（芯から r3.2 の円柱で切り出す）
if (part == "a_brk_screw") intersection() {
    brk();
    translate([0, 0, PCB_TOP]) cube([BODY_X, BODY_Y, 0.10]);
    translate([BRK_SCR[0], BRK_SCR[1], PCB_TOP - 1]) cylinder(d = 6.4, h = 3);
}

// ⑦ ナットの座（足の天面のうち、M2 ナットの外接円 φ3.7 の中に残っている面積）
if (part == "a_nut_seat") intersection() {
    brk();
    translate([0, 0, PCB_TOP + BRK_FT - 0.10]) cube([BODY_X, BODY_Y, 0.10]);
    translate([BRK_SCR[0], BRK_SCR[1], 0]) cylinder(d = 3.7, h = 30);
}

// ============================================================
// 接着の面積（2026-09-13・裁定 #2 の取り消し後）
//   A スカートの下端の輪 … 引っ張りで受ける。高さ 1.0 で押し出すので 体積＝面積
//   B 柱と穴の隙間       … せん断で受ける。溝（BND_STOPZ）で止まるので高さはそこまで
// ============================================================
module bore_slot_2d() intersection() {
    circle(d = KN_PEG + SLIP);
    square([2 * KN_PEG, KN_FLAT + SLIP], center = true);
}
if (part == "a_bond_rim") linear_extrude(1.0) difference() {
    circle(d = BND_UC);
    bore_slot_2d();
}
if (part == "a_bond_bore") linear_extrude(BND_STOPZ - GTOP) difference() {   // 体積 ÷ 膜は取らない
    bore_slot_2d();                                                          // 周長を出すための体
    offset(r = -0.01) bore_slot_2d();
}
echo(str("接着 B: 穴の周長 × 高さ。高さ ", BND_STOPZ - GTOP,
         "（GTOP ", GTOP, " → 溝 ", BND_STOPZ, "）／溝より上の乾いた穴 ", BND_DRY));
echo(str("逃げ 外: スカートを φ", KN_SKIRT, " → φ", BND_UC, " に細くした所の容積 ",
         PI / 4 * (pow(KN_BORE, 2) - pow(BND_UC, 2)) * BND_UCZ, "mm3"));
echo(str("逃げ 上: 毛管止めの溝 φ", BND_STOPD, " × ", BND_STOPT, " の容積 ",
         PI / 4 * (pow(BND_STOPD, 2) - pow(KN_PEG, 2)) * BND_STOPT, "mm3"));
