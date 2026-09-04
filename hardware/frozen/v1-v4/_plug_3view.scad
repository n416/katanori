include <case_v3.scad>
// micro-B の口の前の「自由な空間」の三面図。部品は色分けし、凡例で名前を出す
// ⚠ アダプタ本体は描かない（L 字の曲がる向きが商品図から一意に決まらないため）
C  = pb2box([-0.5, pb_usb()[1], pb_pcb_t() + pb_usb_sz()[2] / 2]);   // 口の面の中心 (81.7, 23.5, 36.4)
FX = 8.6; FY = 13.5; FZ = 11.0;                                       // ✅ 実測（当たり 0〜3mm³）
GX0 = C[0] - FX/2; GY0 = C[1] - FY; GZ0 = C[2] - FZ/2;

NAMES = ["PowerBoost", "ReSpeaker", "右の壁", "左の壁", "ブリッジ", "ハブ基板", "床",
         "ハウジング", "INA226", "電池", "天面", "フロント", "ハッチ"];
COLS  = ["#c026d3", "#2563eb", "#475569", "#94a3b8", "#ea580c", "#ca8a04", "#cbd5e1",
         "#7c3aed", "#db2777", "#eab308", "#64748b", "#0d9488", "#78716c"];
module g(i) {
    if (i ==  0) pb_v3();
    if (i ==  1) respeaker_at();
    if (i ==  2) right_wall_v3();
    if (i ==  3) left_wall_v3();
    if (i ==  4) bridge_v3();
    if (i ==  5) hub_at();
    if (i ==  6) floor_v3();
    if (i ==  7) for (id = PLUGGED_9) housing(id);
    if (i ==  8) translate([INA_AT[0], INA_AT[1] + ina_size()[1], INA_AT[2] + ina_h()]) rotate([180, 0, 0]) ina226_module();
    if (i ==  9) translate(LIPO_AT) lipo_1000mah();
    if (i == 10) top_plate();
    if (i == 11) front_plate();
    if (i == 12) hatch();
}
module free_box() translate([GX0, GY0, GZ0]) cube([FX, FY, FZ]);
module axis_rod() translate([C[0] - 0.25, GY0, C[2] - 0.25]) cube([0.5, FY, 0.5]);

module sec_x(x)  projection(cut = true) translate([0, 0, x])  rotate([0, 90, 0]) children();                  // 横=Z 縦=Y
module sec_z2(z) projection(cut = true) translate([0, 0, -z]) children();                                      // 横=X 縦=Y
module sec_y2(y) mirror([0, 1]) projection(cut = true) rotate([90, 0, 0]) translate([0, -y, 0]) children();    // 横=X 縦=Z
module clip(a0, a1, b0, b1) intersection() { children(); translate([a0, b0]) square([a1-a0, b1-b0]); }
module border(a0, a1, b0, b1) color("#334155") linear_extrude(0.5) difference() { square([a1-a0, b1-b0]); translate([0.25,0.25]) square([a1-a0-0.5, b1-b0-0.5]); }
module lbl(p, s, sz = 1.7, w = 0) {
    if (w > 0) color("#f7f7f7") translate([p[0] - 0.5, p[1] - 0.5]) linear_extrude(4.6) square([w, sz * 1.45]);
    color("#0f172a") translate(p) linear_extrude(5) text(s, size = sz, font = "Meiryo");
}
module dim(p, q) color("#dc2626") linear_extrude(4.5) hull() { translate(p) circle(0.16); translate(q) circle(0.16); }

W = [[66, 90, 6, 40], [66, 90, 20, 52], [20, 52, 6, 40]];   // TOP / FRONT / SIDE の窓
AT = [[0, 47], [0, 0], [58, 47]];

module view(v) {
    w = W[v]; at = AT[v];
    translate(at) {
        translate([-w[0], -w[2]]) {
            for (i = [0 : len(NAMES) - 1])
                color(COLS[i]) linear_extrude(1 + i * 0.01) clip(w[0], w[1], w[2], w[3])
                    { if (v == 0) sec_z2(C[2]) g(i); else if (v == 1) sec_y2(C[1] - FY/2) g(i); else sec_x(C[0]) g(i); }
            color("#15803d") linear_extrude(2.5) clip(w[0], w[1], w[2], w[3])
                { if (v == 0) sec_z2(C[2]) free_box(); else if (v == 1) sec_y2(C[1] - FY/2) free_box(); else sec_x(C[0]) free_box(); }
            if (v != 1) color("#000000") linear_extrude(3) clip(w[0], w[1], w[2], w[3])
                { if (v == 0) sec_z2(C[2]) axis_rod(); else sec_x(C[0]) axis_rod(); }
        }
        border(w[0], w[1], w[2], w[3]);
    }
}
view(0); view(1); view(2);

lbl([AT[0][0],       AT[0][1] + 35.6], "上から　横＝X　縦＝Y", 2.0);
lbl([AT[1][0],       AT[1][1] + 33.6], "前から　横＝X　縦＝Z", 2.0);
lbl([AT[2][0],       AT[2][1] + 35.6], "横から　横＝Z　縦＝Y", 2.0);

dim([AT[0][0]+11.4, AT[0][1]+18.6], [AT[0][0]+20.0, AT[0][1]+18.6]);  lbl([AT[0][0]+12.9, AT[0][1]+19.5], "X 8.6", 1.7, 5.8);
dim([AT[0][0]+10.2, AT[0][1]+4.0],  [AT[0][0]+10.2, AT[0][1]+17.5]);  lbl([AT[0][0]+3.4,  AT[0][1]+10.2], "Y 13.5", 1.7, 6.6);
dim([AT[0][0]+24.0, AT[0][1]+17.5], [AT[0][0]+26.5, AT[0][1]+17.5]);  lbl([AT[0][0]+27.0, AT[0][1]+16.8], "口の面 Y23.5");
dim([AT[0][0]+24.0, AT[0][1]+4.0],  [AT[0][0]+26.5, AT[0][1]+4.0]);   lbl([AT[0][0]+27.0, AT[0][1]+3.3],  "ReSpeaker の背面 Y10.0");
dim([AT[0][0]+24.0, AT[0][1]+30.0], [AT[0][0]+26.5, AT[0][1]+30.0]);  lbl([AT[0][0]+27.0, AT[0][1]+29.3], "右の壁 X86.0");

dim([AT[1][0]+11.4, AT[1][1]+23.0], [AT[1][0]+20.0, AT[1][1]+23.0]);  lbl([AT[1][0]+12.9, AT[1][1]+23.9], "X 8.6", 1.7, 5.8);
dim([AT[1][0]+10.2, AT[1][1]+10.9], [AT[1][0]+10.2, AT[1][1]+21.9]);  lbl([AT[1][0]+3.4,  AT[1][1]+15.8], "Z 11.0", 1.7, 6.6);
dim([AT[1][0]+24.0, AT[1][1]+16.4], [AT[1][0]+26.5, AT[1][1]+16.4]);  lbl([AT[1][0]+27.0, AT[1][1]+15.7], "口の軸 Z36.4");

dim([AT[2][0]+10.9, AT[2][1]+18.6], [AT[2][0]+21.9, AT[2][1]+18.6]);  lbl([AT[2][0]+14.0, AT[2][1]+19.5], "Z 11.0", 1.7, 6.6);
dim([AT[2][0]+9.7,  AT[2][1]+4.0],  [AT[2][0]+9.7,  AT[2][1]+17.5]);  lbl([AT[2][0]+2.9,  AT[2][1]+10.2], "Y 13.5", 1.7, 6.6);

// ---- 凡例
LG = [100, 2];
color("#15803d") linear_extrude(1) translate([LG[0], LG[1] + 34]) square([2.4, 2.4]);
lbl([LG[0] + 3.4, LG[1] + 34.4], "自由な空間　X8.6 × Y13.5 × Z11.0");
color("#000000") linear_extrude(1) translate([LG[0], LG[1] + 30.6]) square([2.4, 2.4]);
lbl([LG[0] + 3.4, LG[1] + 31.0], "micro-B の口の軸");
for (i = [0 : len(NAMES) - 1]) {
    y = LG[1] + 26.4 - i * 2.9;
    color(COLS[i]) linear_extrude(1) translate([LG[0], y]) square([2.4, 2.4]);
    lbl([LG[0] + 3.4, y + 0.4], NAMES[i]);
}
dim([0, -6], [10, -6]);  lbl([11, -6.8], "10 mm", 1.7);
lbl([0, -11], "アダプタ本体は描いていない（L 字の曲がる向きが商品図から決まらないため）", 1.6);
