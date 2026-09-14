// 🔒 提案 B の Z の積みを、絵にしただけの一時ファイル。**本体（_v6_portrait.scad）には触っていない。**
//   数字は 2026-09-13 に 4 スレッドで決めた値。⚠ ユーザー未承認。
//   機構の _tmp_gearbox_proposal.scad と同じ扱い（提案ファイル）。
$fn = 48;
W = 48;   // 幅
// [下端, 高さ, 色, 名前]
BANDS = [
  [ 0.00, 2.00, "#6e7276", "背面の板 2.00（別部品・ねじ 10 本）"],
  [ 2.00, 5.50, "#ef9f27", "電池の部屋 5.50（電池 5.0 ＋ 膨らみ代 0.5 ⚠仮定）"],
  [ 7.50, 0.80, "#8a8f94", "部屋の天井 0.80（別部品・中継基板が押さえる）"],
  [ 8.30, 1.60, "#d85a30", "中継基板 1.60"],
  [ 9.90, 5.39, "#9a4a2a", "隙間 D 5.39（板の上 〜 ReSpeaker）"],
  [15.29, 1.85, "#2e6b3f", "ReSpeaker 1.85"],
  [17.14, 4.45, "#b0b4b8", "ギアボックスの帯 4.45（機構の要求）"],
  [21.59, 2.00, "#55585c", "前の壁 2.00"],
];
// 🔴 薄い帯はラベルが重なるので、右側に**等間隔**で並べて引き出し線でつなぐ
PITCH = 2.9;
module band(b, i) {
  ly = 1.0 + i * PITCH;                       // ラベルの高さ（等間隔）
  by = b[0] + b[1]/2;                         // 帯の中心
  color(b[2]) translate([0, 0, b[0]]) cube([W, 1, b[1]]);
  color("#666") hull() {                      // 引き出し線
    translate([W + 0.5, 0.4, by - 0.06]) cube([0.12, 0.2, 0.12]);
    translate([W + 5.0, 0.4, ly + 0.5]) cube([0.12, 0.2, 0.12]);
  }
  color("#222") translate([W + 5.6, 0, ly]) rotate([90,0,0])
    linear_extrude(0.2) text(b[3], size = 1.5, font = "Meiryo");
  color("#222") translate([-6.5, 0, by - 0.7]) rotate([90,0,0])
    linear_extrude(0.2) text(str(b[0]), size = 1.4, font = "Meiryo");
}
for (i = [0 : len(BANDS) - 1]) band(BANDS[i], i);
// 電池の部屋の壁（X 方向の断面に見える分）
color("#8a8f94") translate([ 8.0, 0, 2.0]) cube([0.6, 1, 5.5]);
color("#8a8f94") translate([39.4, 0, 2.0]) cube([0.6, 1, 5.5]);
color("#222") translate([-6.5, 0, 25.6]) rotate([90,0,0]) linear_extrude(0.2)
  text("v6 案B の積み（幅 48・厚み 23.59）⚠ 未承認・本体未反映", size = 1.6, font = "Meiryo");
color("#222") translate([-6.5, 0, -3.2]) rotate([90,0,0]) linear_extrude(0.2)
  text("SPLIT_Z = 2.00 で割る ⇒ 柱 10 本が切れない", size = 1.4, font = "Meiryo");
